# 数据备份

## 插件信息

| 属性 | 值 |
|------|-----|
| 插件ID | skill.backup |
| 类型 | 官方内置技能 |
| 版本 | 2.0.0 |
| 分类 | 运维管理 |
| 难度 | 中级 |
| 作者 | WanClaw |

## 功能描述

数据备份：文件备份、定时备份、增量备份、压缩存储

## 关键词

备份 / 数据 / ops

## 权限说明

filesystem:read、filesystem:write

## 使用方法

```python
# 通过插件系统调用
result = await plugin_manager.execute("skill.backup", {"action": "xxx", ...})
```

## 更新日志

### v2.0.0
- 转换为标准插件格式
- 支持通过 ClawHub 生态站分发

---
*此插件由 WanClaw 官方提供*
