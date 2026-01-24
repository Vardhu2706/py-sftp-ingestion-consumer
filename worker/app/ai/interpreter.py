import json
from app.ai.client import AIClient
from app.ai.prompts import SYSTEM_PROMPT, USER_TEMPLATE

class AIInterpreter:
    def __init__(self):
        self.client = AIClient()

    def interpret(self, text: str) -> dict:
        response = self.client.complete(
            SYSTEM_PROMPT,
            USER_TEMPLATE.format(document=text)
        )

        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"AI returned invalid JSON: {e}")
