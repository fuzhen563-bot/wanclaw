# 会议纪要生成

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.ai_meeting_minutes |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | AI增强 |
| 难度 | 中级 |
| 作者 | WanClaw |

## 功能说明

上传会议录音或文字记录，AI 自动生成结构化会议纪要，包含决议、待办和负责人

## 关键词

会议纪要 / 会议记录 / 待办事项 / AI

## 权限说明

network, filesystem:read, filesystem:write

## 依赖

无外部依赖

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.ai_meeting_minutes", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
