#!/usr/bin/env python3

"""Command-line interface for the AI Music Composer."""

import os
import sys
import click
from rich.console import Console
from rich.prompt import Prompt
from typing import List, Optional

# Add src directory to Python path when running directly
if __name__ == "__main__":
    src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, src_dir)

from composer.midi_controller import MIDIController
from composer.transport import PreciseTransport
from composer.sequencer import MIDISequencer

console = Console()


def parse_sequence(sequence_str: str) -> List[tuple]:
    """Parse a sequence string into a list of note tuples.

    Format: note,velocity,channel,duration;note,velocity,channel,duration;...

    Args:
        sequence_str: String containing semicolon-separated note definitions.

    Returns:
        List of tuples containing (note, velocity, channel, duration).

    Raises:
        ValueError: If the sequence format is invalid.
    """
    sequence = []
    notes = sequence_str.split(";")

    for note in notes:
        if not note.strip():
            continue
        parts = note.split(",")
        if len(parts) < 2:
            raise ValueError("Each note must have at least note and velocity values")

        note_num = int(parts[0])
        velocity = int(parts[1])
        channel = int(parts[2]) if len(parts) > 2 else 0
        duration = float(parts[3]) if len(parts) > 3 else 0.5

        if not (0 <= note_num <= 127 and 0 <= velocity <= 127 and 0 <= channel <= 15):
            raise ValueError("Invalid note parameters")

        sequence.append((note_num, velocity, channel, duration))

    return sequence


def print_help():
    """Print available commands."""
    help_text = """
[bold]Available Commands:[/bold]
    [yellow]list[/yellow] - List available MIDI ports
    [yellow]connect <port_number>[/yellow] - Connect to a specific MIDI port
    [yellow]note <note> <velocity> [channel] [duration][/yellow] - Send a MIDI note
    [yellow]sequence <note_sequence> [--loop][/yellow] - Schedule a sequence of notes
    [yellow]stoploop <sequence_id>[/yellow] - Stop a looping sequence
    [yellow]start[/yellow] - Start the transport
    [yellow]stop[/yellow] - Stop all playing sequences
    [yellow]help[/yellow] - Show this help message
    [yellow]exit[/yellow] - Exit the program

[bold]Sequence Format:[/bold]
    note,velocity,channel,duration;note,velocity,channel,duration;...
    Example: 60,100,0,0.5;67,100,0,0.5;72,100,0,0.5

[bold]Note:[/bold] Durations in sequences are in beats (musical timing)
    Add --loop flag to sequence command to make it loop indefinitely
    """
    console.print(help_text)


def handle_note_command(controller: MIDIController, parts: List[str]) -> None:
    """Handle the note command.

    Args:
        controller: The MIDI controller instance.
        parts: Command parts (note, velocity, optional channel and duration).
    """
    if len(parts) < 3:
        console.print("[red]Usage: note <note> <velocity> [channel] [duration][/red]")
        return

    try:
        note = int(parts[1])
        velocity = int(parts[2])
        channel = int(parts[3]) if len(parts) > 3 else 0
        duration = float(parts[4]) if len(parts) > 4 else 0.5

        if not (0 <= note <= 127 and 0 <= velocity <= 127 and 0 <= channel <= 15):
            raise ValueError

        controller.send_note(note, velocity, channel, duration)
    except ValueError:
        msg = "[red]Invalid params: Note and velocity must be 0-127, channel 0-15[/red]"
        console.print(msg)


def handle_sequence_command(sequencer: MIDISequencer, parts: List[str]) -> None:
    """Handle the sequence command.

    Args:
        sequencer: The MIDI sequencer instance.
        parts: Command parts (sequence string and optional --loop flag).
    """
    if len(parts) < 2:
        console.print("[red]Usage: sequence <note_sequence> [--loop][/red]")
        console.print("Example: sequence 60,100,0,0.5;67,100,0,0.5;72,100,0,0.5")
        return

    try:
        # Check for --loop flag
        loop = "--loop" in parts
        sequence_str = " ".join(p for p in parts[1:] if p != "--loop")
        sequence = parse_sequence(sequence_str)

        # Schedule the sequence with the sequencer
        sequence_id = sequencer.schedule_sequence(sequence, loop=loop)
        status = "looping" if loop else "scheduled"
        console.print(f"[green]Sequence {status} (ID: {sequence_id})[/green]")

    except ValueError as e:
        console.print(f"[red]Error in sequence format: {str(e)}[/red]")


