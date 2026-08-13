"""Vercel FastAPI entry — same Studio app as local, no extra proxy hop."""
from src.documentary.runtime import configure_workspace

configure_workspace()

from studio.server import studio_app as app
