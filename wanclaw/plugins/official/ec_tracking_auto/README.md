# 物流单号自动识别

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.ec_tracking_auto |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | 电商自动化 |
| 难度 | 中级 |
| 作者 | WanClaw |

## 功能说明

发货时自动识别快递单号格式、回填物流信息、异常单号自动提醒

## 关键词

物流 / 快递 / 单号识别 / 回填 / 电商

## 权限说明

network, database

## 依赖

无外部依赖

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.ec_tracking_auto", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
