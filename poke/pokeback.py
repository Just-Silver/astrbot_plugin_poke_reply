"""反戳：默认关闭，开启后按概率与次数戳回去。"""

from __future__ import annotations

import asyncio
import random

from astrbot.api import logger


class Pokeback:
    def __init__(self, *, enabled: bool, probability: float, times: int, interval: float) -> None:
        self.enabled = bool(enabled)
        self.probability = min(1.0, max(0.0, float(probability)))
        self.times = max(1, int(times))
        self.interval = max(0.0, float(interval))

    def should_send(self) -> bool:
        """按概率决定这次要不要反戳。"""
        if not self.enabled or self.probability <= 0:
            return False
        if self.probability >= 1:
            return True
        return random.random() < self.probability

    async def send(self, event, target_id: str) -> int:
        """执行反戳，返回实际发出的次数。"""
        if not self.should_send():
            return 0

        group_id = str(event.get_group_id() or "").strip()
        sent = 0
        for _ in range(self.times):
            try:
                if group_id:
                    await event.bot.group_poke(group_id=int(group_id), user_id=int(target_id))
                else:
                    await event.bot.friend_poke(user_id=int(target_id))
                sent += 1
            except Exception as e:
                logger.warning(f"[戳一戳应答] 反戳失败 target={target_id}: {e}")
                break

            if self.interval and sent < self.times:
                await asyncio.sleep(self.interval)

        return sent
