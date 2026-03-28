# OCR文字识别

## 插件信息

| 属性 | 值 |
|------|-----|
| 插件ID | skill.ocr_processor |
| 类型 | 官方内置技能 |
| 版本 | 2.0.0 |
| 分类 | AI增强 |
| 难度 | 中级 |
| 作者 | WanClaw |

## 功能描述

OCR识别：图片文字识别、PDF转文字、表格识别、批量识别

## 关键词

ocr / 识别 / 文字 / ai

## 权限说明

filesystem:read

## 使用方法

```python
# 通过插件系统调用
result = await plugin_manager.execute("skill.ocr_processor", {"action": "xxx", ...})
```

## 更新日志

### v2.0.0
- 转换为标准插件格式
- 支持通过 ClawHub 生态站分发

---
*此插件由 WanClaw 官方提供*
