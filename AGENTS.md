# AGENTS

## 项目定位

自用插件，不上架插件市场。目录名、`metadata.yaml` 的 `name`、Python 包名保持一致（`astrbot_plugin_poke_reply`），否则 AstrBot 更新匹配会失效。

## 硬约束

- **不要修改 `event.message_obj.message`**。天使之心靠 `Poke` 组件识别戳一戳并放行，替换组件会让它误判成普通文本消息。需要给下游传信息就写 `event.set_extra(...)`。
- **必须先调 `event.should_call_llm(True)`**。它语义是「禁止框架默认 LLM 链路」，不是「允许」。私聊戳一戳会被判成唤醒，不掐掉会回两条。
- **不引入插件间依赖**。检查天使之魂是否安装会让插件在对方被关掉时静默失效，得不偿失。
- 平台限定 aiocqhttp，非 OneBot 适配器没有戳一戳能力。

## 门禁

推送前必须本地通过：

```bash
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
```

## 文档

- 用户视角改动 → `README.md`
- 契约 / 实现 / 边界改动 → `docs/design.md`
- 新增文档须在同一次改动里登记到 `docs/README.md`

## 提交

提交信息用中文，格式 `type(scope): 中文摘要`，type 取 `feat` / `fix` / `refactor` / `docs` / `chore`。
