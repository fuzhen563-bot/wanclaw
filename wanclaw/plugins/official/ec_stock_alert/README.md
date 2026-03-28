# 库存阈值自动告警

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.ec_stock_alert |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | 电商自动化 |
| 难度 | 初级 |
| 作者 | WanClaw |

## 功能说明

商品库存低于预设阈值时自动告警，支持多平台店铺、多SKU监控，消息推送到钉钉/飞书/邮件

## 关键词

库存 / 告警 / 阈值 / 库存预警 / 电商

## 权限说明

network, database

## 依赖

无外部依赖

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.ec_stock_alert", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
