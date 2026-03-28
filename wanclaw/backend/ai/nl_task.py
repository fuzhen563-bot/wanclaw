import logging
import time
import re
import json

logger = logging.getLogger(__name__)


class NLTaskEngine:
    def __init__(self, config, ollama_client, skill_manager):
        self.ollama_client = ollama_client
        self.skill_manager = skill_manager
        nl_cfg = config.get("ai", {}).get("nl_task", {})
        self.max_steps = nl_cfg.get("max_steps", 10)
        self.default_system = "You are a JSON assistant. Always respond with valid JSON."

    async def parse_command(self, user_input):
        parse_prompt = f"""You are a task planning assistant. 
User request: {user_input}
Available skills with required params:
- HealthChecker: action (check)
- ProcessMonitor: action (list), limit (number)
- FileManager: action (list), path (directory path)
- LogViewer: action (view), log_path (file path), lines (number)
- Backup: action (create), path (directory path)

Respond ONLY with valid JSON:
{{"intent": "brief description", "steps": [{{"skill": "SkillName", "params": {{"param": "value"}}}}]}}
If no skill needed, return empty steps array. Max 3 steps."""
        result = await self.ollama_client.chat(
            messages=[{"role": "user", "content": parse_prompt}],
            system=self.default_system
        )
        try:
            text = result.get("text", "") or result.get("response", "")
            if not text:
                return {"intent": user_input, "steps": [], "error": "Empty AI response"}
            text = text.strip()
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                plan = json.loads(json_match.group())
            else:
                plan = json.loads(text)
            plan["steps"] = plan.get("steps", [])[:self.max_steps]
            return plan
        except Exception as e:
            logger.error(f"Parse error: {e}, result: {result}")
            return {"intent": user_input, "steps": [], "error": str(e)}

    def _get_available_skills(self):
        return "HealthChecker, ProcessMonitor, FileManager"

    async def execute_plan(self, plan, callback=None):
        steps = plan.get("steps", [])
        results = []
        total_start = time.time()
        for idx, step in enumerate(steps):
            step_start = time.time()
            skill_name = step.get("skill")
            params = step.get("params", {})
            try:
                if self.skill_manager and hasattr(self.skill_manager, "execute_skill"):
                    skill_result = await self.skill_manager.execute_skill(skill_name, params)
                    if hasattr(skill_result, 'data'):
                        skill_result = skill_result.data or {}
                else:
                    skill_result = {"error": "Skill manager not available"}
                results.append({
                    "step": idx + 1,
                    "skill": skill_name,
                    "params": params,
                    "success": "error" not in skill_result,
                    "result": skill_result,
                    "duration": round(time.time() - step_start, 3)
                })
            except Exception as e:
                results.append({"step": idx + 1, "skill": skill_name, "success": False, "result": {"error": str(e)}})
        return {"total_steps": len(steps), "completed": sum(1 for r in results if r["success"]), "failed": sum(1 for r in results if not r["success"]), "steps": results, "total_duration": round(time.time() - total_start, 3)}

    async def handle_message(self, user_input):
        plan = await self.parse_command(user_input)
        if "error" in plan and not plan.get("steps"):
            return {"success": False, "plan": plan, "execution": None, "output": f"Failed: {plan.get('error')}"}
        execution = await self.execute_plan(plan)
        return {"success": execution["failed"] == 0, "plan": plan, "execution": execution, "output": f"{execution['completed']}/{execution['total_steps']} steps completed"}
