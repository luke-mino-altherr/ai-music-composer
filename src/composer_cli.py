#!/usr/bin/env python3

"""Command-line interface for the AI Music Composer."""

import os
import sys
from typing import List, Optional

import click
from rich.console import Console
from rich.prompt import Prompt

# Add src directory to Python path when running directly
if __name__ == "__main__":
    src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, src_dir)

from config import get_default_bpm
from logging_config import setup_logging
from midi_generator import InstrumentManager, MIDIControllerAdapter, SequencerAdapter
from midi_generator.midi_controller import MIDIController
from midi_generator.sequencer import MIDISequencer
from midi_generator.structures import Note, Sequence
from midi_generator.transport import PreciseTransport

console = Console()


def parse_sequence(sequence_str: str) -> Sequence:
    """Parse a sequence string into a Sequence object.

    Format: note,velocity,channel,duration;note,velocity,channel,duration;...

    Args:
        sequence_str: String containing semicolon-separated note definitions.

    Returns:
        Sequence object containing the parsed notes.

    Raises:
        ValueError: If the sequence format is invalid.
    """
    notes = []
    current_beat = 0.0
    note_parts = sequence_str.split(";")

    for note_str in note_parts:
        if not note_str.strip():
            continue
        parts = note_str.split(",")
        if len(parts) < 2:
            raise ValueError("Each note must have at least note and velocity values")

        note_num = int(parts[0])
        velocity = int(parts[1])
        channel = int(parts[2]) if len(parts) > 2 else 0
        duration = float(parts[3]) if len(parts) > 3 else 0.5

        if not (0 <= note_num <= 127 and 0 <= velocity <= 127 and 0 <= channel <= 15):
            raise ValueError("Invalid note parameters")

        note = Note(
            pitch=note_num,
            velocity=velocity,
            duration=duration,
            start_beat=current_beat,
            channel=channel,
        )
        notes.append(note)
        current_beat += duration

    return Sequence(notes=notes)


