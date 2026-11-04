"""The `flowglyph` command, available with `pip install 'flowglyph[cli]'`."""

import sys


def run() -> None:
    """Entry point of the `flowglyph` executable."""
    try:
        from flowglyph.cli.main import app  # noqa: PLC0415
    except ModuleNotFoundError as error:
        if error.name not in {"typer", "rich"}:
            raise
        sys.exit("flowglyph: the command line needs extra packages: pip install 'flowglyph[cli]'")
    app()
