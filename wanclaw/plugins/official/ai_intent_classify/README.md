# AI意图识别

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.ai_intent_classify |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | AI增强 |
| 难度 | 高级 |
| 作者 | WanClaw |

## 功能说明

无需配置，自动识别用户消息意图（咨询/投诉/购买/退款等），驱动智能路由

## 关键词

意图识别 / NLP / 分类 / AI / 客服

## 权限说明

network

## 依赖

无外部依赖

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.ai_intent_classify", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
