# 合同要素提取

## 插件信息

| 属性 | 值 |
|------|-----|
| 插件ID | skill.contract_extractor |
| 类型 | 官方内置技能 |
| 版本 | 2.0.0 |
| 分类 | 办公自动化 |
| 难度 | 高级 |
| 作者 | WanClaw |

## 功能描述

合同提取：自动识别合同中的关键要素、甲乙方、金额、期限、违约条款

## 关键词

合同 / 提取 / 要素 / office

## 权限说明

filesystem:read

## 使用方法

```python
# 通过插件系统调用
result = await plugin_manager.execute("skill.contract_extractor", {"action": "xxx", ...})
```

## 更新日志

### v2.0.0
- 转换为标准插件格式
- 支持通过 ClawHub 生态站分发

---
*此插件由 WanClaw 官方提供*
