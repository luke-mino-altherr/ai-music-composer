"""Main composer module that interfaces with LLMs to generate MIDI commands."""

import json
from typing import List, Optional

from langchain.callbacks.base import BaseCallbackHandler
from langchain.chains import LLMChain
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from ..config import get_config
from ..logging_config import get_logger
from .context import ContextBuilder, PromptAugmenter
from .memory import ComposerMemory, ConversationTurn
from .midi_tools import MIDIToolHandler, MIDIToolResult
from .models import (
    CreateInstrumentCommand,
    MIDICommand,
    PlayNoteCommand,
    PlaySequenceCommand,
    RemoveInstrumentCommand,
    StopAllCommand,
    StopSequenceCommand,
)

logger = get_logger(__name__)


def validate_midi_command(raw_cmd: dict) -> MIDICommand:
    """Validate and parse a raw command dictionary into a MIDICommand.

    Args:
        raw_cmd: Dictionary containing command data

    Returns:
        Validated MIDICommand instance

    Raises:
        ValidationError: If command is invalid
    """
    command_type = raw_cmd.get("type")

    command_classes = {
        "play_note": PlayNoteCommand,
        "play_sequence": PlaySequenceCommand,
        "create_instrument": CreateInstrumentCommand,
        "remove_instrument": RemoveInstrumentCommand,
        "stop_sequence": StopSequenceCommand,
        "stop_all": StopAllCommand,
    }

    if command_type not in command_classes:
        raise ValidationError(f"Unknown command type: {command_type}")

    command_class = command_classes[command_type]
    return command_class.model_validate(raw_cmd)


