"""插件入口的装配：装饰器链与配置对象都要对得上框架契约。"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

PARENT = Path(__file__).resolve().parent.parent.parent
if str(PARENT) not in sys.path:
    sys.path.insert(0, str(PARENT))

PACKAGE = "astrbot_plugin_poke_reply"


def test_main_module_imports_and_builds_plugin():
    main = importlib.import_module(f"{PACKAGE}.main")

    class _Context:
        conversation_manager = None

    plugin = main.Main(_Context(), {"enabled": True})

    assert plugin.reply is not None


def test_entry_handler_is_registered():
    main = importlib.import_module(f"{PACKAGE}.main")

    assert hasattr(main.Main, "on_poke")
    assert callable(main.Main.on_poke)
