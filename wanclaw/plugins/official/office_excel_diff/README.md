# Excel批量对比差异

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.office_excel_diff |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | 办公RPA |
| 难度 | 中级 |
| 作者 | WanClaw |

## 功能说明

两个或多个Excel文件对比，快速找出差异单元格、新增行、删除行，高亮标注

## 关键词

Excel / 对比 / 差异 / 表格 / 办公

## 权限说明

filesystem:read

## 依赖

openpyxl

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.office_excel_diff", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
