import json
import aiohttp
from typing import Optional, List
from shared_types import Command


class AIClient:
    def __init__(self, url: str, model: str, system_prompt: str):
        self.url = url
        self.model = model
        self.system_prompt = system_prompt

    async def query(self, text: str, screenshot_b64: str) -> Optional[List[Command]]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": text},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{screenshot_b64}"}
                        }
                    ]
                }
            ],
            "temperature": 0.1,
            "max_tokens": 512
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.url, json=payload) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    content = data["choices"][0]["message"]["content"]
                    return self._parse_response(content)
        except Exception:
            return None

    def _parse_response(self, content: str) -> Optional[List[Command]]:
        try:
            json_start = content.index("{")
            json_end = content.rindex("}") + 1
            clean = content[json_start:json_end]
            parsed = json.loads(clean)
        except (ValueError, json.JSONDecodeError):
            return None

        commands = []
        if "sequence" in parsed:
            for step in parsed["sequence"]:
                action = step.get("action", "HOVER")
                params = step.get("params", {})
                if "duration" in params:
                    params["duration"] = float(params["duration"])
                if "angle" in params:
                    params["angle"] = float(params["angle"])
                commands.append(Command(action=action, params=params, source="ai"))
        elif "action" in parsed:
            action = parsed["action"]
            params = parsed.get("params", {})
            if "duration" in params:
                params["duration"] = float(params["duration"])
            if "angle" in params:
                params["angle"] = float(params["angle"])
            commands.append(Command(action=action, params=params, source="ai"))
        else:
            return None

        return commands if commands else None