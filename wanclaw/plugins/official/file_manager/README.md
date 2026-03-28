# 文件管理器

## 插件信息

| 属性 | 值 |
|------|-----|
| 插件ID | skill.file_manager |
| 类型 | 官方内置技能 |
| 版本 | 2.0.0 |
| 分类 | 办公自动化 |
| 难度 | 初级 |
| 作者 | WanClaw |

## 功能描述

文件管理：批量重命名、分类整理、搜索查找、权限管理

## 关键词

文件 / 重命名 / 整理 / 搜索 / office

## 权限说明

filesystem:read、filesystem:write

## 使用方法

```python
# 通过插件系统调用
result = await plugin_manager.execute("skill.file_manager", {"action": "xxx", ...})
```

## 更新日志

### v2.0.0
- 转换为标准插件格式
- 支持通过 ClawHub 生态站分发

---
*此插件由 WanClaw 官方提供*
