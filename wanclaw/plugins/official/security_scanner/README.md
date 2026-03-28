# 安全扫描

## 插件信息

| 属性 | 值 |
|------|-----|
| 插件ID | skill.security_scanner |
| 类型 | 官方内置技能 |
| 版本 | 2.0.0 |
| 分类 | 安全管理 |
| 难度 | 高级 |
| 作者 | WanClaw |

## 功能描述

安全扫描：代码安全扫描、敏感信息检测、漏洞检测

## 关键词

安全 / 扫描 / 漏洞 / security

## 权限说明

filesystem:read

## 使用方法

```python
# 通过插件系统调用
result = await plugin_manager.execute("skill.security_scanner", {"action": "xxx", ...})
```

## 更新日志

### v2.0.0
- 转换为标准插件格式
- 支持通过 ClawHub 生态站分发

---
*此插件由 WanClaw 官方提供*
