import os
import sys
from pathlib import Path

# Ensure UTF-8 output to prevent crashes with emojis on Windows terminals
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Resolve the local 'src' directory and add it to sys.path
src_dir = Path(__file__).resolve().parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from ulolm.cli import main

if __name__ == "__main__":
    main()
