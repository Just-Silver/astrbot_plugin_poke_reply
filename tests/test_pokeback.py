"""反戳：默认关闭，开启后按概率与次数生效。"""

from __future__ import annotations

import pytest
from astrbot_plugin_poke_reply.poke.pokeback import Pokeback
from conftest import FakeBot, FakeEvent


@pytest.mark.asyncio
async def test_disabled_pokeback_sends_nothing():
    bot = FakeBot()
    event = FakeEvent(bot=bot)
    back = Pokeback(enabled=False, probability=1.0, times=1, interval=0)

    sent = await back.send(event, target_id="123456")

    assert sent == 0
    assert bot.pokes == []


@pytest.mark.asyncio
async def test_zero_probability_sends_nothing():
    bot = FakeBot()
    event = FakeEvent(bot=bot)
    back = Pokeback(enabled=True, probability=0.0, times=3, interval=0)

    sent = await back.send(event, target_id="123456")

    assert sent == 0
    assert bot.pokes == []


@pytest.mark.asyncio
async def test_full_probability_sends_configured_times():
    bot = FakeBot()
    event = FakeEvent(bot=bot)
    back = Pokeback(enabled=True, probability=1.0, times=3, interval=0)

    sent = await back.send(event, target_id="123456")

    assert sent == 3
    assert bot.pokes == [("group", "123456")] * 3


@pytest.mark.asyncio
async def test_private_chat_uses_friend_poke():
    bot = FakeBot()
    event = FakeEvent(bot=bot, group_id="")
    back = Pokeback(enabled=True, probability=1.0, times=1, interval=0)

    await back.send(event, target_id="123456")

    assert bot.pokes == [("friend", "123456")]
