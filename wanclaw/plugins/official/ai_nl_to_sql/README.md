# 自然语言转 SQL

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.ai_nl_to_sql |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | AI增强 |
| 难度 | 高级 |
| 作者 | WanClaw |

## 功能说明

用自然语言提问，自动生成 SQL 查询语句，从数据库获取结果并解读

## 关键词

NL2SQL / 自然语言 / 数据库查询 / AI

## 权限说明

network, database

## 依赖

无外部依赖

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.ai_nl_to_sql", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
