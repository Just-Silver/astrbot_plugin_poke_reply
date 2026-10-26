"""天使之魂桥接：让记忆检索拿到真实对话而不是字面量 [Poke]。"""

from __future__ import annotations

import json

from astrbot_plugin_poke_reply.poke.bridge import build_angelheart_context, extract_last_user_text


def test_bridge_payload_has_single_identified_record():
    payload = json.loads(
        build_angelheart_context(
            username="张三",
            user_id="123456",
            scene="群聊",
            last_user_text="",
            timestamp=1772000000.0,
        )
    )

    records = payload["chat_records"]
    assert len(records) == 1
    assert records[0]["role"] == "user"
    assert records[0]["sender_id"] == "123456"
    assert records[0]["sender_name"] == "张三"
    assert payload["historical_count"] == 0
    assert payload["secretary_decision"] == {}


def test_bridge_never_contains_raw_poke_outline():
    payload = build_angelheart_context(
        username="张三",
        user_id="123456",
        scene="群聊",
        last_user_text="明天几点集合？",
        timestamp=1772000000.0,
    )

    assert "[Poke]" not in payload
    assert "明天几点集合？" in payload


def test_bridge_mentions_person_and_scene_without_history():
    payload = build_angelheart_context(
        username="张三",
        user_id="123456",
        scene="私聊",
        last_user_text="",
        timestamp=1772000000.0,
    )

    assert "张三" in payload
    assert "私聊" in payload


def test_extract_last_user_text_picks_latest_user_message():
    history = json.dumps(
        [
            {"role": "user", "content": "第一句"},
            {"role": "assistant", "content": "回复"},
            {"role": "user", "content": [{"type": "text", "text": "最后一句"}]},
        ]
    )

    assert extract_last_user_text(history) == "最后一句"


def test_extract_last_user_text_tolerates_broken_history():
    assert extract_last_user_text("{ not json") == ""
    assert extract_last_user_text("") == ""
    assert extract_last_user_text("[]") == ""


def test_extract_last_user_text_skips_placeholder_entries():
    history = json.dumps([{"role": "user", "content": "[Poke]"}])

    assert extract_last_user_text(history) == ""
