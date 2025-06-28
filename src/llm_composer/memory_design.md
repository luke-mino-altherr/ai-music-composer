# LLM Composer Memory System Design

## Overview

This document describes the design of an in-memory state management system for the LLM Composer module. The system will track the current composition state, provide context to the LLM, and enable stateful musical conversations.

## Design Goals

### Primary Goals
- **State Persistence**: Track instruments, sequences, and musical context across LLM interactions
- **Context Injection**: Automatically provide relevant state information to LLM prompts
- **Musical Intelligence**: Understand musical relationships (key signatures, chord progressions, etc.)
- **Conversational Continuity**: Enable references to previous musical elements ("the piano from before", "that bass line")

### Secondary Goals
- **Performance**: Fast state queries and updates
- **Extensibility**: Easy to add new state types
- **Debugging**: Clear state inspection capabilities
- **Serialization**: Future ability to save/load compositions

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                          LLMComposer                           │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────┐                    │
│  │  ComposerMemory │    │  ContextBuilder │                    │
│  │                 │    │                 │                    │
│  │ - InstrumentMap │    │ - StateContext  │                    │
│  │ - SequenceMap   │◄──►│ - MusicContext  │                    │
│  │ - MusicalState  │    │ - HistoryContext│                    │
│  │ - ConversationHist│  │                 │                    │
│  └─────────────────┘    └─────────────────┘                    │
│           │                       │                             │
│           ▼                       ▼                             │
│  ┌─────────────────┐    ┌─────────────────┐                    │
│  │ StateSerializer │    │  PromptAugmenter│                    │
│  └─────────────────┘    └─────────────────┘                    │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │  MIDIToolHandler│
                  └─────────────────┘
```

## Core Components

### 1. ComposerMemory (Central State Store)

**Purpose**: Central repository for all composition state

**Data Structures**:

```python
@dataclass
class InstrumentMemory:
    name: str
    channel: int
    instrument_type: str  # "piano", "bass", "drums", etc.
    velocity: int
    transpose: int
    created_at: datetime
    last_used: datetime
    active_sequences: List[int]
    musical_role: str  # "melody", "harmony", "rhythm", "bass"

@dataclass
class SequenceMemory:
    id: int
    instrument_name: str
    notes: List[Note]
    is_looping: bool
    musical_purpose: str  # "chord_progression", "melody", "bassline", "drums"
    key_signature: Optional[str]
    time_signature: str
    created_at: datetime
    iteration_count: int

@dataclass
class MusicalContext:
    current_key: Optional[str]
    current_tempo: float
    time_signature: str
    musical_style: Optional[str]  # "jazz", "classical", "rock", etc.
    chord_progression: List[str]  # ["Cmaj", "Am", "F", "G"]
    harmonic_rhythm: Optional[str]  # "4/4", "1/1", etc.

@dataclass
class ConversationTurn:
    timestamp: datetime
    user_prompt: str
    llm_response: str
    commands_executed: List[MIDICommand]
    musical_intent: str  # Extracted intent
```

### 2. ContextBuilder (State-to-Context Converter)

**Purpose**: Convert memory state into natural language context for LLM

**Responsibilities**:
- Generate current state summaries
- Create musical context descriptions
- Format conversation history
- Identify relevant state for current prompt

**Context Types**:

```python
@dataclass
class StateContext:
    """Current system state"""
    active_instruments: List[str]
    active_sequences: List[str]
    system_status: str

@dataclass
class MusicContext:
    """Musical/compositional context"""
    current_key: Optional[str]
    tempo: float
    active_chord_progression: List[str]
    harmonic_analysis: str
    rhythmic_pattern: str

@dataclass
class HistoryContext:
    """Relevant conversation history"""
    recent_requests: List[str]
    musical_themes: List[str]
    referenced_elements: List[str]  # Things user mentioned
```

### 3. PromptAugmenter (Context Injection)

**Purpose**: Intelligently augment user prompts with relevant context

**Strategies**:
- **Implicit Context**: Always include current state
- **Explicit Context**: Add specific context based on prompt analysis
- **Historical Context**: Include relevant past interactions
- **Musical Context**: Add music theory context when relevant

**Example Augmentation**:
```
User: "Make it more jazzy"

Augmented Prompt:
"Current context: Piano playing C major chord progression (C-Am-F-G),
bass line in C major, tempo 120 BPM.

User request: Make it more jazzy

Musical context: Current key is C major, 4/4 time signature,
simple rock progression. Jazz modifications could include:
swing rhythm, 7th chords, syncopation, extended harmonies."
```

## State Management Operations

### 1. State Updates

```python
class ComposerMemory:
    def add_instrument(self, instrument: InstrumentMemory) -> None
    def remove_instrument(self, name: str) -> None
    def update_instrument_activity(self, name: str, sequence_id: int) -> None

    def add_sequence(self, sequence: SequenceMemory) -> None
    def remove_sequence(self, sequence_id: int) -> None
    def update_sequence_status(self, sequence_id: int, status: SequenceStatus) -> None

    def update_musical_context(self, context: MusicalContext) -> None
    def add_conversation_turn(self, turn: ConversationTurn) -> None
