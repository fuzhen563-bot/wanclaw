# Bug 自动检测

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.ai_bug_detect |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | AI增强 |
| 难度 | 高级 |
| 作者 | WanClaw |

## 功能说明

扫描代码自动发现潜在 Bug、安全漏洞、性能问题，提供修复建议和示例代码

## 关键词

Bug检测 / 漏洞扫描 / 静态分析 / AI

## 权限说明

network, filesystem:read

## 依赖

无外部依赖

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.ai_bug_detect", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
