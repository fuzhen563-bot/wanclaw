# 执行结果自动通知

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.wf_result_notify |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | 工作流 |
| 难度 | 初级 |
| 作者 | WanClaw |

## 功能说明

工作流执行完成后自动发送通知，支持钉钉/飞书/邮件/微信

## 关键词

通知 / 工作流 / 执行结果

## 权限说明

network, database

## 依赖

无外部依赖

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.wf_result_notify", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
