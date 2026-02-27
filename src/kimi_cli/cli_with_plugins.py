"""
Kimi CLI with plugins entry point.

This module loads user plugins before importing the CLI,
ensuring patches are applied correctly without circular imports.
"""

# Load plugins first, before any other kimi_cli imports
import warnings

try:
    from kimi_cli.plugins import apply_all_patches

    apply_all_patches()
except Exception as e:
    warnings.warn(f"[Plugin] Failed to load plugins: {e}", RuntimeWarning, stacklevel=2)

# Now import and run the CLI
from kimi_cli.cli import cli

__all__ = ["cli"]
