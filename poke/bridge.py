"""给天使之魂写检索桥接数据。

天使之魂拿 event.get_message_outline() 当记忆检索词，而戳一戳通知的 outline
是字面量 "[Poke]"，检索会退化成随机召回。这里补一份它认识的 angelheart_context：
secretary_decision 留空，逼它退到 format_chat_records 分支，用下面这条
带真实身份的记录拼出检索词。

只写这一个 extra，不改 message_obj.message —— 天使之心靠 Poke 组件识别并放行
戳一戳，替换组件会让它误当成普通文本消息。
"""

from __future__ import annotations

import json

_PLACEHOLDER_TEXTS = {"[Poke]", "[poke]", "Poke", ""}


def extract_last_user_text(history: str) -> str:
    """从原生会话历史里取最近一条用户发言，取不到返回空串。"""
    if not history:
        return ""

    try:
        records = json.loads(history)
    except (json.JSONDecodeError, TypeError, ValueError):
        return ""

    if not isinstance(records, list):
        return ""

    for record in reversed(records):
        if not isinstance(record, dict) or record.get("role") != "user":
            continue
        text = _record_text(record.get("content")).strip()
        if text and text not in _PLACEHOLDER_TEXTS:
            return text

    return ""


def _record_text(content) -> str:
    """把 content 统一成文本，兼容字符串与多模态列表。"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
        return " ".join(part for part in parts if part)
    return ""


def build_angelheart_context(
    *,
    username: str,
    user_id: str,
    scene: str,
    last_user_text: str,
    timestamp: float,
) -> str:
    """构造天使之魂认识的 angelheart_context JSON 字符串。"""
    action = f"{username} 戳了你一下"
    if last_user_text:
        action = f"{action}。对方上一条消息：{last_user_text}"

    record = {
        "role": "user",
        "content": [{"type": "text", "text": f"{scene}：{action}"}],
        "sender_id": user_id,
        "sender_name": username,
        "timestamp": timestamp,
        "is_processed": False,
        "is_structured_toolcall": False,
    }

    payload = {
        "chat_records": [record],
        "historical_count": 0,
        "secretary_decision": {},
    }
    return json.dumps(payload, ensure_ascii=False)
