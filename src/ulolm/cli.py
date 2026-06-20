import sys
import os
import time
from pathlib import Path

# Try importing Rich for advanced styling, fallback to ANSI if not available
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.markdown import Markdown
    HAS_RICH = True
    console = Console()
except ImportError:
    HAS_RICH = False

# Add parent 'src' directory to sys.path to resolve local package imports
src_dir = Path(__file__).resolve().parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# Import local modules
from ulolm.config import Config
from ulolm.models import ModelEngine
from ulolm.memory import ProjectMemory
from ulolm.router import ExpertRouter
from ulolm.executor import WorkspaceExecutor

def print_banner(config):
    model = config.active_model
    backend = config.backend
    workspace = config.workspace_path
    
    if HAS_RICH:
        banner = (
            f"[bold cyan]UloLM Ready[/bold cyan]\n"
            f"[dim]Current Model:[/dim] [green]{model}[/green] [dim]({backend} backend)[/dim]\n"
            f"[dim]Active Workspace:[/dim] [yellow]{workspace}[/yellow]"
        )
        console.print(Panel(banner, border_style="cyan"))
    else:
        print("\033[96m\033[1mUloLM Ready\033[0m")
        print(f"\033[90mCurrent Model:\033[0m \033[92m{model}\033[0m \033[90m({backend} backend)\033[0m")
        print(f"\033[90mActive Workspace:\033[0m \033[93m{workspace}\033[0m")
        print("-" * 50)

