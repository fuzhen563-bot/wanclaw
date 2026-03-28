# 媒体内容处理

## 插件信息

| 属性 | 值 |
|------|-----|
| 插件ID | skill.media_processor |
| 类型 | 官方内置技能 |
| 版本 | 2.0.0 |
| 分类 | 营销获客 |
| 难度 | 中级 |
| 作者 | WanClaw |

## 功能描述

媒体处理：图片压缩、视频转码、音频提取、格式转换

## 关键词

媒体 / 图片 / 视频 / marketing

## 权限说明

filesystem:read、filesystem:write

## 使用方法

```python
# 通过插件系统调用
result = await plugin_manager.execute("skill.media_processor", {"action": "xxx", ...})
```

## 更新日志

### v2.0.0
- 转换为标准插件格式
- 支持通过 ClawHub 生态站分发

---
*此插件由 WanClaw 官方提供*
