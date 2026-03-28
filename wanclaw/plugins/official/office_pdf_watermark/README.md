# PDF批量水印处理

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.office_pdf_watermark |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | 办公RPA |
| 难度 | 中级 |
| 作者 | WanClaw |

## 功能说明

批量给PDF添加文字/图片水印，或批量去除水印，支持自定义透明度、位置、旋转角度

## 关键词

PDF / 水印 / 批量 / 办公

## 权限说明

filesystem:read, filesystem:write

## 依赖

PyPDF2

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.office_pdf_watermark", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
