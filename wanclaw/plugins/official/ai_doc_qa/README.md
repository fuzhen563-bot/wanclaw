# 文档智能问答

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.ai_doc_qa |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | AI增强 |
| 难度 | 中级 |
| 作者 | WanClaw |

## 功能说明

上传 PDF/Word/Excel 后，直接用自然语言提问，AI 从文档中找出答案并标注来源

## 关键词

文档问答 / PDF / Word / 问答 / AI

## 权限说明

network, filesystem:read

## 依赖

无外部依赖

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.ai_doc_qa", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
