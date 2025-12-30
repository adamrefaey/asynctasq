"""Rich console utilities for beautiful task output."""

from rich import print as rich_print
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

# Global console instance for all asynctasq output
console = Console()


def print(*args, **kwargs):
    """Rich-enhanced print function for use in tasks.

    Drop-in replacement for built-in print() with beautiful formatting:
    - Automatic syntax highlighting for code, JSON, etc.
    - Colorized output
    - Support for Rich markup ([bold], [red], etc.)
    - Tables, panels, and other Rich renderables

    Usage in tasks:
        from asynctasq.utils.console import print

        @task
        async def my_task():
            print("Hello [bold cyan]World[/bold cyan]!")
            print({"data": [1, 2, 3]})  # Auto-formatted JSON
    """
    rich_print(*args, **kwargs)


__all__ = ["console", "print", "Console", "Syntax", "Table", "Panel"]
