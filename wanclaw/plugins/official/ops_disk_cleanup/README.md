# 磁盘空间自动清理

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.ops_disk_cleanup |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | 系统运维 |
| 难度 | 初级 |
| 作者 | WanClaw |

## 功能说明

磁盘使用率超过阈值时自动清理日志、临时文件、旧的备份，支持白名单保护

## 关键词

磁盘清理 / 日志清理 / 运维 / 存储

## 权限说明

filesystem:write

## 依赖

psutil

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.ops_disk_cleanup", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
