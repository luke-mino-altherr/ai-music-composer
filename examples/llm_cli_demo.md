# LLM CLI Demo

## Starting the LLM CLI

```bash
# Using Poetry
poetry run llm-composer

# Or after poetry install
llm-composer

# Or directly
python src/llm_cli.py
```

## Example Session

```
🎵 AI Music Composer - LLM CLI
Initializing...
✓ Systems initialized successfully

Type /help for commands or just describe what music you want!

System Status: ✗ No MIDI output connected | ♪ BPM: 120.0 | ⏸ Transport stopped | 🎹 No instruments created | 🎵 No active sequences

🎵> /connect
Available MIDI ports:
0: IAC Driver Bus 1
1: Logic Pro Virtual Out

🎵> /connect 0
✓ Connected to MIDI port 0

🎵> Create a piano instrument and play a C major chord
🎵 Composing...
✓ Command 1: Created instrument 'piano' on channel 0
✓ Command 2: Playing C major chord on piano

🎵> /status
System Status: ✓ MIDI output connected | ♪ BPM: 120.0 | ▶ Transport running | 🎹 Instruments: piano | 🎵 1 active sequences

🎵> Now create a bass line that loops in the same key
🎵 Composing...
✓ Command 1: Created instrument 'bass' on channel 1
✓ Command 2: Playing looping bass line in C major

🎵> Make it faster and add drums
🎵 Composing...
✓ Command 1: Set BPM to 140
✓ Command 2: Created instrument 'drums' on channel 9
✓ Command 3: Playing drum pattern

🎵> /sequences
Active Sequences:
┌────┬───────┬─────────┬───────────┐
│ ID │ Notes │ Looping │ Iteration │
├────┼───────┼─────────┼───────────┤
│ 1  │ 3     │ No      │ 0         │
│ 2  │ 8     │ Yes     │ 15        │
│ 3  │ 16    │ Yes     │ 8         │
└────┴───────┴─────────┴───────────┘

🎵> Stop everything and start a jazz ballad
🎵 Composing...
✓ Command 1: Stopped all instruments and sequences
✓ Command 2: Set BPM to 80
✓ Command 3: Created instrument 'jazz_piano' on channel 0
✓ Command 4: Playing jazz ballad chord progression

🎵> /quit
Cleaning up...
Goodbye!
```

## Natural Language Examples

The LLM CLI understands natural language commands like:

### Instrument Creation
- "Create a piano instrument"
- "Add a bass guitar on channel 2"
- "Make a drum kit with higher velocity"

### Playing Music
- "Play a C major scale ascending"
- "Create a looping bass line in G minor"
- "Play a jazz chord progression"
- "Add a drum pattern with kick on 1 and 3"

### Modifications
- "Make it faster"
- "Change to minor key"
- "Make the bass louder"
- "Add more swing to the rhythm"

### Control
- "Stop the drums but keep the piano"
- "What instruments are currently playing?"
- "Pause everything"
- "Start over with a new song"

## CLI Commands

- `/help` - Show help
- `/status` - Show system status
- `/connect` - List MIDI ports
- `/connect N` - Connect to port N
- `/instruments` - Show all instruments
- `/sequences` - Show active sequences
- `/stop` - Stop all music
- `/quit` - Exit

## Tips

1. **Be specific**: "Create a piano" vs "Create a bright electric piano"
2. **Ask for status**: "What's currently playing?"
3. **Request changes**: "Make it louder" or "Change tempo"
4. **Use musical terms**: The LLM understands scales, chords, rhythms
5. **Build incrementally**: Start simple and add complexity
