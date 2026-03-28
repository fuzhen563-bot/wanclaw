# PDF 文档问答

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.ai_pdf_qa |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | AI增强 |
| 难度 | 中级 |
| 作者 | WanClaw |

## 功能说明

上传 PDF 文档，用自然语言提问，AI 在文档范围内精准回答，标注答案所在页码

## 关键词

PDF问答 / 文档理解 / PDF阅读 / AI

## 权限说明

network, filesystem:read

## 依赖

无外部依赖

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.ai_pdf_qa", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
