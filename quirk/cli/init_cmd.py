"""quirk init — generate a starter config.yaml from the bundled template."""
import os
import shutil
from importlib.resources import files  # Python 3.10+


def run_init(output_path: str) -> None:
    """Copy the bundled config template to *output_path*.

    If the file already exists, print a warning and exit without overwriting.
    """
    try:
        from rich.console import Console
        console = Console()
        _info = lambda msg: console.print(f"[bold #3b9dff]QU.I.R.K.[/] {msg}")
        _warn = lambda msg: console.print(f"[bold yellow]WARNING:[/] {msg}")
    except ImportError:
        _info = lambda msg: print(f"QU.I.R.K. {msg}")
        _warn = lambda msg: print(f"WARNING: {msg}")

    output_path = os.path.abspath(output_path)

    # CR-01 / D-13: path-traversal guard — resolved path must descend from CWD.
    _cwd_real = os.path.realpath(os.getcwd())
    _out_real = os.path.realpath(output_path)

    # Reject if resolved path does not start with CWD (handles symlink escapes).
    if not (_out_real.startswith(_cwd_real + os.sep) or _out_real == _cwd_real):
        _warn(
            f"Output path '{output_path}' resolves outside the current working "
            "directory. Absolute paths and symlinks escaping CWD are not allowed."
        )
        return

    # Defense-in-depth: reject explicit dotdot segments before resolution.
    if ".." in os.path.normpath(output_path).split(os.sep):
        _warn(
            f"Output path '{output_path}' contains path-traversal segments (..)."
        )
        return

    if os.path.exists(output_path):
        _warn(f"Config file already exists at {output_path} — not overwriting.")
        _warn("Delete the file first or specify a different --output path.")
        return

    # Locate the bundled template using importlib.resources (works after pip install)
    try:
        template_ref = files("quirk").joinpath("config_template.yaml")
        template_path = str(template_ref)
    except Exception:
        # Fallback for development installs where __file__ is available
        template_path = os.path.join(os.path.dirname(__file__), "..", "config_template.yaml")
        template_path = os.path.normpath(template_path)

    if not os.path.exists(template_path):
        _warn(f"Bundled template not found at {template_path}. Re-install QU.I.R.K.")
        return

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    shutil.copy2(template_path, output_path)
    _info(f"Config file created: {output_path}")
    _info("Edit the [bold]targets[/bold] section, then run:")
    _info(f"  [dim]quirk --config {output_path}[/dim]")
