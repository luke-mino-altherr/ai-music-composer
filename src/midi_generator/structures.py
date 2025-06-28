"""Data structures for musical composition and MIDI sequencing."""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Note:
    """Represents a musical note with timing and expression."""

    pitch: int  # MIDI note number (0-127)
    velocity: int  # Note velocity (0-127)
    duration: float  # Duration in beats
    start_beat: float = 0.0  # Starting beat position
    channel: int = 0  # MIDI channel (0-15)

    def __post_init__(self):
        """Validate note parameters."""
        if not (0 <= self.pitch <= 127):
            raise ValueError(f"Pitch must be 0-127, got {self.pitch}")
        if not (0 <= self.velocity <= 127):
            raise ValueError(f"Velocity must be 0-127, got {self.velocity}")
        if not (0 <= self.channel <= 15):
            raise ValueError(f"Channel must be 0-15, got {self.channel}")
        if self.duration <= 0:
            raise ValueError(f"Duration must be positive, got {self.duration}")
        if self.start_beat < 0:
            raise ValueError(f"Start beat must be non-negative, got {self.start_beat}")

    def to_tuple(self) -> tuple:
        """Convert to legacy tuple format for backward compatibility.

        Returns:
            Tuple of (pitch, velocity, channel, duration).
        """
        return (self.pitch, self.velocity, self.channel, self.duration)


@dataclass
class Sequence:
    """Represents a musical sequence."""

    notes: List[Note]
    tempo_bpm: Optional[float] = None  # Override global tempo
    loop: bool = False
    name: Optional[str] = None

    def __post_init__(self):
        """Validate sequence parameters."""
        if not self.notes:
            raise ValueError("Sequence must contain at least one note")
        if self.tempo_bpm is not None and self.tempo_bpm <= 0:
            raise ValueError(f"Tempo must be positive, got {self.tempo_bpm}")

    def to_tuple_list(self) -> List[tuple]:
        """Convert to legacy tuple list format for backward compatibility.

        Returns:
            List of (pitch, velocity, channel, duration) tuples.
        """
        return [note.to_tuple() for note in self.notes]

    def total_duration(self) -> float:
        """Calculate the total duration of the sequence in beats.

        Returns:
            Total duration in beats.
        """
        if not self.notes:
            return 0.0
        return max(note.start_beat + note.duration for note in self.notes)

    @classmethod
    def from_tuple_list(cls, tuples: List[tuple], **kwargs) -> "Sequence":
        """Create a Sequence from a list of tuples.

        Args:
            tuples: List of (pitch, velocity, channel, duration) tuples.
            **kwargs: Additional sequence parameters.

        Returns:
            Sequence object.
        """
        notes = []
        current_beat = 0.0

        for tuple_data in tuples:
            if len(tuple_data) == 4:
                pitch, velocity, channel, duration = tuple_data
            else:
                raise ValueError(f"Tuple must have 4 elements, got {len(tuple_data)}")

            note = Note(
                pitch=pitch,
                velocity=velocity,
                duration=duration,
                start_beat=current_beat,
                channel=channel,
            )
            notes.append(note)
            current_beat += duration

        return cls(notes=notes, **kwargs)
