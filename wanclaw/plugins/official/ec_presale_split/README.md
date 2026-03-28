# 预售订单自动拆分

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.ec_presale_split |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | 电商自动化 |
| 难度 | 高级 |
| 作者 | WanClaw |

## 功能说明

预售订单按商品库存状态自动拆分为现货单/预售单，分别推送至仓库处理

## 关键词

预售 / 订单拆分 / 库存 / 电商

## 权限说明

network, database

## 依赖

无外部依赖

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.ec_presale_split", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
