# 订单同步

## 插件信息

| 属性 | 值 |
|------|-----|
| 插件ID | skill.order_sync |
| 类型 | 官方内置技能 |
| 版本 | 2.0.0 |
| 分类 | 管理运营 |
| 难度 | 高级 |
| 作者 | WanClaw |

## 功能描述

订单同步：多平台订单拉取、状态同步、异常告警

## 关键词

订单 / 同步 / management

## 权限说明

network、database

## 使用方法

```python
# 通过插件系统调用
result = await plugin_manager.execute("skill.order_sync", {"action": "xxx", ...})
```

## 更新日志

### v2.0.0
- 转换为标准插件格式
- 支持通过 ClawHub 生态站分发

---
*此插件由 WanClaw 官方提供*
