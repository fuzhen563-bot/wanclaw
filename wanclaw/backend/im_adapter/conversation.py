import asyncio
import logging
import time
import json
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ConversationContext:
    user_id: str
    platform: str
    chat_id: str
    history: List[Dict] = field(default_factory=list)
    last_active: float = field(default_factory=time.time)
    metadata: Dict = field(default_factory=dict)


class ConversationEngine:
    def __init__(self, gateway=None, ai_client=None, skill_manager=None, hook_manager=None):
        self.gateway = gateway
        self.ai_client = ai_client
        self.skill_manager = skill_manager
        self.hooks = hook_manager
        self.contexts: Dict[str, ConversationContext] = {}
        self.rules: List[Dict] = []
        self.system_prompt = "你是 WanClaw，一个专业的 AI 助手。简洁友好地回复用户，不要编造信息。"
        self.max_history = 20
        self._running = False

    def _get_ctx_key(self, platform: str, chat_id: str, user_id: str) -> str:
        return f"{platform}:{chat_id}:{user_id}"

    def get_context(self, platform: str, chat_id: str, user_id: str) -> ConversationContext:
        key = self._get_ctx_key(platform, chat_id, user_id)
        if key not in self.contexts:
            self.contexts[key] = ConversationContext(
                user_id=user_id,
                platform=platform,
                chat_id=chat_id,
            )
        ctx = self.contexts[key]
        ctx.last_active = time.time()
        return ctx

    def add_history(self, ctx: ConversationContext, role: str, content: str):
        ctx.history.append({"role": role, "content": content, "time": time.time()})
        if len(ctx.history) > self.max_history * 2:
            ctx.history = ctx.history[-self.max_history * 2:]

    def add_rule(self, keywords: List[str], reply: str, platform: str = None):
        self.rules.append({"keywords": keywords, "reply": reply, "platform": platform, "enabled": True})

    def remove_rule(self, index: int):
        if 0 <= index < len(self.rules):
            self.rules.pop(index)

    def toggle_rule(self, index: int, enabled: bool = True):
        if 0 <= index < len(self.rules):
            self.rules[index]["enabled"] = enabled

    def get_rules(self) -> List[Dict]:
        return self.rules

    def _match_rule(self, text: str, platform: str) -> Optional[str]:
        text_lower = text.lower()
        for rule in self.rules:
            if not rule.get("enabled", True):
                continue
            if rule.get("platform") and rule["platform"] != platform:
                continue
            for kw in rule["keywords"]:
                if kw.lower() in text_lower:
                    return rule["reply"]
        return None

    def _check_security(self, text: str) -> tuple:
        blocked = ["忽略之前的指令", "ignore previous", "system prompt", "你是开发者", "假装你是", "act as"]
        for pattern in blocked:
            if pattern.lower() in text.lower():
                return False, f"输入包含阻断模式: {pattern}"
        if len(text) > 4000:
            return False, "输入过长"
        return True, ""

    async def _generate_ai_reply(self, ctx: ConversationContext, user_msg: str) -> str:
        if not self.ai_client:
            return ""
        try:
            messages = [{"role": "system", "content": self.system_prompt}]
            for h in ctx.history[-self.max_history:]:
                messages.append({"role": h["role"], "content": h["content"]})
            messages.append({"role": "user", "content": user_msg})
            result = await self.ai_client.chat(messages)
            return result.get("text", "")
        except Exception as e:
            logger.error(f"AI reply failed: {e}")
            return ""

    async def _try_skill_execution(self, text: str) -> Optional[str]:
        if not self.skill_manager:
            return None
        skill_triggers = {
            "查看进程": ("processmonitor", {"action": "list", "limit": 5}),
            "系统状态": ("processmonitor", {"action": "info"}),
            "备份": ("backup", {"action": "list"}),
            "清理日志": ("logcleaner", {"action": "clean", "path": "/tmp", "days": 7}),
            "查看文件": ("filemanager", {"action": "list", "path": ".", "limit": 5}),
        }
        for trigger, (skill_name, params) in skill_triggers.items():
            if trigger in text:
                try:
                    result = await self.skill_manager.execute_skill(skill_name, params)
                    if result.success:
                        return f"执行结果:\n{json.dumps(result.data, ensure_ascii=False, indent=2)}"
                    return f"执行失败: {result.error or result.message}"
                except Exception as e:
                    return f"技能执行出错: {str(e)}"
        return None

    async def process_message(self, platform: str, chat_id: str, user_id: str, content: str, message_type: str = "text") -> Dict:
        if message_type != "text":
            return {"reply": "", "handled": False, "reason": "non-text message"}

        session_key = f"{platform}:{chat_id}:{user_id}"

        if self.hooks:
            from wanclaw.backend.agent.hooks import DispatchInterceptorContext, MessageHookContext
            disp_ctx = DispatchInterceptorContext(
                session_key=session_key,
                platform=platform,
                channel_id=chat_id,
                user_id=user_id,
                content=content,
            )
            intercept_result = await self.hooks.fire_dispatch_interceptor(disp_ctx)
            if intercept_result.handled:
                return {"reply": intercept_result.reply, "handled": True, "blocked": True, "source": "dispatch_interceptor"}

            msg_ctx = MessageHookContext(
                session_key=session_key,
                platform=platform,
                channel_id=chat_id,
                user_id=user_id,
                content=content,
                message_type=message_type,
            )
            asyncio.create_task(self.hooks.fire("message_received", msg_ctx))

        is_safe, reason = self._check_security(content)
        if not is_safe:
            return {"reply": f"消息被安全模块拦截: {reason}", "handled": True, "blocked": True}

        ctx = self.get_context(platform, chat_id, user_id)
        self.add_history(ctx, "user", content)

        if self.hooks:
            from wanclaw.backend.agent.hooks import AgentHookContext
            agent_ctx = AgentHookContext(
                session_key=session_key,
                platform=platform,
                channel_id=chat_id,
                user_id=user_id,
                user_input=content,
            )
            claiming = await self.hooks.fire_claiming("before_agent_reply", agent_ctx)
            if claiming.handled:
                self.add_history(ctx, "assistant", claiming.reply)
                asyncio.create_task(self.hooks.fire("message_sending", msg_ctx))
                return {"reply": claiming.reply, "handled": True, "source": "before_agent_reply_hook"}

        rule_reply = self._match_rule(content, platform)
        if rule_reply:
            self.add_history(ctx, "assistant", rule_reply)
            if self.hooks:
                asyncio.create_task(self.hooks.fire("response:before_deliver", msg_ctx))
            return {"reply": rule_reply, "handled": True, "source": "rule"}

        skill_reply = await self._try_skill_execution(content)
        if skill_reply:
            self.add_history(ctx, "assistant", skill_reply)
            if self.hooks:
                asyncio.create_task(self.hooks.fire("response:before_deliver", msg_ctx))
            return {"reply": skill_reply, "handled": True, "source": "skill"}

        ai_reply = await self._generate_ai_reply(ctx, content)
        if ai_reply:
            self.add_history(ctx, "assistant", ai_reply)
            if self.hooks:
                asyncio.create_task(self.hooks.fire("response:before_deliver", msg_ctx))
            return {"reply": ai_reply, "handled": True, "source": "ai"}

        fallback = "抱歉，我暂时无法处理您的消息。请稍后再试或联系人工客服。"
        self.add_history(ctx, "assistant", fallback)
        return {"reply": fallback, "handled": True, "source": "fallback"}

    async def handle_incoming(self, message: Dict) -> Dict:
        platform = message.get("platform", "")
        chat_id = message.get("chat_id", message.get("from_user", ""))
        user_id = message.get("user_id", message.get("from_user", ""))
        content = message.get("content", "")
        message_type = message.get("message_type", "text")
        return await self.process_message(platform, chat_id, user_id, content, message_type)

    def get_stats(self) -> Dict:
        return {
            "active_contexts": len(self.contexts),
            "rules_count": len(self.rules),
            "ai_enabled": self.ai_client is not None,
            "skill_enabled": self.skill_manager is not None,
        }


_conversation_engine: Optional[ConversationEngine] = None


def get_conversation_engine(**kwargs) -> ConversationEngine:
    global _conversation_engine
    if _conversation_engine is None:
        defaults = {}
        if "hook_manager" not in kwargs:
            try:
                from wanclaw.backend.agent import get_hook_manager
                defaults["hook_manager"] = get_hook_manager()
            except Exception:
                pass
        defaults.update(kwargs)
        _conversation_engine = ConversationEngine(**defaults)
    return _conversation_engine
