# 邮件自动化

## 插件信息

| 属性 | 值 |
|------|-----|
| 插件ID | skill.email_automation |
| 类型 | 官方内置技能 |
| 版本 | 2.0.0 |
| 分类 | 办公自动化 |
| 难度 | 中级 |
| 作者 | WanClaw |

## 功能描述

邮件自动化：定时发送、批量群发、邮件模板、跟踪提醒

## 关键词

邮件 / 自动化 / 群发 / 模板 / office

## 权限说明

email

## 使用方法

```python
# 通过插件系统调用
result = await plugin_manager.execute("skill.email_automation", {"action": "xxx", ...})
```

## 更新日志

### v2.0.0
- 转换为标准插件格式
- 支持通过 ClawHub 生态站分发

---
*此插件由 WanClaw 官方提供*
