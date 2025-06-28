# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Package Management
- **Install dependencies**: `poetry install`
- **Activate environment**: `poetry shell`
- **Add dependency**: `poetry add <package>`
- **Add dev dependency**: `poetry add --group dev <package>`

### Running the Application
- **Direct MIDI CLI**: `poetry run composer` or `composer` (after `poetry install`)
- **LLM-powered CLI**: `poetry run llm-composer` or `llm-composer` (after `poetry install`)
- **Direct execution**: `python src/composer_cli.py` or `python src/llm_cli.py`

### Testing
- **Run all tests**: `pytest`
- **Run specific test**: `pytest tests/test_<module>.py`
- **Run with verbose output**: `pytest -v`

### Code Quality
- **Format code**: `black .`
- **Sort imports**: `isort .`
- **Remove unused imports/variables**: `autoflake --remove-all-unused-imports --remove-unused-variables --in-place --recursive .`
- **Lint code**: `flake8`
- **Run all formatting (automated)**: `pre-commit run --all-files`
- **Install pre-commit hooks**: `pre-commit install` (runs automatically on commit)

### Database (Neo4j)
- **Start Neo4j**: `docker-compose up -d` (starts Neo4j in background)
- **Stop Neo4j**: `docker-compose down`
- **Initialize music database**: `python src/database/init_music_db.py`

## Architecture Overview

### Core Components

**MIDI System Architecture**:
1. **MIDIController** (`src/midi_generator/midi_controller.py`) - Low-level MIDI output handling
2. **PreciseTransport** (`src/midi_generator/transport.py`) - High-precision timing engine
3. **MIDISequencer** (`src/midi_generator/sequencer.py`) - Connects controller and transport for sequenced playback
4. **Instrument System** (`src/midi_generator/instrument*.py`) - Abstraction layer for musical instruments

**LLM Integration**:
- **LLMComposer** (`src/llm_composer/composer.py`) - Translates natural language to MIDI commands using LangChain
- **MIDIToolHandler** (`src/llm_composer/midi_tools.py`) - Executes LLM-generated MIDI commands
- Uses OpenAI API (requires `OPENAI_API_KEY` in `.env`)

**Database Layer**:
- **Neo4j Graph Database** - Stores music theory relationships (chords, scales, intervals)
- **Models** (`src/database/models.py`) - Neomodel-based graph models for music theory
- **Connection**: `bolt://neo4j:musiccomposer@localhost:7687`

### Module Structure

**Legacy modules** (marked for deletion in git status):
- `src/composer/` - Original modules being replaced by `midi_generator/`

**Current active modules**:
- `src/midi_generator/` - MIDI generation and playback system
- `src/llm_composer/` - LLM-to-MIDI translation
- `src/database/` - Music theory graph database
- `src/composer_cli.py` - Main CLI interface

**Key Patterns**:
- Adapter pattern used for instrument abstraction (`MIDIControllerAdapter`, `SequencerAdapter`)
- Command pattern for LLM-generated MIDI operations
- Repository pattern with Neo4j for music theory data

### Data Flow

1. **CLI Input** → `composer_cli.py` parses commands
2. **Direct MIDI** → Commands route to `MIDIController`/`MIDISequencer`
3. **LLM Composition** → `LLMComposer` → `MIDIToolHandler` → MIDI system
4. **Music Theory** → Neo4j graph queries via neomodel

### Configuration

- **Centralized Config**: All settings managed in `src/config.py`
- **Centralized Logging**: All logging configured in `src/logging_config.py`
- **Environment File**: Copy `.env.example` to `.env` and customize values
- **Required**: `OPENAI_API_KEY` in `.env` for LLM features
- **Logging**: Configure via `LOG_LEVEL`, `MIDI_LOG_LEVEL`, etc. in `.env`
- **Neo4j**: Database settings configurable via `NEO4J_*` environment variables
- **MIDI**: Default BPM, velocity, channel configurable via `MIDI_*` variables
- **Code style**: Black (88 char line length), Flake8 with Google docstrings

### Logging Best Practices

- **Get loggers**: Use `from logging_config import get_logger; logger = get_logger(__name__)`
- **Module-specific levels**: Configured per module in `logging_config.py`
- **File rotation**: Automatic log file rotation (10MB, 5 backups)
- **Debug utilities**: `get_debug_logger()` and `temporary_log_level()` context manager
- **Centralized setup**: Call `setup_logging()` once at application start

### Testing Strategy

- Unit tests for individual components (generator, instrument, instrument_manager)
- Tests use pytest framework
- Test files follow `test_<module>.py` naming convention
- Focus on MIDI generation and instrument management functionality
