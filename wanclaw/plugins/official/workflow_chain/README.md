# 工作流链式编排

## 插件信息

| 属性 | 值 |
|------|-----|
| 插件ID | skill.workflow_chain |
| 类型 | 官方内置技能 |
| 版本 | 2.0.0 |
| 分类 | AI增强 |
| 难度 | 高级 |
| 作者 | WanClaw |

## 功能描述

工作流编排：多个技能链式执行、条件分支、循环处理

## 关键词

工作流 / 编排 / 链式 / ai

## 权限说明

无需特殊权限

## 使用方法

```python
# 通过插件系统调用
result = await plugin_manager.execute("skill.workflow_chain", {"action": "xxx", ...})
```

## 更新日志

### v2.0.0
- 转换为标准插件格式
- 支持通过 ClawHub 生态站分发

---
*此插件由 WanClaw 官方提供*
