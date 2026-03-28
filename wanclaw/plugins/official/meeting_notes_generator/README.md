# 会议纪要生成

## 插件信息

| 属性 | 值 |
|------|-----|
| 插件ID | skill.meeting_notes_generator |
| 类型 | 官方内置技能 |
| 版本 | 2.0.0 |
| 分类 | 管理运营 |
| 难度 | 中级 |
| 作者 | WanClaw |

## 功能描述

会议纪要：根据会议内容自动生成结构化会议纪要、待办事项

## 关键词

会议 / 纪要 / management

## 权限说明

无需特殊权限

## 使用方法

```python
# 通过插件系统调用
result = await plugin_manager.execute("skill.meeting_notes_generator", {"action": "xxx", ...})
```

## 更新日志

### v2.0.0
- 转换为标准插件格式
- 支持通过 ClawHub 生态站分发

---
*此插件由 WanClaw 官方提供*
