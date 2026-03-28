# 网页数据定时采集

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.office_web_scraper |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | 办公RPA |
| 难度 | 高级 |
| 作者 | WanClaw |

## 功能说明

可视化配置采集规则，定时抓取网页数据，支持登录认证、翻页、增量采集

## 关键词

爬虫 / 采集 / 网页 / 数据 / 办公

## 权限说明

network, filesystem:write

## 依赖

requests, beautifulsoup4

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.office_web_scraper", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
