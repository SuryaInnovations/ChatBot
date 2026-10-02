"""
Terminal / CLI interface for the All-in-One AI Assistant.
Interactive REPL using rich formatting and live status traces.
"""

import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt

import core.config
from core.conversation import ConversationSession
from core.llm_provider import LLMProvider
from core.orchestrator import ChatbotOrchestrator

console = Console()

def run_cli():
    console.print(Panel.fit(
        "[bold cyan]All-in-One AI Assistant[/bold cyan]\n"
        "[dim]Universal problem-solving pipeline active. Type 'exit' or 'quit' to end.[/dim]",
        title="🤖 AI ASSISTANT",
        border_style="cyan"
    ))

    # Detect provider
    groq_key = os.environ.get("GROQ_API_KEY")
    gemini_key = os.environ.get("GEMINI_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")

    if groq_key:
        provider = "groq"
    elif gemini_key:
        provider = "gemini"
    elif openai_key:
        provider = "openai"
    else:
        provider = "autonomous_local"

    console.print(f"[green]Initialized Provider:[/green] [bold]{provider.upper()}[/bold]")

    llm = LLMProvider(provider=provider)
    orchestrator = ChatbotOrchestrator(provider=llm)
    session = ConversationSession()

    while True:
        try:
            user_input = Prompt.ask("\n[bold green]You[/bold green]")
            if not user_input.strip():
                continue
            if user_input.lower() in ["exit", "quit", "q"]:
                console.print("[yellow]Exiting assistant. Goodbye![/yellow]")
                break
            if user_input.lower() in ["clear", "reset"]:
                session.clear()
                console.print("[dim]Conversation history cleared.[/dim]")
                continue

            with console.status("[bold blue]Executing Universal Pipeline...[/bold blue]", spinner="dots") as status:
                def update_cb(txt):
                    status.update(f"[bold blue]{txt}[/bold blue]")

                result = orchestrator.process_message(
                    session=session,
                    user_message=user_input,
                    on_status_update=update_cb
                )

            # Display executed tools
            tools_used = result.get("executed_tools", [])
            if tools_used:
                tool_names = ", ".join([t.get("name") for t in tools_used])
                console.print(f"[dim]🛠️ Tools used: {tool_names}[/dim]")

            # Render response
            console.print("\n[bold cyan]Assistant:[/bold cyan]")
            console.print(Markdown(result.get("content", "")))

            # Generated artifacts
            for art in result.get("generated_artifacts", []):
                console.print(f"[green]📁 Generated Artifact:[/green] {art.get('name')} at `{art.get('path')}`")

        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Session ended.[/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error:[/red] {str(e)}")

if __name__ == "__main__":
    run_cli()
