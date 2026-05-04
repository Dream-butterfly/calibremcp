"""
Utility functions for discovering and managing Calibre libraries.

NOTE: Library discovery now delegates to config_discovery.py.
This module provides backward-compatible wrappers.
"""

from pathlib import Path


def discover_calibre_libraries() -> dict[str, Path]:
    """
    Discover all Calibre libraries on the system.

    Delegates to config_discovery for actual discovery logic.
    Converts CalibreLibrary objects to simple Path values
    for backward compatibility with existing callers.

    Returns:
        Dict mapping library names to their Paths
    """
    from calibre_mcp.config_discovery import discover_calibre_libraries as _new_discovery

    discovered = _new_discovery()
    return {name: lib.path for name, lib in discovered.items()}


def get_library_metadata(library_path: Path) -> dict[str, any]:
    """
    Get metadata about a specific library.

    Args:
        library_path: Path to the library directory

    Returns:
        Dictionary containing library metadata
    """
    metadata = {
        "name": library_path.name,
        "path": str(library_path),
        "metadata_db": str(library_path / "metadata.db"),
        "exists": (library_path / "metadata.db").exists(),
        "size_mb": 0,
        "book_count": 0,
    }

    # Calculate library size - avoid expensive recursive glob (**/*) which causes 502/404 on large libraries
    try:
        metadata_db = library_path / "metadata.db"
        if metadata_db.exists():
            metadata["size_mb"] = metadata_db.stat().st_size / (1024 * 1024)
        else:
            metadata["size_mb"] = 0
    except (OSError, PermissionError):
        metadata["size_mb"] = 0

    # Count books from database (more accurate than directory counting)
    metadata_db = library_path / "metadata.db"
    if metadata_db.exists():
        try:
            import sqlite3

            conn = sqlite3.connect(str(metadata_db))
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM books")
            metadata["book_count"] = cursor.fetchone()[0] or 0
            conn.close()
        except (sqlite3.Error, OSError, PermissionError):
            # Fallback to directory counting if database query fails
            try:
                metadata["book_count"] = sum(
                    1 for _ in library_path.glob("*") if _.is_dir() and _.name.isdigit()
                )
            except (OSError, PermissionError):
                metadata["book_count"] = 0
    else:
        # No database, try directory counting
        try:
            metadata["book_count"] = sum(
                1 for _ in library_path.glob("*") if _.is_dir() and _.name.isdigit()
            )
        except (OSError, PermissionError):
            metadata["book_count"] = 0

    return metadata


def get_current_library() -> Path | None:
    """
    Get the current active library path from configuration.

    Returns:
        Path to the current library or None if not set
    """
    from ...config import get_config

    config = get_config()
    if config.local_library_path and (config.local_library_path / "metadata.db").exists():
        return config.local_library_path

    # Fallback to first found library
    libraries = discover_calibre_libraries()
    if libraries:
        return next(iter(libraries.values()))

    return None
