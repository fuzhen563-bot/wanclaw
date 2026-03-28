# 条件分支工作流

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.wf_condition_branch |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | 工作流 |
| 难度 | 中级 |
| 作者 | WanClaw |

## 功能说明

工作流中支持IF/ELSE条件判断，根据数据动态选择执行分支

## 关键词

工作流 / 条件分支 / IF / 判断

## 权限说明

database

## 依赖

无外部依赖

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.wf_condition_branch", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
