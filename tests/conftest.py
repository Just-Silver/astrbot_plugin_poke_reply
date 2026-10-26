"""注入 astrbot 框架桩，让插件源码可在无 AstrBot 环境的机器上直接跑测试。

导入路径与 AstrBot 真实加载一致：以插件目录为包名（`astrbot_plugin_poke_reply`），
避免测试用顶层 `poke.*`、运行时用相对导入，导致同名模块被加载两份。
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PACKAGE_PARENT = ROOT.parent
for _path in (str(ROOT), str(PACKAGE_PARENT)):
    if _path not in sys.path:
        sys.path.insert(0, _path)


def _module(name: str) -> types.ModuleType:
    module = types.ModuleType(name)
    sys.modules[name] = module
    return module


class Poke:
    """与框架同名的戳一戳组件桩，只需 target_id() 契约。"""

    def __init__(self, id=None, qq=None):
        self.id = id
        self.qq = qq

    def target_id(self):
        for value in (self.id, self.qq):
            if value is None:
                continue
            text = str(value).strip()
            if text and text != "0":
                return text
        return None


class Plain:
    def __init__(self, text=""):
        self.text = text


class At:
    def __init__(self, qq="", name=""):
        self.qq = qq
        self.name = name


class Star:
    def __init__(self, context, config=None):
        self.context = context
        self.config = config or {}


def _install_stubs() -> None:
    if "astrbot" in sys.modules and getattr(sys.modules["astrbot"], "_poke_reply_stub", False):
        return

    astrbot = _module("astrbot")
    astrbot._poke_reply_stub = True

    api = _module("astrbot.api")
    api.logger = __import__("logging").getLogger("astrbot")
    api.AstrBotConfig = dict

    def _decorator(*_args, **_kwargs):
        def wrap(func):
            return func

        return wrap

    event_pkg = _module("astrbot.api.event")
    event_pkg.AstrMessageEvent = object

    class _Filter:
        PlatformAdapterType = types.SimpleNamespace(AIOCQHTTP="aiocqhttp")
        EventMessageType = types.SimpleNamespace(ALL=7, GROUP_MESSAGE=1, PRIVATE_MESSAGE=2, OTHER_MESSAGE=4)

        @staticmethod
        def platform_adapter_type(*_a, **_k):
            return _decorator()

        @staticmethod
        def event_message_type(*_a, **_k):
            return _decorator()

    event_pkg.filter = _Filter

    star_pkg = _module("astrbot.api.star")
    star_pkg.Context = object
    star_pkg.Star = Star
    star_pkg.register = _decorator

    core = _module("astrbot.core")
    core.__path__ = []

    message_pkg = _module("astrbot.core.message")
    message_pkg.__path__ = []

    components = _module("astrbot.core.message.components")
    components.Poke = Poke
    components.Plain = Plain
    components.At = At

    api.AstrBotConfig = dict


_install_stubs()


class FakeConversation:
    def __init__(self, cid="cid-1", history="[]"):
        self.cid = cid
        self.history = history


class FakeConversationManager:
    def __init__(self, history="[]"):
        self.history = history
        self.created = 0

    async def get_curr_conversation_id(self, _umo):
        return "cid-1"

    async def get_conversation(self, _umo, _cid):
        return FakeConversation(history=self.history)

    async def new_conversation(self, _umo, _platform_id=None):
        self.created += 1
        return "cid-1"


class FakeBot:
    """只实现插件会调用的 OneBot 接口，并记录调用。"""

    def __init__(self, member_info=None):
        self.member_info = member_info or {}
        self.pokes: list[tuple[str, str]] = []

    async def get_group_member_info(self, group_id=None, user_id=None):
        if isinstance(self.member_info, Exception):
            raise self.member_info
        return self.member_info

    async def group_poke(self, group_id=None, user_id=None):
        self.pokes.append(("group", str(user_id)))

    async def friend_poke(self, user_id=None):
        self.pokes.append(("friend", str(user_id)))


class FakeEvent:
    """戳一戳通知事件的最小可用替身。"""

    def __init__(
        self,
        chain=None,
        self_id="90000",
        sender_id="123456",
        sender_name="123456",
        group_id="55555",
        umo=None,
        bot=None,
        conversation_manager=None,
    ):
        self._chain = list(chain or [])
        self._self_id = self_id
        self._sender_id = sender_id
        self._sender_name = sender_name
        self._group_id = group_id
        self._extras: dict = {}
        self.call_llm = False
        self.requests: list[dict] = []
        self.bot = bot or FakeBot()
        self.unified_msg_origin = umo or (
            f"aiocqhttp:GroupMessage:{group_id}" if group_id else f"aiocqhttp:FriendMessage:{sender_id}"
        )
        self.conversation_manager = conversation_manager or FakeConversationManager()

    def get_messages(self):
        return self._chain

    def get_self_id(self):
        return self._self_id

    def get_sender_id(self):
        return self._sender_id

    def get_sender_name(self):
        return self._sender_name

    def get_group_id(self):
        return self._group_id

    def get_platform_name(self):
        return "aiocqhttp"

    def get_platform_id(self):
        return "aiocqhttp-1"

    def is_private_chat(self):
        return not self._group_id

    def set_extra(self, key, value):
        self._extras[key] = value

    def get_extra(self, key=None, default=None):
        if key is None:
            return self._extras
        return self._extras.get(key, default)

    def should_call_llm(self, value):
        self.call_llm = value

    def request_llm(self, prompt="", conversation=None, **_kwargs):
        payload = {"prompt": prompt, "conversation": conversation}
        self.requests.append(payload)
        return payload


@pytest.fixture
def context():
    class _Context:
        def __init__(self):
            self.conversation_manager = FakeConversationManager()

    return _Context()
