"""MIDI controller module for handling MIDI output and playback."""

import time
from rich.console import Console
import mido
from typing import List

console = Console()


class MIDIController:
    """Controller class for handling MIDI output and playback functionality."""

    def __init__(self):
        """Initialize the MIDI controller with no active port or sequence."""
        self.port = None
        self.current_sequence = None
        self.is_playing = False

    def list_ports(self):
        """List all available MIDI output ports."""
        available_ports = mido.get_output_names()
        if not available_ports:
            console.print("[red]No MIDI output ports available![/red]")
            return []

        for i, port in enumerate(available_ports):
            console.print(f"[green]{i}[/green]: {port}")
        return available_ports

    def connect_port(self, port_number: int) -> bool:
        """Connect to a specific MIDI port.

        Args:
            port_number: Index of the port to connect to.

        Returns:
            True if connection successful, False otherwise.
        """
        available_ports = mido.get_output_names()

        if not 0 <= port_number < len(available_ports):
            console.print("[red]Invalid port number![/red]")
            return False

        try:
            port_name = available_ports[port_number]
            self.port = mido.open_output(port_name)
            console.print(f"[green]Connected to: {port_name}[/green]")
            return True
        except Exception as e:
            console.print(f"[red]Failed to connect to the port: {str(e)}[/red]")
            return False

    def send_note(
        self, note: int, velocity: int, channel: int = 0, duration: float = 0.5
    ):
        """Send a MIDI note with specified parameters.

        Args:
            note: MIDI note number (0-127).
            velocity: Note velocity (0-127).
            channel: MIDI channel (0-15).
            duration: Note duration in seconds.
        """
        if not self.port:
            console.print("[red]No MIDI port connected![/red]")
            return

        # Note ON message
        msg_on = mido.Message("note_on", note=note, velocity=velocity, channel=channel)
        self.port.send(msg_on)

        # Wait for duration
        time.sleep(duration)

        # Note OFF message
        msg_off = mido.Message("note_off", note=note, velocity=0, channel=channel)
        self.port.send(msg_off)

    def play_sequence(self, sequence: List[tuple], loop: bool = True):
        """Play a sequence of notes using mido's built-in timing.

        Args:
            sequence: List of tuples (note, velocity, channel, duration).
            loop: Whether to loop the sequence continuously.
        """
        if not self.port:
            console.print("[red]No MIDI port connected![/red]")
            return

        self.is_playing = True

        try:
            while self.is_playing:
                for note, velocity, channel, duration in sequence:
                    if not self.is_playing:
                        break

                    # Create messages
                    msg_on = mido.Message(
                        "note_on", note=note, velocity=velocity, channel=channel
                    )
                    msg_off = mido.Message(
                        "note_off", note=note, velocity=0, channel=channel
                    )

                    # Send note on
                    self.port.send(msg_on)

                    # Use mido's sleep function for more accurate timing
                    time.sleep(duration)

                    # Send note off
                    self.port.send(msg_off)

                if not loop:
                    break

        except Exception as e:
            console.print(f"[red]Error playing sequence: {str(e)}[/red]")
            self.is_playing = False

    def stop_sequence(self):
        """Stop the currently playing sequence and send all notes off."""
        self.is_playing = False

        # Send all notes off on all channels
        if self.port:
            for channel in range(16):
                for note in range(128):
                    msg_off = mido.Message(
                        "note_off", note=note, velocity=0, channel=channel
                    )
                    self.port.send(msg_off)

    def close(self):
        """Close the MIDI connection and clean up resources."""
        if self.port:
            self.stop_sequence()
            self.port.close()
