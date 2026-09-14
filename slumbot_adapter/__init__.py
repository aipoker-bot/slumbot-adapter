"""slumbot-adapter: parse Slumbot's action strings and talk to its public API."""
from .state import BB, SB, STACK, SCALE, ParsedState, parse, sc, sc_text
from .client import SlumbotClient, SlumbotError, Hand

__all__ = ["BB", "SB", "STACK", "SCALE", "ParsedState", "parse", "sc", "sc_text", "SlumbotClient", "SlumbotError", "Hand"]
__version__ = "0.1.0"
