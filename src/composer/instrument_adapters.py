"""Adapter classes to bridge Instrument abstraction with existing composer classes."""

from typing import TYPE_CHECKING
from .structures import Sequence

# Avoid circular imports
if TYPE_CHECKING:
    from .midi_controller import MIDIController
    from .sequencer import MIDISequencer


class MIDIControllerAdapter:
    """Adapter to use MIDIController with Instrument."""

    def __init__(self, midi_controller: "MIDIController"):
        """Initialize adapter with MIDIController instance.

        Args:
            midi_controller: MIDIController instance for MIDI output
        """
        self.midi_controller = midi_controller

    def play_note(
        self, pitch: int, velocity: int, channel: int, duration: float
    ) -> None:
        """Implement NotePlayerProtocol using MIDIController.

        Args:
            pitch: MIDI note number (0-127)
            velocity: Note velocity (0-127)
            channel: MIDI channel (0-15)
            duration: Note duration in seconds
        """
        self.midi_controller.send_note(
            note=pitch, velocity=velocity, channel=channel, duration=duration
        )

    def stop_note(self, pitch: int, channel: int) -> None:
        """Stop a specific note on a channel.

        Args:
            pitch: MIDI note number (0-127)
            channel: MIDI channel (0-15)
        """
        self.midi_controller.send_note_off(note=pitch, channel=channel)


class SequencerAdapter:
    """Adapter to use MIDISequencer with Instrument."""

    def __init__(self, sequencer: "MIDISequencer"):
        """Initialize adapter with MIDISequencer instance.

        Args:
            sequencer: MIDISequencer instance for sequence playback
        """
        self.sequencer = sequencer

    def play_sequence(self, sequence: Sequence) -> int:
        """Implement SequencePlayerProtocol using MIDISequencer.

        Args:
            sequence: Sequence object to play

        Returns:
            Sequence ID for later control
        """
        return self.sequencer.schedule_sequence(sequence)

    def stop_sequence(self, sequence_id: int) -> None:
        """Stop a playing sequence.

        Args:
            sequence_id: ID of sequence to stop
        """
        self.sequencer.remove_sequence(sequence_id)


class CombinedAdapter:
    """Combined adapter that provides both note and sequence playing capabilities."""

    def __init__(self, midi_controller: "MIDIController", sequencer: "MIDISequencer"):
        """Initialize with both MIDIController and MIDISequencer.

        Args:
            midi_controller: MIDIController instance for individual notes
            sequencer: MIDISequencer instance for sequences
        """
        self.note_player = MIDIControllerAdapter(midi_controller)
        self.sequence_player = SequencerAdapter(sequencer)

    def get_note_player(self) -> MIDIControllerAdapter:
        """Get the note player adapter.

        Returns:
            MIDIControllerAdapter instance
        """
        return self.note_player

    def get_sequence_player(self) -> SequencerAdapter:
        """Get the sequence player adapter.

        Returns:
            SequencerAdapter instance
        """
        return self.sequence_player
