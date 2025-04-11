"""Terminal utilities for displaying colorful output in the console."""

from __future__ import annotations

import platform
from collections.abc import Callable
from typing import TypeVar

# Check if we're running on Windows
COLORS_ENABLED = platform.system() != "Windows"

# ANSI color/style codes - used only if COLORS_ENABLED is True
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
BLUE = "\033[34m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"


def styled_text(text: str, *styles: str) -> str:
    """Apply ANSI styles to text if colors are enabled.

    Args:
        text: The text to style
        *styles: ANSI style codes to apply

    Returns:
        The styled text, or the original text if colors are disabled
    """
    if not COLORS_ENABLED or not styles:
        return text

    style = "".join(styles)
    return f"{style}{text}{RESET}"


def create_printer(style: str) -> Callable[[str], None]:
    """Create a function that prints text with the given style.

    Args:
        style: ANSI style code (will be ignored on Windows)

    Returns:
        A function that prints text with the given style if supported
    """

    def printer(text: str) -> None:
        print(styled_text(text, style))

    return printer


print_success = create_printer(f"{GREEN}{BOLD}")
print_info = create_printer(CYAN)
print_error = create_printer(f"{RED}{BOLD}")
print_warning = create_printer(f"{YELLOW}{BOLD}")
print_header = create_printer(f"{BLUE}{BOLD}")


T = TypeVar("T")


class TerminalUI:
    """A simple UI class for terminal-based interfaces."""

    @staticmethod
    def header(title: str) -> None:
        """Print a header with a title.

        Args:
            title: The title to display
        """
        print(f"\n{styled_text('╔' + '═' * 50 + '╗', BLUE, BOLD)}")
        print(
            f"{styled_text('║', BLUE, BOLD)} {styled_text(title.center(48), CYAN, BOLD)} {styled_text('║', BLUE, BOLD)}"
        )
        print(f"{styled_text('╚' + '═' * 50 + '╝', BLUE, BOLD)}")

    @staticmethod
    def section(title: str) -> None:
        """Print a section divider with a title.

        Args:
            title: The title to display
        """
        print(f"\n{styled_text(f'▓▒░ {title} ░▒▓', YELLOW, BOLD)}")

    @staticmethod
    def success(message: str) -> None:
        """Print a success message.

        Args:
            message: The message to display
        """
        print(f"{styled_text(f'✓ {message}', GREEN, BOLD)}")

    @staticmethod
    def info(message: str) -> None:
        """Print an info message.

        Args:
            message: The message to display
        """
        print(f"{styled_text(message, CYAN)}")

    @staticmethod
    def error(message: str) -> None:
        """Print an error message.

        Args:
            message: The message to display
        """
        print(f"{styled_text(f'✗ {message}', RED, BOLD)}")

    @staticmethod
    def warning(message: str) -> None:
        """Print a warning message.

        Args:
            message: The message to display
        """
        print(f"{styled_text(f'⚠ {message}', YELLOW, BOLD)}")

    @staticmethod
    def box(title: str, messages: list[str], style: str = MAGENTA) -> None:
        """Print a box with a title and messages.

        Args:
            title: The box title
            messages: The messages to display inside the box
            style: ANSI style code for the box
        """
        # Find the longest message to size the box
        width = max(len(title), max(len(m) for m in messages)) + 4

        # Print the box
        print(
            f"{styled_text(f'┌─ {title} ' + '─' * (width - len(title) - 4) + '┐', style, BOLD)}"
        )
        for msg in messages:
            print(
                f"{styled_text(f'│ {msg}' + ' ' * (width - len(msg) - 2) + '│', style, BOLD)}"
            )
        print(f"{styled_text('└' + '─' * (width - 2) + '┘', style, BOLD)}")

    @staticmethod
    def table(
        items: list[T], formatter: Callable[[T], str], border_style: str = CYAN
    ) -> None:
        """Print a simple table of items.

        Args:
            items: List of items to display
            formatter: Function to format each item
            border_style: ANSI style code for the table border
        """
        if not items:
            print(styled_text("No items to display", CYAN))
            return

        # Create header and footer
        print(f"{styled_text('╭─ Items ' + '─' * 40 + '╮', border_style)}")

        # Print each item
        for item in items:
            print(f"{styled_text('│', border_style)} {formatter(item)}")

        # Footer
        print(f"{styled_text('╰' + '─' * 48 + '╯', border_style)}")


console = TerminalUI()
