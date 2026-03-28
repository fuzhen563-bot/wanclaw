# 微信群监控

## 插件信息

| 属性 | 值 |
|------|-----|
| 插件ID | skill.wechat_group_monitor |
| 类型 | 官方内置技能 |
| 版本 | 2.0.0 |
| 分类 | 营销获客 |
| 难度 | 中级 |
| 作者 | WanClaw |

## 功能描述

微信群监控：关键词提醒、新消息通知、群活跃度统计

## 关键词

微信 / 群 / 监控 / marketing

## 权限说明

network

## 使用方法

```python
# 通过插件系统调用
result = await plugin_manager.execute("skill.wechat_group_monitor", {"action": "xxx", ...})
```

## 更新日志

### v2.0.0
- 转换为标准插件格式
- 支持通过 ClawHub 生态站分发

---
*此插件由 WanClaw 官方提供*
