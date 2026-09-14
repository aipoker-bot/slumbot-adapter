"""Minimal async client for slumbot.com: one object per session (the API token lives here).

    async with SlumbotClient() as sb:
        hand = await sb.new_hand()          # -> Hand(state=ParsedState, hole_cards=[...], board=[...], resp=raw)
        while not hand.over:
            if hand.state.hero_turn:
                hand = await sb.act("c")    # k / c / f / bN (N = TOTAL street contribution, blinds included)
        print(hand.winnings)                # chips from the client's perspective

Blinds 50/100, stacks 20000 per hand (200bb), reset every hand. Legal raise sizes: `hand.state.raise_window()`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import httpx

from .state import ParsedState, parse

API = "https://slumbot.com/api"


class SlumbotError(RuntimeError):
    """The API answered with error_msg (bad token, illegal action, hand already over)."""


@dataclass
class Hand:
    resp: dict
    state: ParsedState
    client_pos: int
    hole_cards: list[str] = field(default_factory=list)
    board: list[str] = field(default_factory=list)

    @property
    def over(self) -> bool:
        return "winnings" in self.resp

    @property
    def winnings(self) -> int | None:
        return self.resp.get("winnings")

    @property
    def bot_hole_cards(self) -> list[str] | None:
        return self.resp.get("bot_hole_cards")


class SlumbotClient:
    def __init__(self, timeout: float = 20.0, client: httpx.AsyncClient | None = None):
        self._own = client is None
        self.client = client or httpx.AsyncClient(timeout=timeout)
        self.token: str | None = None
        self.client_pos: int = 0

    async def __aenter__(self) -> "SlumbotClient":
        return self

    async def __aexit__(self, *exc) -> None:
        if self._own:
            await self.client.aclose()

    async def _post(self, path: str, payload: dict) -> dict:
        r = await self.client.post(f"{API}/{path}", json=payload)
        r.raise_for_status()
        data = r.json()
        if "error_msg" in data:
            raise SlumbotError(data["error_msg"])
        return data

    def _hand(self, data: dict) -> Hand:
        # client_pos is only sent on new_hand; keep it for the rest of the hand
        if "client_pos" in data:
            self.client_pos = data["client_pos"]
        st = parse(data.get("action", ""), self.client_pos)
        return Hand(resp=data, state=st, client_pos=self.client_pos,
                    hole_cards=list(data.get("hole_cards", [])), board=list(data.get("board", [])))

    async def new_hand(self) -> Hand:
        data = await self._post("new_hand", {"token": self.token} if self.token else {})
        self.token = data.get("token", self.token)
        return self._hand(data)

    async def act(self, incr: str) -> Hand:
        """incr: 'k' | 'c' | 'f' | 'b<total street contribution>'."""
        if self.token is None:
            raise SlumbotError("call new_hand() first")
        return self._hand(await self._post("act", {"token": self.token, "incr": incr}))
