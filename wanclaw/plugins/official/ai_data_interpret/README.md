# 数据智能解读

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.ai_data_interpret |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | AI增强 |
| 难度 | 中级 |
| 作者 | WanClaw |

## 功能说明

上传 Excel/CSV 数据文件，AI 自动分析数据特征，发现规律，生成文字解读报告

## 关键词

数据分析 / 数据解读 / Excel / AI

## 权限说明

network, filesystem:read

## 依赖

无外部依赖

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.ai_data_interpret", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
