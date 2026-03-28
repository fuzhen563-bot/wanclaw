# 客服会话智能转接

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.im_transfer_handoff |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | IM智能客服 |
| 难度 | 高级 |
| 作者 | WanClaw |

## 功能说明

根据客服技能组、在线状态、客户级别自动转接会话，支持转接历史记录

## 关键词

转接 / 会话 / 客服 / 工单 / IM

## 权限说明

network, database

## 依赖

无外部依赖

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.im_transfer_handoff", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
