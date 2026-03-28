# 插件使用数据统计

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.data_plugin_usage |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | 数据统计 |
| 难度 | 中级 |
| 作者 | WanClaw |

## 功能说明

统计各插件的使用频率、执行成功率、平均耗时，支持按团队/用户筛选

## 关键词

插件统计 / 使用数据 / 分析

## 权限说明

database

## 依赖

无外部依赖

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.data_plugin_usage", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
