"""Instrument management for organizing and controlling multiple instruments."""

from typing import Dict, Optional

from rich.console import Console
from rich.table import Table

from .instrument import (
    Instrument,
    InstrumentConfig,
    NotePlayerProtocol,
    SequencePlayerProtocol,
)

console = Console()


class InstrumentManager:
    """Manages multiple instruments for musical composition and performance."""

    def __init__(
        self, note_player: NotePlayerProtocol, sequence_player: SequencePlayerProtocol
    ):
        """Initialize the instrument manager.

        Args:
            note_player: Implementation for playing individual notes
            sequence_player: Implementation for playing sequences
        """
        self.note_player = note_player
        self.sequence_player = sequence_player
        self.instruments: Dict[str, Instrument] = {}

    def create_instrument(
        self, name: str, channel: int, default_velocity: int = 100, transpose: int = 0
    ) -> bool:
        """Create a new instrument.

        Args:
            name: Instrument name (must be unique)
            channel: MIDI channel (0-15)
            default_velocity: Default velocity (0-127)
            transpose: Transpose in semitones (-127 to 127)

        Returns:
            True if created successfully, False if name exists or invalid params
        """
        if name in self.instruments:
            return False

        try:
            config = InstrumentConfig(
                channel=channel,
                name=name,
                default_velocity=default_velocity,
                transpose=transpose,
            )
            instrument = Instrument(config, self.note_player, self.sequence_player)
            self.instruments[name] = instrument
            return True
        except ValueError:
            return False

    def get_instrument(self, name: str) -> Optional[Instrument]:
        """Get an instrument by name.

        Args:
            name: Instrument name

        Returns:
            Instrument instance or None if not found
        """
        return self.instruments.get(name)

    def list_instruments(self) -> Dict[str, Instrument]:
        """Get all instruments.

        Returns:
            Dictionary of instrument name to Instrument instance
        """
        return self.instruments.copy()

    def remove_instrument(self, name: str) -> bool:
        """Remove an instrument.

        Args:
            name: Instrument name

        Returns:
            True if removed successfully, False if not found
        """
        if name in self.instruments:
            # Stop all sequences on this instrument before removing
            self.instruments[name].stop_all_sequences()
            del self.instruments[name]
            return True
        return False

    def stop_all_instruments(self) -> int:
        """Stop all sequences on all instruments.

        Returns:
            Total number of sequences stopped
        """
        total_stopped = 0
        for instrument in self.instruments.values():
            total_stopped += len(instrument.get_active_sequences())
            instrument.stop_all_sequences()
        return total_stopped

    def get_instrument_names(self) -> list[str]:
        """Get list of all instrument names.

        Returns:
            List of instrument names
        """
        return list(self.instruments.keys())

    def has_instrument(self, name: str) -> bool:
        """Check if an instrument exists.

        Args:
            name: Instrument name

        Returns:
            True if instrument exists
        """
        return name in self.instruments

    def get_total_active_sequences(self) -> int:
        """Get total number of active sequences across all instruments.

        Returns:
            Total number of active sequences
        """
        return sum(
            len(instrument.get_active_sequences())
            for instrument in self.instruments.values()
        )

    def print_instruments_table(self) -> None:
        """Print a formatted table of all instruments using Rich."""
        if not self.instruments:
            console.print("[yellow]No instruments created[/yellow]")
            return

        table = Table(title="Instruments")
        table.add_column("Name", style="cyan")
        table.add_column("Channel", style="green")
        table.add_column("Default Velocity", style="blue")
        table.add_column("Transpose", style="magenta")
        table.add_column("Active Sequences", style="yellow")

        for name, instrument in self.instruments.items():
            active_count = len(instrument.get_active_sequences())
            table.add_row(
                name,
                str(instrument.channel),
                str(instrument.config.default_velocity),
                (
                    f"{instrument.config.transpose:+d}"
                    if instrument.config.transpose != 0
                    else "0"
                ),
                str(active_count),
            )
        console.print(table)

    def get_instruments_by_channel(self, channel: int) -> list[Instrument]:
        """Get all instruments on a specific channel.

        Args:
            channel: MIDI channel (0-15)

        Returns:
            List of instruments on the specified channel
        """
        return [
            instrument
            for instrument in self.instruments.values()
            if instrument.channel == channel
        ]

    def clear_all_instruments(self) -> int:
        """Remove all instruments after stopping their sequences.

        Returns:
            Number of instruments removed
        """
        count = len(self.instruments)
        self.stop_all_instruments()
        self.instruments.clear()
        return count
