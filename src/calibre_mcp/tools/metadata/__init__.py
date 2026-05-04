"""
Metadata management tools for CalibreMCP.

This module provides the manage_metadata portmanteau tool for comprehensive metadata management.
"""

# Import portmanteau tool (this is registered with @mcp.tool() and visible to Claude)
from .manage_metadata import manage_metadata  # noqa: F401
from .web_enrichment import enrich_book_metadata  # noqa: F401
from .linovelib_synopses import fetch_volume_synopses  # noqa: F401

# List of tools to register - ONLY portmanteau tool is registered
# Helper functions are NOT in this list (they have no @mcp.tool() decorator)
tools = [
    manage_metadata,  # Portmanteau tool
    enrich_book_metadata,  # Web metadata enrichment
    fetch_volume_synopses,  # Volume synopsis fetching
]

__all__ = ["manage_metadata", "enrich_book_metadata", "fetch_volume_synopses"]
