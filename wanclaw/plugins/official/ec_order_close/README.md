# 超时订单自动关闭

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.ec_order_close |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | 电商自动化 |
| 难度 | 初级 |
| 作者 | WanClaw |

## 功能说明

电商平台超时未支付订单自动关闭，释放库存，支持自定义超时时间规则

## 关键词

订单 / 超时 / 自动关闭 / 库存释放 / 电商

## 权限说明

network, database

## 依赖

无外部依赖

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.ec_order_close", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