def main():
    # Load configuration
    config = Config()
    config.load()
    
    # Initialize workspace memory and executor
    memory = ProjectMemory(config.workspace_path)
    executor = WorkspaceExecutor(config.workspace_path)
    router = ExpertRouter()
    engine = ModelEngine(config)
    
    # Initial scan of codebase removed to prevent blocking on large directories.
    # Users can manually trigger a scan with `/scan`
    if not memory.db_path.exists():
        memory.initialize()
    print_banner(config)
    
    while True:
        try:
            # Read user input
            if HAS_RICH:
                user_input = console.input("\n[bold blue]You:[/bold blue]\n> ")
            else:
                user_input = input("\nYou:\n> ")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting UloLM...")
            break
            
        user_input = user_input.strip()
        if not user_input:
            continue
            
        if user_input.lower() in ["exit", "quit", "/exit"]:
            print("Exiting UloLM...")
            break
            
        if user_input.startswith("/config"):
            parts = user_input.split(maxsplit=2)
            if len(parts) == 3:
                key, val = parts[1], parts[2]
                if key == "backend":
                    config.backend = val
                elif key == "model":
                    config.active_model = val
                elif key == "gemini_api_key":
                    config.gemini_api_key = val
                elif key == "openai_api_key":
                    config.openai_api_key = val
                config.save(Path(config.workspace_path) / ".ulolm" / "config.json")
                print(f"Updated config {key} = {val}")
            else:
                print("Usage: /config <backend|model|gemini_api_key|openai_api_key> <value>")
            continue
            
        if user_input == "/models":
            from ulolm.generative import AVAILABLE_MODELS, GenerativeEngine
            gen = GenerativeEngine(config.workspace_path)
            current = gen.model_key
            if HAS_RICH:
                console.print("\n[bold cyan]Available Native Models (UloLlama)[/bold cyan]")
                console.print(f"[dim]{'Key':<20} {'Name':<35} {'RAM':<8}[/dim]")
                console.print("[dim]" + "─" * 63 + "[/dim]")
                for key, info in AVAILABLE_MODELS.items():
                    marker = " [green]◀ active[/green]" if key == current else ""
                    console.print(f"  [yellow]{key:<20}[/yellow] {info['name']:<35} [dim]{info['ram']:<8}[/dim]{marker}")
                console.print(f"\n[dim]Switch with:[/dim] /model <key>")
            else:
                print("\nAvailable Native Models (UloLlama)")
                for key, info in AVAILABLE_MODELS.items():
                    marker = " <-- active" if key == current else ""
                    print(f"  {key:<20} {info['name']:<35} {info['ram']:<8}{marker}")
                print(f"\nSwitch with: /model <key>")
            continue

        if user_input.startswith("/model "):
            model_key = user_input.split(maxsplit=1)[1].strip()
            from ulolm.generative import GenerativeEngine
            gen = GenerativeEngine(config.workspace_path)
            success, msg = gen.set_model(model_key)
            if HAS_RICH:
                if success:
                    console.print(f"[bold green]✔ {msg}[/bold green]")
                else:
                    console.print(f"[bold red]✖ {msg}[/bold red]")
            else:
                print(f"{'✔' if success else '✖'} {msg}")
            continue

        if user_input == "/train_gen":
            from ulolm.generative import GenerativeEngine
            gen_engine = GenerativeEngine(config.workspace_path)
            model_name = gen_engine.model_info['name']
            
            if HAS_RICH:
                from rich.progress import Progress, BarColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn, TextColumn
                
                progress = Progress(
                    TextColumn("[bold cyan]{task.description}"),
                    BarColumn(),
                    DownloadColumn(),
                    TransferSpeedColumn(),
                    TimeRemainingColumn(),
                    transient=True
                )
                
                with progress:
                    task = progress.add_task(f"Downloading {model_name}...", total=None)
                    
                    def cb(downloaded, total):
                        if total:
                            progress.update(task, completed=downloaded, total=total)
                        else:
                            progress.update(task, completed=downloaded)
                            
                    success, msg = gen_engine.train_on_workspace(progress_callback=cb)
                
                if success:
                    console.print(f"[bold green]✔ {msg}[/bold green]")
                else:
                    console.print(f"[bold red]✖ {msg}[/bold red]")
            else:
                print(f"Downloading {model_name}...")
                last_pct = -1
                
                def cb(downloaded, total):
                    nonlocal last_pct
                    if total:
                        pct = int((downloaded / total) * 100)
                        if pct % 5 == 0 and pct != last_pct:
                            print(f"Progress: {pct}% ({downloaded // (1024*1024)}MB / {total // (1024*1024)}MB)")
                            last_pct = pct
                    else:
                        if downloaded % (10 * 1024 * 1024) == 0:
                            print(f"Downloaded: {downloaded // (1024*1024)}MB")
                            
                success, msg = gen_engine.train_on_workspace(progress_callback=cb)
                print(f"{'✔' if success else '✖'} {msg}")
            continue

        if user_input.startswith("/train "):
            parts = user_input.split(maxsplit=2)
            if len(parts) == 3:
                intent, text = parts[1].upper(), parts[2]
                memory.save_training_example(intent, text)
                if HAS_RICH:
                    console.print(f"[bold green]✔ Successfully trained local model:[/bold green] '{text}' -> {intent}")
                else:
                    print(f"✔ Successfully trained local model: '{text}' -> {intent}")
            else:
                print("Usage: /train <INTENT> <example prompt text>")
            continue
            
        if user_input == "/info":
            context = memory.get_project_context()
            if HAS_RICH:
                console.print(Panel(context, title="Workspace Memory Info", border_style="yellow"))
            else:
                print(context)
            continue
            
        if user_input == "/help":
            help_text = (
                "UloLM CLI Commands:\n"
                "  /models         - Lists all available native AI models\n"
                "  /model <key>    - Switches the active native model (e.g. /model deepseek-r1-7b)\n"
                "  /train_gen      - Downloads and initializes the selected native model\n"
                "  /info           - Displays project state and indexed symbols\n"
                "  /config <k> <v> - Modifies configuration (e.g. /config backend native)\n"
                "  /train <i> <t>  - Teaches the intent classifier a new pattern\n"
                "  /scan           - Re-indexes workspace files and symbols\n"
                "  /help           - Displays this menu\n"
                "  /exit           - Closes the application"
            )
            print(help_text)
            continue
            
        if user_input == "/scan":
            if HAS_RICH:
                with console.status("[cyan]Scanning workspace files and indexing symbols...", spinner="dots"):
                    modified = memory.scan_and_sync()
            else:
                print("Scanning workspace files and indexing symbols...")
                modified = memory.scan_and_sync()
                
            if HAS_RICH:
                console.print(f"[dim]Index Sync complete. Detected {len(modified)} file changes.[/dim]")
            else:
                print(f"Index Sync complete. Detected {len(modified)} file changes.")
            continue
            
        # 1. Sync file system modifications before inference (REMOVED)
        # We now rely on the user to run /scan manually, or auto-sync after writes.
            
        # 2. Expert Routing
        expert = router.route(user_input)
        if HAS_RICH:
            console.print(f"[bold purple][Expert Router][/bold purple] Routing to [bold yellow]{expert.name}[/bold yellow]...")
        else:
            print(f"[Expert Router] Routing to {expert.name}...")
            
        # 3. Model Query with injected workspace memory
        project_context = memory.get_project_context()
        tool_instructions = (
            "\n\nAVAILABLE TOOLS:\n"
            "You have access to the following tools. To execute a tool, output a JSON block formatted exactly like this:\n"
            "```json\n"
            "[\n"
            "  {\n"
            "    \"name\": \"write_file\",\n"
            "    \"parameters\": {\"path\": \"relative/path/to/file.py\", \"content\": \"new file contents\"}\n"
            "  }\n"
            "]\n"
            "```\n"
        )
        system_context = f"{expert.system_prompt}\n\n{project_context}{tool_instructions}"
        
        response = None
        if HAS_RICH:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True
            ) as progress:
                task = progress.add_task(description=f"Querying model via {config.backend}...", total=None)
                response = engine.query(user_input, system_context)
        else:
            print(f"Querying model via {config.backend}...")
            response = engine.query(user_input, system_context)
            
        # 4. Execute Tools Generated by Model
        if response.tools_to_call:
            for tool in response.tools_to_call:
                tool_name = tool.get("name")
                tool_params = tool.get("parameters", {})
                
                if HAS_RICH:
                    console.print(f"[dim]Security Gatekeeper: Approved Action '{tool_name}' for path '{tool_params.get('path')}'[/dim]")
                else:
                    print(f"Security Gatekeeper: Approved Action '{tool_name}' for path '{tool_params.get('path')}'")
                    
                exec_res = executor.execute_tool(tool)
                
                if exec_res.get("status") == "success":
                    if HAS_RICH:
                        console.print(f"  [green]✔[/green] File [yellow]{exec_res.get('filepath')}[/yellow] generated ({exec_res.get('bytes_written')} bytes)")
                    else:
                        print(f"  ✔ File {exec_res.get('filepath')} generated ({exec_res.get('bytes_written')} bytes)")
                else:
                    if HAS_RICH:
                        console.print(f"  [red]✘[/red] Error: {exec_res.get('message')}")
                    else:
                        print(f"  ✘ Error: {exec_res.get('message')}")
                        
            # Sync memory index again after writes
            memory.scan_and_sync()
            
        # 5. Output response text
        if HAS_RICH:
            console.print("\n[bold green]Assistant:[/bold green]")
            console.print(Markdown(response.text))
        else:
            print("\nAssistant:")
            print(response.text)

if __name__ == "__main__":
    main()
