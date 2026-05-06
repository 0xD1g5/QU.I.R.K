"""QU.I.R.K. CLI startup banner — random art + palette each invocation."""
import random
from typing import NamedTuple

from rich.console import Console
from rich.panel import Panel
from rich.text import Text


# ── ASCII art variants ────────────────────────────────────────────────────────
# NOTE: All art strings use r"..." (raw strings) so that backslashes are
# treated as literal characters and not interpreted as Python escape sequences
# (e.g. \n, \t, \r, \b etc.).  The explicit + "\n" at the end of each line
# provides the real newline that terminates each row of art.

_ACROBAT = (
    r"      o__ __o        o         o   __o__   o__ __o         o         o/ " + "\n"
    r"     /v     v\      <|>       <|>    |    <|     v\       <|>       /v  " + "\n"
    r"    />       <\     / \       / \   / \   / \     <\      / >      />   " + "\n"
    r"  o/           \o   \o/       \o/   \o/   \o/     o/      \o__ __o/     " + "\n"
    r" <|             |>   |         |     |     |__  _<|        |__ __|      " + "\n"
    r"  \\           //   < >       < >   < >    |       \       |      \     " + "\n"
    r"    \       \o/      \         /     |    <o>       \o    <o>      \o   " + "\n"
    r"     o       |        o       o      o     |         v\    |        v\  " + "\n"
    r"     <\__   / \       <\__ __/>    __|>_  / \         <\  / \        <\ " + "\n"
)

# _SHADOW uses only box-drawing Unicode characters — no backslashes at all,
# so a plain string is fine here.
_SHADOW = (
    " ██████╗ ██╗   ██╗ ██╗ ██████╗ ██╗  ██╗\n"
    "██╔═══██╗██║   ██║ ██║ ██╔══██╗██║ ██╔╝\n"
    "██║   ██║██║   ██║ ██║ ██████╔╝█████╔╝ \n"
    "██║▄▄ ██║██║   ██║ ██║ ██╔══██╗██╔═██╗ \n"
    "╚██████╔╝╚██████╔╝ ██║ ██║  ██║██║  ██╗\n"
    " ╚══▀▀═╝  ╚═════╝  ╚═╝ ╚═╝  ╚═╝╚═╝  ╚═╝"
)

# _BASIC has backticks but no backslashes — plain string is safe.
_BASIC = (
    "  .d88b.  db    db d888888b d8888b. db   dD \n"
    " .8P  Y8. 88    88   `88'   88  `8D 88 ,8P' \n"
    " 88    88 88    88    88    88oobY' 88,8P   \n"
    " 88    88 88    88    88    88`8b   88`8b   \n"
    " `8P  d8' 88b  d88   .88.   88 `88. 88 `88. \n"
    "  `Y88'Y8 ~Y8888P' Y888888P 88   YD YP   YD \n"
)

# _ISO is heavy with backslashes — raw strings required.
_ISO = (
    r"      ___           ___                       ___           ___      " + "\n"
    r"     /\  \         /\__\          ___        /\  \         /\__\     " + "\n"
    r"    /::\  \       /:/  /         /\  \      /::\  \       /:/  /     " + "\n"
    r"   /:/\:\  \     /:/  /          \:\  \    /:/\:\  \     /:/__/      " + "\n"
    r"   \:\~\:\  \   /:/  /  ___      /::\__\  /::\~\:\  \   /::\__\____  " + "\n"
    r"    \:\ \:\__\ /:/__/  /\__\  __/:/\/__/ /:/\:\ \:\__\ /:/\:::::\__\ " + "\n"
    r"     \:\/:/  / \:\  \ /:/  / /\/:/  /    \/_|::\/:/  / \/_|:|~~|~    " + "\n"
    r"      \::/  /   \:\  /:/  /  \::/__/        |:|::/  /     |:|  |     " + "\n"
    r"      /:/  /     \:\/:/  /    \:\__\        |:|\/__/      |:|  |     " + "\n"
    r"     /:/  /       \::/  /      \/__/        |:|  |        |:|  |     " + "\n"
    r"     \/__/         \/__/                     \|__|         \|__|     " + "\n"
)

# _FACES has \- which is technically undefined behavior in non-raw strings.
_FACES = (
    r"     @__          \-^-/          |||           ((_           /777       " + "\n"
    r"    (o o)         (o o)         (o o)         (o o)         (o o)       " + "\n"
    r" ooO--(_)--Ooo-ooO--(_)--Ooo-ooO--(_)--Ooo-ooO--(_)--Ooo-ooO--(_)--Ooo- " + "\n"
)

# _STANDARD has several backslash sequences — raw strings required.
_STANDARD = (
    r"  ___  _   _ ___ ____  _  __ " + "\n"
    r" / _ \| | | |_ _|  _ \| |/ / " + "\n"
    r"| | | | | | || || |_) | ' /  " + "\n"
    r"| |_| | |_| || ||  _ <| . \  " + "\n"
    r" \__\_\\___/|___|_| \_\_|\_\ " + "\n"
)

