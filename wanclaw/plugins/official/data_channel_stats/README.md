# 客户来源渠道分析

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.data_channel_stats |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | 数据统计 |
| 难度 | 中级 |
| 作者 | WanClaw |

## 功能说明

分析客户来源渠道（搜索/广告/社群/活动等），统计各渠道转化率和ROI

## 关键词

渠道分析 / 来源统计 / ROI / 转化率

## 权限说明

database, filesystem:write

## 依赖

无外部依赖

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.data_channel_stats", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
