"""
WanClaw Voice Engine - TTS/STT support

Provides text-to-speech and speech-to-text capabilities.
Supports OpenAI TTS/Whisper, Azure Speech, and local models.
"""

import logging
import base64
import tempfile
import os
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

TTS_PROVIDERS = {
    "openai": {"endpoint": "/v1/audio/speech", "voices": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]},
    "azure": {"endpoint": "/cognitiveservices/v1", "voices": ["zh-CN-XiaoxiaoNeural", "zh-CN-YunxiNeural", "en-US-JennyNeural"]},
}

STT_PROVIDERS = {
    "openai": {"endpoint": "/v1/audio/transcriptions", "models": ["whisper-1"]},
    "azure": {"endpoint": "/speech/recognition/conversation/cognitiveservices/v1"},
}


class VoiceEngine:
    def __init__(self, config: Dict[str, Any] = None):
        config = config or {}
        self.tts_provider = config.get("tts_provider", "openai")
        self.stt_provider = config.get("stt_provider", "openai")
        self.api_key = config.get("api_key", "")
        self.base_url = config.get("base_url", "https://api.openai.com")
        self.tts_voice = config.get("tts_voice", "nova")
        self.tts_model = config.get("tts_model", "tts-1")
        self.stt_model = config.get("stt_model", "whisper-1")
        self.language = config.get("language", "zh")

    async def text_to_speech(self, text: str, voice: str = None, format: str = "mp3") -> Dict:
        import httpx
        voice = voice or self.tts_voice
        if self.tts_provider == "openai":
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        f"{self.base_url}/v1/audio/speech",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json={"model": self.tts_model, "input": text, "voice": voice, "response_format": format},
                        timeout=30,
                    )
                    if resp.status_code == 200:
                        audio_b64 = base64.b64encode(resp.content).decode()
                        return {"success": True, "audio_base64": audio_b64, "format": format, "voice": voice}
                    return {"success": False, "error": f"TTS API error: {resp.status_code}"}
            except Exception as e:
                logger.error(f"TTS failed: {e}")
                return {"success": False, "error": str(e)}
        return {"success": False, "error": f"Unsupported TTS provider: {self.tts_provider}"}

    async def speech_to_text(self, audio_data: bytes, format: str = "wav") -> Dict:
        import httpx
        if self.stt_provider == "openai":
            try:
                with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as f:
                    f.write(audio_data)
                    tmp_path = f.name
                async with httpx.AsyncClient() as client:
                    with open(tmp_path, "rb") as audio_file:
                        resp = await client.post(
                            f"{self.base_url}/v1/audio/transcriptions",
                            headers={"Authorization": f"Bearer {self.api_key}"},
                            files={"file": (f"audio.{format}", audio_file)},
                            data={"model": self.stt_model, "language": self.language},
                            timeout=60,
                        )
                os.unlink(tmp_path)
                if resp.status_code == 200:
                    data = resp.json()
                    return {"success": True, "text": data.get("text", ""), "language": data.get("language", "")}
                return {"success": False, "error": f"STT API error: {resp.status_code}"}
            except Exception as e:
                logger.error(f"STT failed: {e}")
                return {"success": False, "error": str(e)}
        return {"success": False, "error": f"Unsupported STT provider: {self.stt_provider}"}

    async def speech_to_text_base64(self, audio_b64: str, format: str = "wav") -> Dict:
        audio_data = base64.b64decode(audio_b64)
        return await self.speech_to_text(audio_data, format)

    def get_supported_voices(self) -> list:
        provider_info = TTS_PROVIDERS.get(self.tts_provider, {})
        return provider_info.get("voices", [])


_voice_engine: Optional[VoiceEngine] = None


def get_voice_engine(**kwargs) -> VoiceEngine:
    global _voice_engine
    if _voice_engine is None:
        _voice_engine = VoiceEngine(**kwargs)
    return _voice_engine
