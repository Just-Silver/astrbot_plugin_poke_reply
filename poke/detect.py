"""从事件里识别「谁戳了谁」，只放行戳机器人自己的通知。"""

from __future__ import annotations

from dataclasses import dataclass

from astrbot.core.message.components import Poke


@dataclass(frozen=True)
class PokeSignal:
    """一次被戳事件的关键信息。"""

    sender_id: str
    group_id: str
    is_group: bool


def _poked_target(component) -> str | None:
    """取出 Poke 组件里的被戳目标。

    新版组件提供 target_id()；老版本只有 qq/id 字段，逐级回退。
    """
    resolver = getattr(component, "target_id", None)
    if callable(resolver):
        try:
            return resolver()
        except Exception:
            pass

    for attr in ("id", "qq"):
        value = getattr(component, attr, None)
        if value is None:
            continue
        text = str(value).strip()
        if text and text != "0":
            return text
    return None


def detect_poke(event) -> PokeSignal | None:
    """判断当前事件是否为「别人戳我」。

    戳别人、机器人自己发出的戳、普通消息都返回 None。
    """
    target_id = None
    for component in event.get_messages() or []:
        if isinstance(component, Poke):
            target_id = _poked_target(component)
            break
    if not target_id:
        return None

    self_id = str(event.get_self_id() or "").strip()
    if not self_id or target_id != self_id:
        return None

    sender_id = str(event.get_sender_id() or "").strip()
    if not sender_id or sender_id == self_id:
        return None

    group_id = str(event.get_group_id() or "").strip()
    return PokeSignal(sender_id=sender_id, group_id=group_id, is_group=bool(group_id))
