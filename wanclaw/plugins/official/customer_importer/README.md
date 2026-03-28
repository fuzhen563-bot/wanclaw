# 客户数据导入

## 插件信息

| 属性 | 值 |
|------|-----|
| 插件ID | skill.customer_importer |
| 类型 | 官方内置技能 |
| 版本 | 2.0.0 |
| 分类 | 营销获客 |
| 难度 | 中级 |
| 作者 | WanClaw |

## 功能描述

客户导入：批量导入客户数据、重复检测、数据验证

## 关键词

客户 / 导入 / 数据 / marketing

## 权限说明

filesystem:read、database

## 使用方法

```python
# 通过插件系统调用
result = await plugin_manager.execute("skill.customer_importer", {"action": "xxx", ...})
```

## 更新日志

### v2.0.0
- 转换为标准插件格式
- 支持通过 ClawHub 生态站分发

---
*此插件由 WanClaw 官方提供*
