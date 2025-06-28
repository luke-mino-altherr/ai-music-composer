"""Context generation for LLM Composer memory system."""

from dataclasses import dataclass
from typing import Dict, List, Optional

from .memory import ComposerMemory, SequenceStatus


@dataclass
class StateContext:
    """Current system state context."""

    active_instruments: List[str]
    active_sequences: List[str]
    system_status: str
    instrument_details: Dict[str, str]


@dataclass
class MusicContext:
    """Musical/compositional context."""

    current_key: Optional[str]
    tempo: float
    active_chord_progression: List[str]
    harmonic_analysis: str
    rhythmic_pattern: str
    musical_style: Optional[str]


@dataclass
class HistoryContext:
    """Relevant conversation history context."""

    recent_requests: List[str]
    musical_themes: List[str]
    referenced_elements: List[str]


class ContextBuilder:
    """Builds contextual information for LLM prompts."""

    def __init__(self, memory: ComposerMemory):
        """Initialize context builder with memory reference."""
        self.memory = memory

    def build_state_context(self) -> StateContext:
        """Build current state context."""
        active_instruments = []
        instrument_details = {}

        for name, instrument in self.memory.instruments.items():
            role_desc = instrument.musical_role.value
            channel_desc = f"Ch{instrument.channel}"
            details = f"{role_desc} on {channel_desc}"

            if instrument.active_sequences:
                details += f" ({len(instrument.active_sequences)} sequences)"
                active_instruments.append(name)

            instrument_details[name] = details

        active_sequences = []
        for seq_id, sequence in self.memory.sequences.items():
            if sequence.status == SequenceStatus.ACTIVE:
                desc = f"#{seq_id}: {sequence.musical_purpose}"
                if sequence.is_looping:
                    desc += " (looping)"
                active_sequences.append(desc)

        system_status = self.memory.get_composition_summary()

        return StateContext(
            active_instruments=active_instruments,
            active_sequences=active_sequences,
            system_status=system_status,
            instrument_details=instrument_details,
        )

    def build_music_context(self) -> MusicContext:
        """Build musical context."""
        musical_ctx = self.memory.get_current_musical_context()

        # Get harmonic analysis
        harmonic_analysis = self.memory.get_harmonic_analysis()

        # Analyze rhythmic patterns
        rhythmic_pattern = self._analyze_rhythmic_patterns()

        return MusicContext(
            current_key=musical_ctx.current_key,
            tempo=musical_ctx.current_tempo,
            active_chord_progression=musical_ctx.chord_progression,
            harmonic_analysis=harmonic_analysis,
            rhythmic_pattern=rhythmic_pattern,
            musical_style=musical_ctx.musical_style,
        )

    def build_history_context(self, turns: int = 3) -> HistoryContext:
        """Build conversation history context."""
        recent_turns = self.memory.get_recent_conversation_context(turns)

        recent_requests = []
        musical_themes = set()
        referenced_elements = set()

        for turn in recent_turns:
            # Add user request
            recent_requests.append(turn.user_prompt)

            # Extract musical themes from intent
            if turn.musical_intent:
                musical_themes.add(turn.musical_intent)

            # Add referenced elements
            referenced_elements.update(turn.referenced_elements)

        return HistoryContext(
            recent_requests=recent_requests,
            musical_themes=list(musical_themes),
            referenced_elements=list(referenced_elements),
        )

    def _analyze_rhythmic_patterns(self) -> str:
        """Analyze rhythmic patterns in active sequences."""
        active_sequences = self.memory.get_active_sequences()
        if not active_sequences:
            return "No active rhythmic patterns"

        pattern_types = []

        # Check for different types of rhythmic content
        rhythm_seqs = [
            s for s in active_sequences if s.musical_purpose in ["drums", "percussion"]
        ]
        bass_seqs = [s for s in active_sequences if s.musical_purpose == "bassline"]
        melody_seqs = [s for s in active_sequences if s.musical_purpose == "melody"]

        if rhythm_seqs:
            pattern_types.append("percussion patterns")
        if bass_seqs:
            pattern_types.append("bass rhythms")
        if melody_seqs:
            pattern_types.append("melodic rhythms")

        if pattern_types:
            return f"Active: {', '.join(pattern_types)}"
        else:
            return "Simple rhythmic content"


