# 表格处理器

## 插件信息

| 属性 | 值 |
|------|-----|
| 插件ID | skill.spreadsheet_handler |
| 类型 | 官方内置技能 |
| 版本 | 2.0.0 |
| 分类 | 办公自动化 |
| 难度 | 高级 |
| 作者 | WanClaw |

## 功能描述

表格处理：数据透视、公式计算、图表生成、条件格式

## 关键词

表格 / 透视 / 公式 / 图表 / office

## 权限说明

filesystem:read

## 使用方法

```python
# 通过插件系统调用
result = await plugin_manager.execute("skill.spreadsheet_handler", {"action": "xxx", ...})
```

## 更新日志

### v2.0.0
- 转换为标准插件格式
- 支持通过 ClawHub 生态站分发

---
*此插件由 WanClaw 官方提供*
