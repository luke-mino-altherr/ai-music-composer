"""
Tests for the music generator module
"""
import pytest
from src.composer.generator import MusicGenerator

def test_music_generator_initialization():
    generator = MusicGenerator()
    assert generator.model_path is None
    assert generator.model is None
    
    generator_with_path = MusicGenerator("test_path")
    assert generator_with_path.model_path == "test_path"
    
def test_generate_not_implemented():
    generator = MusicGenerator()
    with pytest.raises(NotImplementedError):
        generator.generate() 