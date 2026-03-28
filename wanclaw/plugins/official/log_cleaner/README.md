# 日志清理

## 插件信息

| 属性 | 值 |
|------|-----|
| 插件ID | skill.log_cleaner |
| 类型 | 官方内置技能 |
| 版本 | 2.0.0 |
| 分类 | 运维管理 |
| 难度 | 初级 |
| 作者 | WanClaw |

## 功能描述

日志清理：过期日志清理、磁盘空间释放、日志归档

## 关键词

日志 / 清理 / 磁盘 / ops

## 权限说明

filesystem:write

## 使用方法

```python
# 通过插件系统调用
result = await plugin_manager.execute("skill.log_cleaner", {"action": "xxx", ...})
```

## 更新日志

### v2.0.0
- 转换为标准插件格式
- 支持通过 ClawHub 生态站分发

---
*此插件由 WanClaw 官方提供*
