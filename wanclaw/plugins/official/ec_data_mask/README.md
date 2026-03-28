# 订单数据脱敏导出

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.ec_data_mask |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | 电商自动化 |
| 难度 | 高级 |
| 作者 | WanClaw |

## 功能说明

订单数据导出时自动脱敏（手机号、地址、姓名），支持自定义脱敏规则，满足数据安全合规

## 关键词

脱敏 / 数据安全 / 隐私 / 导出 / 电商

## 权限说明

database, filesystem:write

## 依赖

无外部依赖

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.ec_data_mask", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
