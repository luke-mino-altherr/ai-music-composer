"""MIDI sequencer module for connecting MIDIController with PreciseTransport."""

from dataclasses import dataclass
from typing import Dict, List, Union

from ..logging_config import get_logger
from .midi_controller import MIDIController
from .structures import Sequence
from .transport import PreciseTransport

# Get logger for this module
logger = get_logger(__name__)


@dataclass
class SequenceState:
    """Represents the state of a musical sequence."""

    sequence: Sequence  # Updated to use Sequence dataclass
    beats_per_note: float
    current_iteration: int
    sequence_length: float = 0.0  # Total length in beats


class MIDISequencer:
    """Handles sequencing of MIDI events using precise timing."""

    def __init__(self, midi_controller: MIDIController, transport: PreciseTransport):
        """Initialize the sequencer.

        Args:
            midi_controller: Instance of MIDIController for MIDI output
            transport: Instance of PreciseTransport for timing
        """
        logger.debug("Initializing MIDISequencer")
        self.midi_controller = midi_controller
        self.transport = transport
        self.active_sequences: Dict[int, SequenceState] = {}
        self._next_sequence_id = 0
        logger.debug(f"MIDISequencer initialized with transport BPM: {transport.bpm}")

    def schedule_note(
        self,
        beat: float,
        note: int,
        velocity: int,
        channel: int = 0,
        duration: float = 0.5,
    ) -> None:
        """Schedule a single note to play at a specific beat.

        Args:
            beat: Beat position when the note should start
            note: MIDI note number (0-127)
            velocity: Note velocity (0-127)
            channel: MIDI channel (0-15)
            duration: Note duration in beats
        """
        logger.debug(
            f"Scheduling single note: beat={beat}, note={note}, "
            f"velocity={velocity}, channel={channel}, duration={duration}"
        )

        def note_on():
            logger.debug(f"Executing note_on for note {note}")
            self.midi_controller.send_note_on(
                note=note, velocity=velocity, channel=channel
            )

        def note_off():
            logger.debug(f"Executing note_off for note {note}")
            self.midi_controller.send_note_off(note=note, channel=channel)

        # Schedule note on and off events
        self.transport.schedule_event(beat, note_on)
        self.transport.schedule_event(beat + duration, note_off)

        logger.debug(
            f"Note scheduled - events submitted for note {note} at beat {beat}"
        )

    def schedule_sequence(
        self, sequence: Union[List[tuple], Sequence], beats_per_note: float = 1.0
    ) -> int:
        """Schedule a sequence of notes to play.

        Args:
            sequence: Either a Sequence object or list of (note, velocity,
                channel, duration) tuples
            beats_per_note: Number of beats each note should take (ignored if
                sequence is Sequence object)

        Returns:
            Sequence ID that can be used to remove the sequence later
        """
        # Convert legacy tuple list to Sequence object if needed
        if isinstance(sequence, list):
            seq_obj = Sequence.from_tuple_list(sequence, loop=False)
            logger.debug(
                f"Converted tuple list to Sequence object: length={len(sequence)}, "
                f"beats_per_note={beats_per_note}"
            )
        else:
            seq_obj = sequence
            logger.debug(
                f"Using Sequence object: length={len(seq_obj.notes)}, "
                f"loop={seq_obj.loop}"
            )

        sequence_id = self._next_sequence_id
        self._next_sequence_id += 1

        # Calculate total sequence length
        sequence_length = seq_obj.total_duration()

        logger.debug(
            f"Sequence {sequence_id} - calculated length: {sequence_length} beats"
        )

        # Create and store sequence state
        state = SequenceState(
            sequence=seq_obj,
            beats_per_note=beats_per_note,
            current_iteration=0,
            sequence_length=sequence_length,
        )
        self.active_sequences[sequence_id] = state

        # Schedule the first iteration starting at the current beat position
        # This prevents scheduling events in the past which causes jitter
        current_beat = self.transport.current_beat
        logger.debug(
            f"Scheduling sequence {sequence_id} starting at beat {current_beat}"
        )
        self._schedule_iteration(sequence_id, current_beat)

        logger.info(
            f"Sequence {sequence_id} scheduled successfully with "
            f"{len(seq_obj.notes)} notes"
        )
        return sequence_id

    def _schedule_iteration(self, sequence_id: int, start_beat: float) -> None:
        """Schedule one iteration of a sequence starting at the specified beat.

        Args:
            sequence_id: ID of the sequence to schedule
            start_beat: Starting beat position for this iteration
        """
        if sequence_id not in self.active_sequences:
            logger.warning(
                f"Cannot schedule iteration for sequence {sequence_id}: "
                f"sequence not found"
            )
            return

        state = self.active_sequences[sequence_id]
        seq_obj = state.sequence

        logger.debug(
            f"Scheduling iteration {state.current_iteration} of sequence "
            f"{sequence_id} starting at beat {start_beat}"
        )

        # Schedule all notes in the sequence
        notes_scheduled = 0
        for note in seq_obj.notes:
            # Calculate absolute beat position
            absolute_beat = start_beat + note.start_beat

            # Use default parameters to properly capture loop variables
            def make_note_on(
                n=note.pitch, v=note.velocity, c=note.channel, seq_id=sequence_id
            ):
                def note_on_callback():
                    logger.debug(
                        f"Executing note_on for sequence {seq_id}: note={n}, "
                        f"velocity={v}, channel={c}"
                    )
                    self.midi_controller.send_note_on(note=n, velocity=v, channel=c)

                return note_on_callback

            def make_note_off(n=note.pitch, c=note.channel, seq_id=sequence_id):
                def note_off_callback():
                    logger.debug(
                        f"Executing note_off for sequence {seq_id}: note={n}, "
                        f"channel={c}"
                    )
                    self.midi_controller.send_note_off(note=n, channel=c)

                return note_off_callback

            self.transport.schedule_event(absolute_beat, make_note_on())
            self.transport.schedule_event(
                absolute_beat + note.duration, make_note_off()
            )
            logger.debug(
                f"Sequence {sequence_id} note {notes_scheduled}: scheduled at "
                f"beat {absolute_beat}, duration {note.duration}"
            )

            notes_scheduled += 1

        logger.debug(
            f"Sequence {sequence_id} iteration {state.current_iteration}: "
            f"scheduled {notes_scheduled} notes"
        )

        # If looping, schedule the next iteration
        if seq_obj.loop:
            state.current_iteration += 1
            next_start = start_beat + state.sequence_length

            logger.debug(
                f"Sequence {sequence_id} will loop - next iteration "
                f"{state.current_iteration} at beat {next_start}"
            )

            def schedule_next():
                logger.debug(f"Triggering next iteration of sequence {sequence_id}")
                self._schedule_iteration(sequence_id, next_start)

            self.transport.schedule_event(next_start, schedule_next)
        else:
            logger.debug(
                f"Sequence {sequence_id} iteration {state.current_iteration} "
                f"is final (no loop)"
            )

    def start_loop(self, sequence_id: int) -> None:
        """Enable looping for a sequence.

        Args:
            sequence_id: ID of the sequence to start looping

        Raises:
            KeyError: If sequence_id is not found in active sequences
        """
        logger.debug(f"Starting loop for sequence {sequence_id}")

        if sequence_id in self.active_sequences:
            state = self.active_sequences[sequence_id]
            was_looping = state.sequence.loop

            if not was_looping:
                current_beat = self.transport.current_beat
                logger.debug(
                    f"Scheduling sequence {sequence_id} starting at beat {current_beat}"
                )
                self._schedule_iteration(sequence_id, current_beat)
            else:
                logger.warning(f"Sequence {sequence_id} was already looping")
        else:
            logger.warning(f"Sequence {sequence_id} not found in active sequences")
            raise KeyError(f"No active sequence with ID {sequence_id}")

    def stop_loop(self, sequence_id: int) -> None:
        """Stop a looping sequence.

        Args:
            sequence_id: ID of the sequence to stop looping
        """
        logger.debug(f"Stopping loop for sequence {sequence_id}")

        if sequence_id in self.active_sequences:
            state = self.active_sequences[sequence_id]
            was_looping = state.sequence.loop
            state.sequence.loop = (
                False  # This will prevent the next iteration from being scheduled
            )

            if was_looping:
                logger.info(
                    f"Sequence {sequence_id} loop stopped after iteration "
                    f"{state.current_iteration}"
                )
            else:
                logger.warning(f"Sequence {sequence_id} was not looping")
        else:
            logger.warning(f"Sequence {sequence_id} not found in active sequences")
            raise KeyError(f"No active sequence with ID {sequence_id}")

    def remove_sequence(self, sequence_id: int) -> None:
        """Remove a previously scheduled sequence.

        Args:
            sequence_id: ID of the sequence to remove
        """
        logger.debug(f"Removing sequence {sequence_id}")

        if sequence_id in self.active_sequences:
            state = self.active_sequences[sequence_id]
            del self.active_sequences[sequence_id]
            logger.info(
                f"Sequence {sequence_id} removed (was at iteration "
                f"{state.current_iteration})"
            )
        else:
            logger.warning(f"Cannot remove sequence {sequence_id}: sequence not found")

    def clear_all_sequences(self) -> None:
        """Remove all scheduled sequences."""
        sequence_count = len(self.active_sequences)
        logger.debug(f"Clearing all sequences ({sequence_count} active)")

        if sequence_count > 0:
            sequence_ids = list(self.active_sequences.keys())
            self.active_sequences.clear()
            logger.info(f"Cleared {sequence_count} sequences: {sequence_ids}")
        else:
            logger.debug("No sequences to clear")

    def all_notes_off(self) -> None:
        """Send all notes off messages on all channels."""
        logger.debug("Sending all notes off on all channels")

        if self.midi_controller.port:
            notes_sent = 0
            for channel in range(16):
                for note in range(128):
                    self.midi_controller.send_note_off(note=note, channel=channel)
                    notes_sent += 1
            logger.debug(f"Sent {notes_sent} note_off messages across all channels")
        else:
            logger.warning("Cannot send all notes off: no MIDI port connected")
