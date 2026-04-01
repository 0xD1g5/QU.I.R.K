"""QU.I.R.K. CLI startup banner."""
from rich.console import Console
from rich.panel import Panel
from rich.text import Text


BANNER_ART = """\
 ___  ___   ___ ____  ____  _  __
/ _ \| | | |_ _|  _ \| | |/ |/ /
| | | | | |  | || |_) | | `| / /
| |_| | |_| _| ||  _ <| |  | / /
 \__\_\___/ |___|_| \_\_|  |_/_/"""


def print_banner(version: str, quiet: bool = False) -> None:
    """Print the QU.I.R.K. startup banner unless quiet=True."""
    if quiet:
        return
    console = Console()
    title = Text()
    title.append("QU.I.R.K.", style="bold #3b9dff")
    title.append(f"  v{version}", style="dim white")
    subtitle = Text("Quantum Infrastructure Readiness Kit", style="dim #3b9dff")
    content = Text()
    content.append(BANNER_ART, style="#3b9dff")
    content.append("\n")
    content.append_text(subtitle)
    panel = Panel(content, title=title, border_style="#3b9dff", padding=(0, 1))
    console.print(panel)
