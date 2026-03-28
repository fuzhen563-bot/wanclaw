# 服务崩溃自动重启

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.ops_auto_restart |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | 系统运维 |
| 难度 | 中级 |
| 作者 | WanClaw |

## 功能说明

监控服务健康状态，进程崩溃、网络断连时自动重启，支持邮件/钉钉通知

## 关键词

重启 / 自愈 / 守护进程 / 运维

## 权限说明

无需特殊权限

## 依赖

psutil

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.ops_auto_restart", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
