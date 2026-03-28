# 定时任务触发

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.wf_schedule_trigger |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | 工作流 |
| 难度 | 中级 |
| 作者 | WanClaw |

## 功能说明

工作流支持定时触发（cron表达式），按日/周/月循环执行

## 关键词

定时任务 / Cron / 工作流 / 触发

## 权限说明

database

## 依赖

无外部依赖

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.wf_schedule_trigger", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
