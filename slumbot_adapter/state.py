"""State parser for the Slumbot HTTP API: walk an action string, get pot, stacks, whose turn, legal raise window.

Protocol (derived empirically 2026-08-14 + community clients):
  POST /api/new_hand {"token"?} -> {action, client_pos, hole_cards, board, token}
  POST /api/act {token, incr}   -> same, plus at terminal: winnings, bot_hole_cards?
  Action string: k=check c=call f=fold bN (N = TOTAL street contribution, blinds
  included), streets separated by "/". Blinds 50/100, stacks 20000, reset per hand.
  client_pos 0 => client is BB (bot acted first preflop); 1 => client is SB.

Slumbot is by Eric Jackson (slumbot.com). This adapter is MIT; see README for the
permission note.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

SB, BB, STACK = 50, 100, 20000
HERO_TIMEOUT = 30
SCALE = 50  # display divisor: blinds 1/2, stacks 400 (200bb deep) when you want table-sized numbers


def sc(x):
    """Scale chips for display; whole numbers stay ints."""
    v = x / SCALE
    return int(v) if float(v).is_integer() else round(v, 1)


def sc_text(verb: str) -> str:
    return re.sub(r"\d+", lambda m: str(sc(int(m.group()))), verb)
API = "https://slumbot.com/api"
STREETS = ("preflop", "flop", "turn", "river")


@dataclass
class ParsedState:
    """Full walk of a Slumbot action string from the client's perspective."""
    street: int = 0
    hero_total: int = 0          # committed across all streets
    bot_total: int = 0
    hero_street: int = 0         # committed on current street
    bot_street: int = 0
    to_call: int = 0
    last_increment: int = BB
    level: int = 0               # current street bet level (max contribution)
    hero_turn: bool = False
    log: list[tuple[str, str]] = field(default_factory=list)  # (who, verb)

    @property
    def pot(self) -> int:
        return self.hero_total + self.bot_total

    @property
    def hero_stack(self) -> int:
        return STACK - self.hero_total

    @property
    def bot_stack(self) -> int:
        return STACK - self.bot_total

    def raise_window(self) -> tuple[int | None, int | None]:
        """(min_to, max_to) as TOTAL street contribution, None if unavailable."""
        max_to = self.hero_street + self.hero_stack
        if max_to <= self.level:
            return None, None
        min_to = min(self.level + max(self.last_increment, BB), max_to)
        return min_to, max_to


_TOKEN_RX = re.compile(r"k|c|f|b\d+")


def parse(action: str, client_pos: int) -> ParsedState:
    """client_pos 0 => client is BB; 1 => client is SB (empirical)."""
    st = ParsedState()
    hero_is_sb = client_pos == 1
    # street contributions: (sb, bb); preflop starts with blinds posted
    contrib = {"sb": SB, "bb": BB}
    totals = {"sb": SB, "bb": BB}
    st.level = BB
    st.last_increment = BB
    streets = action.split("/")
    for i, street_str in enumerate(streets):
        st.street = i
        if i > 0:
            contrib = {"sb": 0, "bb": 0}
            st.level = 0
            st.last_increment = 0
        order = ("sb", "bb") if i == 0 else ("bb", "sb")
        turn = 0
        for tok in _TOKEN_RX.findall(street_str):
            who = order[turn % 2]
            name = "hero" if (who == "sb") == hero_is_sb else "bot"
            if tok == "k":
                st.log.append((name, "checks"))
            elif tok == "c":
                paid = st.level - contrib[who]
                totals[who] += paid
                contrib[who] = st.level
                st.log.append((name, f"calls {paid}" if paid else "checks"))
            elif tok == "f":
                st.log.append((name, "folds"))
            else:
                to = int(tok[1:])
                st.last_increment = max(to - st.level, st.last_increment if st.level else BB)
                verb = "raises to" if st.level > (BB if i == 0 else 0) or (i == 0) else "bets"
                if i > 0 and st.level == 0:
                    verb = "bets"
                totals[who] += to - contrib[who]
                contrib[who] = to
                st.level = to
                st.log.append((name, f"{verb} {to}"))
            turn += 1
        # whose turn next on this street
        next_who = order[turn % 2]
        st.hero_turn = (next_who == "sb") == hero_is_sb
    hero_key = "sb" if hero_is_sb else "bb"
    bot_key = "bb" if hero_is_sb else "sb"
    st.hero_total, st.bot_total = totals[hero_key], totals[bot_key]
    st.hero_street, st.bot_street = contrib[hero_key], contrib[bot_key]
    st.to_call = max(0, st.level - st.hero_street)
    return st
