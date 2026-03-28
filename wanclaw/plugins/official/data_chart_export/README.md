# 可视化图表导出

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.data_chart_export |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | 数据统计 |
| 难度 | 初级 |
| 作者 | WanClaw |

## 功能说明

数据一键生成折线图、柱状图、饼图、漏斗图，支持导出PNG/SVG/Excel

## 关键词

图表 / 可视化 / 导出 / 报表

## 权限说明

filesystem:write

## 依赖

matplotlib

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.data_chart_export", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
