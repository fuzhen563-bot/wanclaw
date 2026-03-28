# 高精度OCR识别

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.ai_ocr_high_precision |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | AI增强 |
| 难度 | 中级 |
| 作者 | WanClaw |

## 功能说明

票据、身份证、营业执照、合同等高精度识别，支持批量图片转文字，结构化输出

## 关键词

OCR / 文字识别 / 票据 / 身份证 / AI

## 权限说明

filesystem:read, network

## 依赖

pytesseract, Pillow

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.ai_ocr_high_precision", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
