# 向量语义检索

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.ai_vector_search |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | AI增强 |
| 难度 | 高级 |
| 作者 | WanClaw |

## 功能说明

将文档、图片等内容向量化，支持语义相似度搜索，返回最相关结果

## 关键词

向量 / 语义搜索 / embedding / 相似度 / AI

## 权限说明

network, database

## 依赖

无外部依赖

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.ai_vector_search", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
