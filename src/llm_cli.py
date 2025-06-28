#!/usr/bin/env python3

"""LLM-powered CLI for AI Music Composer.

This CLI provides a conversational interface to the music composer,
allowing users to generate and control music through natural language.
"""

import asyncio
import os
import sys
from typing import List, Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

# Add src directory to Python path when running directly
if __name__ == "__main__":
    src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, src_dir)

from .config import get_default_bpm, get_openai_api_key
from .llm_composer import LLMComposer
from .llm_composer.midi_tools import MIDIToolHandler, MIDIToolResult
from .logging_config import get_logger, setup_logging
from .midi_generator import InstrumentManager, MIDIControllerAdapter, SequencerAdapter
from .midi_generator.midi_controller import MIDIController
from .midi_generator.sequencer import MIDISequencer
from .midi_generator.transport import PreciseTransport

console = Console()
logger = get_logger(__name__)


class LLMCLISession:
    """Manages an LLM CLI session with state awareness."""

    def __init__(self):
        """Initialize the CLI session."""
        self.controller = None
        self.transport = None
        self.sequencer = None
        self.instrument_manager = None
        self.llm_composer = None
        self.running = False

    def initialize_midi_system(self) -> bool:
        """Initialize the MIDI system.

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            self.controller = MIDIController()
            self.transport = PreciseTransport(initial_bpm=get_default_bpm())
            self.sequencer = MIDISequencer(self.controller, self.transport)

            # Create adapters and instrument manager
            note_player = MIDIControllerAdapter(self.controller)
            sequence_player = SequencerAdapter(self.sequencer)
            self.instrument_manager = InstrumentManager(note_player, sequence_player)

            logger.info("MIDI system initialized successfully")
            return True

        except Exception as e:
            console.print(f"[red]Failed to initialize MIDI system: {e}[/red]")
            logger.error(f"MIDI system initialization failed: {e}")
            return False

    def initialize_llm_composer(self) -> bool:
        """Initialize the LLM composer.

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Check for API key
            api_key = get_openai_api_key()
            if not api_key:
                console.print(
                    "[red]No OpenAI API key found. Please set OPENAI_API_KEY in your .env file.[/red]"
                )
                return False

            # Create MIDI tool handler
            midi_tool_handler = MIDIToolHandler(self.sequencer, self.instrument_manager)

            # Initialize LLM composer
            self.llm_composer = LLMComposer(midi_tool_handler=midi_tool_handler)

            logger.info("LLM composer initialized successfully")
            return True

        except Exception as e:
            console.print(f"[red]Failed to initialize LLM composer: {e}[/red]")
            logger.error(f"LLM composer initialization failed: {e}")
            return False

    def get_system_status(self) -> str:
        """Get current system status for LLM context.

        Returns:
            String describing current system state
        """
        status_parts = []

        # MIDI connection status
        if self.controller and self.controller.port:
            status_parts.append("✓ MIDI output connected")
        else:
            status_parts.append("✗ No MIDI output connected")

        # Transport status
        if self.transport:
            status_parts.append(f"♪ BPM: {self.transport.bpm}")
            if hasattr(self.transport, "is_running") and self.transport.is_running:
                status_parts.append("▶ Transport running")
            else:
                status_parts.append("⏸ Transport stopped")

        # Active instruments
        if self.instrument_manager:
            instruments = list(self.instrument_manager.instruments.keys())
            if instruments:
                status_parts.append(f"🎹 Instruments: {', '.join(instruments)}")
            else:
                status_parts.append("🎹 No instruments created")

        # Active sequences
        if self.sequencer:
            active_count = len(self.sequencer.active_sequences)
            if active_count > 0:
                status_parts.append(f"🎵 {active_count} active sequences")
            else:
                status_parts.append("🎵 No active sequences")

        return " | ".join(status_parts)

    def display_status(self):
        """Display current system status."""
        status = self.get_system_status()
        panel = Panel(
            status, title="[bold blue]System Status[/bold blue]", border_style="blue"
        )
        console.print(panel)

    def display_results(self, results: List[MIDIToolResult]):
        """Display LLM execution results.

        Args:
            results: List of MIDI tool results to display
        """
        if not results:
            console.print("[yellow]No results returned[/yellow]")
            return

        for i, result in enumerate(results, 1):
            if result.success:
                console.print(f"[green]✓ Command {i}: {result.message}[/green]")
            else:
                console.print(f"[red]✗ Command {i}: {result.message}[/red]")

            if result.data:
                # Display additional data if present
                table = Table(show_header=False, box=None, padding=(0, 1))
                for key, value in result.data.items():
                    table.add_row(f"[dim]{key}:[/dim]", str(value))
                console.print(table)

    async def process_prompt(self, prompt: str) -> bool:
        """Process a user prompt with the LLM.

        Args:
            prompt: User's natural language prompt

        Returns:
            True if processing should continue, False to exit
        """
        if not self.llm_composer:
            console.print("[red]LLM composer not initialized[/red]")
            return True

        try:
            # Add system context to the prompt
            context = f"Current system status: {self.get_system_status()}\n\nUser request: {prompt}"

            # Show thinking indicator
            with console.status("[bold green]🎵 Composing..."):
                results = await self.llm_composer.generate_and_execute(context)

            # Display results
            self.display_results(results)

            return True

        except Exception as e:
            console.print(f"[red]Error processing prompt: {e}[/red]")
            logger.error(f"Error processing prompt '{prompt}': {e}")
            return True

    def handle_command(self, user_input: str) -> bool:
        """Handle special CLI commands.

        Args:
            user_input: Raw user input

        Returns:
            True if this was a command and was handled, False if it's a regular prompt
        """
        if not user_input.startswith("/"):
            return False

        command = user_input[1:].strip().lower()
        return self._process_command(command)

    def _process_command(self, command: str) -> bool:
        """Process a parsed command.

        Args:
            command: The command string without the leading slash

        Returns:
            True if command was handled, "exit" if should exit
        """
        # Simple commands
        simple_commands = {
            "help": self.show_help,
            "status": self.display_status,
            "connect": self.handle_connect_command,
            "instruments": self.show_instruments,
            "sequences": self.show_sequences,
            "stop": self.handle_stop_command,
        }

        if command in simple_commands:
            simple_commands[command]()
            return True

        # Exit commands
        if command in ("quit", "exit"):
            return "exit"

        # Connect with port number
        if command.startswith("connect "):
            return self._handle_connect_with_port(command)

        # Unknown command
        console.print(f"[red]Unknown command: /{command}[/red]")
        console.print("Type [cyan]/help[/cyan] for available commands")
        return True

    def _handle_connect_with_port(self, command: str) -> bool:
        """Handle connect command with port number.

        Args:
            command: The full connect command string

        Returns:
            True (command was handled)
        """
        port_str = command[8:].strip()
        try:
            port_num = int(port_str)
            self.handle_connect_command(port_num)
        except ValueError:
            console.print(f"[red]Invalid port number: {port_str}[/red]")
        return True

    def show_help(self):
        """Display help information."""
        help_text = """
[bold cyan]LLM Music Composer CLI[/bold cyan]

[bold]Natural Language Commands:[/bold]
Just type what you want in plain English:
  • "Create a piano instrument"
  • "Play a C major scale"
  • "Create a looping bass line in G minor"
  • "Stop all music and start over"

[bold]CLI Commands:[/bold]
  [cyan]/status[/cyan]     - Show system status
  [cyan]/connect[/cyan]    - List and connect to MIDI ports
  [cyan]/connect N[/cyan]  - Connect to MIDI port N
  [cyan]/instruments[/cyan] - Show all instruments
  [cyan]/sequences[/cyan]  - Show active sequences
  [cyan]/stop[/cyan]      - Stop all sequences
  [cyan]/help[/cyan]      - Show this help
  [cyan]/quit[/cyan]      - Exit the CLI

[bold]Tips:[/bold]
  • Be specific about instruments and musical terms
  • Ask for status updates: "What's currently playing?"
  • Request modifications: "Make it louder" or "Change to minor key"
        """
        console.print(Panel(help_text.strip(), title="Help", border_style="cyan"))

    def handle_connect_command(self, port_num: Optional[int] = None):
        """Handle MIDI port connection."""
        if port_num is not None:
            success = self.controller.connect_port(port_num)
            if success:
                console.print(f"[green]Connected to MIDI port {port_num}[/green]")
            else:
                console.print(f"[red]Failed to connect to MIDI port {port_num}[/red]")
        else:
            console.print("[bold]Available MIDI ports:[/bold]")
            self.controller.list_ports()

    def show_instruments(self):
        """Show all created instruments."""
        if not self.instrument_manager.instruments:
            console.print("[yellow]No instruments created[/yellow]")
            return

        table = Table(title="Active Instruments")
        table.add_column("Name", style="cyan")
        table.add_column("Channel", style="magenta")
        table.add_column("Velocity", style="green")
        table.add_column("Transpose", style="yellow")
        table.add_column("Active Sequences", style="blue")

        for name, instrument in self.instrument_manager.instruments.items():
            active_seqs = len(instrument.get_active_sequences())
            table.add_row(
                name,
                str(instrument.channel),
                str(instrument.default_velocity),
                f"{instrument.transpose:+d}" if instrument.transpose != 0 else "0",
                str(active_seqs),
            )

        console.print(table)

    def show_sequences(self):
        """Show all active sequences."""
        if not self.sequencer.active_sequences:
            console.print("[yellow]No active sequences[/yellow]")
            return

        table = Table(title="Active Sequences")
        table.add_column("ID", style="cyan")
        table.add_column("Notes", style="magenta")
        table.add_column("Looping", style="green")
        table.add_column("Iteration", style="yellow")

        for seq_id, state in self.sequencer.active_sequences.items():
            table.add_row(
                str(seq_id),
                str(len(state.sequence.notes)),
                "Yes" if state.sequence.loop else "No",
                str(state.current_iteration),
            )

        console.print(table)

    def handle_stop_command(self):
        """Stop all sequences and instruments."""
        if self.instrument_manager:
            self.instrument_manager.stop_all_instruments()
        if self.sequencer:
            self.sequencer.clear_all_sequences()
            self.sequencer.all_notes_off()
        console.print("[yellow]Stopped all sequences and instruments[/yellow]")

    def cleanup(self):
        """Clean up resources."""
        try:
            if self.instrument_manager:
                self.instrument_manager.stop_all_instruments()
            if self.sequencer:
                self.sequencer.clear_all_sequences()
            if self.transport:
                self.transport.stop()
            if self.controller:
                self.controller.close()
            logger.info("Session cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


def _initialize_systems(session: LLMCLISession) -> bool:
    """Initialize MIDI and LLM systems.

    Args:
        session: The CLI session to initialize

    Returns:
        True if initialization successful, False otherwise
    """
    # ASCII Art Introduction
    # flake8: noqa
    ascii_art = """
[bold cyan]
                                    ~~~
                                   (   )
                                  (     )
                                 (       )
                                (  🎵 🎹 🎵  )
                             ∩───(           )───∩
                            (     ~~~~~~~~~~     )
                           (    AI MUSIC COMPOSER   )
                          (    ~~~~~~~~~~~~~~~~    )
                         (                          )
                        (  ~~~~~~~~~~~~~~~~~~~~~~~~  )
                       (                              )
                      (  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  )
                     (                                    )
                    (  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  )
                   (                                          )
                  (                                            )
                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
[/bold cyan]

[bold magenta]🎼 MIDI Generation Through Natural Conversation 🎵[/bold magenta]

[bold white]Simply describe the music you want in plain English:[/bold white]
[italic green]"Create a gentle piano melody in C major"
"Add a bass line that follows the chord progression"
"Make it sound more upbeat and energetic"[/italic green]

[bold yellow]✨ AI translates your words into real-time MIDI ✨[/bold yellow]

[dim]Created by Luke Mino-Altherr[/dim]
"""
    console.print(ascii_art)
    console.print("[bold green]Initializing systems...[/bold green]")

    if not session.initialize_midi_system():
        return False

    if not session.initialize_llm_composer():
        return False

    # Start transport
    session.transport.start()
    console.print("[green]✓ Systems initialized successfully[/green]")
    console.print(
        "\nType [cyan]/help[/cyan] for commands or just describe what music you want!"
    )
    session.display_status()
    return True


async def _run_main_loop(session: LLMCLISession) -> None:
    """Run the main CLI loop.

    Args:
        session: The CLI session to run
    """
    while True:
        try:
            user_input = Prompt.ask("\n[bold green]🎵>[/bold green]").strip()

            if not user_input:
                continue

            # Handle special commands
            command_result = session.handle_command(user_input)
            if command_result == "exit":
                break
            elif command_result:
                continue  # Command was handled

            # Process as LLM prompt
            should_continue = await session.process_prompt(user_input)
            if not should_continue:
                break

        except KeyboardInterrupt:
            console.print("\n[yellow]Use /quit to exit gracefully[/yellow]")
        except EOFError:
            break


async def run_cli_session():
    """Run the main CLI session."""
    session = LLMCLISession()

    try:
        if not _initialize_systems(session):
            return 1

        await _run_main_loop(session)

    finally:
        console.print("\n[blue]Cleaning up...[/blue]")
        session.cleanup()
        console.print("[blue]Goodbye![/blue]")

    return 0


@click.command()
def main():
    """LLM-powered music composition CLI."""
    # Setup logging
    setup_logging()

    # Run the async CLI session
    return asyncio.run(run_cli_session())


if __name__ == "__main__":
    sys.exit(main())
