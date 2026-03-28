# Excel处理

## 插件信息

| 属性 | 值 |
|------|-----|
| 插件ID | skill.excel_processor |
| 类型 | 官方内置技能 |
| 版本 | 2.0.0 |
| 分类 | 办公自动化 |
| 难度 | 中级 |
| 作者 | WanClaw |

## 功能描述

Excel处理：多表合并、拆分、去重、筛选、排序、汇总，生成日报周报月报，批量替换格式

## 关键词

excel / 表格 / 合并 / 拆分 / 报表 / office

## 权限说明

filesystem:read

## 使用方法

```python
# 通过插件系统调用
result = await plugin_manager.execute("skill.excel_processor", {"action": "xxx", ...})
```

## 更新日志

### v2.0.0
- 转换为标准插件格式
- 支持通过 ClawHub 生态站分发

---
*此插件由 WanClaw 官方提供*
