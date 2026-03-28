# 文件夹自动整理归档

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.office_folder_auto_sort |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | 办公RPA |
| 难度 | 初级 |
| 作者 | WanClaw |

## 功能说明

按文件类型、日期、名称等规则自动整理文件夹，支持自定义规则、定期自动执行

## 关键词

文件夹 / 整理 / 归档 / 自动化 / 办公

## 权限说明

filesystem:read, filesystem:write

## 依赖

无外部依赖

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.office_folder_auto_sort", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
