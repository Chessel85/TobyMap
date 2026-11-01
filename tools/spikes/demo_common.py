"""Console helpers shared by the spike demos: plain numbered menus that read well with NVDA."""
from __future__ import annotations


def ask(prompt: str) -> str:
    try:
        return input(prompt + " ").strip().lower()
    except EOFError:
        return "q"


def choose(title: str, options: list[tuple[str, str]]) -> str | None:
    """Numbered choice. Returns the key, or None for back."""
    print()
    print(title)
    for i, (_key, label) in enumerate(options, 1):
        print(f"{i}. {label}")
    print("0. Back")
    while True:
        answer = ask("Type a number and press Enter:")
        if answer in ("0", "q", "b"):
            return None
        if answer.isdigit() and 1 <= int(answer) <= len(options):
            return options[int(answer) - 1][0]
        print("Please type one of the numbers.")
