# 客户消息智能分级

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.im_message_priority |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | IM智能客服 |
| 难度 | 高级 |
| 作者 | WanClaw |

## 功能说明

基于消息内容和客户画像自动分级（紧急/重要/普通），优先推送高价值客户消息

## 关键词

消息分级 / 优先级 / 客户分层 / 私域

## 权限说明

network, database

## 依赖

无外部依赖

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.im_message_priority", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