def print_help():
    """Print available commands."""
    help_text = """
[bold]Available Commands:[/bold]

[bold cyan]MIDI & Transport:[/bold cyan]
    [yellow]list[/yellow] - List available MIDI ports
    [yellow]connect <port_number>[/yellow] - Connect to a specific MIDI port
    [yellow]start[/yellow] - Start the transport
    [yellow]stop[/yellow] - Stop all playing sequences

[bold cyan]Direct MIDI:[/bold cyan]
    [yellow]note <note> <velocity> [channel] [duration][/yellow] - Send a MIDI note
    [yellow]sequence <note_sequence> [--loop][/yellow] - Schedule a sequence of notes
    [yellow]stoploop <sequence_id>[/yellow] - Stop a looping sequence

[bold cyan]Instruments:[/bold cyan]
    [yellow]instrument create <name> <channel> [velocity] [transpose][/yellow]
        - Create instrument
    [yellow]instrument list[/yellow] - List all instruments
    [yellow]instrument remove <name>[/yellow] - Remove an instrument
    [yellow]play <instrument_name> <note> [velocity] [duration][/yellow]
        - Play note on instrument
    [yellow]playseq <instrument_name> <note_sequence> [--loop][/yellow]
        - Play sequence on instrument
    [yellow]stopinst <instrument_name>[/yellow] - Stop all sequences on instrument

[bold cyan]General:[/bold cyan]
    [yellow]help[/yellow] - Show this help message
    [yellow]exit[/yellow] - Exit the program

[bold]Sequence Format:[/bold]
    note,velocity,channel,duration;note,velocity,channel,duration;...
    Example: 60,100,0,0.5;67,100,0,0.5;72,100,0,0.5

[bold]Notes:[/bold]
    - Durations in sequences are in beats (musical timing)
    - Add --loop flag to sequence commands to make them loop indefinitely
    - Instrument transpose: positive values transpose up, negative down
    - Channel range: 0-15, Note/Velocity range: 0-127
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
        msg = (
            "[red]Invalid params: Note and velocity must be 0-127, "
            "channel 0-15[/red]"
        )
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

        # Set loop property on the sequence
        sequence.loop = loop

        # Schedule the sequence with the sequencer
        sequence_id = sequencer.schedule_sequence(sequence)
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


def handle_instrument_command(
    instrument_manager: InstrumentManager, parts: List[str]
) -> None:
    """Handle instrument management commands.

    Args:
        instrument_manager: The instrument manager instance.
        parts: Command parts.
    """
    if len(parts) < 2:
        console.print("[red]Usage: instrument <create|list|remove> [args...][/red]")
        return

    subcommand = parts[1]

    if subcommand == "create":
        _handle_instrument_create(instrument_manager, parts)
    elif subcommand == "list":
        instrument_manager.print_instruments_table()
    elif subcommand == "remove":
        _handle_instrument_remove(instrument_manager, parts)
    else:
        console.print(f"[red]Unknown instrument command: {subcommand}[/red]")


def _handle_instrument_create(
    instrument_manager: InstrumentManager, parts: List[str]
) -> None:
    """Handle instrument creation command."""
    if len(parts) < 4:
        console.print(
            "[red]Usage: instrument create <name> <channel> [velocity] "
            "[transpose][/red]"
        )
        return

    try:
        name = parts[2]
        channel = int(parts[3])
        velocity = int(parts[4]) if len(parts) > 4 else 100
        transpose = int(parts[5]) if len(parts) > 5 else 0

        if instrument_manager.create_instrument(name, channel, velocity, transpose):
            console.print(
                f"[green]Created instrument '{name}' on channel {channel}[/green]"
            )
            if transpose != 0:
                console.print(f"[blue]  Transpose: {transpose:+d} semitones[/blue]")
            if velocity != 100:
                console.print(f"[blue]  Default velocity: {velocity}[/blue]")
        else:
            console.print(
                f"[red]Failed to create instrument '{name}' "
                f"(name exists or invalid params)[/red]"
            )

    except ValueError:
        console.print(
            "[red]Invalid parameters. Channel: 0-15, Velocity: 0-127, "
            "Transpose: -127 to 127[/red]"
        )


def _handle_instrument_remove(
    instrument_manager: InstrumentManager, parts: List[str]
) -> None:
    """Handle instrument removal command."""
    if len(parts) != 3:
        console.print("[red]Usage: instrument remove <name>[/red]")
        return

    name = parts[2]
    if instrument_manager.remove_instrument(name):
        console.print(f"[green]Removed instrument '{name}'[/green]")
    else:
        console.print(f"[red]Instrument '{name}' not found[/red]")


def handle_play_command(
    instrument_manager: InstrumentManager, parts: List[str]
) -> None:
    """Handle playing a note on an instrument.

    Args:
        instrument_manager: The instrument manager instance.
        parts: Command parts.
    """
    if len(parts) < 3:
        console.print(
            "[red]Usage: play <instrument_name> <note> [velocity] [duration][/red]"
        )
        return

    instrument_name = parts[1]
    instrument = instrument_manager.get_instrument(instrument_name)

    if not instrument:
        console.print(f"[red]Instrument '{instrument_name}' not found[/red]")
        return

    try:
        note = int(parts[2])
        velocity = int(parts[3]) if len(parts) > 3 else None
        duration = float(parts[4]) if len(parts) > 4 else 0.5

        instrument.play_note(note, velocity, duration)
        vel_str = f" (vel: {velocity})" if velocity is not None else ""
        console.print(
            f"[green]Playing note {note} on '{instrument_name}'{vel_str}[/green]"
        )

    except ValueError as e:
        console.print(f"[red]Error: {str(e)}[/red]")


def handle_playseq_command(
    instrument_manager: InstrumentManager, parts: List[str]
) -> None:
    """Handle playing a sequence on an instrument.

    Args:
        instrument_manager: The instrument manager instance.
        parts: Command parts.
    """
    if len(parts) < 3:
        console.print(
            "[red]Usage: playseq <instrument_name> <note_sequence> [--loop][/red]"
        )
        return

    instrument_name = parts[1]
    instrument = instrument_manager.get_instrument(instrument_name)

    if not instrument:
        console.print(f"[red]Instrument '{instrument_name}' not found[/red]")
        return

    try:
        # Check for --loop flag
        loop = "--loop" in parts
        sequence_str = " ".join(p for p in parts[2:] if p != "--loop")
        sequence = parse_sequence(sequence_str)

        # Set loop property on the sequence
        sequence.loop = loop

        # Play sequence on instrument
        sequence_id = instrument.play_sequence(sequence)
        status = "looping" if loop else "scheduled"
        console.print(
            f"[green]Sequence {status} on '{instrument_name}' "
            f"(ID: {sequence_id})[/green]"
        )

    except ValueError as e:
        console.print(f"[red]Error in sequence format: {str(e)}[/red]")


def handle_stopinst_command(
    instrument_manager: InstrumentManager, parts: List[str]
) -> None:
    """Handle stopping all sequences on an instrument.

    Args:
        instrument_manager: The instrument manager instance.
        parts: Command parts.
    """
    if len(parts) != 2:
        console.print("[red]Usage: stopinst <instrument_name>[/red]")
        return

    instrument_name = parts[1]
    instrument = instrument_manager.get_instrument(instrument_name)

    if not instrument:
        console.print(f"[red]Instrument '{instrument_name}' not found[/red]")
        return

    active_count = len(instrument.get_active_sequences())
    instrument.stop_all_sequences()
    console.print(
        f"[green]Stopped {active_count} sequence(s) on '{instrument_name}'[/green]"
    )


def handle_command(
    controller: MIDIController,
    sequencer: MIDISequencer,
    transport: PreciseTransport,
    instrument_manager: InstrumentManager,
    command: str,
    parts: List[str],
) -> Optional[bool]:
    """Handle a single command.

    Args:
        controller: The MIDI controller instance.
        sequencer: The MIDI sequencer instance.
        transport: The PreciseTransport instance.
        instrument_manager: The instrument manager instance.
        command: The full command string.
        parts: The command split into parts.

    Returns:
        True if should exit, None otherwise.
    """
    if command == "exit":
        return _handle_exit_command(instrument_manager, sequencer, transport)

    # Handle other commands
    command_handlers = {
        "help": lambda: print_help(),
        "list": lambda: controller.list_ports(),
        "connect": lambda: handle_connect_command(controller, parts),
        "note": lambda: handle_note_command(controller, parts),
        "sequence": lambda: handle_sequence_command(sequencer, parts),
        "stoploop": lambda: handle_stoploop_command(sequencer, parts),
        "instrument": lambda: handle_instrument_command(instrument_manager, parts),
        "play": lambda: handle_play_command(instrument_manager, parts),
        "playseq": lambda: handle_playseq_command(instrument_manager, parts),
        "stopinst": lambda: handle_stopinst_command(instrument_manager, parts),
        "start": lambda: transport.start(),
        "stop": lambda: _handle_stop_command(instrument_manager, sequencer),
    }

    handler = command_handlers.get(command)
    if handler:
        handler()
    else:
        console.print(f"[red]Unknown command: {command}[/red]")
        print_help()

    return None


def _handle_exit_command(
    instrument_manager: InstrumentManager,
    sequencer: MIDISequencer,
    transport: PreciseTransport,
) -> bool:
    """Handle the exit command."""
    # Stop all instruments and sequences
    instrument_manager.stop_all_instruments()
    sequencer.clear_all_sequences()
    transport.stop()
    return True


def _handle_stop_command(
    instrument_manager: InstrumentManager,
    sequencer: MIDISequencer,
) -> None:
    """Handle the stop command."""
    # Stop all instruments and sequences
    instrument_manager.stop_all_instruments()
    sequencer.clear_all_sequences()
    sequencer.all_notes_off()
    console.print("[yellow]Stopped all sequences and instruments[/yellow]")


@click.command()
def main():
    """AI Music Composer CLI for controlling MIDI output and playback."""
    console.print("[bold blue]AI Music Composer CLI[/bold blue]")
    console.print("Type 'help' for available commands")

    # Initialize logging
    setup_logging()

    controller = MIDIController()
    transport = PreciseTransport(initial_bpm=get_default_bpm())
    sequencer = MIDISequencer(controller, transport)

    # Create adapters and instrument manager
    note_player = MIDIControllerAdapter(controller)
    sequence_player = SequencerAdapter(sequencer)
    instrument_manager = InstrumentManager(note_player, sequence_player)

    try:
        while True:
            try:
                command = (
                    Prompt.ask("\n[bold green]composer>[/bold green]").strip().lower()
                )
                parts = command.split()

                if not parts:
                    continue

                if handle_command(
                    controller,
                    sequencer,
                    transport,
                    instrument_manager,
                    parts[0],
                    parts,
                ):
                    break

            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'exit' to quit[/yellow]")
            except Exception as e:
                console.print(f"[red]Error: {str(e)}[/red]")
    finally:
        # Ensure proper cleanup even if an exception occurs
        try:
            # Stop all instruments
            instrument_manager.stop_all_instruments()
            sequencer.clear_all_sequences()
            transport.stop()
        except Exception as e:
            console.print(f"[red]Error during cleanup: {str(e)}[/red]")

        controller.close()
        console.print("[blue]Goodbye![/blue]")


if __name__ == "__main__":
    main()
