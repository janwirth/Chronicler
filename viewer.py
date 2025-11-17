#!/usr/bin/env python3
"""
Chronicler Viewer - Display activity logs in markdown format
"""

import sys
from pathlib import Path

CHRONICLES_DIR = Path.home() / "chronicles"


def main():
    """Main entry point - simply display the markdown log file"""
    # Find most recent log file
    log_files = sorted(CHRONICLES_DIR.glob("log_*.md"))

    if not log_files:
        print(f"No log files found in {CHRONICLES_DIR}")
        return

    # Use most recent
    log_file = log_files[-1]

    if len(sys.argv) > 1:
        # Allow specifying a different log file
        log_file = Path(sys.argv[1])

    if not log_file.exists():
        print(f"Log file not found: {log_file}")
        return

    print(f"Viewing: {log_file}\n")
    print("=" * 80)

    # Simply display the markdown content
    with open(log_file, "r", encoding="utf-8") as f:
        print(f.read())

    print("=" * 80)


if __name__ == "__main__":
    main()
