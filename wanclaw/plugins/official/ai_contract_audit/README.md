# 合同智能审查

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.ai_contract_audit |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | AI增强 |
| 难度 | 高级 |
| 作者 | WanClaw |

## 功能说明

上传合同 PDF，自动识别风险条款、缺失条款、不合理条款，生成审查报告

## 关键词

合同审查 / 法务 / 风险识别 / AI

## 权限说明

network, filesystem:read

## 依赖

无外部依赖

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.ai_contract_audit", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
