# 本地插件离线导入

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.eco_offline_import |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | 插件生态 |
| 难度 | 中级 |
| 作者 | WanClaw |

## 功能说明

支持导入本地ZIP包插件，无需联网，离线环境下也能扩展功能

## 关键词

离线导入 / 本地安装 / 插件生态

## 权限说明

filesystem:read

## 依赖

无外部依赖

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.eco_offline_import", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
