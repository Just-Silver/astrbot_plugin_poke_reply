"""戳一戳应答的核心流程。

顺序要点：
1. 先抑制框架默认 LLM 链路（私聊戳一戳会被判成唤醒，否则会回两遍）。
2. 不改 message_obj.message，Poke 组件原样留给其它插件。
3. 传 conversation 让对话历史进入请求，同时用 bridge 把检索词换成真实对话。
"""

from __future__ import annotations

import time

from astrbot.api import logger

from .bridge import build_angelheart_context, extract_last_user_text
from .cooldown import Cooldown
from .detect import detect_poke
from .pokeback import Pokeback
from .prompt import DEFAULT_TEMPLATE, render_prompt


class PokeReply:
    def __init__(self, context, config) -> None:
        self.context = context
        # 保留配置对象引用而不是拷贝：面板改完立刻生效，不必重载插件。
        self.config = config if config is not None else {}
        self.cooldown = Cooldown(self._value("cooldown_seconds", 8))

    def _value(self, key, default):
        raw = self.config.get(key, default)
        return default if raw is None else raw

    def _pokeback(self) -> Pokeback:
        raw = self.config.get("pokeback") or {}
        return Pokeback(
            enabled=raw.get("enabled", False),
            probability=raw.get("probability", 0.15),
            times=raw.get("times", 1),
            interval=raw.get("interval", 0.4),
        )

    async def on_event(self, event):
        """处理一次事件，被戳且通过全部检查时产出 LLM 请求。"""
        if not self._value("enabled", True):
            return

        signal = detect_poke(event)
        if signal is None:
            return

        # should_call_llm(True) 的语义是「禁止框架默认 LLM 链路」，别被方法名读反：
        # 私聊里的戳一戳会被框架判成唤醒，不掐掉就会和我们各回一条。
        # 放在开关/冷却判断之前是故意的——选择沉默时也不许默认链路插话。
        event.should_call_llm(True)

        if signal.is_group:
            if not self._value("reply_in_group", True):
                return
            if not self._group_allowed(signal.group_id):
                return
        elif not self._value("reply_in_private", True):
            return

        # 面板改完冷却时间是热生效的，所以每次事件重读一遍。
        self.cooldown.seconds = max(0.0, float(self._value("cooldown_seconds", 8)))
        scope = event.unified_msg_origin
        if not self.cooldown.allow(scope, signal.sender_id):
            logger.debug(f"[戳一戳应答] {signal.sender_id} 处于冷却中，忽略")
            return

        username = await self._nickname(event, signal)
        scene = "群聊" if signal.is_group else "私聊"

        await self._pokeback().send(event, target_id=signal.sender_id)

        conversation = await self._conversation(event)
        last_user_text = extract_last_user_text(getattr(conversation, "history", "") if conversation else "")
        event.set_extra(
            "angelheart_context",
            build_angelheart_context(
                username=username,
                user_id=signal.sender_id,
                scene=scene,
                last_user_text=last_user_text,
                timestamp=time.time(),
            ),
        )

        prompt = render_prompt(
            self._value("prompt_template", DEFAULT_TEMPLATE),
            username=username,
            user_id=signal.sender_id,
            scene=scene,
        )
        logger.info(f"[戳一戳应答] {scene} 用户 {username}({signal.sender_id}) 戳了机器人")
        yield event.request_llm(
            prompt=prompt,
            conversation=conversation if self._value("carry_history", True) else None,
        )

    def _group_allowed(self, group_id: str) -> bool:
        """白名单为空表示所有群都放行。"""
        allowed = self.config.get("group_whitelist") or []
        ids = {str(item).strip() for item in allowed if str(item).strip()}
        return not ids or group_id in ids

    async def _nickname(self, event, signal) -> str:
        """优先取群名片，取不到退回昵称、再退回 QQ 号。"""
        if signal.is_group:
            try:
                info = await event.bot.get_group_member_info(
                    group_id=int(signal.group_id),
                    user_id=int(signal.sender_id),
                )
                if isinstance(info, dict):
                    name = info.get("card") or info.get("nickname")
                    if name:
                        return str(name)
            except Exception as e:
                logger.debug(f"[戳一戳应答] 取群名片失败，退回默认昵称: {e}")

        name = str(event.get_sender_name() or "").strip()
        return name or signal.sender_id

    async def _conversation(self, event):
        """取当前会话的 conversation；失败返回 None，不阻塞回复。"""
        manager = getattr(self.context, "conversation_manager", None)
        if manager is None:
            return None

        try:
            cid = await manager.get_curr_conversation_id(event.unified_msg_origin)
            if not cid:
                cid = await manager.new_conversation(
                    event.unified_msg_origin,
                    event.get_platform_id(),
                )
            return await manager.get_conversation(event.unified_msg_origin, cid)
        except Exception as e:
            logger.warning(f"[戳一戳应答] 获取对话失败，将以无上下文模式回应: {e}")
            return None
