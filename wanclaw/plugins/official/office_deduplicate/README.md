# 表格重复数据去重

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.office_deduplicate |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | 办公RPA |
| 难度 | 初级 |
| 作者 | WanClaw |

## 功能说明

Excel/CSV表格按指定列去重，支持完全去重和模糊去重，生成去重报告

## 关键词

去重 / 重复 / 表格 / 数据清洗 / 办公

## 权限说明

filesystem:read, filesystem:write

## 依赖

pandas

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.office_deduplicate", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
