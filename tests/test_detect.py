"""识别「谁戳了谁」：只认戳机器人自己，其余一律不处理。"""

from __future__ import annotations

from astrbot_plugin_poke_reply.poke.detect import detect_poke
from conftest import At, FakeEvent, Poke


def test_poke_aimed_at_bot_is_detected():
    event = FakeEvent(chain=[Poke(id="90000")], self_id="90000", sender_id="123456")

    signal = detect_poke(event)

    assert signal is not None
    assert signal.sender_id == "123456"
    assert signal.group_id == "55555"
    assert signal.is_group is True


def test_poke_aimed_at_another_member_is_ignored():
    event = FakeEvent(chain=[Poke(id="777777")], self_id="90000")

    assert detect_poke(event) is None


def test_poke_sent_by_bot_itself_is_ignored():
    event = FakeEvent(chain=[Poke(id="123456")], self_id="90000", sender_id="90000")

    assert detect_poke(event) is None


def test_plain_message_is_ignored():
    event = FakeEvent(
        chain=[
            At(qq="90000"),
        ],
        self_id="90000",
    )

    assert detect_poke(event) is None


def test_private_poke_is_marked_as_private_scene():
    event = FakeEvent(chain=[Poke(id="90000")], self_id="90000", group_id="")

    signal = detect_poke(event)

    assert signal is not None
    assert signal.is_group is False
    assert signal.group_id == ""
