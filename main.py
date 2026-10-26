"""插件入口：只在被戳机器人自己时走标准 LLM 链路回应一句。"""

from __future__ import annotations

from astrbot.api.event import filter
from astrbot.api.star import Context, Star

from .poke.plugin import PokeReply


class Main(Star):
    """插件入口。

    不需要 @register 装饰器：继承 Star 时框架按模块路径自动注册，
    名称与展示信息统一由 metadata.yaml 提供，避免双处维护。
    """

    def __init__(self, context: Context, config=None) -> None:
        super().__init__(context, config)
        self.reply = PokeReply(context, config)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_poke(self, event):
        """监听戳一戳通知。"""
        async for result in self.reply.on_event(event):
            yield result
