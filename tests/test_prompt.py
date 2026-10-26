"""提示词渲染：带昵称与场景，未知占位符不炸。"""

from __future__ import annotations

from astrbot_plugin_poke_reply.poke.prompt import DEFAULT_TEMPLATE, render_prompt


def test_render_fills_nickname_user_id_and_scene():
    text = render_prompt(
        DEFAULT_TEMPLATE,
        username="张三",
        user_id="123456",
        scene="群聊",
    )

    assert "张三" in text
    assert "123456" in text
    assert "群聊" in text


def test_render_tolerates_unknown_placeholder():
    text = render_prompt("{username} 戳了你{不存在的占位符}", username="张三", user_id="1", scene="群聊")

    assert "张三" in text
    assert "{不存在的占位符}" in text


def test_render_never_leaks_raw_placeholders_for_known_fields():
    text = render_prompt("{username}|{user_id}|{scene}", username="李四", user_id="42", scene="私聊")

    assert text == "李四|42|私聊"
