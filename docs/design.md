<!-- 职责：本插件的实现契约——事件判定、请求链路、桥接数据格式、已知边界；不写：安装步骤、配置项逐条解释（见 README）。 -->

# 设计说明

## 事件判定

OneBot v11 的戳一戳是通知事件，AstrBot 把它转成 `AstrMessageEvent`，消息链里只有一个 `Poke` 组件（`aiocqhttp_platform_adapter.py` 的 `_convert_handle_notice_event`）。

判定顺序（`poke/detect.py`）：

1. 消息链里有 `Poke` 组件，且它的 `target_id()` 等于机器人自己 → 否则退出（戳别人不处理）。
2. 发送者不是机器人自己 → 否则退出（自己发出的戳不处理）。
3. 有 `group_id` 就是群聊，否则私聊。

## 请求链路

```
Poke 通知事件
  ↓ should_call_llm(True)        抑制框架默认链路
  ↓ 开关 / 白名单 / 冷却
  ↓ 查群名片（失败回退昵称、再回退 QQ 号）
  ↓ 反戳（默认关）
  ↓ 写 event.angelheart_context   给天使之魂的检索桥接
  ↓ render_prompt                 {username} {user_id} {scene}
  ↓ event.request_llm(prompt, conversation)
框架 ProcessStage → OnLLMRequestEvent 钩子（天使之魂在此注入记忆）
  ↓
模型回复
```

### 必须 `should_call_llm(True)` 的原因

方法名读起来像「允许调用」，实际语义是「禁止框架默认 LLM 链路」。私聊里的戳一戳通知会被 `waking_check` 判成唤醒（`is_at_or_wake_command = True`），不掐掉就会和本插件各回一条。

调用位置在开关与冷却判断**之前**：即使我们决定沉默，也不该让默认链路插一句。

## 桥接数据契约

写入 `event.set_extra("angelheart_context", <json 字符串>)`：

```json
{
  "chat_records": [
    {
      "role": "user",
      "content": [{"type": "text", "text": "群聊：张三 戳了你一下。对方上一条消息：明天几点集合？"}],
      "sender_id": "123456",
      "sender_name": "张三",
      "timestamp": 1772000000.0,
      "is_processed": false,
      "is_structured_toolcall": false
    }
  ],
  "historical_count": 0,
  "secretary_decision": {}
}
```

四个约束各有原因：

| 约束 | 原因 |
|---|---|
| `sender_id` / `sender_name` 非空 | 天使之魂的 `_dedupe_and_sort_chat_records` 会静默丢弃身份缺失的 user 记录 |
| `historical_count: 0` | 让它走 `_split_chat_snapshot` 的显式分支，0 = 全部属于当前块 |
| `secretary_decision` 留空 | 非空会走关键词检索分支；留空才退到 `format_chat_records`，用它拼出的人话当检索词 |
| 只放一条、话题写进 content | 原生会话历史的 user 记录没有 sender_id，补身份等于伪造发言人 |

### 绝不修改 message_obj.message

天使之心靠 `isinstance(comp, Poke)` 识别戳一戳并放行。把 Poke 换掉会让它误判成普通文本消息，进入防抖与秘书链路。桥接数据是纯增量字段，不影响任何人的判定。

## 已知边界

- **天使之心的账本不含戳一戳轮次**。它重写群聊上下文时用自己账本覆盖 `req.contexts`，所以我们这次回复在它那边不可见。当前戳一戳路径不会触发重写（缺 `angelheart_decision_context`），所以暂时没有影响；若上游改了触发条件，表现为回复接不上前文。
- **带 QQ 号进模型**。默认模板含 `{user_id}`，用于区分同名群友。不想要就删掉该占位符。
- **仅 aiocqhttp**。其它平台没有原生戳一戳能力。
