# 进程监控

## 插件信息

| 属性 | 值 |
|------|-----|
| 插件ID | skill.process_monitor |
| 类型 | 官方内置技能 |
| 版本 | 2.0.0 |
| 分类 | 运维管理 |
| 难度 | 中级 |
| 作者 | WanClaw |

## 功能描述

进程监控：进程列表、CPU/内存占用、异常检测、自动重启

## 关键词

进程 / 监控 / ops

## 权限说明

无需特殊权限

## 使用方法

```python
# 通过插件系统调用
result = await plugin_manager.execute("skill.process_monitor", {"action": "xxx", ...})
```

## 更新日志

### v2.0.0
- 转换为标准插件格式
- 支持通过 ClawHub 生态站分发

---
*此插件由 WanClaw 官方提供*
