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
- `note <note> <velocity> [channel] [duration]` - Send a MIDI note
  - `note`: 0-127 (MIDI note number)
  - `velocity`: 0-127 (note velocity/volume)
  - `channel`: 0-15 (optional, defaults to 0)
  - `duration`: float (optional, defaults to 0.5 seconds)
- `help` - Show available commands
- `exit` - Exit the program

### Example Usage

```bash
# List available MIDI ports
composer> list

# Connect to port 0
composer> connect 0

# Send a note (middle C, full velocity)
composer> note 60 127

# Send a note on channel 1 with 0.8 second duration
composer> note 60 127 1 0.8
```

## Notes

- Make sure your MIDI device is connected before starting the program
- The program will show available MIDI ports when you use the `list` command
- You must connect to a port using the `connect` command before sending notes
- Use Ctrl+C or type `exit` to quit the program

## Project Structure
```
ai-music-composer/
├── src/                    # Source code
│   ├── __init__.py
│   ├── composer/          # AI composition modules
│   ├── database/          # Data storage and management
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
