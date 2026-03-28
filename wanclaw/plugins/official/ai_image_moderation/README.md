# 图片内容安全审核

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.ai_image_moderation |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | AI增强 |
| 难度 | 高级 |
| 作者 | WanClaw |

## 功能说明

自动检测图片中的色情、暴恐、政治敏感等违规内容，返回风险评分和位置

## 关键词

图片审核 / 内容安全 / 鉴黄 / AI

## 权限说明

network, filesystem:read

## 依赖

无外部依赖

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.ai_image_moderation", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
