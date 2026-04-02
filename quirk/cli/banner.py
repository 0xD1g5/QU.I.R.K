"""QU.I.R.K. CLI startup banner — random art + palette each invocation."""
import random
from typing import NamedTuple

from rich.console import Console
from rich.panel import Panel
from rich.text import Text


# ── ASCII art variants ────────────────────────────────────────────────────────

_BIG = (
    "  ___   _   _  ___  ____   _  __\n"
    " / _ \\ | | | ||_ _||  _ \\ | |/ /\n"
    "| | | || | | | | | | |_) || ' /\n"
    "| |_| || |_| | | | |  _ < | . \\\n"
    " \\__\\_\\ \\___/ |___|_| \\_\\|_|\\_\\"
)

_SHADOW = (
    " ██████╗ ██╗   ██╗ ██╗ ██████╗ ██╗  ██╗\n"
    "██╔═══██╗██║   ██║ ██║ ██╔══██╗██║ ██╔╝\n"
    "██║   ██║██║   ██║ ██║ ██████╔╝█████╔╝ \n"
    "██║▄▄ ██║██║   ██║ ██║ ██╔══██╗██╔═██╗ \n"
    "╚██████╔╝╚██████╔╝ ██║ ██║  ██║██║  ██╗\n"
    " ╚══▀▀═╝  ╚═════╝  ╚═╝ ╚═╝  ╚═╝╚═╝  ╚═╝"
)

_SLANT = (
    "   ____    __  __    _    ___    __ __\n"
    "  / __ \\  / / / /  (_)  / _ \\  / //_/\n"
    " / / / / / / / /  / /  / /_) |/ ,<   \n"
    "/ /_/ /  \\ \\/ /  / /  / _, _// /| |  \n"
    "\\___\\_\\   \\__/  (_)  /_/ |_|/_/ |_|  "
)

BANNER_VARIANTS = [_BIG, _SHADOW, _SLANT]


# ── Color palettes ────────────────────────────────────────────────────────────

class _Palette(NamedTuple):
    name: str
    art: str
    title: str
    subtitle: str
    domains: str
    border: str
    sep: str


PALETTES = [
    _Palette("electric blue",
        art="#00cfff", title="#00e5ff", subtitle="#3b9dff",
        domains="#4a7aaa", border="#1a5a9a", sep="#2a4a6a"),
    _Palette("matrix green",
        art="#00ff41", title="#39ff14", subtitle="#00cc33",
        domains="#007a1f", border="#004a10", sep="#003a0d"),
    _Palette("neon magenta",
        art="#ff2d9b", title="#ff69b4", subtitle="#cc0077",
        domains="#8a0050", border="#7a0045", sep="#5a0035"),
    _Palette("gold",
        art="#ffb700", title="#ffd700", subtitle="#cc8800",
        domains="#7a5500", border="#6a4500", sep="#4a3000"),
    _Palette("void purple",
        art="#c77dff", title="#e040fb", subtitle="#9d4edd",
        domains="#5a2a8a", border="#4a1a7a", sep="#3a1060"),
    _Palette("ember",
        art="#ff6b35", title="#ff4500", subtitle="#cc3300",
        domains="#7a2000", border="#6a1a00", sep="#4a1000"),
    _Palette("arctic teal",
        art="#00e5b4", title="#00ffd0", subtitle="#00b894",
        domains="#006a52", border="#007a5a", sep="#005040"),
]

BYLINE = "0xD1g5 // fulcrum"
DOMAINS = "TLS · SSH · JWT · CBOM · KMS · PQC"


def print_banner(version: str, quiet: bool = False) -> None:
    """Print the QU.I.R.K. startup banner unless quiet=True."""
    if quiet:
        return

    art = random.choice(BANNER_VARIANTS)
    p = random.choice(PALETTES)

    console = Console()

    title = Text()
    title.append("QU.I.R.K.", style=f"bold {p.title}")
    title.append(f"  v{version}", style=f"bold {p.subtitle}")

    content = Text()
    content.append(art, style=f"bold {p.art}")
    content.append("\n")
    content.append("· · · · · · · · · · · · · · · · · · ·", style=f"dim {p.sep}")
    content.append("\n")
    content.append("Quantum Infrastructure Readiness Kit", style=f"bold {p.subtitle}")
    content.append("  ")
    content.append(DOMAINS, style=f"dim {p.domains}")
    content.append("\n")
    content.append(BYLINE, style=f"dim {p.art}")

    panel = Panel(content, title=title, border_style=p.border, padding=(0, 1))
    console.print(panel)
