"""Main composer module that interfaces with LLMs to generate MIDI commands."""

import json
from typing import List, Optional

from dotenv import load_dotenv
from langchain.callbacks.base import BaseCallbackHandler
from langchain.chains import LLMChain
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import ValidationError

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
        model_name: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
        callback_handler: Optional[BaseCallbackHandler] = None,
    ):
        """Initialize the LLM composer.

        Args:
            midi_tool_handler: Handler for executing MIDI commands
            model_name: The name of the OpenAI model to use
            temperature: The temperature for generation (0.0 to 1.0)
            callback_handler: Optional callback handler for LangChain
        """
        load_dotenv()  # Load environment variables from .env file

        self.midi_tool_handler = midi_tool_handler
        self.llm = ChatOpenAI(
            model_name=model_name,
            temperature=temperature,
            callbacks=[callback_handler] if callback_handler else None,
        )

        # Initialize default prompt template
        self.prompt = ChatPromptTemplate.from_messages(
            [("system", DEFAULT_SYSTEM_PROMPT), ("user", "{input}")]
        )

        self.chain = LLMChain(llm=self.llm, prompt=self.prompt)

    async def generate_and_execute(self, input_text: str) -> List[MIDIToolResult]:
        """Generate and execute MIDI commands based on the input text.

        Args:
            input_text: The text description of the desired musical output

        Returns:
            List of MIDIToolResults from executing the commands
        """
        response = await self.chain.ainvoke({"input": input_text})
        try:
            # Parse the response text as JSON
            raw_commands = json.loads(response["text"])
            if not isinstance(raw_commands, list):
                raw_commands = [raw_commands]

            # Validate and convert each command
            results = []
            for raw_cmd in raw_commands:
                try:
                    # Validate command against our models
                    command = MIDICommand.model_validate(raw_cmd)
                    result = self.midi_tool_handler.execute_command(command)
                    results.append(result)
                except ValidationError as e:
                    results.append(
                        MIDIToolResult(
                            success=False,
                            message=f"Invalid command format: {str(e)}",
                            data={"raw_command": raw_cmd},
                        )
                    )

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
