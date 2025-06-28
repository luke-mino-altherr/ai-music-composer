"""Main composer module that interfaces with LLMs to generate MIDI commands."""

import json
from typing import List, Optional

from langchain.callbacks.base import BaseCallbackHandler
from langchain.chains import LLMChain
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from ..config import get_config
from .context import ContextBuilder, PromptAugmenter
from .memory import ComposerMemory, ConversationTurn
from .midi_tools import MIDIToolHandler, MIDIToolResult
from .models import MIDICommand

DEFAULT_SYSTEM_PROMPT = """You are a music composition assistant that generates MIDI commands. Your role is to translate natural language music requests into specific MIDI commands.

You can use the following commands:
1. play_note: Play a single note on an instrument
   {
     "type": "play_note",
     "instrument": "instrument_name",
     "note": 60-72,  # C4 to C5
     "velocity": 0-127,  # Optional, default 100
     "duration": float  # Optional, default 0.5 beats
   }

2. play_sequence: Play a sequence of notes
   {
     "type": "play_sequence",
     "notes": [
       {
         "pitch": 60-72,
         "velocity": 0-127,  # Optional
         "duration": float,  # Optional
         "channel": 0-15     # Optional
       }
     ],
     "instrument": "instrument_name",  # Optional
     "loop": boolean  # Optional, default false
   }

3. create_instrument: Create a new instrument
   {
     "type": "create_instrument",
     "name": "instrument_name",
     "channel": 0-15,
     "velocity": 0-127,  # Optional
     "transpose": -127 to 127  # Optional
   }

4. remove_instrument: Remove an instrument
   {
     "type": "remove_instrument",
     "name": "instrument_name"
   }

5. stop_sequence: Stop a specific sequence
   {
     "type": "stop_sequence",
     "sequence_id": int
   }

6. stop_all: Stop all sequences and instruments
   {
     "type": "stop_all"
   }

Respond with valid JSON commands that match these schemas. You can send multiple commands in an array.
For musical notes, use MIDI note numbers (60 = middle C).

Common musical patterns:
- C major scale: [60, 62, 64, 65, 67, 69, 71, 72]
- C minor scale: [60, 62, 63, 65, 67, 68, 70, 72]
- C major chord: [60, 64, 67]
- C minor chord: [60, 63, 67]
"""


