# 知识库智能问答

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.ai_knowledge_qa |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | AI增强 |
| 难度 | 高级 |
| 作者 | WanClaw |

## 功能说明

基于企业知识库进行 RAG 检索问答，支持上传文档构建知识库，精准回答内部问题

## 关键词

知识库 / RAG / 问答 / 检索增强 / AI

## 权限说明

network, database

## 依赖

无外部依赖

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.ai_knowledge_qa", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
