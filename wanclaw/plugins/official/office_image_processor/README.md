# 图片批量处理

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.office_image_processor |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | 办公RPA |
| 难度 | 中级 |
| 作者 | WanClaw |

## 功能说明

批量压缩图片、调整尺寸、裁剪、加logo/水印，支持JPG/PNG/GIF/WebP格式

## 关键词

图片 / 压缩 / 裁剪 / 水印 / 批量 / 办公

## 权限说明

filesystem:read, filesystem:write

## 依赖

Pillow

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.office_image_processor", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
