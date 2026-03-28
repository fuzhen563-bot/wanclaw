# 运费智能计算

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.ec_shipping_fee |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | 电商自动化 |
| 难度 | 中级 |
| 作者 | WanClaw |

## 功能说明

根据商品重量、地区、快递公司自动计算运费，支持首重续重、满减包邮规则

## 关键词

运费 / 物流计算 / 快递 / 电商

## 权限说明

network, database

## 依赖

无外部依赖

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.ec_shipping_fee", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
