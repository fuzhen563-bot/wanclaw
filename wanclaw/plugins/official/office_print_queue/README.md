# 打印任务自动队列

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.office_print_queue |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | 办公RPA |
| 难度 | 初级 |
| 作者 | WanClaw |

## 功能说明

批量文件加入打印队列，自动分页、自动排版、按打印机分配任务

## 关键词

打印 / 队列 / 自动化 / 办公

## 权限说明

filesystem:read

## 依赖

无外部依赖

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.office_print_queue", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
