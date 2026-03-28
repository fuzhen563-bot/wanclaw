# 配置文件自动备份

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.ops_config_backup |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | 系统运维 |
| 难度 | 初级 |
| 作者 | WanClaw |

## 功能说明

配置文件修改时自动备份至指定目录，支持版本管理、超量自动清理

## 关键词

配置备份 / 版本管理 / 运维

## 权限说明

filesystem:read, filesystem:write

## 依赖

无外部依赖

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.ops_config_backup", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
