# 批量文件处理

## 插件信息

| 属性 | 值 |
|------|-----|
| 插件ID | skill.batch_file_processor |
| 类型 | 官方内置技能 |
| 版本 | 2.0.0 |
| 分类 | 办公自动化 |
| 难度 | 中级 |
| 作者 | WanClaw |

## 功能描述

批量文件：批量转换格式、压缩解压、批量重命名、格式统一

## 关键词

批量 / 文件 / 转换 / 压缩 / office

## 权限说明

filesystem:read、filesystem:write

## 使用方法

```python
# 通过插件系统调用
result = await plugin_manager.execute("skill.batch_file_processor", {"action": "xxx", ...})
```

## 更新日志

### v2.0.0
- 转换为标准插件格式
- 支持通过 ClawHub 生态站分发

---
*此插件由 WanClaw 官方提供*
