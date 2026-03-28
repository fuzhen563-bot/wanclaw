# 插件一键安装升级

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.eco_oneclick_install |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | 插件生态 |
| 难度 | 初级 |
| 作者 | WanClaw |

## 功能说明

从ClawHub生态站一键安装插件，自动处理依赖，支持版本升级和回滚

## 关键词

插件安装 / 升级 / 卸载 / 生态站

## 权限说明

network, filesystem:write

## 依赖

无外部依赖

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.eco_oneclick_install", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
