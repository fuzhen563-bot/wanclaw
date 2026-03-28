# 客服接待量实时报表

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.data_agent_stats |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | 数据统计 |
| 难度 | 中级 |
| 作者 | WanClaw |

## 功能说明

客服的接待消息数、平均响应时长、好评率实时统计，生成个人/团队排行榜

## 关键词

客服统计 / 接待量 / 排行榜 / 客服

## 权限说明

database

## 依赖

无外部依赖

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.data_agent_stats", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
