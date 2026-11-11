"""Root entry point for TradingDesk CLI.

Usage:
    python main.py MSFT
    python main.py
"""

import sys
from pathlib import Path

# Add src to sys.path so it works seamlessly out of the box
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from tradingdesk.cli import main

if __name__ == "__main__":
    main()
