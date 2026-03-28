import re
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class SoulScan:
    PROMPT_INJECTION_PATTERNS = [
        r"ignore\s+(previous|all)\s+instructions",
        r"disregard\s+.*instruction",
        r"forget\s+.*rules",
        r"you\s+are\s+(now\s+)?developer",
        r"developer\s+mode",
        r"act\s+as\s+(a\s+)?developer",
        r"pretend\s+you\s+are\s+(a\s+)?developer",
        r"new\s+system\s*prompt",
        r"override\s+system\s*prompt",
        r"<system>",
        r"<instruction>",
    ]

    EXFILTRATION_PATTERNS = [
        r"(api_key|apikey)\s*[=:]\s*['\"]?[\w\-]{20,}",
        r"(password|passwd|pwd)\s*[=:]\s*['\"]?[^\s]{8,}",
        r"(secret|token|auth)\s*[=:]\s*['\"]?[\w\-]{20,}",
        r"bearer\s+[\w\-]{20,}",
        r"sk-[\w]{20,}",
    ]

    HARMFUL_PATTERNS = [
        r"sudo\s+rm\s+-rf",
        r"rm\s+-rf\s+/",
        r"curl\s+.*\|\s*sh",
        r"wget\s+.*\|\s*bash",
        r"chmod\s+777\s+/etc",
        r"chmod\s+777\s+/root",
    ]

    SECURITY_RULES = [
        "no_external_data_exfiltration",
        "no_prompt_injection",
        "no_system_prompt_override",
        "no_credential_exposure",
        "no_dangerous_commands",
    ]

    def __init__(self):
        self.issue_count = 0

    def scan_file(self, content: str) -> Dict:
        findings = {
            "prompt_injections": [],
            "exfiltration": [],
            "harmful": [],
            "score": 0,
            "passed": True,
            "details": [],
        }
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            line_stripped = line.strip()
            if not line_stripped or line_stripped.startswith("#"):
                continue
            for pattern in self.PROMPT_INJECTION_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    findings["prompt_injections"].append({
                        "line": i,
                        "content": line_stripped[:100],
                        "pattern": pattern,
                    })
            for pattern in self.EXFILTRATION_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    findings["exfiltration"].append({
                        "line": i,
                        "content": line_stripped[:100],
                        "pattern": pattern,
                    })
            for pattern in self.HARMFUL_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    findings["harmful"].append({
                        "line": i,
                        "content": line_stripped[:100],
                        "pattern": pattern,
                    })
        total = (len(findings["prompt_injections"]) * 3 +
                 len(findings["exfiltration"]) * 5 +
                 len(findings["harmful"]) * 4)
        findings["score"] = max(0, 100 - total)
        findings["passed"] = findings["score"] >= 70 and not findings["exfiltration"]
        if findings["prompt_injections"]:
            findings["details"].append(f"{len(findings['prompt_injections'])} prompt injection patterns found")
        if findings["exfiltration"]:
            findings["details"].append(f"{len(findings['exfiltration'])} credential exposure patterns found")
        if findings["harmful"]:
            findings["details"].append(f"{len(findings['harmful'])} dangerous command patterns found")
        self.issue_count += len(findings["prompt_injections"]) + len(findings["exfiltration"])
        logger.info(f"SoulScan: score={findings['score']}, passed={findings['passed']}")
        return findings

    def scan_soul_file(self, path: str) -> Dict:
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            return self.scan_file(content)
        except FileNotFoundError:
            return {"error": "File not found", "passed": True}
        except Exception as e:
            return {"error": str(e), "passed": False}


class PersonaDriftDetector:
    def __init__(self, baseline_soul: str = ""):
        self.baseline_tokens = self._tokenize(baseline_soul) if baseline_soul else set()
        self.drift_threshold = 0.4

    def _tokenize(self, text: str) -> set:
        words = re.findall(r'\w+', text.lower())
        return set(words)

    def detect_drift(self, current_soul: str) -> Dict:
        if not self.baseline_tokens:
            return {"drifted": False, "score": 0, "reason": "no_baseline"}
        current_tokens = self._tokenize(current_soul)
        if not current_tokens:
            return {"drifted": False, "score": 0, "reason": "empty_soul"}
        overlap = len(self.baseline_tokens & current_tokens)
        union = len(self.baseline_tokens | current_tokens)
        similarity = overlap / union if union > 0 else 0
        drifted = similarity < (1 - self.drift_threshold)
        return {
            "drifted": drifted,
            "score": round(similarity, 3),
            "threshold": 1 - self.drift_threshold,
            "new_tokens": list(current_tokens - self.baseline_tokens)[:10],
            "removed_tokens": list(self.baseline_tokens - current_tokens)[:10],
        }

    def update_baseline(self, soul: str):
        self.baseline_tokens = self._tokenize(soul)
        logger.info("Persona baseline updated")


_soulscan: Optional[SoulScan] = None
_drift_detector: Optional[PersonaDriftDetector] = None


def get_soul_scan() -> SoulScan:
    global _soulscan
    if _soulscan is None:
        _soulscan = SoulScan()
    return _soulscan


def get_drift_detector(baseline: str = "") -> PersonaDriftDetector:
    global _drift_detector
    if _drift_detector is None:
        _drift_detector = PersonaDriftDetector(baseline)
    return _drift_detector
