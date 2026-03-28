import logging
import re

logger = logging.getLogger(__name__)


class AutoReplyEngine:
    """Smart auto-reply engine with keyword rules and AI fallback."""

    def __init__(self, config, ollama_client):
        self.ollama_client = ollama_client
        ai_cfg = config.get("ai", {}).get("auto_reply", {})
        self.enabled = ai_cfg.get("enabled", True)
        self.use_ai_fallback = ai_cfg.get("use_ai_fallback", True)
        self.default_model = ai_cfg.get("model", None)
        self.rules = []

        rules_data = ai_cfg.get("rules", [])
        for rule in rules_data:
            keywords = rule.get("keywords", [])
            reply = rule.get("reply", "")
            platform = rule.get("platform", None)
            self.rules.append({
                "keywords": [k.lower() for k in keywords],
                "reply": reply,
                "platform": platform
            })

        self.rate_limit_window = ai_cfg.get("rate_limit_window", 60)
        self.rate_limit_max = ai_cfg.get("rate_limit_max", 10)
        self._request_counts = {}

    async def match_rule(self, message_text, platform=None):
        text_lower = message_text.lower()
        for idx, rule in enumerate(self.rules):
            if rule["platform"] is not None and rule["platform"] != platform:
                continue
            for keyword in rule["keywords"]:
                if keyword in text_lower:
                    logger.info(f"Rule {idx} matched for keyword '{keyword}'")
                    return rule["reply"]
        return None

    async def generate_ai_reply(self, message_text, platform=None, context=None):
        if not self.ollama_client:
            return None

        try:
            from wanclaw.backend.agent.memory import get_memory_system
            memory = get_memory_system()
            system_prompt = memory.build_system_prompt(platform=platform)
        except Exception:
            system_prompt = "你是 WanClaw，一个有帮助的 AI 助手。回复使用中文，简洁友好。"

        messages = [{"role": "user", "content": message_text}]
        if context:
            context_text = f"Context: {context}\n\nUser message: {message_text}"
            messages = [{"role": "user", "content": context_text}]

        result = await self.ollama_client.chat(messages, system=system_prompt)
        return result.get("text", "")

    async def process_message(self, message_text, platform=None, context=None):
        if not self.enabled:
            return None

        matched_reply = await self.match_rule(message_text, platform)
        if matched_reply:
            return {
                "type": "rule",
                "reply": matched_reply,
                "matched": True
            }

        if self.use_ai_fallback:
            ai_reply = await self.generate_ai_reply(message_text, platform, context)
            if ai_reply:
                return {
                    "type": "ai",
                    "reply": ai_reply,
                    "matched": False
                }

        return None

    def add_rule(self, keywords, reply, platform=None):
        if isinstance(keywords, str):
            keywords = [keywords]
        self.rules.append({
            "keywords": [k.lower() for k in keywords],
            "reply": reply,
            "platform": platform
        })
        logger.info(f"Added rule: keywords={keywords}, platform={platform}")

    def remove_rule(self, index):
        if 0 <= index < len(self.rules):
            removed = self.rules.pop(index)
            logger.info(f"Removed rule: {removed}")
            return True
        return False

    def get_rules(self):
        return list(self.rules)
