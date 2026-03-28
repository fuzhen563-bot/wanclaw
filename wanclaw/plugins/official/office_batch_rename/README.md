# 批量文件规则重命名

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.office_batch_rename |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | 办公RPA |
| 难度 | 初级 |
| 作者 | WanClaw |

## 功能说明

按前缀/后缀/序号/日期等规则批量重命名文件，支持预览和撤销

## 关键词

重命名 / 批量 / 文件 / 自动化 / 办公

## 权限说明

filesystem:read, filesystem:write

## 依赖

无外部依赖

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.office_batch_rename", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
