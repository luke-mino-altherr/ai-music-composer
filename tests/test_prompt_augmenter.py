"""Test suite for PromptAugmenter class from llm_composer.context module."""

from datetime import datetime
from unittest.mock import Mock

import pytest

from src.llm_composer.context import (
    ContextBuilder,
    HistoryContext,
    MusicContext,
    PromptAugmenter,
    StateContext,
)
from src.llm_composer.memory import (
    ComposerMemory,
    ConversationTurn,
    InstrumentMemory,
    MusicalRole,
    SequenceMemory,
    SequenceStatus,
)


class TestPromptAugmenter:
    """Test suite for PromptAugmenter class."""

    @pytest.fixture
    def mock_memory(self):
        """Create a mock ComposerMemory for testing."""
        memory = Mock(spec=ComposerMemory)

        # Mock instruments
        piano_instrument = Mock(spec=InstrumentMemory)
        piano_instrument.musical_role = MusicalRole.MELODY
        piano_instrument.channel = 0
        piano_instrument.active_sequences = []

        bass_instrument = Mock(spec=InstrumentMemory)
        bass_instrument.musical_role = MusicalRole.BASS
        bass_instrument.channel = 1
        bass_instrument.active_sequences = [1, 2]

        memory.instruments = {
            "piano": piano_instrument,
            "bass": bass_instrument,
        }

        # Mock sequences
        melody_sequence = Mock(spec=SequenceMemory)
        melody_sequence.status = SequenceStatus.ACTIVE
        melody_sequence.musical_purpose = "melody"
        melody_sequence.is_looping = False
        melody_sequence.instrument_name = "piano"
        melody_sequence.created_at = datetime(2023, 1, 1, 12, 0, 0)

        bass_sequence = Mock(spec=SequenceMemory)
        bass_sequence.status = SequenceStatus.ACTIVE
        bass_sequence.musical_purpose = "bassline"
        bass_sequence.is_looping = True
        bass_sequence.instrument_name = "bass"
        bass_sequence.created_at = datetime(2023, 1, 1, 12, 1, 0)

        memory.sequences = {
            1: melody_sequence,
            2: bass_sequence,
        }

        # Mock methods
        memory.get_composition_summary.return_value = "2 instruments, 2 sequences"
        memory.get_current_musical_context.return_value = Mock(
            current_key="C major",
            current_tempo=120.0,
            chord_progression=["C", "Am", "F", "G"],
            musical_style="pop",
        )
        memory.get_harmonic_analysis.return_value = "I-vi-IV-V progression"
        memory.get_active_sequences.return_value = [melody_sequence, bass_sequence]
        memory.get_recent_conversation_context.return_value = []
        memory.find_referenced_elements.return_value = []

        return memory

    @pytest.fixture
    def context_builder(self, mock_memory):
        """Create a ContextBuilder with mock memory."""
        return ContextBuilder(mock_memory)

    @pytest.fixture
    def prompt_augmenter(self, context_builder):
        """Create a PromptAugmenter with mock context builder."""
        return PromptAugmenter(context_builder)

    def test_initialization(self, context_builder):
        """Test PromptAugmenter initialization."""
        augmenter = PromptAugmenter(context_builder)

        assert augmenter.context_builder is context_builder
        assert augmenter.memory is context_builder.memory

    def test_analyze_prompt_context_needs_basic(self, prompt_augmenter):
        """Test basic prompt context analysis."""
        # Simple prompt should only need state context
        needs = prompt_augmenter._analyze_prompt_context_needs("Create a piano")

        assert needs["state"] is True
        assert needs["musical"] is False
        assert needs["history"] is False
        assert needs["references"] is False

    def test_analyze_prompt_context_needs_musical(self, prompt_augmenter):
        """Test musical context detection."""
        musical_prompts = [
            "Play in C major key",
            "Add a chord progression",
            "Change the tempo to 140 bpm",
            "Make it sound more jazz",
            "Use a minor scale",
        ]

        for prompt in musical_prompts:
            needs = prompt_augmenter._analyze_prompt_context_needs(prompt)
            assert needs["musical"] is True, f"Failed for prompt: {prompt}"

    def test_analyze_prompt_context_needs_history(self, prompt_augmenter):
        """Test history context detection."""
        history_prompts = [
            "Like the previous melody",
            "Remember what we did before",
            "The last sequence was good",
            "Earlier we had a nice rhythm",
        ]

        for prompt in history_prompts:
            needs = prompt_augmenter._analyze_prompt_context_needs(prompt)
            assert needs["history"] is True, f"Failed for prompt: {prompt}"

    def test_analyze_prompt_context_needs_references(self, prompt_augmenter):
        """Test reference context detection."""
        reference_prompts = [
            "Make that louder",
            "Change this instrument",
            "Stop the bass",
            "Modify them all",
        ]

        for prompt in reference_prompts:
            needs = prompt_augmenter._analyze_prompt_context_needs(prompt)
            assert needs["references"] is True, f"Failed for prompt: {prompt}"

    def test_resolve_references_empty(self, prompt_augmenter):
        """Test reference resolution with no references."""
        result = prompt_augmenter._resolve_references("Create a new piano")
        assert result == ""

    def test_resolve_references_with_instruments(self, prompt_augmenter):
        """Test reference resolution with instrument references."""
        prompt_augmenter.memory.find_referenced_elements.return_value = [
            "instrument:piano",
            "instrument:bass",
        ]

        result = prompt_augmenter._resolve_references("Modify the piano and bass")

        assert "instruments mentioned: piano, bass" in result

    def test_resolve_references_with_musical_terms(self, prompt_augmenter):
        """Test reference resolution with musical term references."""
        prompt_augmenter.memory.find_referenced_elements.return_value = [
            "musical_term:chord",
            "musical_term:melody",
        ]

        result = prompt_augmenter._resolve_references("Change the chord and melody")

        assert "musical concepts: chord, melody" in result

    def test_get_recent_musical_elements(self, prompt_augmenter):
        """Test getting recent musical elements."""
        result = prompt_augmenter._get_recent_musical_elements()

        # Should return description of recent sequences
        assert "bassline on bass (looping)" in result
        assert "melody on piano" in result

    def test_get_recent_musical_elements_empty(self, prompt_augmenter):
        """Test getting recent musical elements when none exist."""
        prompt_augmenter.memory.sequences = {}

        result = prompt_augmenter._get_recent_musical_elements()

        assert result == "no recent musical elements"

    def test_augment_prompt_basic(self, prompt_augmenter):
        """Test basic prompt augmentation with only state context."""
        original_prompt = "Create a new instrument"

        result = prompt_augmenter.augment_prompt(original_prompt)

        # Should include state context
        assert "Current composition state:" in result
        assert "User request: Create a new instrument" in result

    def test_augment_prompt_with_musical_context(self, prompt_augmenter):
        """Test prompt augmentation with musical context."""
        original_prompt = "Play in C major key"

        result = prompt_augmenter.augment_prompt(original_prompt)

        # Should include both state and musical context
        assert "Current composition state:" in result
        assert "Musical context:" in result
        assert "Key: C major" in result
        assert "Tempo: 120.0 BPM" in result
        assert "User request: Play in C major key" in result

    def test_augment_prompt_with_history_context(self, prompt_augmenter):
        """Test prompt augmentation with history context."""
        # Mock conversation history
        conversation_turn = Mock(spec=ConversationTurn)
        conversation_turn.user_prompt = "Create a piano"
        conversation_turn.musical_intent = "create_instrument"
        conversation_turn.referenced_elements = ["piano"]

        prompt_augmenter.memory.get_recent_conversation_context.return_value = [
            conversation_turn
        ]

        original_prompt = "Like the previous instrument"
        result = prompt_augmenter.augment_prompt(original_prompt)

        # Should include history context
        assert "Recent conversation context:" in result
        assert "Recent requests:" in result
        assert "Create a piano" in result

    def test_augment_prompt_with_references(self, prompt_augmenter):
        """Test prompt augmentation with reference resolution."""
        prompt_augmenter.memory.find_referenced_elements.return_value = [
            "instrument:piano"
        ]

        original_prompt = "Make that louder"
        result = prompt_augmenter.augment_prompt(original_prompt)

        # Should include reference resolution
        assert "Referenced elements:" in result
        assert "instruments mentioned: piano" in result

    def test_format_state_context(self, prompt_augmenter):
        """Test state context formatting."""
        state_context = StateContext(
            active_instruments=["piano", "bass"],
            active_sequences=["#1: melody", "#2: bassline (looping)"],
            system_status="2 instruments, 2 sequences",
            instrument_details={
                "piano": "melody on Ch0",
                "bass": "bass on Ch1 (2 sequences)",
            },
        )

        result = prompt_augmenter._format_state_context(state_context)

        assert "Current composition state:" in result
        assert (
            "Active instruments: piano (melody on Ch0), bass (bass on Ch1 (2 sequences))"
            in result
        )
        assert "Active sequences: #1: melody, #2: bassline (looping)" in result

    def test_format_state_context_empty(self, prompt_augmenter):
        """Test state context formatting when empty."""
        state_context = StateContext(
            active_instruments=[],
            active_sequences=[],
            system_status="No activity",
            instrument_details={},
        )

        result = prompt_augmenter._format_state_context(state_context)

        assert "No active instruments" in result
        assert "No active sequences" in result

    def test_format_music_context(self, prompt_augmenter):
        """Test musical context formatting."""
        music_context = MusicContext(
            current_key="C major",
            tempo=120.0,
            active_chord_progression=["C", "Am", "F", "G"],
            harmonic_analysis="I-vi-IV-V progression",
            rhythmic_pattern="4/4 time",
            musical_style="pop",
        )

        result = prompt_augmenter._format_music_context(music_context)

        assert "Musical context:" in result
        assert "Key: C major" in result
        assert "Tempo: 120.0 BPM" in result
        assert "Style: pop" in result
        assert "Chord progression: C - Am - F - G" in result
        assert "Harmonic analysis: I-vi-IV-V progression" in result
        assert "Rhythmic patterns: 4/4 time" in result

    def test_format_history_context(self, prompt_augmenter):
        """Test history context formatting."""
        history_context = HistoryContext(
            recent_requests=["Create a piano", "Add bass line", "Make it faster"],
            musical_themes=["create_instrument", "modify_tempo"],
            referenced_elements=["piano", "bass"],
        )

        result = prompt_augmenter._format_history_context(history_context)

        assert "Recent conversation context:" in result
        assert "Recent requests:" in result
        assert "1. Create a piano" in result
        assert "2. Add bass line" in result
        assert "3. Make it faster" in result
        assert "Musical themes discussed: create_instrument, modify_tempo" in result

    def test_complex_prompt_augmentation(self, prompt_augmenter):
        """Test complex prompt with multiple context types."""
        # Setup complex scenario
        conversation_turn = Mock(spec=ConversationTurn)
        conversation_turn.user_prompt = "Create jazz piano"
        conversation_turn.musical_intent = "create_instrument"
        conversation_turn.referenced_elements = ["piano"]

        prompt_augmenter.memory.get_recent_conversation_context.return_value = [
            conversation_turn
        ]
        prompt_augmenter.memory.find_referenced_elements.return_value = [
            "instrument:piano",
            "musical_term:jazz",
        ]

        # Complex prompt that triggers multiple context types
        original_prompt = (
            "Make that piano sound more like the previous jazz style we had"
        )
        result = prompt_augmenter.augment_prompt(original_prompt)

        # Should include all context types
        assert "Current composition state:" in result
        assert "Musical context:" in result
        assert "Recent conversation context:" in result
        assert "Referenced elements:" in result
        assert "User request:" in result

        # Verify content
        assert "instruments mentioned: piano" in result
        assert "musical concepts: jazz" in result
        assert "Create jazz piano" in result

    def test_prompt_without_context_needs(self, prompt_augmenter):
        """Test prompt that doesn't need additional context."""
        # Mock to return minimal context needs
        original_method = prompt_augmenter._analyze_prompt_context_needs
        prompt_augmenter._analyze_prompt_context_needs = lambda _: {
            "state": False,
            "musical": False,
            "history": False,
            "references": False,
        }

        try:
            result = prompt_augmenter.augment_prompt("Simple test")
            # Should return original prompt when no context needed
            assert result == "Simple test"
        finally:
            # Restore original method
            prompt_augmenter._analyze_prompt_context_needs = original_method


