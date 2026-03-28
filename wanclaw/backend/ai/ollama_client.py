import httpx
import logging
import time
import json
import re
from typing import Optional

logger = logging.getLogger(__name__)

CLOUD_PROVIDERS = {
    "siliconflow": {
        "base_url": "https://api.siliconflow.cn/v1",
        "default_model": "Pro/deepseek-ai/DeepSeek-V3",
        "endpoint": "/chat/completions",
    },
    "baidu": {
        "base_url": "https://aip.baidubce.com",
        "default_model": "ernie-4.0-8k",
        "endpoint": "/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions",
        "auth_type": "baidu_ak_sk",
    },
    "hunyuan": {
        "base_url": "https://hunyuan.cloud.tencent.com",
        "default_model": "hunyuan-pro",
        "endpoint": "/compat/v1/chat/completions",
    },
    "volcengine": {
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "default_model": "doubao-pro-32k",
        "endpoint": "/chat/completions",
    },
    "baichuan": {
        "base_url": "https://api.baichuan-ai.com",
        "default_model": "Baichuan4",
        "endpoint": "/v1/chat/completions",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "endpoint": "/chat/completions",
    },
    "qwen": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen-plus",
        "endpoint": "/chat/completions",
    },
    "zhipu": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "default_model": "glm-4-flash",
        "endpoint": "/chat/completions",
    },
    "moonshot": {
        "base_url": "https://api.moonshot.cn/v1",
        "default_model": "moonshot-v1-8k",
        "endpoint": "/chat/completions",
    },
    "ollama": {
        "base_url": "http://localhost:11434",
        "default_model": "qwen2.5:7b",
        "endpoint": "/api/chat",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "endpoint": "/chat/completions",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
        "endpoint": "/chat/completions",
    },
    "wanyue": {
        "base_url": "https://api.vanyue.cn",
        "default_model": "wanxy-chat",
        "endpoint": "/chat/completions",
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com/v1",
        "default_model": "claude-3-5-haiku-20241022",
        "endpoint": "/messages",
        "auth_header": "x-api-key",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "default_model": "gemini-2.0-flash",
        "endpoint": "/models/{model}:generateContent",
        "auth_param": "key",
    },
    "mistral": {
        "base_url": "https://api.mistral.ai/v1",
        "default_model": "mistral-small-latest",
        "endpoint": "/chat/completions",
    },
    "azure": {
        "base_url": "",
        "default_model": "",
        "endpoint": "/chat/completions",
        "azure": True,
    },
}


