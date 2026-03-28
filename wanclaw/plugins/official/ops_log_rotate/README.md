# 日志自动切割归档

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.ops_log_rotate |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | 系统运维 |
| 难度 | 初级 |
| 作者 | WanClaw |

## 功能说明

日志文件按大小或日期自动切割，压缩归档，保留指定天数历史日志

## 关键词

日志切割 / logrotate / 归档 / 运维

## 权限说明

filesystem:read, filesystem:write

## 依赖

无外部依赖

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.ops_log_rotate", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