class TestPromptAugmenterIntegration:
    """Integration tests for PromptAugmenter with real components."""

    @pytest.fixture
    def real_memory(self):
        """Create a real ComposerMemory instance for integration testing."""
        memory = ComposerMemory()

        # Add some test data
        piano = InstrumentMemory(
            name="piano",
            channel=0,
            instrument_type="piano",
            velocity=100,
            transpose=0,
            musical_role=MusicalRole.MELODY,
        )
        memory.add_instrument(piano)

        bass = InstrumentMemory(
            name="bass",
            channel=1,
            instrument_type="bass",
            velocity=80,
            transpose=0,
            musical_role=MusicalRole.BASS,
        )
        memory.add_instrument(bass)

        # Add a sequence
        sequence = SequenceMemory(
            id=1,
            instrument_name="piano",
            notes=[],
            is_looping=False,
            musical_purpose="melody",
            key_signature="C major",
        )
        memory.add_sequence(sequence)

        return memory

    @pytest.fixture
    def real_prompt_augmenter(self, real_memory):
        """Create PromptAugmenter with real components."""
        context_builder = ContextBuilder(real_memory)
        return PromptAugmenter(context_builder)

    def test_real_prompt_augmentation(self, real_prompt_augmenter):
        """Test prompt augmentation with real components."""
        result = real_prompt_augmenter.augment_prompt("Create a new bass line")

        # Should contain actual context information
        assert "Current composition state:" in result
        assert "piano" in result  # Should mention existing piano
        assert "User request: Create a new bass line" in result

    def test_real_musical_context_augmentation(self, real_prompt_augmenter):
        """Test musical context with real components."""
        result = real_prompt_augmenter.augment_prompt("Change to minor key")

        # Should include musical context
        assert "Musical context:" in result
        assert "User request: Change to minor key" in result
