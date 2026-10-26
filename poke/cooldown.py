"""按「会话 + 用户」的冷却，防止同一人连续戳时刷屏。"""

from __future__ import annotations

import time


class Cooldown:
    """记录每个用户最后一次被回应的时间。

    秒数为 0 表示关闭冷却，任何时刻都放行。
    """

    def __init__(self, seconds: float) -> None:
        self.seconds = max(0.0, float(seconds))
        self._last: dict[tuple[str, str], float] = {}

    def allow(self, scope: str, user_id: str, now: float | None = None) -> bool:
        """判断本次是否放行；放行时顺手记录时间。

        冷却为 0 时仍记录时间：面板从 0 改成非 0 后能立刻按新值判断，
        不必等下一次「真正的」戳。
        """
        current = time.time() if now is None else now
        key = (str(scope), str(user_id))
        last = self._last.get(key)

        if self.seconds <= 0:
            self._last[key] = current
            return True

        if last is not None and current - last < self.seconds:
            return False

        self._last[key] = current
        return True
