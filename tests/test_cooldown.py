"""冷却规则：同一会话内同一用户连续戳，冷却期内只回应一次。"""

from __future__ import annotations

from astrbot_plugin_poke_reply.poke.cooldown import Cooldown


def test_first_poke_is_allowed():
    guard = Cooldown(seconds=8)

    assert guard.allow("group:55555", "123456", now=1000.0) is True


def test_second_poke_within_cooldown_is_rejected():
    guard = Cooldown(seconds=8)
    guard.allow("group:55555", "123456", now=1000.0)

    assert guard.allow("group:55555", "123456", now=1005.0) is False


def test_poke_after_cooldown_expires_is_allowed():
    guard = Cooldown(seconds=8)
    guard.allow("group:55555", "123456", now=1000.0)

    assert guard.allow("group:55555", "123456", now=1008.1) is True


def test_different_users_do_not_share_cooldown():
    guard = Cooldown(seconds=8)
    guard.allow("group:55555", "123456", now=1000.0)

    assert guard.allow("group:55555", "654321", now=1000.5) is True


def test_different_sessions_do_not_share_cooldown():
    guard = Cooldown(seconds=8)
    guard.allow("group:55555", "123456", now=1000.0)

    assert guard.allow("group:66666", "123456", now=1000.5) is True


def test_zero_seconds_disables_cooldown():
    guard = Cooldown(seconds=0)
    guard.allow("group:55555", "123456", now=1000.0)

    assert guard.allow("group:55555", "123456", now=1000.0) is True
