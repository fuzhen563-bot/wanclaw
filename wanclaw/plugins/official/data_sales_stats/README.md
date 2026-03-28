# 经营数据自动统计

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.data_sales_stats |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | 数据统计 |
| 难度 | 中级 |
| 作者 | WanClaw |

## 功能说明

日/周/月度订单销售额、退款额、客单价自动统计，支持多平台汇总对比

## 关键词

销售统计 / 经营数据 / 报表 / 电商

## 权限说明

database, filesystem:write

## 依赖

pandas

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.data_sales_stats", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
