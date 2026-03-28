# 失败步骤自动重试

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.wf_auto_retry |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | 工作流 |
| 难度 | 中级 |
| 作者 | WanClaw |

## 功能说明

工作流节点执行失败时自动重试，支持设置重试次数、间隔、可跳过的错误类型

## 关键词

重试 / 容错 / 工作流 / 失败处理

## 权限说明

database

## 依赖

无外部依赖

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.wf_auto_retry", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
