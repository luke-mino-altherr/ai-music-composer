"""MIDI tools handler for LLM commands."""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from midi_generator import InstrumentManager
from midi_generator.sequencer import MIDISequencer
from midi_generator.structures import Note, Sequence

from .models import (
    CreateInstrumentCommand,
    MIDICommand,
    PlayNoteCommand,
    PlaySequenceCommand,
    RemoveInstrumentCommand,
    StopAllCommand,
    StopSequenceCommand,
)


@dataclass
class MIDIToolResult:
    """Result from executing a MIDI command."""

    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class MIDIToolHandler:
    """Handles execution of MIDI commands from LLM responses."""

    def __init__(
        self,
        sequencer: MIDISequencer,
        instrument_manager: InstrumentManager,
    ):
        """Initialize the MIDI tool handler.

        Args:
            sequencer: Instance of MIDISequencer for direct MIDI control
            instrument_manager: Instance of InstrumentManager for instrument control
        """
        self.sequencer = sequencer
        self.instrument_manager = instrument_manager

    def execute_command(self, command: MIDICommand) -> MIDIToolResult:
        """Execute a MIDI command from the LLM.

        Args:
            command: A validated MIDI command object

        Returns:
            MIDIToolResult containing success status and any relevant data
        """
        handlers = {
            "play_note": self._handle_play_note,
            "play_sequence": self._handle_play_sequence,
            "create_instrument": self._handle_create_instrument,
            "remove_instrument": self._handle_remove_instrument,
            "stop_sequence": self._handle_stop_sequence,
            "stop_all": self._handle_stop_all,
        }

        handler = handlers.get(command.type)
        if not handler:
            return MIDIToolResult(
                success=False,
                message=f"Unknown command type: {command.type}",
            )

        try:
            return handler(command)
        except Exception as e:
            return MIDIToolResult(
                success=False,
                message=f"Error executing {command.type}: {str(e)}",
            )

    def _handle_play_note(self, command: PlayNoteCommand) -> MIDIToolResult:
        """Handle playing a single note."""
        instrument = self.instrument_manager.get_instrument(command.instrument)
        if not instrument:
            return MIDIToolResult(
                success=False,
                message=f"Instrument not found: {command.instrument}",
            )

        try:
            instrument.play_note(command.note, command.velocity, command.duration)
            return MIDIToolResult(
                success=True,
                message=f"Playing note {command.note} on {command.instrument}",
                data={"note": command.note, "instrument": command.instrument},
            )
        except ValueError as e:
            return MIDIToolResult(
                success=False,
                message=str(e),
            )

    def _handle_play_sequence(self, command: PlaySequenceCommand) -> MIDIToolResult:
        """Handle playing a sequence of notes."""
        try:
            notes = []
            current_beat = 0.0
            for note_data in command.notes:
                note = Note(
                    pitch=note_data.pitch,
                    velocity=note_data.velocity,
                    duration=note_data.duration,
                    start_beat=current_beat,
                    channel=note_data.channel,
                )
                notes.append(note)
                current_beat += note.duration

            sequence = Sequence(notes=notes, loop=command.loop)

            # If instrument specified, play through instrument
            if command.instrument:
                instrument = self.instrument_manager.get_instrument(command.instrument)
                if not instrument:
                    return MIDIToolResult(
                        success=False,
                        message=f"Instrument not found: {command.instrument}",
                    )
                sequence_id = instrument.play_sequence(sequence)
            else:
                sequence_id = self.sequencer.schedule_sequence(sequence)

            return MIDIToolResult(
                success=True,
                message=f"Sequence scheduled (ID: {sequence_id})",
                data={"sequence_id": sequence_id},
            )

        except ValueError as e:
            return MIDIToolResult(
                success=False,
                message=f"Invalid sequence data: {str(e)}",
            )

    def _handle_create_instrument(
        self, command: CreateInstrumentCommand
    ) -> MIDIToolResult:
        """Handle creating a new instrument."""
        if self.instrument_manager.create_instrument(
            command.name,
            command.channel,
            command.velocity,
            command.transpose,
        ):
            return MIDIToolResult(
                success=True,
                message=f"Created instrument '{command.name}' on channel {command.channel}",
                data={"name": command.name, "channel": command.channel},
            )
        else:
            return MIDIToolResult(
                success=False,
                message=f"Failed to create instrument '{command.name}'",
            )

    def _handle_remove_instrument(
        self, command: RemoveInstrumentCommand
    ) -> MIDIToolResult:
        """Handle removing an instrument."""
        if self.instrument_manager.remove_instrument(command.name):
            return MIDIToolResult(
                success=True,
                message=f"Removed instrument '{command.name}'",
            )
        else:
            return MIDIToolResult(
                success=False,
                message=f"Instrument '{command.name}' not found",
            )

    def _handle_stop_sequence(self, command: StopSequenceCommand) -> MIDIToolResult:
        """Handle stopping a sequence."""
        try:
            self.sequencer.stop_loop(command.sequence_id)
            return MIDIToolResult(
                success=True,
                message=f"Stopped sequence {command.sequence_id}",
            )
        except KeyError:
            return MIDIToolResult(
                success=False,
                message=f"Sequence {command.sequence_id} not found",
            )

    def _handle_stop_all(self, command: StopAllCommand) -> MIDIToolResult:
        """Handle stopping all sequences and instruments."""
        self.instrument_manager.stop_all_instruments()
        self.sequencer.clear_all_sequences()
        self.sequencer.all_notes_off()

        return MIDIToolResult(
            success=True,
            message="Stopped all sequences and instruments",
        )
