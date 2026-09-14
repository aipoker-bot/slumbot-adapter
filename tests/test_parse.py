"""Parser tests pinned to strings recorded from the live API on 2026-08-14."""

from slumbot_adapter import BB, SB, STACK, parse


def test_new_hand_bot_opens():
    # client_pos 0 => client BB; bot (SB) raised to 200
    st = parse("b200", 0)
    assert st.hero_turn
    assert st.to_call == 100
    assert st.pot == 300          # bot 200 + hero blind 100
    lo, hi = st.raise_window()
    assert lo == 300              # min re-raise: 200 + increment 100
    assert hi == 20000            # all-in total street contribution
    assert ("bot", "raises to 200") in st.log


def test_flop_after_call():
    st = parse("b200c/", 0)
    assert st.street == 1
    assert st.hero_turn           # BB first postflop
    assert st.to_call == 0
    assert st.pot == 400
    lo, hi = st.raise_window()
    assert lo == 100 and hi == 19800  # fresh street: min bet = BB, max = stack


def test_river_facing_bet():
    st = parse("b200c/kk/kk/kb200", 0)
    assert st.street == 3
    assert st.hero_turn
    assert st.to_call == 200
    assert st.pot == 600
    assert ("hero", "checks") in st.log and ("bot", "bets 200") in st.log


def test_client_is_sb_first_to_act():
    st = parse("", 1)
    assert st.hero_turn           # client SB acts first preflop
    assert st.to_call == SB       # 100 - 50
    assert st.pot == SB + BB


def test_reraise_min_increment():
    # bot 200, hero raises to 600 (increment 400) -> bot min re-raise = 1000
    st = parse("b200b600", 0)
    assert not st.hero_turn
    st2 = parse("b200b600b1000", 0)
    assert st2.hero_turn
    assert st2.to_call == 400