class PromptAugmenter:
    """Augments user prompts with relevant context."""

    def __init__(self, context_builder: ContextBuilder):
        """Initialize with context builder."""
        self.context_builder = context_builder
        self.memory = context_builder.memory

    def augment_prompt(self, user_prompt: str) -> str:
        """Augment user prompt with relevant context."""
        # Analyze prompt to determine what context is needed
        context_needs = self._analyze_prompt_context_needs(user_prompt)

        # Build contexts based on needs
        context_parts = []

        if context_needs.get("state", True):  # Always include basic state
            state_context = self.context_builder.build_state_context()
            context_parts.append(self._format_state_context(state_context))

        if context_needs.get("musical", False):
            music_context = self.context_builder.build_music_context()
            context_parts.append(self._format_music_context(music_context))

        if context_needs.get("history", False):
            history_context = self.context_builder.build_history_context()
            context_parts.append(self._format_history_context(history_context))

        if context_needs.get("references", False):
            references = self._resolve_references(user_prompt)
            if references:
                context_parts.append(f"Referenced elements: {references}")

        # Combine context with user prompt
        if context_parts:
            context_section = "\n".join(context_parts)
            return f"{context_section}\n\nUser request: {user_prompt}"
        else:
            return user_prompt

    def _analyze_prompt_context_needs(self, prompt: str) -> Dict[str, bool]:
        """Analyze what context the prompt needs."""
        prompt_lower = prompt.lower()

        needs = {
            "state": True,  # Always include basic state
            "musical": False,
            "history": False,
            "references": False,
        }

        # Musical context triggers
        musical_keywords = [
            "key",
            "chord",
            "scale",
            "harmony",
            "progression",
            "style",
            "major",
            "minor",
            "jazz",
            "classical",
            "tempo",
            "bpm",
        ]
        if any(keyword in prompt_lower for keyword in musical_keywords):
            needs["musical"] = True

        # History context triggers
        history_keywords = [
            "before",
            "previous",
            "earlier",
            "last",
            "recent",
            "remember",
        ]
        if any(keyword in prompt_lower for keyword in history_keywords):
            needs["history"] = True

        # Reference triggers
        reference_words = ["that", "this", "the", "it", "them", "those"]
        if any(word in prompt_lower for word in reference_words):
            needs["references"] = True

        return needs

    def _resolve_references(self, prompt: str) -> str:
        """Resolve references in the prompt to specific elements."""
        referenced_elements = self.memory.find_referenced_elements(prompt)

        if not referenced_elements:
            return ""

        # Group by type
        instruments = [
            elem.split(":")[1]
            for elem in referenced_elements
            if elem.startswith("instrument:")
        ]
        musical_terms = [
            elem.split(":")[1]
            for elem in referenced_elements
            if elem.startswith("musical_term:")
        ]

        resolution_parts = []

        if instruments:
            resolution_parts.append(f"instruments mentioned: {', '.join(instruments)}")

        if musical_terms:
            resolution_parts.append(f"musical concepts: {', '.join(musical_terms)}")

        # Add context about what "that" or "this" might refer to
        if any("reference:" in elem for elem in referenced_elements):
            recent_elements = self._get_recent_musical_elements()
            if recent_elements:
                resolution_parts.append(f"likely referring to: {recent_elements}")

        return "; ".join(resolution_parts)

    def _get_recent_musical_elements(self) -> str:
        """Get recently created/modified musical elements."""
        # Get most recently active sequences
        recent_sequences = sorted(
            self.memory.sequences.values(), key=lambda s: s.created_at, reverse=True
        )[:3]

        if recent_sequences:
            descriptions = []
            for seq in recent_sequences:
                desc = f"{seq.musical_purpose} on {seq.instrument_name}"
                if seq.is_looping:
                    desc += " (looping)"
                descriptions.append(desc)
            return ", ".join(descriptions)

        return "no recent musical elements"

    def _format_state_context(self, state_context: StateContext) -> str:
        """Format state context for prompt."""
        lines = ["Current composition state:"]

        if state_context.active_instruments:
            inst_list = []
            for name in state_context.active_instruments:
                details = state_context.instrument_details.get(name, "")
                inst_list.append(f"{name} ({details})")
            lines.append(f"- Active instruments: {', '.join(inst_list)}")
        else:
            lines.append("- No active instruments")

        if state_context.active_sequences:
            lines.append(
                f"- Active sequences: {', '.join(state_context.active_sequences)}"
            )
        else:
            lines.append("- No active sequences")

        return "\n".join(lines)

    def _format_music_context(self, music_context: MusicContext) -> str:
        """Format musical context for prompt."""
        lines = ["Musical context:"]

        if music_context.current_key:
            lines.append(f"- Key: {music_context.current_key}")

        lines.append(f"- Tempo: {music_context.tempo} BPM")

        if music_context.musical_style:
            lines.append(f"- Style: {music_context.musical_style}")

        if music_context.active_chord_progression:
            progression = " - ".join(music_context.active_chord_progression)
            lines.append(f"- Chord progression: {progression}")

        if music_context.harmonic_analysis:
            lines.append(f"- Harmonic analysis: {music_context.harmonic_analysis}")

        if music_context.rhythmic_pattern:
            lines.append(f"- Rhythmic patterns: {music_context.rhythmic_pattern}")

        return "\n".join(lines)

    def _format_history_context(self, history_context: HistoryContext) -> str:
        """Format conversation history context for prompt."""
        lines = ["Recent conversation context:"]

        if history_context.recent_requests:
            lines.append("- Recent requests:")
            for i, request in enumerate(history_context.recent_requests[-3:], 1):
                lines.append(f"  {i}. {request}")

        if history_context.musical_themes:
            themes = ", ".join(history_context.musical_themes)
            lines.append(f"- Musical themes discussed: {themes}")

        return "\n".join(lines)


class ContextualPromptGenerator:
    """Generates contextually-aware prompts for specific scenarios."""

    def __init__(self, memory: ComposerMemory):
        """Initialize with memory reference."""
        self.memory = memory
        self.context_builder = ContextBuilder(memory)

    def generate_status_prompt(self) -> str:
        """Generate a prompt asking LLM to describe current state."""
        state_context = self.context_builder.build_state_context()
        music_context = self.context_builder.build_music_context()

        return f"""Please provide a natural language description of the current musical composition:

{self.context_builder._format_state_context(state_context)}

{self.context_builder._format_music_context(music_context)}

Describe what's currently playing in a way that helps the user understand the musical content."""

    def generate_suggestion_prompt(self) -> str:
        """Generate a prompt asking LLM for musical suggestions."""
        state_context = self.context_builder.build_state_context()
        music_context = self.context_builder.build_music_context()

        return f"""Based on the current composition, suggest musical elements that could be added:

{self.context_builder._format_state_context(state_context)}

{self.context_builder._format_music_context(music_context)}

What would be good musical additions or modifications to enhance this composition?"""
