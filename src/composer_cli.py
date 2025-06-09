#!/usr/bin/env python3

"""Command-line interface for the AI Music Composer."""

import click
from rich.console import Console
from rich.prompt import Prompt
from typing import List, Optional
import threading
from composer.midi_controller import MIDIController

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
    [yellow]sequence <note_sequence>[/yellow] - Play a sequence of notes in a loop
    [yellow]stop[/yellow] - Stop the currently playing sequence
    [yellow]help[/yellow] - Show this help message
    [yellow]exit[/yellow] - Exit the program

[bold]Sequence Format:[/bold]
    note,velocity,channel,duration;note,velocity,channel,duration;...
    Example: 60,100,0,0.5;67,100,0,0.5;72,100,0,0.5
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


def handle_sequence_command(controller: MIDIController, parts: List[str]) -> None:
    """Handle the sequence command.

    Args:
        controller: The MIDI controller instance.
        parts: Command parts (sequence string).
    """
    if len(parts) < 2:
        console.print("[red]Usage: sequence <note_sequence>[/red]")
        console.print("Example: sequence 60,100,0,0.5;67,100,0,0.5;72,100,0,0.5")
        return

    try:
        # Stop any existing sequence
        controller.stop_sequence()

        # Parse and start new sequence
        sequence_str = " ".join(parts[1:])
        sequence = parse_sequence(sequence_str)
        controller.is_playing = True
        # Start sequence in a background thread
        sequence_thread = threading.Thread(
            target=controller.play_sequence, args=(sequence,), daemon=True
        )
        sequence_thread.start()
        console.print("[green]Started playing sequence[/green]")
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


def handle_command(
    controller: MIDIController, command: str, parts: List[str]
) -> Optional[bool]:
    """Handle a single command.

    Args:
        controller: The MIDI controller instance.
        command: The full command string.
        parts: The command split into parts.

    Returns:
        True if should exit, None otherwise.
    """
    if command == "exit":
        controller.stop_sequence()
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
        handle_sequence_command(controller, parts)
    elif command == "stop":
        controller.stop_sequence()
        console.print("[yellow]Stopped sequence playback[/yellow]")
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

    while True:
        try:
            command = Prompt.ask("\n[bold green]composer>[/bold green]").strip().lower()
            parts = command.split()

            if not parts:
                continue

            if handle_command(controller, parts[0], parts):
                break

        except KeyboardInterrupt:
            console.print("\n[yellow]Use 'exit' to quit[/yellow]")
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")

    controller.close()
    console.print("[blue]Goodbye![/blue]")


if __name__ == "__main__":
    main()
