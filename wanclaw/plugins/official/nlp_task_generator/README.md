# NLP任务生成器

## 插件信息

| 属性 | 值 |
|------|-----|
| 插件ID | skill.nlp_task_generator |
| 类型 | 官方内置技能 |
| 版本 | 2.0.0 |
| 分类 | AI增强 |
| 难度 | 高级 |
| 作者 | WanClaw |

## 功能描述

NLP任务：文本分类、情感分析、实体识别、关键词提取

## 关键词

nlp / 自然语言 / 分类 / ai

## 权限说明

无需特殊权限

## 使用方法

```python
# 通过插件系统调用
result = await plugin_manager.execute("skill.nlp_task_generator", {"action": "xxx", ...})
```

## 更新日志

### v2.0.0
- 转换为标准插件格式
- 支持通过 ClawHub 生态站分发

---
*此插件由 WanClaw 官方提供*
