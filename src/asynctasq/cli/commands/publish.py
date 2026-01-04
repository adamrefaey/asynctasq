"""Publish command implementation."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
import shutil

logger = logging.getLogger(__name__)


async def run_publish(args: argparse.Namespace, config: object | None = None) -> None:
    """Publish .env.example file to the consumer project root.

    Args:
        args: Parsed command-line arguments
        config: Configuration object (unused for publish command)
    """
    # Get the path to the .env.example file in the asynctasq package
    package_root = Path(__file__).parent.parent.parent.parent.parent
    source_file = package_root / ".env.example"

    # Determine the target directory (default to current working directory)
    target_dir = Path(args.output_dir or Path.cwd())
    target_file = target_dir / ".env.example"

    # Validate source file exists
    if not source_file.exists():
        logger.error(f".env.example file not found at: {source_file}")
        raise FileNotFoundError(f".env.example file not found at: {source_file}")

    # Create target directory if it doesn't exist
    target_dir.mkdir(parents=True, exist_ok=True)

    # Check if target file already exists
    if target_file.exists() and not args.force:
        logger.error(
            f".env.example already exists at: {target_file}\n"
            "Use --force to overwrite the existing file."
        )
        raise FileExistsError(
            f".env.example already exists at: {target_file}. Use --force to overwrite."
        )

    # Copy the file
    try:
        shutil.copy2(source_file, target_file)
        logger.info(f"Successfully published .env.example to: {target_file}")
        print(f"✓ Published .env.example to: {target_file}")
        print("\nNext steps:")
        print("  1. Copy .env.example to .env")
        print("  2. Update the values in .env with your configuration")
    except Exception as e:
        logger.error(f"Failed to copy .env.example: {e}")
        raise