class LLMComposer:
    """A class that uses LLMs to generate MIDI composition commands."""

    def __init__(
        self,
        midi_tool_handler: MIDIToolHandler,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        callback_handler: Optional[BaseCallbackHandler] = None,
        memory: Optional[ComposerMemory] = None,
    ):
        """Initialize the LLM composer.

        Args:
            midi_tool_handler: Handler for executing MIDI commands
            model_name: The name of the OpenAI model to use (defaults to config)
            temperature: The temperature for generation (defaults to config)
            callback_handler: Optional callback handler for LangChain
            memory: Optional memory system (creates new one if None)
        """
        config = get_config()

        self.midi_tool_handler = midi_tool_handler
        self.memory = memory or ComposerMemory()
        self.context_builder = ContextBuilder(self.memory)
        self.prompt_augmenter = PromptAugmenter(self.context_builder)

        self.llm = ChatOpenAI(
            model_name=model_name or config.llm.model_name,
            temperature=temperature or config.llm.temperature,
            openai_api_key=config.llm.openai_api_key,
            openai_organization=config.llm.openai_organization_id,
            max_tokens=config.llm.max_tokens,
            request_timeout=config.llm.timeout,
            callbacks=[callback_handler] if callback_handler else None,
        )

        # Initialize default prompt template
        self.prompt = ChatPromptTemplate.from_messages(
            [("system", DEFAULT_SYSTEM_PROMPT), ("user", "{input}")]
        )

        self.chain = LLMChain(llm=self.llm, prompt=self.prompt)

    def _extract_musical_intent(self, user_prompt: str) -> str:
        """Extract musical intent from user prompt."""
        prompt_lower = user_prompt.lower()

        # Basic intent classification
        if any(word in prompt_lower for word in ["create", "add", "make", "new"]):
            if any(
                word in prompt_lower
                for word in ["instrument", "piano", "bass", "drums"]
            ):
                return "create_instrument"
            elif any(
                word in prompt_lower
                for word in ["sequence", "melody", "chord", "scale"]
            ):
                return "create_sequence"
        elif any(word in prompt_lower for word in ["stop", "pause", "halt"]):
            return "stop_music"
        elif any(word in prompt_lower for word in ["play", "start", "begin"]):
            return "play_music"
        elif any(
            word in prompt_lower for word in ["change", "modify", "adjust", "update"]
        ):
            return "modify_music"
        elif any(word in prompt_lower for word in ["faster", "slower", "tempo", "bpm"]):
            return "change_tempo"
        elif any(
            word in prompt_lower for word in ["louder", "softer", "volume", "velocity"]
        ):
            return "change_volume"

        return "general_musical_request"

    def _update_memory_from_results(
        self, commands: List[MIDICommand], results: List[MIDIToolResult]
    ):
        """Update memory based on executed commands and their results."""
        from .memory import InstrumentMemory, SequenceMemory

        for command, result in zip(commands, results):
            if not result.success:
                continue

            # Handle different command types
            if hasattr(command, "type"):
                if command.type == "create_instrument":
                    # Add instrument to memory
                    instrument_memory = InstrumentMemory(
                        name=command.name,
                        channel=command.channel,
                        instrument_type=self._infer_instrument_type(command.name),
                        velocity=getattr(command, "velocity", 100),
                        transpose=getattr(command, "transpose", 0),
                        musical_role=self._infer_musical_role(command.name),
                    )
                    self.memory.add_instrument(instrument_memory)

                elif (
                    command.type == "play_sequence"
                    and result.data
                    and "sequence_id" in result.data
                ):
                    # Add sequence to memory
                    sequence_id = result.data["sequence_id"]
                    sequence_memory = SequenceMemory(
                        id=sequence_id,
                        instrument_name=getattr(command, "instrument", "unknown"),
                        notes=getattr(command, "notes", []),
                        is_looping=getattr(command, "loop", False),
                        musical_purpose=self._infer_sequence_purpose(command),
                        key_signature=self.memory.musical_context.current_key,
                    )
                    self.memory.add_sequence(sequence_memory)

                elif command.type == "remove_instrument":
                    self.memory.remove_instrument(command.name)

                elif command.type == "stop_sequence" and hasattr(
                    command, "sequence_id"
                ):
                    self.memory.remove_sequence(command.sequence_id)

                elif command.type == "stop_all":
                    # Clear all sequences but keep instruments
                    for seq_id in list(self.memory.sequences.keys()):
                        self.memory.remove_sequence(seq_id)

        # Update musical context based on current state
        self.memory.infer_musical_context()

    def _infer_instrument_type(self, name: str) -> str:
        """Infer instrument type from name."""
        name_lower = name.lower()

        if any(word in name_lower for word in ["piano", "keyboard", "keys"]):
            return "piano"
        elif any(word in name_lower for word in ["bass", "low"]):
            return "bass"
        elif any(word in name_lower for word in ["drum", "percussion", "beat"]):
            return "drums"
        elif any(word in name_lower for word in ["guitar", "string"]):
            return "guitar"
        elif any(word in name_lower for word in ["synth", "pad", "lead"]):
            return "synthesizer"
        else:
            return "unknown"

    def _infer_musical_role(self, name: str):
        """Infer musical role from instrument name."""
        from .memory import MusicalRole

        name_lower = name.lower()

        if any(word in name_lower for word in ["bass", "low"]):
            return MusicalRole.BASS
        elif any(
            word in name_lower for word in ["drum", "percussion", "beat", "rhythm"]
        ):
            return MusicalRole.RHYTHM
        elif any(word in name_lower for word in ["lead", "solo"]):
            return MusicalRole.LEAD
        elif any(word in name_lower for word in ["pad", "string", "choir"]):
            return MusicalRole.PAD
        elif any(word in name_lower for word in ["harmony", "chord"]):
            return MusicalRole.HARMONY
        else:
            return MusicalRole.MELODY

    def _infer_sequence_purpose(self, command) -> str:
        """Infer sequence purpose from command."""
        if hasattr(command, "instrument"):
            instrument_name = command.instrument.lower()
            if any(word in instrument_name for word in ["bass"]):
                return "bassline"
            elif any(word in instrument_name for word in ["drum", "percussion"]):
                return "drums"
            elif any(word in instrument_name for word in ["chord", "harmony"]):
                return "chord_progression"

        # Default to melody
        return "melody"

    async def generate_and_execute(self, input_text: str) -> List[MIDIToolResult]:
        """Generate and execute MIDI commands based on the input text.

        Args:
            input_text: The text description of the desired musical output

        Returns:
            List of MIDIToolResults from executing the commands
        """
        from datetime import datetime

        # Augment prompt with context from memory
        augmented_prompt = self.prompt_augmenter.augment_prompt(input_text)

        # Generate response from LLM
        response = await self.chain.ainvoke({"input": augmented_prompt})

        try:
            # Parse the response text as JSON
            raw_commands = json.loads(response["text"])
            if not isinstance(raw_commands, list):
                raw_commands = [raw_commands]

            # Validate and convert each command
            results = []
            executed_commands = []

            for raw_cmd in raw_commands:
                try:
                    # Validate command against our models
                    command = MIDICommand.model_validate(raw_cmd)
                    result = self.midi_tool_handler.execute_command(command)
                    results.append(result)
                    executed_commands.append(command)
                except ValidationError as e:
                    results.append(
                        MIDIToolResult(
                            success=False,
                            message=f"Invalid command format: {str(e)}",
                            data={"raw_command": raw_cmd},
                        )
                    )

            # Record interaction in memory
            conversation_turn = ConversationTurn(
                timestamp=datetime.now(),
                user_prompt=input_text,
                llm_response=response["text"],
                commands_executed=executed_commands,
                musical_intent=self._extract_musical_intent(input_text),
                referenced_elements=self.memory.find_referenced_elements(input_text),
            )
            self.memory.add_conversation_turn(conversation_turn)

            # Update memory based on successful commands
            self._update_memory_from_results(executed_commands, results)

            return results

        except json.JSONDecodeError:
            return [
                MIDIToolResult(
                    success=False,
                    message="Failed to parse LLM response as JSON",
                    data={"raw_response": response["text"]},
                )
            ]

    def update_prompt(self, system_message: str, user_template: str) -> None:
        """Update the prompt template used by the composer.

        Args:
            system_message: The new system message
            user_template: The new user message template
        """
        self.prompt = ChatPromptTemplate.from_messages(
            [("system", system_message), ("user", user_template)]
        )
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt)
