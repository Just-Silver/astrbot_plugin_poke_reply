"""渲染被戳提示词。

用正则替换 {key} 形式占位符：未知占位符原样保留，不用 str.format（配置里的
花括号会让它抛 KeyError），也不用 string.Template（占位符风格是 $key）。
"""

from __future__ import annotations

import re

DEFAULT_TEMPLATE = (
    "{username}（{user_id}）在{scene}里戳了你一下。"
    "请结合最近聊过的内容，用一句自然的话回应。"
    "不要复述这条说明，也不要解释“我被戳了”。"
)

_PLACEHOLDER = re.compile(r"\{(\w+)\}")


def render_prompt(template: str, *, username: str, user_id: str, scene: str) -> str:
    """把昵称、用户 ID、场景填进模板，未知占位符保持原样。"""
    body = template if template and template.strip() else DEFAULT_TEMPLATE
    values = {"username": username, "user_id": user_id, "scene": scene}
    return _PLACEHOLDER.sub(
        lambda match: str(values.get(match.group(1), match.group(0))),
        body,
    )
