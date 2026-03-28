# 库存周转率分析

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.data_inventory_turnover |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | 数据统计 |
| 难度 | 高级 |
| 作者 | WanClaw |

## 功能说明

自动计算各SKU的库存周转天数、呆滞库存预警、补货建议

## 关键词

库存周转 / 呆滞库存 / 补货 / 电商

## 权限说明

database

## 依赖

pandas

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.data_inventory_turnover", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
