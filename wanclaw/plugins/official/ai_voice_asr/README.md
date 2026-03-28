# 语音识别转文字

## 基本信息

| 属性 | 值 |
|------|-----|
| 插件ID | wanclaw.ai_voice_asr |
| 类型 | 官方内置插件 |
| 版本 | 2.0.0 |
| 分类 | AI增强 |
| 难度 | 中级 |
| 作者 | WanClaw |

## 功能说明

音频/视频文件自动转文字，支持普通话、方言、英语，生成带时间戳的字幕文件

## 关键词

ASR / 语音转文字 / 字幕 / 录音转文字 / AI

## 权限说明

network, filesystem:read

## 依赖

无外部依赖

## 使用方法

```python
result = await plugin_manager.execute("wanclaw.ai_voice_asr", {"action": "xxx"})
```

---
*WanClaw 官方插件 · 2026*
