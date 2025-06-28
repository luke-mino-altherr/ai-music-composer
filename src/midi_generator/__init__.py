"""Core music composition and generation functionality."""

from .instrument import (
    Instrument,
    InstrumentConfig,
    NotePlayerProtocol,
    SequencePlayerProtocol,
)
from .instrument_adapters import (
    CombinedAdapter,
    MIDIControllerAdapter,
    SequencerAdapter,
)
from .instrument_manager import InstrumentManager
from .midi_controller import MIDIController
from .structures import Note, Sequence

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
