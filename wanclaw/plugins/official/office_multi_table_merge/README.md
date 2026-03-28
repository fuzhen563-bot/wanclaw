# 多表格自动汇总

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.office_multi_table_merge |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | 办公RPA |
| 难度 | 中级 |
| 作者 | WanClaw |

## 功能说明

将多个结构相同或不同的表格按字段关联汇总，支持vlookup、数据透视

## 关键词

汇总 / 合并 / 表格 / vlookup / 办公

## 权限说明

filesystem:read, filesystem:write

## 依赖

pandas, openpyxl

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.office_multi_table_merge", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
