# 考勤处理

## 插件信息

| 属性 | 值 |
|------|-----|
| 插件ID | skill.attendance_processor |
| 类型 | 官方内置技能 |
| 版本 | 2.0.0 |
| 分类 | 管理运营 |
| 难度 | 中级 |
| 作者 | WanClaw |

## 功能描述

考勤处理：导入打卡记录自动算工时、迟到、加班，生成工资表基础数据

## 关键词

考勤 / 打卡 / 工资 / management

## 权限说明

filesystem:read、database

## 使用方法

```python
# 通过插件系统调用
result = await plugin_manager.execute("skill.attendance_processor", {"action": "xxx", ...})
```

## 更新日志

### v2.0.0
- 转换为标准插件格式
- 支持通过 ClawHub 生态站分发

---
*此插件由 WanClaw 官方提供*
