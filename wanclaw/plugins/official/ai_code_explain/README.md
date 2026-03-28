# 代码解释与重构

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.ai_code_explain |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | AI增强 |
| 难度 | 中级 |
| 作者 | WanClaw |

## 功能说明

上传代码片段，自动解释逻辑并给出优化重构建议，支持多语言

## 关键词

代码解释 / 重构 / code review / AI

## 权限说明

network, filesystem:read

## 依赖

无外部依赖

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.ai_code_explain", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
