import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from config import config
from chatbot import GeminiChatbot

console = Console()


def show_banner():
    console.print(
        Panel.fit(
            f"[bold cyan]Google Gemini AI Chatbot[/bold cyan]\n"
            f"[dim]Modelo ativo: [green]{config.model}[/green][/dim]\n"
            f"[dim]Skill/Comportamento: [magenta]{config.active_skill}[/magenta][/dim]\n"
            f"[dim]Banco de Dados: [blue]SQLite (In-Memory)[/blue][/dim]\n"
            f"[dim]Comandos: [yellow]/limpar[/yellow] (reinicia o chat) | [yellow]/sair[/yellow] (encerra)[/dim]",
            border_style="cyan",
            title="🤖 Assistente Virtual",
        )
    )


def main():
    try:
        bot = GeminiChatbot(config=config, session_id="cli_user")
    except ValueError as err:
        console.print(f"[bold red]Erro de configuração:[/bold red] {err}")
        sys.exit(1)
    except FileNotFoundError as err:
        console.print(f"[bold red]Erro de Skill:[/bold red] {err}")
        sys.exit(1)

    show_banner()

    while True:
        try:
            user_input = Prompt.ask("\n[bold green]Você[/bold green]").strip()

            if not user_input:
                continue

            if user_input.lower() in ("/sair", "sair", "exit", "quit"):
                console.print("[dim]Até logo![/dim]")
                break

            if user_input.lower() in ("/limpar", "limpar", "clear"):
                bot.reset()
                console.print("[yellow]Histórico da conversa reiniciado na memória![/yellow]")
                continue

            console.print("\n[bold cyan]Gemini:[/bold cyan]")
            
            # Streaming da resposta
            for chunk in bot.send_message_stream(user_input):
                sys.stdout.write(chunk)
                sys.stdout.flush()

            sys.stdout.write("\n")
            sys.stdout.flush()

        except KeyboardInterrupt:
            console.print("\n[dim]Conversa encerrada.[/dim]")
            break
        except Exception as err:
            console.print(f"\n[bold red]Erro ao processar mensagem:[/bold red] {err}")


if __name__ == "__main__":
    main()
