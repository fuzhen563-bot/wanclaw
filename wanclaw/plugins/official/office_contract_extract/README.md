# 合同要素智能提取

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.office_contract_extract |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | 办公RPA |
| 难度 | 高级 |
| 作者 | WanClaw |

## 功能说明

自动识别PDF/图片合同中的关键要素：甲乙方、金额、期限、违约条款，高亮标注

## 关键词

合同 / 提取 / NLP / 要素识别 / 办公

## 权限说明

filesystem:read, filesystem:write

## 依赖

pytesseract

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.office_contract_extract", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