class OllamaClient:
    def __init__(self, config):
        ai_cfg = config.get("ai", {}) if "ai" in config else config
        self.provider = ai_cfg.get("engine", "ollama")
        provider_cfg = ai_cfg.get(self.provider, ai_cfg.get("ollama", {}))
        defaults = CLOUD_PROVIDERS.get(self.provider, CLOUD_PROVIDERS["ollama"])
        self.base_url = provider_cfg.get("base_url", defaults["base_url"])
        self.model = provider_cfg.get("model", defaults["default_model"])
        self.timeout = provider_cfg.get("timeout", 120)
        self.temperature = provider_cfg.get("temperature", 0.7)
        self.max_tokens = provider_cfg.get("max_tokens", 2048)
        self.api_key = provider_cfg.get("api_key", "")
        self._client = None

        if self.provider == "azure":
            self.azure_deployment = provider_cfg.get("azure_deployment", "")
            self.azure_api_version = provider_cfg.get("azure_api_version", "2024-02-01")
            if not self.base_url:
                resource = provider_cfg.get("azure_resource", "")
                self.base_url = f"https://{resource}.openai.azure.com/openai/deployments/{self.azure_deployment}"

        if self.provider == "baidu":
            self.baidu_api_key = provider_cfg.get("baidu_api_key", "")
            self.baidu_secret_key = provider_cfg.get("baidu_secret_key", self.api_key)
            self._baidu_access_token: Optional[str] = None
            self._baidu_token_expires_at: float = 0

        if self.provider == "gemini" and self.api_key:
            sep = "&" if "?" in self.base_url else "?"
            self.base_url = f"{self.base_url}{sep}key={self.api_key}"

    async def _get_client(self):
        if self._client is None:
            headers = {}
            if self.provider == "anthropic" and self.api_key:
                headers["x-api-key"] = self.api_key
                headers["anthropic-version"] = "2023-06-01"
                headers["anthropic-dangerous-direct-browser-access"] = "true"
            elif self.provider == "azure" and self.api_key:
                headers["api-key"] = self.api_key
            elif self.api_key and self.provider not in ("ollama", "gemini"):
                headers["Authorization"] = f"Bearer {self.api_key}"

            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers=headers,
            )
        return self._client

    async def _refresh_baidu_token(self):
        if self._baidu_access_token and time.time() < self._baidu_token_expires_at - 60:
            return
        async with httpx.AsyncClient(timeout=30) as c:
            resp = await c.post(
                "https://aip.baidubce.com/oauth/2.0/token",
                params={
                    "grant_type": "client_credentials",
                    "client_id": self.baidu_api_key,
                    "client_secret": self.baidu_secret_key,
                },
            )
            data = resp.json()
            self._baidu_access_token = data["access_token"]
            self._baidu_token_expires_at = time.time() + data.get("expires_in", 2592000)

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def check_health(self):
        try:
            client = await self._get_client()
            if self.provider == "ollama":
                resp = await client.get("/api/tags")
                return resp.status_code == 200
            else:
                resp = await client.get("/models")
                return resp.status_code == 200
        except Exception as e:
            logger.warning(f"LLM health check failed ({self.provider}): {e}")
            return False

    async def list_models(self):
        try:
            client = await self._get_client()
            if self.provider == "ollama":
                resp = await client.get("/api/tags")
                if resp.status_code == 200:
                    return [m["name"] for m in resp.json().get("models", [])]
            else:
                resp = await client.get("/models")
                if resp.status_code == 200:
                    data = resp.json()
                    return [m["id"] for m in data.get("data", [])]
        except Exception as e:
            logger.warning(f"List models failed: {e}")
        return []

    async def generate(self, prompt, system=None, temperature=None, max_tokens=None):
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return await self.chat(messages, temperature=temperature, max_tokens=max_tokens)

    async def chat(self, messages, system=None, temperature=None, max_tokens=None):
        start = time.time()
        client = await self._get_client()
        messages = list(messages)
        temp = temperature if temperature is not None else self.temperature
        tokens = max_tokens if max_tokens is not None else self.max_tokens
        try:
            if self.provider == "baidu":
                await self._refresh_baidu_token()
                payload = {"messages": messages}
                if system:
                    payload["messages"] = [{"role": "user", "content": system}] + payload["messages"]
                resp = await client.post(
                    f"/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions?access_token={self._baidu_access_token}",
                    json=payload,
                )
                data = resp.json()
                if "error_code" in data:
                    raise Exception(f"Baidu API error {data.get('error_code')}: {data.get('error_msg', '')}")
                text = data.get("result", "")
                usage = {}

            elif self.provider == "ollama":
                payload = {
                    "model": self.model,
                    "messages": [{"role": "system", "content": system}] + messages if system else messages,
                    "stream": False,
                    "options": {"temperature": temp, "num_predict": tokens},
                }
                resp = await client.post("/api/chat", json=payload)
                data = resp.json()
                text = data.get("message", {}).get("content", "")
                usage = data.get("usage", {})

            elif self.provider == "anthropic":
                anthropic_messages = [{"role": "user" if m.get("role") == "user" else "assistant", "content": m["content"]} for m in messages]
                payload = {
                    "model": self.model,
                    "max_tokens": tokens,
                    "messages": anthropic_messages,
                }
                if system:
                    payload["system"] = system
                if temp != 0.7:
                    payload["temperature"] = temp
                resp = await client.post("/messages", json=payload)
                data = resp.json()
                text = ""
                if data.get("content") and len(data["content"]) > 0:
                    text = data["content"][0].get("text", "")
                usage = data.get("usage", {})

            elif self.provider == "gemini":
                gemini_contents = []
                for m in messages:
                    role = "user" if m.get("role") in ("user", "system") else "model"
                    gemini_contents.append({"role": role, "parts": [{"text": m["content"]}]})
                payload = {
                    "contents": gemini_contents,
                    "generationConfig": {"temperature": temp, "maxOutputTokens": tokens},
                }
                if system:
                    payload["systemInstruction"] = {"parts": [{"text": system}]}
                endpoint = f"/models/{self.model}:generateContent"
                resp = await client.post(endpoint, json=payload)
                data = resp.json()
                text = ""
                candidates = data.get("candidates", [])
                if candidates and candidates[0].get("content", {}).get("parts"):
                    text = candidates[0]["content"]["parts"][0].get("text", "")
                usage = data.get("usageMetadata", {})

            elif self.provider == "azure":
                payload = {
                    "messages": [{"role": "system", "content": system}] + messages if system else messages,
                    "temperature": temp,
                    "max_tokens": tokens,
                    "stream": False,
                }
                endpoint = f"/chat/completions?api-version={self.azure_api_version}"
                resp = await client.post(endpoint, json=payload)
                data = resp.json()
                choices = data.get("choices", [])
                text = choices[0]["message"]["content"] if choices else ""
                usage = data.get("usage", {})

            else:
                payload = {
                    "model": self.model,
                    "messages": [{"role": "system", "content": system}] + messages if system else messages,
                    "temperature": temp,
                    "max_tokens": tokens,
                    "stream": False,
                }
                defaults = CLOUD_PROVIDERS.get(self.provider, CLOUD_PROVIDERS["openai"])
                resp = await client.post(defaults["endpoint"], json=payload)
                data = resp.json()
                choices = data.get("choices", [])
                text = choices[0]["message"]["content"] if choices else ""
                usage = data.get("usage", {})

            duration = time.time() - start
            return {
                "text": text,
                "tokens_prompt": usage.get("prompt_tokens", 0),
                "tokens_completion": usage.get("completion_tokens", 0),
                "duration": round(duration, 3),
                "model": self.model,
                "provider": self.provider,
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"Chat failed ({self.provider}): {e}")
            return {
                "text": "",
                "error": str(e),
                "status_code": e.response.status_code,
                "duration": round(time.time() - start, 3),
            }
        except Exception as e:
            logger.error(f"Chat failed ({self.provider}): {e}")
            return {
                "text": "",
                "error": str(e),
                "status_code": 0,
                "duration": round(time.time() - start, 3),
            }

    async def stream_chat(self, messages, system=None, temperature=None, max_tokens=None):
        client = await self._get_client()
        messages = list(messages)
        temp = temperature if temperature is not None else self.temperature
        tokens = max_tokens if max_tokens is not None else self.max_tokens

        try:
            if self.provider == "baidu":
                await self._refresh_baidu_token()
                payload = {"messages": messages}
                if system:
                    payload["messages"] = [{"role": "user", "content": system}] + payload["messages"]
                async with client.stream(
                    "POST",
                    f"/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/stream_completions?access_token={self._baidu_access_token}",
                    json=payload,
                ) as resp:
                    async for line in resp.aiter_lines():
                        if line.strip() and line.startswith("data:"):
                            try:
                                data = json.loads(line[5:].strip())
                                chunk = data.get("data", {})
                                text = chunk.get("result", "")
                                if text:
                                    yield {"delta": text, "done": False}
                                if chunk.get("is_end"):
                                    yield {"done": True}
                            except json.JSONDecodeError:
                                continue
                return

            if self.provider == "ollama":
                payload = {
                    "model": self.model,
                    "messages": [{"role": "system", "content": system}] + messages if system else messages,
                    "stream": True,
                    "options": {"temperature": temp, "num_predict": tokens},
                }
                async with client.stream("POST", "/api/chat", json=payload) as resp:
                    async for line in resp.aiter_lines():
                        if line.strip():
                            data = json.loads(line)
                            if "message" in data:
                                content = data["message"].get("content", "")
                                if content:
                                    yield {"delta": content, "done": data.get("done", False)}
                return

            if self.provider == "anthropic":
                anthropic_messages = [{"role": "user" if m.get("role") == "user" else "assistant", "content": m["content"]} for m in messages]
                payload = {
                    "model": self.model,
                    "max_tokens": tokens,
                    "messages": anthropic_messages,
                    "stream": True,
                }
                if system:
                    payload["system"] = system
                headers = dict(client.headers) if client.headers else {}
                headers["Accept"] = "text/event-stream"
                async with client.stream("POST", "/messages", json=payload, headers=headers) as resp:
                    async for line in resp.aiter_lines():
                        if line.strip() and not line.startswith("event:"):
                            try:
                                data = json.loads(line)
                                if data.get("type") == "content_block_delta":
                                    yield {"delta": data.get("delta", {}).get("text", ""), "done": False}
                                elif data.get("type") == "message_stop":
                                    yield {"done": True}
                            except json.JSONDecodeError:
                                continue
                return

            if self.provider == "gemini":
                gemini_contents = []
                for m in messages:
                    role = "user" if m.get("role") in ("user", "system") else "model"
                    gemini_contents.append({"role": role, "parts": [{"text": m["content"]}]})
                payload = {
                    "contents": gemini_contents,
                    "generationConfig": {"temperature": temp, "maxOutputTokens": tokens},
                    "stream": True,
                }
                if system:
                    payload["systemInstruction"] = {"parts": [{"text": system}]}
                endpoint = f"/models/{self.model}:generateContent"
                defaults = CLOUD_PROVIDERS.get(self.provider, CLOUD_PROVIDERS["gemini"])
                async with client.stream("POST", endpoint, json=payload) as resp:
                    async for line in resp.aiter_lines():
                        if line.strip():
                            try:
                                data = json.loads(line)
                                cand = data.get("candidates", [{}])[0]
                                part = cand.get("content", {}).get("parts", [{}])[0]
                                if part.get("text"):
                                    yield {"delta": part["text"], "done": False}
                                usage = data.get("usageMetadata", {})
                                if data.get("done"):
                                    yield {"done": True, "tokens_prompt": usage.get("promptTokenCount", 0), "tokens_completion": usage.get("candidatesTokenCount", 0)}
                            except json.JSONDecodeError:
                                continue
                return

            payload = {
                "model": self.model,
                "messages": [{"role": "system", "content": system}] + messages if system else messages,
                "temperature": temp,
                "max_tokens": tokens,
                "stream": True,
            }
            defaults = CLOUD_PROVIDERS.get(self.provider, CLOUD_PROVIDERS["openai"])
            headers = dict(client.headers) if client.headers else {}
            headers["Accept"] = "text/event-stream"

            endpoint = defaults["endpoint"]
            if self.provider == "azure":
                endpoint = f"/chat/completions?api-version={self.azure_api_version}"

            async with client.stream("POST", endpoint, json=payload, headers=headers) as resp:
                async for line in resp.aiter_lines():
                    if line.strip() and line.startswith("data:"):
                        data_str = line[5:].strip()
                        if data_str == "[DONE]":
                            yield {"done": True}
                            continue
                        try:
                            data = json.loads(data_str)
                            if "choices" in data and data["choices"]:
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield {"delta": content, "done": data.get("done", False)}
                            elif "message" in data:
                                content = data["message"].get("content", "")
                                if content:
                                    yield {"delta": content, "done": data.get("done", False)}
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"Stream chat failed ({self.provider}): {e}")
            yield {"error": str(e), "done": True}

    async def pull_model(self, model_name):
        if self.provider != "ollama":
            return {"success": False, "message": "pull 仅支持 Ollama"}
        try:
            client = await self._get_client()
            resp = await client.post("/api/pull", json={"name": model_name, "stream": False})
            return resp.json()
        except Exception as e:
            return {"success": False, "message": str(e)}
