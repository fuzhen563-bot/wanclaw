# 每日经营数据推送

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.data_daily_push |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | 数据统计 |
| 难度 | 初级 |
| 作者 | WanClaw |

## 功能说明

每天定时将核心经营指标（销售额/订单数/客单价）推送至钉钉群/邮件/微信

## 关键词

数据推送 / 每日简报 / 经营数据

## 权限说明

network, database

## 依赖

无外部依赖

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.data_daily_push", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
