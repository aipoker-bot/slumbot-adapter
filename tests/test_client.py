"""Client tests against a fake transport: no network, strings recorded from the live API on 2026-08-14."""
import httpx
import pytest

from slumbot_adapter import SlumbotClient, SlumbotError


def fake(responses):
    it = iter(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=next(it))

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_new_hand_then_call_keeps_client_pos():
    async with SlumbotClient(client=fake([
        {"action": "b200", "client_pos": 0, "hole_cards": ["Ah", "Kd"], "board": [], "token": "t1"},
        {"action": "b200c/", "board": ["2c", "7d", "Js"], "token": "t1"},
    ])) as sb:
        h = await sb.new_hand()
        assert h.state.hero_turn and h.state.to_call == 100 and sb.token == "t1"
        h2 = await sb.act("c")
        assert h2.client_pos == 0 and h2.state.street == 1 and h2.state.pot == 400 and not h2.over


@pytest.mark.asyncio
async def test_terminal_hand_exposes_winnings():
    async with SlumbotClient(client=fake([
        {"action": "", "client_pos": 1, "hole_cards": ["7s", "2c"], "board": [], "token": "t2"},
        {"action": "f", "winnings": -50, "token": "t2"},
    ])) as sb:
        await sb.new_hand()
        h = await sb.act("f")
        assert h.over and h.winnings == -50


@pytest.mark.asyncio
async def test_error_msg_raises():
    async with SlumbotClient(client=fake([{"error_msg": "Invalid token"}])) as sb:
        with pytest.raises(SlumbotError):
            await sb.new_hand()


@pytest.mark.asyncio
async def test_act_before_new_hand():
    async with SlumbotClient(client=fake([])) as sb:
        with pytest.raises(SlumbotError):
            await sb.act("k")
