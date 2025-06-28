"""Tests for the music generator module."""

import pytest

from src.midi_generator.generator import MusicGenerator


def test_music_generator_initialization():
    """Test initialization of MusicGenerator with and without model path."""
    generator = MusicGenerator()
    assert generator.model_path is None
    assert generator.model is None

    generator_with_path = MusicGenerator("test_path")
    assert generator_with_path.model_path == "test_path"


def test_generate_not_implemented():
    """Test that base class generate method raises NotImplementedError."""
    generator = MusicGenerator()
    with pytest.raises(NotImplementedError):
        generator.generate()
