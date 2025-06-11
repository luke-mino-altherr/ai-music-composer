"""Core music composition and generation functionality."""

from .midi_controller import MIDIController
from .structures import Note, Sequence
from .instrument import (
    Instrument,
    InstrumentConfig,
    NotePlayerProtocol,
    SequencePlayerProtocol,
)
from .instrument_adapters import (
    MIDIControllerAdapter,
    SequencerAdapter,
    CombinedAdapter,
)
from .instrument_manager import InstrumentManager

__all__ = [
    # Existing exports
    "MIDIController",
    "Note",
    "Sequence",
    # New instrument exports
    "Instrument",
    "InstrumentConfig",
    "NotePlayerProtocol",
    "SequencePlayerProtocol",
    "MIDIControllerAdapter",
    "SequencerAdapter",
    "CombinedAdapter",
    "InstrumentManager",
]
