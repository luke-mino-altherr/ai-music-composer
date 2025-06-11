# AI Music Composer

An intelligent music composition system that generates original musical pieces using artificial intelligence, with a MIDI-based command-line interface for controlling and playing the generated music.

## Installation

1. Make sure you have Python 3.8+ installed
2. Install Poetry (package manager) if you haven't already:
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

3. Install the project:
```bash
# Clone the repository
git clone https://github.com/yourusername/ai-music-composer.git
cd ai-music-composer

# Install dependencies
poetry install
```

## Usage

After installation, you can run the CLI in one of two ways:

1. Using Poetry:
```bash
poetry run composer
```

2. Or directly if you're in the project directory:
```bash
python src/composer_cli.py
```

### Available Commands

- `list` - Shows all available MIDI output ports
- `connect <port_number>` - Connect to a specific MIDI port
- `note <note> <velocity> [channel] [duration]` - Send a single MIDI note
  - `note`: 0-127 (MIDI note number)
  - `velocity`: 0-127 (note velocity/volume)
  - `channel`: 0-15 (optional, defaults to 0)
  - `duration`: float (optional, defaults to 0.5 seconds)
- `sequence <note_sequence>` - Schedule a sequence of notes with musical timing
  - Format: `note,velocity,channel,duration;note,velocity,channel,duration;...`
  - Duration is in beats (musical timing)
  - Example: `60,100,0,1;67,100,0,1;72,100,0,2`
- `stop` - Stop all playing sequences
- `help` - Show available commands
- `exit` - Exit the program

### Example Usage

```bash
# List available MIDI ports
composer> list

# Connect to port 0
composer> connect 0

# Send a single note (middle C, full velocity)
composer> note 60 127

# Play a sequence (C-E-G chord progression)
composer> sequence 60,100,0,1;64,100,0,1;67,100,0,1

# Stop all sequences
composer> stop
```

## Notes

- Make sure your MIDI device is connected before starting the program
- The program will show available MIDI ports when you use the `list` command
- You must connect to a port using the `connect` command before sending notes
- Sequence durations are specified in beats for precise musical timing
- Multiple sequences can be scheduled and will play simultaneously
- Use `stop` to clear all playing sequences
- Use Ctrl+C or type `exit` to quit the program

## Project Structure
```
ai-music-composer/
├── src/                    # Source code
│   ├── __init__.py
│   ├── composer/          # AI composition modules
│   │   ├── midi_controller.py  # MIDI output handling
│   │   ├── sequencer.py       # Musical sequence scheduling
│   │   └── transport.py       # Precise timing control
│   └── composer_cli.py    # Main CLI interface
├── tests/                 # Test files
│   └── __init__.py
├── data/                  # Training data and resources
├── models/                # Trained AI models
├── pyproject.toml         # Project configuration and dependencies
└── README.md             # Project documentation
```

## License
MIT License

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request.
