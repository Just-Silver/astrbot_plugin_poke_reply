"""端到端：被戳后产出一条 LLM 请求，且默认链路被抑制。"""

from __future__ import annotations

import pytest
from astrbot_plugin_poke_reply.poke.plugin import PokeReply
from conftest import FakeBot, FakeConversationManager, FakeEvent, Poke


class _Context:
    def __init__(self, history="[]"):
        self.conversation_manager = FakeConversationManager(history=history)


def _plugin(**overrides):
    config = {
        "enabled": True,
        "reply_in_group": True,
        "reply_in_private": True,
        "cooldown_seconds": 8,
        "prompt_template": "{username} 在{scene}里戳了你一下。",
        "carry_history": True,
        "pokeback": {"enabled": False, "probability": 0.15, "times": 1, "interval": 0},
    }
    config.update(overrides)
    return PokeReply(_Context(), config)


async def _collect(plugin, event):
    return [item async for item in plugin.on_event(event)]


@pytest.mark.asyncio
async def test_poke_produces_one_llm_request():
    event = FakeEvent(chain=[Poke(id="90000")], self_id="90000", sender_id="123456")

    results = await _collect(_plugin(), event)

    assert len(results) == 1
    assert "123456" in results[0]["prompt"]


@pytest.mark.asyncio
async def test_default_llm_chain_is_suppressed():
    event = FakeEvent(chain=[Poke(id="90000")], self_id="90000")

    await _collect(_plugin(), event)

    assert event.call_llm is True


@pytest.mark.asyncio
async def test_default_llm_chain_still_suppressed_when_silent():
    """沉默时也不许框架默认链路插一句。"""
    event = FakeEvent(chain=[Poke(id="90000")], self_id="90000")

    results = await _collect(_plugin(reply_in_group=False), event)

    assert results == []
    assert event.call_llm is True


@pytest.mark.asyncio
async def test_disabled_plugin_produces_nothing():
    event = FakeEvent(chain=[Poke(id="90000")], self_id="90000")

    results = await _collect(_plugin(enabled=False), event)

    assert results == []
    assert event.call_llm is False


@pytest.mark.asyncio
async def test_group_disabled_blocks_group_poke():
    event = FakeEvent(chain=[Poke(id="90000")], self_id="90000")

    results = await _collect(_plugin(reply_in_group=False), event)

    assert results == []


@pytest.mark.asyncio
async def test_private_disabled_blocks_private_poke():
    event = FakeEvent(chain=[Poke(id="90000")], self_id="90000", group_id="")

    results = await _collect(_plugin(reply_in_private=False), event)

    assert results == []


@pytest.mark.asyncio
async def test_repeated_poke_within_cooldown_is_answered_once():
    plugin = _plugin()
    first = FakeEvent(chain=[Poke(id="90000")], self_id="90000")
    second = FakeEvent(chain=[Poke(id="90000")], self_id="90000")

    assert len(await _collect(plugin, first)) == 1
    assert await _collect(plugin, second) == []


@pytest.mark.asyncio
async def test_poke_at_other_member_produces_nothing():
    event = FakeEvent(chain=[Poke(id="777777")], self_id="90000")

    assert await _collect(_plugin(), event) == []


@pytest.mark.asyncio
async def test_bridge_context_written_for_memory_plugin():
    event = FakeEvent(chain=[Poke(id="90000")], self_id="90000")

    await _collect(_plugin(), event)

    assert "angelheart_context" in event.get_extra()


@pytest.mark.asyncio
async def test_message_chain_is_left_untouched():
    chain = [Poke(id="90000")]
    event = FakeEvent(chain=chain, self_id="90000")

    await _collect(_plugin(), event)

    assert event.get_messages() == chain
    assert isinstance(event.get_messages()[0], Poke)


@pytest.mark.asyncio
async def test_pokeback_sends_when_enabled():
    bot = FakeBot()
    event = FakeEvent(chain=[Poke(id="90000")], self_id="90000", bot=bot)
    plugin = _plugin(pokeback={"enabled": True, "probability": 1.0, "times": 1, "interval": 0})

    await _collect(plugin, event)

    assert bot.pokes == [("group", "123456")]


@pytest.mark.asyncio
async def test_group_whitelist_blocks_unlisted_group():
    event = FakeEvent(chain=[Poke(id="90000")], self_id="90000")

    results = await _collect(_plugin(group_whitelist=["99999"]), event)

    assert results == []


@pytest.mark.asyncio
async def test_group_whitelist_allows_listed_group():
    event = FakeEvent(chain=[Poke(id="90000")], self_id="90000")

    results = await _collect(_plugin(group_whitelist=["55555"]), event)

    assert len(results) == 1


@pytest.mark.asyncio
async def test_zero_cooldown_answers_every_poke():
    plugin = _plugin(cooldown_seconds=0)
    first = FakeEvent(chain=[Poke(id="90000")], self_id="90000")
    second = FakeEvent(chain=[Poke(id="90000")], self_id="90000")

    assert len(await _collect(plugin, first)) == 1
    assert len(await _collect(plugin, second)) == 1


@pytest.mark.asyncio
async def test_nickname_comes_from_group_card():
    bot = FakeBot(member_info={"card": "群名片", "nickname": "QQ昵称"})
    event = FakeEvent(chain=[Poke(id="90000")], self_id="90000", bot=bot)

    results = await _collect(_plugin(prompt_template="{username} 戳了"), event)

    assert "群名片" in results[0]["prompt"]


@pytest.mark.asyncio
async def test_nickname_falls_back_to_qq_id_when_lookup_fails():
    bot = FakeBot(member_info=RuntimeError("boom"))
    event = FakeEvent(chain=[Poke(id="90000")], self_id="90000", bot=bot, sender_name="")

    results = await _collect(_plugin(prompt_template="{username} 戳了"), event)

    assert "123456" in results[0]["prompt"]


@pytest.mark.asyncio
async def test_cooldown_change_takes_effect_without_reload():
    """面板改完冷却时间，下一次事件就该按新值判断。"""
    plugin = _plugin(cooldown_seconds=0)
    first = FakeEvent(chain=[Poke(id="90000")], self_id="90000")
    assert len(await _collect(plugin, first)) == 1

    plugin.config["cooldown_seconds"] = 8
    second = FakeEvent(chain=[Poke(id="90000")], self_id="90000")
    assert await _collect(plugin, second) == []
