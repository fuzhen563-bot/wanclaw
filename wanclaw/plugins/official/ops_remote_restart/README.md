# 远程服务一键重启

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.ops_remote_restart |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | 系统运维 |
| 难度 | 高级 |
| 作者 | WanClaw |

## 功能说明

通过API或管理后台远程重启指定服务，支持服务分组、批量操作

## 关键词

远程重启 / 服务管理 / 运维

## 权限说明

无需特殊权限

## 依赖

psutil

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.ops_remote_restart", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
