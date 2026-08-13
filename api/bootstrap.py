"""GET /api/bootstrap — file-based Vercel function."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.vercel_bridge import make_handler

handler = make_handler()