DEFAULT_SYSTEM_PROMPT = """You are a music composition assistant that generates MIDI commands. Your role is to translate natural language music requests into specific MIDI commands.

You can use the following commands:
1. play_note: Play a single note on an instrument
   {{
     "type": "play_note",
     "instrument": "instrument_name",
     "note": 60-72,  # C4 to C5
     "velocity": 0-127,  # Optional, default 100
     "duration": float  # Optional, default 0.5 beats
   }}

2. play'
_sequence: Play a sequence of notes
   {{
     "type": "play_sequence",
     "notes": [
       {{
         "pitch": 60-72,
         "velocity": 0-127,  # Optional
         "duration": float,  # Optional
         "channel": 0-15     # Optional
       }}
     ],
     "instrument": "instrument_name",  # Optional
     "loop": boolean  # Optional, default false
   }}

3. create_instrument: Create a new instrument
   {{
     "type": "create_instrument",
     "name": "instrument_name",
     "channel": 0-15,
     "velocity": 0-127,  # Optional
     "transpose": -127 to 127  # Optional
   }}

4. remove_instrument: Remove an instrument
   {{
     "type": "remove_instrument",
     "name": "instrument_name"
   }}

5. stop_sequence: Stop a specific sequence
   {{
     "type": "stop_sequence",
     "sequence_id": int
   }}

6. stop_all: Stop all sequences and instruments
   {{
     "type": "stop_all"
   }}

Respond with valid JSON commands that match these schemas. You can send multiple commands in an array.
For musical notes, use MIDI note numbers (60 = middle C).

IMPORTANT: Return only raw JSON - no markdown formatting, no code blocks, no additional text.

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
        logger.info("Initializing LLMComposer")
        config = get_config()

        # Initialize components
        self.midi_tool_handler = midi_tool_handler
        self.memory = memory or ComposerMemory()
        self.context_builder = ContextBuilder(self.memory)
        self.prompt_augmenter = PromptAugmenter(self.context_builder)

        logger.debug("Memory and context systems initialized")

        # Configure LLM
        model_to_use = model_name or config.llm.model_name
        temp_to_use = temperature or config.llm.temperature

        logger.info(f"Configuring LLM: model={model_to_use}, temperature={temp_to_use}")

        self.llm = ChatOpenAI(
            model_name=model_to_use,
            temperature=temp_to_use,
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

        logger.info("LLMComposer initialization complete")

    def _extract_musical_intent(self, user_prompt: str) -> str:
        """Extract musical intent from user prompt."""
        logger.debug(f"Extracting musical intent from prompt: '{user_prompt[:50]}...'")
        prompt_lower = user_prompt.lower()

        # Basic intent classification
        if any(word in prompt_lower for word in ["create", "add", "make", "new"]):
            if any(
                word in prompt_lower
                for word in ["instrument", "piano", "bass", "drums"]
            ):
                intent = "create_instrument"
                logger.debug(f"Detected intent: {intent}")
                return intent
            elif any(
                word in prompt_lower
                for word in ["sequence", "melody", "chord", "scale"]
            ):
                intent = "create_sequence"
                logger.debug(f"Detected intent: {intent}")
                return intent
        elif any(word in prompt_lower for word in ["stop", "pause", "halt"]):
            intent = "stop_music"
            logger.debug(f"Detected intent: {intent}")
            return intent
        elif any(word in prompt_lower for word in ["play", "start", "begin"]):
            intent = "play_music"
            logger.debug(f"Detected intent: {intent}")
            return intent
        elif any(
            word in prompt_lower for word in ["change", "modify", "adjust", "update"]
        ):
            intent = "modify_music"
            logger.debug(f"Detected intent: {intent}")
            return intent
        elif any(word in prompt_lower for word in ["faster", "slower", "tempo", "bpm"]):
            intent = "change_tempo"
            logger.debug(f"Detected intent: {intent}")
            return intent
        elif any(
            word in prompt_lower for word in ["louder", "softer", "volume", "velocity"]
        ):
            intent = "change_volume"
            logger.debug(f"Detected intent: {intent}")
            return intent

        intent = "general_musical_request"
        logger.debug(f"Detected intent: {intent}")
        return intent

    def _update_memory_from_results(
        self, commands: List[MIDICommand], results: List[MIDIToolResult]
    ):
        """Update memory based on executed commands and their results."""
        logger.debug(
            f"Updating memory from {len(commands)} commands and {len(results)} results"
        )
        from .memory import InstrumentMemory, SequenceMemory

        successful_updates = 0
        failed_updates = 0

        for command, result in zip(commands, results):
            if not result.success:
                failed_updates += 1
                logger.debug(
                    f"Skipping memory update for failed command: {getattr(command, 'type', 'unknown')}"
                )
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
                    logger.info(
                        f"Added instrument '{command.name}' to memory (channel {command.channel})"
                    )
                    successful_updates += 1

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
                    loop_status = (
                        "looping" if getattr(command, "loop", False) else "one-shot"
                    )
                    logger.info(
                        f"Added {loop_status} sequence #{sequence_id} to memory on instrument '{getattr(command, 'instrument', 'unknown')}'"
                    )
                    successful_updates += 1

                elif command.type == "remove_instrument":
                    self.memory.remove_instrument(command.name)
                    logger.info(f"Removed instrument '{command.name}' from memory")
                    successful_updates += 1

                elif command.type == "stop_sequence" and hasattr(
                    command, "sequence_id"
                ):
                    self.memory.remove_sequence(command.sequence_id)
                    logger.info(f"Removed sequence #{command.sequence_id} from memory")
                    successful_updates += 1

                elif command.type == "stop_all":
                    # Clear all sequences but keep instruments
                    num_sequences = len(self.memory.sequences)
                    for seq_id in list(self.memory.sequences.keys()):
                        self.memory.remove_sequence(seq_id)
                    logger.info(f"Cleared all {num_sequences} sequences from memory")
                    successful_updates += 1

        # Update musical context based on current state
        self.memory.infer_musical_context()

        logger.debug(
            f"Memory update complete: {successful_updates} successful, {failed_updates} failed"
        )

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

    async def _get_llm_response(self, input_text: str) -> dict:
        """Get response from LLM with error handling.

        Args:
            input_text: User input text

        Returns:
            LLM response dictionary

        Raises:
            Exception: If LLM request fails
        """
        # Augment prompt with context from memory
        logger.debug("Augmenting prompt with contextual information")
        augmented_prompt = self.prompt_augmenter.augment_prompt(input_text)
        logger.debug(f"Augmented prompt length: {len(augmented_prompt)} characters")

        # Generate response from LLM
        logger.info(f"Sending request to LLM (model: {self.llm.model_name})")
        response = await self.chain.ainvoke({"input": augmented_prompt})
        logger.debug(
            f"LLM response received: {len(response.get('text', ''))} characters"
        )
        return response

    def _parse_llm_response(self, response_text: str) -> List[dict]:
        """Parse LLM response and extract commands.

        Args:
            response_text: Raw response text from LLM

        Returns:
            List of command dictionaries

        Raises:
            json.JSONDecodeError: If JSON parsing fails
        """
        logger.debug("Parsing LLM response as JSON")
        cleaned_text = response_text.strip()

        # Handle markdown-wrapped JSON
        if cleaned_text.startswith("```json") and cleaned_text.endswith("```"):
            logger.debug("Detected markdown-wrapped JSON, extracting content")
            cleaned_text = cleaned_text[7:-3].strip()
        elif cleaned_text.startswith("```") and cleaned_text.endswith("```"):
            logger.debug("Detected markdown code block, extracting content")
            cleaned_text = cleaned_text[3:-3].strip()

        raw_commands = json.loads(cleaned_text)
        if not isinstance(raw_commands, list):
            raw_commands = [raw_commands]

        logger.info(f"Parsed {len(raw_commands)} commands from LLM response")
        return raw_commands

    def _execute_commands(self, raw_commands: List[dict]) -> tuple:
        """Execute validated MIDI commands.

        Args:
            raw_commands: List of raw command dictionaries

        Returns:
            Tuple of (results, executed_commands, validation_errors)
        """
        results = []
        executed_commands = []
        validation_errors = 0

        for i, raw_cmd in enumerate(raw_commands):
            try:
                logger.debug(
                    f"Validating command {i+1}: {raw_cmd.get('type', 'unknown type')}"
                )
                command = validate_midi_command(raw_cmd)

                logger.debug(f"Executing command {i+1}: {command.type}")
                result = self.midi_tool_handler.execute_command(command)

                if result.success:
                    logger.info(
                        f"Command {i+1} executed successfully: {result.message}"
                    )
                else:
                    logger.warning(f"Command {i+1} execution failed: {result.message}")

                results.append(result)
                executed_commands.append(command)
            except ValidationError as e:
                validation_errors += 1
                logger.error(f"Command {i+1} validation failed: {str(e)}")
                logger.debug(f"Invalid command data: {raw_cmd}")
                results.append(
                    MIDIToolResult(
                        success=False,
                        message=f"Invalid command format: {str(e)}",
                        data={"raw_command": raw_cmd},
                    )
                )

        return results, executed_commands, validation_errors

    async def generate_and_execute(self, input_text: str) -> List[MIDIToolResult]:
        """Generate and execute MIDI commands based on the input text.

        Args:
            input_text: The text description of the desired musical output

        Returns:
            List of MIDIToolResults from executing the commands
        """
        from datetime import datetime

        logger.info(
            f"Processing user input: '{input_text[:100]}{'...' if len(input_text) > 100 else ''}'"
        )

        # Extract musical intent
        musical_intent = self._extract_musical_intent(input_text)

        # Get LLM response
        try:
            response = await self._get_llm_response(input_text)
        except Exception as e:
            logger.error(f"LLM request failed: {e}")
            return [
                MIDIToolResult(
                    success=False,
                    message=f"LLM request failed: {str(e)}",
                    data={"input_text": input_text},
                )
            ]

        # Parse and execute commands
        try:
            raw_commands = self._parse_llm_response(response["text"])
            results, executed_commands, validation_errors = self._execute_commands(
                raw_commands
            )

            # Log execution summary
            successful_commands = sum(1 for r in results if r.success)
            failed_commands = len(results) - successful_commands
            logger.info(
                f"Command execution summary: {successful_commands} successful, {failed_commands} failed, {validation_errors} validation errors"
            )

            # Record interaction in memory
            logger.debug("Recording conversation turn in memory")
            conversation_turn = ConversationTurn(
                timestamp=datetime.now(),
                user_prompt=input_text,
                llm_response=response["text"],
                commands_executed=executed_commands,
                musical_intent=musical_intent,
                referenced_elements=self.memory.find_referenced_elements(input_text),
            )
            self.memory.add_conversation_turn(conversation_turn)

            # Update memory based on successful commands
            self._update_memory_from_results(executed_commands, results)

            return results

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {str(e)}")
            logger.debug(f"Invalid JSON response: {response['text']}")
            return [
                MIDIToolResult(
                    success=False,
                    message="Failed to parse LLM response as JSON",
                    data={"raw_response": response["text"], "json_error": str(e)},
                )
            ]

    def update_prompt(self, system_message: str, user_template: str) -> None:
        """Update the prompt template used by the composer.

        Args:
            system_message: The new system message
            user_template: The new user message template
        """
        logger.info("Updating prompt template")
        logger.debug(f"New system message length: {len(system_message)} characters")
        logger.debug(f"New user template: {user_template}")

        self.prompt = ChatPromptTemplate.from_messages(
            [("system", system_message), ("user", user_template)]
        )
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt)

        logger.info("Prompt template updated successfully")
