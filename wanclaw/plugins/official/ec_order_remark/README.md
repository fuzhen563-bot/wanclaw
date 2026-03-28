# 淘宝订单自动备注

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.ec_order_remark |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | 电商自动化 |
| 难度 | 中级 |
| 作者 | WanClaw |

## 功能说明

淘宝/天猫订单自动识别买家留言并打标备注，支持关键词匹配、颜色尺码提取、发货时间承诺

## 关键词

淘宝 / 天猫 / 订单备注 / 打标 / 电商

## 权限说明

network, database

## 依赖

无外部依赖

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.ec_order_remark", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