# _BIG has no backslashes — plain strings are fine.
_BIG = (
    "     QQQQQQQQQ     UUUUUUUU     UUUUUUUUIIIIIIIIIIRRRRRRRRRRRRRRRRR   KKKKKKKKK    KKKKKKK \n"
    "   QQ:::::::::QQ   U::::::U     U::::::UI::::::::IR::::::::::::::::R  K:::::::K    K:::::K \n"
    " QQ:::::::::::::QQ U::::::U     U::::::UI::::::::IR::::::RRRRRR:::::R K:::::::K    K:::::K \n"
    "Q:::::::QQQ:::::::QUU:::::U     U:::::UUII::::::IIRR:::::R     R:::::RK:::::::K   K::::::K \n"
    "Q::::::O   Q::::::Q U:::::U     U:::::U   I::::I    R::::R     R:::::RKK::::::K  K:::::KKK \n"
    "Q:::::O     Q:::::Q U:::::D     D:::::U   I::::I    R::::R     R:::::R  K:::::K K:::::K    \n"
    "Q:::::O     Q:::::Q U:::::D     D:::::U   I::::I    R::::RRRRRR:::::R   K::::::K:::::K     \n"
    "Q:::::O     Q:::::Q U:::::D     D:::::U   I::::I    R:::::::::::::RR    K:::::::::::K      \n"
    "Q:::::O     Q:::::Q U:::::D     D:::::U   I::::I    R::::RRRRRR:::::R   K:::::::::::K      \n"
    "Q:::::O     Q:::::Q U:::::D     D:::::U   I::::I    R::::R     R:::::R  K::::::K:::::K     \n"
    "Q:::::O  QQQQ:::::Q U:::::D     D:::::U   I::::I    R::::R     R:::::R  K:::::K K:::::K    \n"
    "Q::::::O Q::::::::Q U::::::U   U::::::U   I::::I    R::::R     R:::::RKK::::::K  K:::::KKK \n"
    "Q:::::::QQ::::::::Q U:::::::UUU:::::::U II::::::IIRR:::::R     R:::::RK:::::::K   K::::::K \n"
    " QQ::::::::::::::Q   UU:::::::::::::UU  I::::::::IR::::::R     R:::::RK:::::::K    K:::::K \n"
    "   QQ:::::::::::Q      UU:::::::::UU    I::::::::IR::::::R     R:::::RK:::::::K    K:::::K \n"
    "     QQQQQQQQ::::QQ      UUUUUUUUU      IIIIIIIIIIRRRRRRRR     RRRRRRRKKKKKKKKK    KKKKKKK \n"
    "             Q:::::Q                                                                       \n"
    "              QQQQQQ                                                                       \n"
)

# _O8 has no backslashes — plain strings are fine.
_O8 = (
    "   ooooooo  ooooo  oooo ooooo oooooooooo  oooo   oooo \n"
    " o888   888o 888    88   888   888    888  888  o88   \n"
    " 888     888 888    88   888   888oooo88   888888     \n"
    " 888o  8o888 888    88   888   888  88o    888  88o   \n"
    "   88ooo88    888oo88   o888o o888o  88o8 o888o o888o \n"
    "        88o8                                          \n"
)

BANNER_VARIANTS = [_ACROBAT, _SHADOW, _BASIC, _BIG, _FACES, _STANDARD, _ISO, _O8]


# ── Color palettes ────────────────────────────────────────────────────────────

class _Palette(NamedTuple):
    name: str
    art: str
    title: str
    subtitle: str
    border: str
    sep: str


PALETTES = [
    _Palette("electric blue",
        art="#00cfff", title="#00e5ff", subtitle="#3b9dff",
        border="#1a5a9a", sep="#2a4a6a"),
    _Palette("matrix green",
        art="#00ff41", title="#39ff14", subtitle="#00cc33",
        border="#004a10", sep="#003a0d"),
    _Palette("neon magenta",
        art="#ff2d9b", title="#ff69b4", subtitle="#cc0077",
        border="#7a0045", sep="#5a0035"),
    _Palette("gold",
        art="#ffb700", title="#ffd700", subtitle="#cc8800",
        border="#6a4500", sep="#4a3000"),
    _Palette("void purple",
        art="#c77dff", title="#e040fb", subtitle="#9d4edd",
        border="#4a1a7a", sep="#3a1060"),
    _Palette("ember",
        art="#ff6b35", title="#ff4500", subtitle="#cc3300",
        border="#6a1a00", sep="#4a1000"),
    _Palette("arctic teal",
        art="#00e5b4", title="#00ffd0", subtitle="#00b894",
        border="#007a5a", sep="#005040"),
]

BYLINE = "0xD1g5 // fulcrum"


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
    content.append("\n")
    content.append(BYLINE, style=f"dim {p.art}")

    panel = Panel(content, title=title, border_style=p.border, padding=(0, 1))
    console.print(panel)
