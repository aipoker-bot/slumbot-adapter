# slumbot-adapter

Parse [Slumbot](https://slumbot.com)'s action strings and play against it through its public API, from Python.

Slumbot is Eric Jackson's heads-up no-limit hold'em bot, built with counterfactual regret minimization and open to anyone through a small HTTP API. The API is easy to call and awkward to reason about: it answers with one string like `b200c/kk/kb400` and expects you to know whose turn it is, what the pot is and what raise sizes are legal. This package does that bookkeeping. It's the adapter I use at [aipoker.bot](https://aipoker.bot), where Slumbot is the reference opponent for LLM benchmark pairs.

```
pip install git+https://github.com/aipoker-bot/slumbot-adapter
```

## Use

```python
import asyncio
from slumbot_adapter import SlumbotClient

async def main():
    async with SlumbotClient() as sb:
        hand = await sb.new_hand()
        print(hand.hole_cards, "you are", "SB" if hand.client_pos == 1 else "BB")
        while not hand.over and hand.state.hero_turn:
            lo, hi = hand.state.raise_window()       # legal raise-to sizes, total street contribution
            hand = await sb.act("c" if hand.state.to_call else "k")
        print(hand.winnings, hand.bot_hole_cards)

asyncio.run(main())
```

`examples/play_one_hand.py` runs exactly this (needs network). The parser alone needs no network:

```python
from slumbot_adapter import parse
st = parse("b200c/kk/kb400", client_pos=0)
st.street, st.hero_turn, st.to_call, st.pot   # (2, True, 400, 800)
st.log                                        # [('bot', 'raises to 200'), ('hero', 'calls 100'), ...]
```

## What the API does, as far as I can tell

Derived from the live API in August 2026 and from community clients; nothing here is official.

- `POST /api/new_hand {"token"?}` → `{action, client_pos, hole_cards, board, token}`. Keep the token; it identifies your session.
- `POST /api/act {token, incr}` → same shape, plus `winnings` (and usually `bot_hole_cards`) when the hand is over.
- `incr` is one of `k` (check), `c` (call), `f` (fold), `bN` where N is your **total** contribution on the current street, blinds included. So the first preflop raise from the big blind to 300 is `b300`, not `b200`.
- Streets in `action` are separated by `/`. Blinds 50/100, stacks 20,000, reset every hand (200 big blinds deep).
- `client_pos` is sent on `new_hand` only: `0` means you are the big blind (Slumbot acted first preflop), `1` means you are the small blind. The client remembers it for the rest of the hand.
- Slumbot's own actions arrive inside the same response, so when `hero_turn` is false after an `act`, the hand is over.

`parse()` walks the string and returns a `ParsedState`: street, totals per player, amount to call, the current bet level, the last raise increment (for min-raise), whose turn it is, and a readable log. `raise_window()` gives the legal `(min_to, max_to)` or `(None, None)` when raising isn't possible. Divide by `SCALE` (50) if you want table-sized numbers: blinds 1/2, stacks 400.

## Tests

```
pip install -e ".[test]"
pytest
```

Parser tests are pinned to strings recorded from the live API on 2026-08-14. Client tests use a fake transport. If Slumbot changes its protocol, the parser tests are the ones that should go red first.

## Credit and permission

Slumbot is Eric Jackson's work; this package only talks to it. He has kept the API public for years, which is the only reason a project like aipoker.bot can have a strong fixed opponent at all. Please don't hammer it: one hand at a time per token, and back off on errors.

MIT.
