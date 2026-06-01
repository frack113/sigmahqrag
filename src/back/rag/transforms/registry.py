"""Transform registry for format-specific document transforms."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Iterator, Type

from .base import DocumentTransform

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger(__name__)

# Registry mapping format names to transform classes.
_register: dict[str, Type[DocumentTransform]] = {}


class TransformRegistry:
    """Registry for discovering and retrieving document transforms."""

    @classmethod
    def register(
        cls,
        transform_cls: Type[DocumentTransform],
        formats: Sequence[str] | None = None,
    ) -> None:
        """Register a transform class with one or more format names.

        Args:
            transform_cls: The transform class to register.
            formats: Explicit format names to register under.
                Defaults to transform_cls.FORMAT_NAME.
        """
        if not issubclass(transform_cls, DocumentTransform):
            raise TypeError(f"{transform_cls.__name__} is not a DocumentTransform subclass")

        format_names = formats or [transform_cls.FORMAT_NAME]
        if not format_names:
            raise ValueError(f"No format names provided for {transform_cls.__name__}")

        for fmt in format_names:
            if fmt in _register:
                existing = _register[fmt]
                if existing is transform_cls:
                    logger.debug(
                        "Transform %s already registered as '%s'", transform_cls.__name__, fmt
                    )
                    continue
                logger.warning(
                    "Replacing existing transform %s with %s for format '%s'",
                    existing.__name__,
                    transform_cls.__name__,
                    fmt,
                )
            _register[fmt] = transform_cls
            logger.debug("Registered transform %s as format '%s'", transform_cls.__name__, fmt)

    @classmethod
    def get(cls, format_name: str) -> Type[DocumentTransform] | None:
        """Retrieve a registered transform class by format name.

        Args:
            format_name: The format name to look up.

        Returns:
            The transform class, or None if not found.
        """
        return _register.get(format_name)

    @classmethod
    def find_for_file(cls, file_path: Path | str) -> Type[DocumentTransform] | None:
        """Find a suitable transform for a given file by checking supported extensions.

        Iterates through all registered transforms and checks if any of them
        report they can handle the file via their can_handle() method.

        Args:
            file_path: Path to the file to check.

        Returns:
            The transform class that can handle the file, or None.
        """
        path = Path(file_path)
        for format_name, transform_cls in cls._iter():
            if transform_cls.can_handle(path):
                logger.debug("Found transform %s for file '%s'", transform_cls.__name__, path.name)
                return transform_cls
        return None

    @classmethod
    def _iter(cls) -> Iterator[tuple[str, Type[DocumentTransform]]]:
        """Iterate over all registered (format_name, transform_class) pairs."""
        yield from _register.items()

    @classmethod
    def list_formats(cls) -> list[str]:
        """Return a list of all registered format names."""
        return list(_register.keys())

    @classmethod
    def register_all(cls, *transform_cls: Type[DocumentTransform]) -> None:
        """Register multiple transform classes at once.

        Args:
            transform_cls: Transform classes to register.
        """
        for tcls in transform_cls:
            cls.register(tcls)


# Module-level convenience function exposed for imports.
register_transform = TransformRegistry.register
