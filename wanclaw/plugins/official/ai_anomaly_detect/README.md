# 异常数据检测

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.ai_anomaly_detect |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | AI增强 |
| 难度 | 高级 |
| 作者 | WanClaw |

## 功能说明

自动识别数据中的异常值和异常事件，标注异常点并给出可能原因分析

## 关键词

异常检测 / 离群点 / 数据质量 / AI

## 权限说明

network, database

## 依赖

无外部依赖

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.ai_anomaly_detect", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