def handle_connect_command(controller: MIDIController, parts: List[str]) -> None:
    """Handle the connect command.

    Args:
        controller: The MIDI controller instance.
        parts: Command parts (port number).
    """
    if len(parts) != 2:
        console.print("[red]Usage: connect <port_number>[/red]")
        return
    try:
        port_num = int(parts[1])
        controller.connect_port(port_num)
    except ValueError:
        console.print("[red]Port number must be an integer![/red]")


def handle_stoploop_command(sequencer: MIDISequencer, parts: List[str]) -> None:
    """Handle the stoploop command.

    Args:
        sequencer: The MIDI sequencer instance.
        parts: Command parts (sequence ID).
    """
    if len(parts) != 2:
        console.print("[red]Usage: stoploop <sequence_id>[/red]")
        return

    try:
        sequence_id = int(parts[1])
        sequencer.stop_loop(sequence_id)
        console.print(f"[green]Stopped looping sequence {sequence_id}[/green]")
    except ValueError:
        console.print("[red]Sequence ID must be a number[/red]")
    except KeyError:
        console.print(f"[red]No looping sequence found with ID {sequence_id}[/red]")


def handle_command(
    controller: MIDIController,
    sequencer: MIDISequencer,
    transport: PreciseTransport,
    command: str,
    parts: List[str],
) -> Optional[bool]:
    """Handle a single command.

    Args:
        controller: The MIDI controller instance.
        sequencer: The MIDI sequencer instance.
        transport: The PreciseTransport instance.
        command: The full command string.
        parts: The command split into parts.

    Returns:
        True if should exit, None otherwise.
    """
    if command == "exit":
        sequencer.clear_all_sequences()
        transport.stop()
        return True

    if command == "help":
        print_help()
    elif command == "list":
        controller.list_ports()
    elif command == "connect":
        handle_connect_command(controller, parts)
    elif command == "note":
        handle_note_command(controller, parts)
    elif command == "sequence":
        handle_sequence_command(sequencer, parts)
    elif command == "stoploop":
        handle_stoploop_command(sequencer, parts)
    elif command == "start":
        transport.start()
    elif command == "stop":
        sequencer.clear_all_sequences()
        sequencer.all_notes_off()
        console.print("[yellow]Stopped all sequences[/yellow]")
    else:
        console.print(f"[red]Unknown command: {command}[/red]")
        print_help()

    return None


@click.command()
def main():
    """AI Music Composer CLI for controlling MIDI output and playback."""
    console.print("[bold blue]AI Music Composer CLI[/bold blue]")
    console.print("Type 'help' for available commands")

    controller = MIDIController()
    transport = PreciseTransport(initial_bpm=120.0)  # Default 120 BPM
    sequencer = MIDISequencer(controller, transport)

    try:
        while True:
            try:
                command = (
                    Prompt.ask("\n[bold green]composer>[/bold green]").strip().lower()
                )
                parts = command.split()

                if not parts:
                    continue

                if handle_command(controller, sequencer, transport, parts[0], parts):
                    break

            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'exit' to quit[/yellow]")
            except Exception as e:
                console.print(f"[red]Error: {str(e)}[/red]")
    finally:
        # Ensure proper cleanup even if an exception occurs
        try:
            sequencer.clear_all_sequences()
            transport.stop()
        except Exception as e:
            console.print(f"[red]Error during cleanup: {str(e)}[/red]")

        controller.close()
        console.print("[blue]Goodbye![/blue]")


if __name__ == "__main__":
    main()
