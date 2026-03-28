# 拼多多售后自动退款

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.ec_refund_auto |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | 电商自动化 |
| 难度 | 高级 |
| 作者 | WanClaw |

## 功能说明

拼多多售后单自动审核，符合条件自动同意退款退货，异常单标记人工处理

## 关键词

拼多多 / 售后 / 退款 / 自动审核 / 电商

## 权限说明

network, database

## 依赖

无外部依赖

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.ec_refund_auto", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
