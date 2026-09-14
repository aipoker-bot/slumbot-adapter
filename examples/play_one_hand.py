"""Play one hand against Slumbot as a calling station. Needs network. Run: python examples/play_one_hand.py"""
import asyncio

from slumbot_adapter import SlumbotClient, sc


async def main():
    async with SlumbotClient() as sb:
        h = await sb.new_hand()
        print("hole:", h.hole_cards, "| you are", "SB" if h.client_pos == 1 else "BB")
        while not h.over:
            if not h.state.hero_turn:
                break  # Slumbot acts inside the same response; nothing to wait for
            incr = "c" if h.state.to_call else "k"
            h = await sb.act(incr)
            print("board:", h.board, "| pot:", sc(h.state.pot), "bb-scaled |", h.state.log[-2:])
        print("winnings:", h.winnings, "chips; bot showed", h.bot_hole_cards)


asyncio.run(main())