```

### 2. State Queries

```python
class ComposerMemory:
    def get_active_instruments(self) -> List[InstrumentMemory]
    def get_instruments_by_role(self, role: str) -> List[InstrumentMemory]
    def get_current_musical_context(self) -> MusicalContext
    def get_recent_conversation_context(self, turns: int = 3) -> List[ConversationTurn]
    def find_referenced_elements(self, text: str) -> List[str]
```

### 3. Musical Intelligence

```python
class MusicalAnalyzer:
    def analyze_harmonic_progression(self, sequences: List[SequenceMemory]) -> str
    def detect_key_signature(self, notes: List[Note]) -> Optional[str]
    def identify_musical_role(self, sequence: SequenceMemory) -> str
    def suggest_complementary_instruments(self, current_instruments: List[str]) -> List[str]
```

## Context Generation Examples

### 1. Basic State Context

```
"Current composition state:
- Instruments: piano (C0, melody), bass (C1, bassline), drums (C9, rhythm)
- Active sequences: 3 (2 looping)
- Key: C major, Tempo: 120 BPM, Time: 4/4
- Style: Jazz ballad
- Chord progression: Cmaj7 - Am7 - Dm7 - G7"
```

### 2. Contextual References

```
User: "Change that bass line to minor"

Context: "The user is referring to sequence #2 (bass instrument,
8-note looping pattern in C major). They want to modify it to
use minor tonality. Current bass line uses notes: C-E-G-C-G-E-C-G"
```

### 3. Musical Relationships

```
User: "Add some harmony"

Context: "Current melody is played by piano in C major.
Suitable harmony options:
- Second piano with chord voicings
- String section with sustained chords
- Vocal harmonies following the chord progression
Current chord progression supports traditional jazz harmonies."
```

## Implementation Strategy

### Phase 1: Basic State Tracking
1. Implement core data structures (`InstrumentMemory`, `SequenceMemory`)
2. Create basic `ComposerMemory` with CRUD operations
3. Simple context injection (current state only)

### Phase 2: Musical Intelligence
1. Add `MusicalContext` and analysis capabilities
2. Implement key detection and harmonic analysis
3. Enhanced context generation with musical understanding

### Phase 3: Conversational Memory
1. Add conversation history tracking
2. Implement reference resolution ("that bass line")
3. Context-aware prompt augmentation

### Phase 4: Advanced Features
1. Musical pattern recognition
2. Style and genre awareness
3. Compositional suggestions and intelligence

## Integration Points

### 1. LLMComposer Integration

```python
class LLMComposer:
    def __init__(self, ...):
        self.memory = ComposerMemory()
        self.context_builder = ContextBuilder(self.memory)
        self.prompt_augmenter = PromptAugmenter(self.context_builder)

    async def generate_and_execute(self, prompt: str) -> List[MIDIToolResult]:
        # Augment prompt with context
        augmented_prompt = self.prompt_augmenter.augment_prompt(prompt)

        # Generate and execute commands
        results = await self._generate_commands(augmented_prompt)

        # Update memory with results
        self.memory.record_interaction(prompt, results)

        return results
```

### 2. MIDIToolHandler Integration

```python
class MIDIToolHandler:
    def __init__(self, sequencer, instrument_manager, memory):
        self.memory = memory
        # ... existing init

    def execute_command(self, command: MIDICommand) -> MIDIToolResult:
        result = self._execute_command_impl(command)

        # Update memory based on command execution
        self.memory.update_from_command(command, result)

        return result
```

## Benefits

### 1. Enhanced User Experience
- **Natural references**: "Stop that drum pattern"
- **Musical continuity**: LLM understands ongoing composition
- **Intelligent suggestions**: Context-aware musical recommendations

### 2. Improved LLM Performance
- **Relevant context**: Only include pertinent information
- **Musical understanding**: Provide music theory context
- **Consistency**: Maintain musical coherence across interactions

### 3. Debugging and Development
- **State inspection**: Clear view of current composition state
- **Interaction history**: Track how conversations evolve compositions
- **Musical analysis**: Understand harmonic and rhythmic patterns

## Future Enhancements

### 1. Persistence Layer
- Save compositions to files
- Load previous sessions
- Export to MIDI/MusicXML

### 2. Advanced Musical Intelligence
- Genre-specific composition patterns
- Automatic arrangement suggestions
- Style transfer capabilities

### 3. Collaborative Features
- Multi-user composition sessions
- Shared musical memory
- Real-time collaboration context

## Technical Considerations

### 1. Performance
- In-memory storage for fast access
- Efficient context generation algorithms
- Lazy loading of complex musical analysis

### 2. Memory Management
- Automatic cleanup of old sequences
- Configurable history retention
- Memory usage monitoring

### 3. Extensibility
- Plugin architecture for new memory types
- Configurable context strategies
- Modular musical intelligence components

This design provides a robust foundation for stateful musical conversations while maintaining performance and extensibility for future enhancements.
