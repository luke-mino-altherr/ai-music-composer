"""MIDI controller module for handling MIDI output and playbook."""

import time

import mido
from rich.console import Console

from ..logging_config import get_logger

console = Console()

# Get logger for this module
logger = get_logger(__name__)


class MIDIController:
    """Controller class for handling MIDI output and playback functionality."""

    def __init__(self):
        """Initialize the MIDI controller with no active port or sequence."""
        self.port = None
        self.current_sequence = None
        self.is_playing = False
        logger.debug("MIDIController initialized")

    def list_ports(self):
        """List all available MIDI output ports."""
        logger.debug("Listing available MIDI output ports")
        available_ports = mido.get_output_names()
        logger.debug(
            f"Found {len(available_ports)} MIDI output ports: {available_ports}"
        )

        if not available_ports:
            console.print("[red]No MIDI output ports available![/red]")
            logger.warning("No MIDI output ports available")
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
        logger.debug(f"Attempting to connect to MIDI port {port_number}")
        available_ports = mido.get_output_names()

        if not 0 <= port_number < len(available_ports):
            console.print("[red]Invalid port number![/red]")
            logger.error(
                f"Invalid port number {port_number}. Available ports: "
                f"0-{len(available_ports)-1}"
            )
            return False

        try:
            port_name = available_ports[port_number]
            logger.debug(f"Opening MIDI output port: {port_name}")
            self.port = mido.open_output(port_name)
            console.print(f"[green]Connected to: {port_name}[/green]")
            logger.info(f"Successfully connected to MIDI port: {port_name}")
            return True
        except Exception as e:
            console.print(f"[red]Failed to connect to the port: {str(e)}[/red]")
            logger.error(f"Failed to connect to MIDI port {port_number}: {str(e)}")
            return False

    def send_note_on(self, note: int, velocity: int, channel: int = 0) -> None:
        """Send a note on message.

        Args:
            note: MIDI note number (0-127)
            velocity: Note velocity (0-127)
            channel: MIDI channel (0-15)
        """
        logger.debug(
            f"Sending note_on: note={note}, velocity={velocity}, channel={channel}"
        )
        if self.port:
            msg = mido.Message("note_on", note=note, velocity=velocity, channel=channel)
            self.port.send(msg)
            logger.debug(f"Note on message sent successfully: {msg}")
        else:
            logger.warning("Attempted to send note_on but no MIDI port is connected")

    def send_note_off(self, note: int, channel: int = 0) -> None:
        """Send a note off message.

        Args:
            note: MIDI note number (0-127)
            channel: MIDI channel (0-15)
        """
        logger.debug(f"Sending note_off: note={note}, channel={channel}")
        if self.port:
            msg = mido.Message("note_off", note=note, velocity=0, channel=channel)
            self.port.send(msg)
            logger.debug(f"Note off message sent successfully: {msg}")
        else:
            logger.warning("Attempted to send note_off but no MIDI port is connected")

    def send_note(
        self, note: int, velocity: int, channel: int = 0, duration: float = 0.5
    ):
        """Send a single MIDI note with blocking timing.

        This is a low-level utility method that uses simple sleep-based timing.
        For more precise musical timing, use MIDISequencer instead.

        Args:
            note: MIDI note number (0-127).
            velocity: Note velocity (0-127).
            channel: MIDI channel (0-15).
            duration: Note duration in seconds.
        """
        logger.debug(
            f"Sending note with duration: note={note}, velocity={velocity}, "
            f"channel={channel}, duration={duration}s"
        )

        if not self.port:
            console.print("[red]No MIDI port connected![/red]")
            logger.error("Cannot send note: no MIDI port connected")
            return

        self.send_note_on(note, velocity, channel)
        logger.debug(f"Sleeping for {duration}s")
        time.sleep(duration)
        self.send_note_off(note, channel)
        logger.debug(f"Note sequence completed for note {note}")

    def stop_sequence(self):
        """Stop the currently playing sequence and send all notes off."""
        logger.debug("Stopping sequence and sending all notes off")
        self.is_playing = False

        # Send all notes off on all channels
        if self.port:
            notes_sent = 0
            for channel in range(16):
                for note in range(128):
                    self.send_note_off(note, channel)
                    notes_sent += 1
            logger.debug(f"Sent {notes_sent} note_off messages across all channels")
        else:
            logger.warning("Cannot stop sequence: no MIDI port connected")

    def close(self):
        """Close the MIDI connection and clean up resources."""
        logger.debug("Closing MIDI controller")
        if self.port:
            self.stop_sequence()
            self.port.close()
            logger.info("MIDI port closed successfully")
        else:
            logger.debug("No MIDI port to close")
