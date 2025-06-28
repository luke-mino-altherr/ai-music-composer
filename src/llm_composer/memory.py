"""Memory system for LLM Composer to track composition state."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set

from ..midi_generator.structures import Note
from .models import MIDICommand


class MusicalRole(Enum):
    """Musical roles for instruments."""

    MELODY = "melody"
    HARMONY = "harmony"
    BASS = "bass"
    RHYTHM = "rhythm"
    PERCUSSION = "percussion"
    LEAD = "lead"
    PAD = "pad"


class SequenceStatus(Enum):
    """Status of musical sequences."""

    ACTIVE = "active"
    STOPPED = "stopped"
    PAUSED = "paused"


@dataclass
class InstrumentMemory:
    """Memory representation of an instrument."""

    name: str
    channel: int
    instrument_type: str  # "piano", "bass", "drums", etc.
    velocity: int
    transpose: int
    created_at: datetime = field(default_factory=datetime.now)
    last_used: datetime = field(default_factory=datetime.now)
    active_sequences: Set[int] = field(default_factory=set)
    musical_role: MusicalRole = MusicalRole.MELODY
    description: str = ""  # User-provided or inferred description


@dataclass
class SequenceMemory:
    """Memory representation of a musical sequence."""

    id: int
    instrument_name: str
    notes: List[Note]
    is_looping: bool
    musical_purpose: str  # "chord_progression", "melody", "bassline", "drums"
    key_signature: Optional[str] = None
    time_signature: str = "4/4"
    created_at: datetime = field(default_factory=datetime.now)
    iteration_count: int = 0
    status: SequenceStatus = SequenceStatus.ACTIVE
    description: str = ""  # What this sequence represents


@dataclass
class MusicalContext:
    """Current musical context of the composition."""

    current_key: Optional[str] = None
    current_tempo: float = 120.0
    time_signature: str = "4/4"
    musical_style: Optional[str] = None  # "jazz", "classical", "rock", etc.
    chord_progression: List[str] = field(default_factory=list)
    harmonic_rhythm: Optional[str] = None  # How often chords change
    dominant_scale: Optional[str] = None  # Major, minor, etc.


@dataclass
class ConversationTurn:
    """A single turn in the conversation history."""

    timestamp: datetime
    user_prompt: str
    llm_response: str
    commands_executed: List[MIDICommand]
    musical_intent: str  # Extracted or inferred intent
    referenced_elements: List[str] = field(default_factory=list)  # What user referenced


class ComposerMemory:
    """Central memory system for the LLM composer."""

    def __init__(self):
        """Initialize the memory system."""
        self.instruments: Dict[str, InstrumentMemory] = {}
        self.sequences: Dict[int, SequenceMemory] = {}
        self.musical_context = MusicalContext()
        self.conversation_history: List[ConversationTurn] = []
        self.next_sequence_id = 1

        # Musical intelligence cache
        self._harmonic_analysis_cache: Optional[str] = None
        self._last_analysis_update: Optional[datetime] = None

    # === Instrument Management ===

    def add_instrument(self, instrument: InstrumentMemory) -> None:
        """Add an instrument to memory."""
        self.instruments[instrument.name] = instrument
        self._invalidate_analysis_cache()

    def remove_instrument(self, name: str) -> None:
        """Remove an instrument from memory."""
        if name in self.instruments:
            instrument = self.instruments[name]
            # Remove associated sequences
            for seq_id in list(instrument.active_sequences):
                self.remove_sequence(seq_id)
            del self.instruments[name]
            self._invalidate_analysis_cache()

    def get_instrument(self, name: str) -> Optional[InstrumentMemory]:
        """Get an instrument by name."""
        return self.instruments.get(name)

    def get_active_instruments(self) -> List[InstrumentMemory]:
        """Get all instruments with active sequences."""
        return [inst for inst in self.instruments.values() if inst.active_sequences]

    def get_instruments_by_role(self, role: MusicalRole) -> List[InstrumentMemory]:
        """Get instruments with a specific musical role."""
        return [inst for inst in self.instruments.values() if inst.musical_role == role]

    def update_instrument_activity(
        self, name: str, sequence_id: int, active: bool = True
    ) -> None:
        """Update instrument's active sequences."""
        if name in self.instruments:
            instrument = self.instruments[name]
            if active:
                instrument.active_sequences.add(sequence_id)
                instrument.last_used = datetime.now()
            else:
                instrument.active_sequences.discard(sequence_id)

    # === Sequence Management ===

    def add_sequence(self, sequence: SequenceMemory) -> int:
        """Add a sequence to memory and return its ID."""
        if sequence.id == 0:  # Auto-assign ID
            sequence.id = self.next_sequence_id
            self.next_sequence_id += 1

        self.sequences[sequence.id] = sequence

        # Update instrument's active sequences
        self.update_instrument_activity(sequence.instrument_name, sequence.id, True)

        self._invalidate_analysis_cache()
        return sequence.id

    def remove_sequence(self, sequence_id: int) -> None:
        """Remove a sequence from memory."""
        if sequence_id in self.sequences:
            sequence = self.sequences[sequence_id]
            # Update instrument
            self.update_instrument_activity(
                sequence.instrument_name, sequence_id, False
            )
            del self.sequences[sequence_id]
            self._invalidate_analysis_cache()

    def get_sequence(self, sequence_id: int) -> Optional[SequenceMemory]:
        """Get a sequence by ID."""
        return self.sequences.get(sequence_id)

    def get_active_sequences(self) -> List[SequenceMemory]:
        """Get all active sequences."""
        return [
            seq
            for seq in self.sequences.values()
            if seq.status == SequenceStatus.ACTIVE
        ]

    def get_sequences_by_purpose(self, purpose: str) -> List[SequenceMemory]:
        """Get sequences with a specific musical purpose."""
        return [
            seq for seq in self.sequences.values() if seq.musical_purpose == purpose
        ]

    def update_sequence_status(self, sequence_id: int, status: SequenceStatus) -> None:
        """Update sequence status."""
        if sequence_id in self.sequences:
            self.sequences[sequence_id].status = status
            if status != SequenceStatus.ACTIVE:
                sequence = self.sequences[sequence_id]
                self.update_instrument_activity(
                    sequence.instrument_name, sequence_id, False
                )

    # === Musical Context Management ===

    def update_musical_context(self, **kwargs) -> None:
        """Update musical context with provided values."""
        for key, value in kwargs.items():
            if hasattr(self.musical_context, key):
                setattr(self.musical_context, key, value)
        self._invalidate_analysis_cache()

    def get_current_musical_context(self) -> MusicalContext:
        """Get current musical context."""
        return self.musical_context

    def infer_musical_context(self) -> None:
        """Infer musical context from active sequences."""
        active_sequences = self.get_active_sequences()
        if not active_sequences:
            return

        # Infer key signature from sequence notes
        all_notes = []
        for seq in active_sequences:
            all_notes.extend([note.pitch % 12 for note in seq.notes])

        if all_notes:
            inferred_key = self._analyze_key_signature(all_notes)
            if inferred_key:
                self.musical_context.current_key = inferred_key

    # === Conversation History ===

    def add_conversation_turn(self, turn: ConversationTurn) -> None:
        """Add a conversation turn to history."""
        self.conversation_history.append(turn)

        # Keep only last 50 turns to prevent memory bloat
        if len(self.conversation_history) > 50:
            self.conversation_history = self.conversation_history[-50:]

    def get_recent_conversation_context(self, turns: int = 3) -> List[ConversationTurn]:
        """Get recent conversation turns."""
        return self.conversation_history[-turns:] if self.conversation_history else []

    def find_referenced_elements(self, text: str) -> List[str]:
        """Find elements referenced in text (instruments, sequences, etc.)."""
        text_lower = text.lower()
        referenced = []

        # Check for instrument references
        for name in self.instruments.keys():
            if name.lower() in text_lower:
                referenced.append(f"instrument:{name}")

        # Check for musical terms
        musical_terms = [
            "bass",
            "melody",
            "harmony",
            "drums",
            "chord",
            "scale",
            "major",
            "minor",
            "jazz",
            "classical",
            "rock",
        ]
        for term in musical_terms:
            if term in text_lower:
                referenced.append(f"musical_term:{term}")

        # Check for relative references
        relative_refs = ["that", "this", "the", "previous", "last", "current"]
        for ref in relative_refs:
            if ref in text_lower:
                referenced.append(f"reference:{ref}")

        return referenced

    # === State Queries ===

    def get_composition_summary(self) -> str:
        """Get a summary of the current composition state."""
        summary_parts = []

        # Instruments
        if self.instruments:
            inst_names = list(self.instruments.keys())
            summary_parts.append(f"Instruments: {', '.join(inst_names)}")
        else:
            summary_parts.append("No instruments")

        # Sequences
        active_seqs = self.get_active_sequences()
        if active_seqs:
            looping_count = sum(1 for seq in active_seqs if seq.is_looping)
            summary_parts.append(
                f"{len(active_seqs)} sequences ({looping_count} looping)"
            )
        else:
            summary_parts.append("No active sequences")

        # Musical context
        if self.musical_context.current_key:
            summary_parts.append(f"Key: {self.musical_context.current_key}")

        summary_parts.append(f"Tempo: {self.musical_context.current_tempo} BPM")

        if self.musical_context.musical_style:
            summary_parts.append(f"Style: {self.musical_context.musical_style}")

        return " | ".join(summary_parts)

    def get_harmonic_analysis(self) -> str:
        """Get harmonic analysis of current composition."""
        if self._harmonic_analysis_cache and self._last_analysis_update:
            # Use cached analysis if recent
            time_since_update = datetime.now() - self._last_analysis_update
            if time_since_update.seconds < 30:  # Cache for 30 seconds
                return self._harmonic_analysis_cache

        # Generate new analysis
        analysis = self._generate_harmonic_analysis()
        self._harmonic_analysis_cache = analysis
        self._last_analysis_update = datetime.now()
        return analysis

    # === Private Methods ===

    def _invalidate_analysis_cache(self) -> None:
        """Invalidate cached musical analysis."""
        self._harmonic_analysis_cache = None
        self._last_analysis_update = None

    def _analyze_key_signature(self, note_pitches: List[int]) -> Optional[str]:
        """Analyze note pitches to infer key signature."""
        if not note_pitches:
            return None

        # Simple key detection based on note frequency
        pitch_counts = {}
        for pitch in note_pitches:
            pitch_counts[pitch] = pitch_counts.get(pitch, 0) + 1

        # Find most common pitch classes
        sorted_pitches = sorted(pitch_counts.items(), key=lambda x: x[1], reverse=True)

        # Basic major/minor key detection
        if sorted_pitches:
            root = sorted_pitches[0][0]
            note_names = [
                "C",
                "C#",
                "D",
                "D#",
                "E",
                "F",
                "F#",
                "G",
                "G#",
                "A",
                "A#",
                "B",
            ]

            # Simple heuristic: if pitch classes suggest major or minor
            # This could be made much more sophisticated
            return f"{note_names[root]} major"  # Simplified for now

        return None

    def _generate_harmonic_analysis(self) -> str:
        """Generate harmonic analysis of current sequences."""
        active_sequences = self.get_active_sequences()
        if not active_sequences:
            return "No active sequences to analyze"

        analysis_parts = []

        # Analyze each sequence type
        melody_seqs = [s for s in active_sequences if s.musical_purpose == "melody"]
        harmony_seqs = [
            s for s in active_sequences if s.musical_purpose == "chord_progression"
        ]
        bass_seqs = [s for s in active_sequences if s.musical_purpose == "bassline"]

        if melody_seqs:
            analysis_parts.append(f"{len(melody_seqs)} melodic sequence(s)")

        if harmony_seqs:
            analysis_parts.append(f"{len(harmony_seqs)} harmonic sequence(s)")

        if bass_seqs:
            analysis_parts.append(f"{len(bass_seqs)} bass sequence(s)")

        if self.musical_context.chord_progression:
            chord_str = " - ".join(self.musical_context.chord_progression)
            analysis_parts.append(f"Progression: {chord_str}")

        return (
            ", ".join(analysis_parts)
            if analysis_parts
            else "Basic rhythmic/melodic content"
        )

    # === Debugging and Inspection ===

    def get_debug_state(self) -> Dict:
        """Get complete state for debugging."""
        return {
            "instruments": {
                name: {
                    "channel": inst.channel,
                    "role": inst.musical_role.value,
                    "active_sequences": list(inst.active_sequences),
                    "last_used": inst.last_used.isoformat(),
                }
                for name, inst in self.instruments.items()
            },
            "sequences": {
                seq_id: {
                    "instrument": seq.instrument_name,
                    "purpose": seq.musical_purpose,
                    "note_count": len(seq.notes),
                    "looping": seq.is_looping,
                    "status": seq.status.value,
                }
                for seq_id, seq in self.sequences.items()
            },
            "musical_context": {
                "key": self.musical_context.current_key,
                "tempo": self.musical_context.current_tempo,
                "style": self.musical_context.musical_style,
                "chord_progression": self.musical_context.chord_progression,
            },
            "conversation_turns": len(self.conversation_history),
        }
