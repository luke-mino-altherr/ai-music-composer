"""MIDI sequencer module for connecting MIDIController with PreciseTransport."""

import logging
import os
from typing import List, Dict
from dataclasses import dataclass
from .midi_controller import MIDIController
from .transport import PreciseTransport

# Configure logger for this module
logger = logging.getLogger(__name__)

# Set default log level from environment variable or INFO
log_level = os.getenv("SEQUENCER_LOG_LEVEL", "INFO").upper()
logger.setLevel(getattr(logging, log_level, logging.INFO))

# Create console handler if it doesn't exist
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


@dataclass
class SequenceState:
    """Represents the state of a musical sequence."""

    sequence: List[tuple]  # List of (note, velocity, channel, duration) tuples
    beats_per_note: float
    loop: bool
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
            f"Scheduling single note: beat={beat}, note={note}, velocity={velocity}, channel={channel}, duration={duration}"
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
        self, sequence: List[tuple], beats_per_note: float = 1.0, loop: bool = False
    ) -> int:
        """Schedule a sequence of notes to play.

        Args:
            sequence: List of (note, velocity, channel, duration) tuples
            beats_per_note: Number of beats each note should take
            loop: If True, sequence will loop indefinitely until stopped

        Returns:
            Sequence ID that can be used to remove the sequence later
        """
        logger.debug(
            f"Scheduling sequence: length={len(sequence)}, beats_per_note={beats_per_note}, loop={loop}"
        )

        sequence_id = self._next_sequence_id
        self._next_sequence_id += 1

        # Calculate total sequence length
        sequence_length = sum(x[3] for x in sequence)

        logger.debug(
            f"Sequence {sequence_id} - calculated length: {sequence_length} beats"
        )

        # Create and store sequence state
        state = SequenceState(
            sequence=sequence,
            beats_per_note=beats_per_note,
            loop=loop,
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
            f"Sequence {sequence_id} scheduled successfully with {len(sequence)} notes"
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
                f"Cannot schedule iteration for sequence {sequence_id}: sequence not found"
            )
            return

        state = self.active_sequences[sequence_id]
        current_beat = start_beat

        logger.debug(
            f"Scheduling iteration {state.current_iteration} of sequence {sequence_id} starting at beat {start_beat}"
        )

        # Schedule all notes in the sequence
        notes_scheduled = 0
        for note, velocity, channel, duration in state.sequence:
            # Use default parameters to properly capture loop variables
            def make_note_on(n=note, v=velocity, c=channel, seq_id=sequence_id):
                def note_on_callback():
                    logger.debug(
                        f"Executing note_on for sequence {seq_id}: note={n}, velocity={v}, channel={c}"
                    )
                    self.midi_controller.send_note_on(note=n, velocity=v, channel=c)

                return note_on_callback

            def make_note_off(n=note, c=channel, seq_id=sequence_id):
                def note_off_callback():
                    logger.debug(
                        f"Executing note_off for sequence {seq_id}: note={n}, channel={c}"
                    )
                    self.midi_controller.send_note_off(note=n, channel=c)

                return note_off_callback

            self.transport.schedule_event(current_beat, make_note_on())
            self.transport.schedule_event(current_beat + duration, make_note_off())
            logger.debug(
                f"Sequence {sequence_id} note {notes_scheduled}: scheduled at beat {current_beat}, duration {duration}"
            )

            current_beat += duration
            notes_scheduled += 1

        logger.debug(
            f"Sequence {sequence_id} iteration {state.current_iteration}: scheduled {notes_scheduled} notes"
        )

        # If looping, schedule the next iteration
        if state.loop:
            state.current_iteration += 1
            next_start = start_beat + state.sequence_length

            logger.debug(
                f"Sequence {sequence_id} will loop - next iteration {state.current_iteration} at beat {next_start}"
            )

            def schedule_next():
                logger.debug(f"Triggering next iteration of sequence {sequence_id}")
                self._schedule_iteration(sequence_id, next_start)

            self.transport.schedule_event(next_start, schedule_next)
        else:
            logger.debug(
                f"Sequence {sequence_id} iteration {state.current_iteration} is final (no loop)"
            )

    def stop_loop(self, sequence_id: int) -> None:
        """Stop a looping sequence.

        Args:
            sequence_id: ID of the sequence to stop looping
        """
        logger.debug(f"Stopping loop for sequence {sequence_id}")

        if sequence_id in self.active_sequences:
            state = self.active_sequences[sequence_id]
            was_looping = state.loop
            state.loop = (
                False  # This will prevent the next iteration from being scheduled
            )

            if was_looping:
                logger.info(
                    f"Sequence {sequence_id} loop stopped after iteration {state.current_iteration}"
                )
            else:
                logger.warning(f"Sequence {sequence_id} was not looping")
        else:
            logger.error(
                f"Cannot stop loop for sequence {sequence_id}: sequence not found"
            )

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
                f"Sequence {sequence_id} removed (was at iteration {state.current_iteration})"
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
