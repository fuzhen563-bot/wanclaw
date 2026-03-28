# 网络断连自动重连

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.ops_network_reconnect |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | 系统运维 |
| 难度 | 中级 |
| 作者 | WanClaw |

## 功能说明

检测网络连接状态，断开后自动重连，失败后告警通知

## 关键词

网络 / 重连 / 自愈 / 运维

## 权限说明

无需特殊权限

## 依赖

无外部依赖

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.ops_network_reconnect", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
