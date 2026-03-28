# 邮件自动分类归档

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.office_email_auto_classify |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | 办公RPA |
| 难度 | 中级 |
| 作者 | WanClaw |

## 功能说明

根据发件人、主题、关键词自动将邮件分类到指定文件夹，支持规则组合

## 关键词

邮件 / 分类 / 归档 / 自动化 / 办公

## 权限说明

email

## 依赖

无外部依赖

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.office_email_auto_classify", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
