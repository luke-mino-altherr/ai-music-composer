"""LLM Composer module for generating MIDI commands using language models."""

from .composer import LLMComposer
from .context import ContextBuilder, PromptAugmenter
from .memory import ComposerMemory, InstrumentMemory, MusicalContext, SequenceMemory

__all__ = [
    "LLMComposer",
    "ComposerMemory",
    "InstrumentMemory",
    "SequenceMemory",
    "MusicalContext",
    "ContextBuilder",
    "PromptAugmenter",
]
