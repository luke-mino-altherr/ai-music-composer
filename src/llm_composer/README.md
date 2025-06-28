# LLM Composer Module

This module provides an interface between language models and MIDI generation, allowing for natural language control of music composition.

## Setup

1. Install the required dependencies using Poetry:
```bash
poetry install
```

2. Create a `.env` file in the project root with your OpenAI API key:
```
OPENAI_API_KEY=your_openai_api_key_here
```

## Usage

Here's a basic example of how to use the LLMComposer with the MIDI system:

```python
from midi_generator.midi_controller import MIDIController
from midi_generator.transport import PreciseTransport
from midi_generator.sequencer import MIDISequencer
from midi_generator import MIDIControllerAdapter, SequencerAdapter, InstrumentManager
from llm_composer import LLMComposer
from llm_composer.midi_tools import MIDIToolHandler

# Initialize MIDI system
controller = MIDIController()
transport = PreciseTransport(initial_bpm=120.0)
sequencer = MIDISequencer(controller, transport)

# Create adapters and managers
note_player = MIDIControllerAdapter(controller)
sequence_player = SequencerAdapter(sequencer)
instrument_manager = InstrumentManager(note_player, sequence_player)

# Initialize the MIDI tool handler
midi_tool_handler = MIDIToolHandler(sequencer, instrument_manager)

# Initialize the composer
composer = LLMComposer(
    midi_tool_handler=midi_tool_handler,
    model_name="gpt-3.5-turbo",
    temperature=0.7
)

# Connect to MIDI output
controller.connect_port(0)  # Connect to first available port
transport.start()  # Start the transport

# Generate and execute MIDI commands
async def compose_music():
    # Create a piano instrument
    results = await composer.generate_and_execute(
        "Create a piano instrument on channel 0"
    )
    for result in results:
        print(result.message)

    # Play a melody
    results = await composer.generate_and_execute(
        "Play a C major scale on the piano, ascending and descending"
    )
    for result in results:
        print(result.message)

# Clean up when done
transport.stop()
controller.close()
```

## Command Types

The LLM can generate the following types of MIDI commands:

1. `play_note`: Play a single note on an instrument
2. `play_sequence`: Play a sequence of notes (optionally looped)
3. `create_instrument`: Create a new instrument
4. `remove_instrument`: Remove an instrument
5. `stop_sequence`: Stop a specific sequence
6. `stop_all`: Stop all sequences and instruments

Each command returns a `MIDIToolResult` containing:
- `success`: Boolean indicating if the command succeeded
- `message`: Human-readable status message
- `data`: Optional dictionary with command-specific data

## Natural Language Examples

The composer understands natural language commands like:

- "Create a piano instrument on channel 0"
- "Play a C major scale on the piano"
- "Create a looping bass line in G minor"
- "Add a drum pattern with kick on beats 1 and 3, snare on 2 and 4"
- "Stop all music"
- "Remove the piano instrument"

## Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `OPENAI_ORGANIZATION_ID`: Your OpenAI organization ID (optional)

## Features

- Natural language to MIDI command translation
- Integration with MIDI sequencer and instruments
- Support for notes, sequences, and instruments
- Asynchronous command generation and execution
- Customizable prompt templates
- Temperature control for creativity
- Callback support for monitoring and logging
- Integration with LangChain for robust LLM interactions
