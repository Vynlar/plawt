"""Design-specific pattern generators exposed by the pattern CLI."""

from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from typing import Callable

from .sierpinski import add_sierpinski_arguments, generate_sierpinski


@dataclass(frozen=True)
class PatternGenerator:
    """CLI adapter for a design-specific SVG generator."""

    description: str
    add_arguments: Callable[[ArgumentParser], None]
    generate: Callable[[Namespace], str]


GENERATORS = {
    "sierpinski": PatternGenerator(
        description="Generate a continuous-path Sierpinski triangle.",
        add_arguments=add_sierpinski_arguments,
        generate=generate_sierpinski,
    ),
}

__all__ = ["GENERATORS", "PatternGenerator"]
