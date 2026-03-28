# 资源超限告警

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.ops_cpu_mem_alert |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | 系统运维 |
| 难度 | 初级 |
| 作者 | WanClaw |

## 功能说明

CPU/内存/磁盘超过阈值时自动告警，支持钉钉/飞书/邮件推送

## 关键词

告警 / 资源监控 / CPU / 内存 / 运维

## 权限说明

无需特殊权限

## 依赖

psutil

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.ops_cpu_mem_alert", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
