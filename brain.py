import json
import os

from settings import config, LAST_CONVERSATION_FILE


def save_last_conversation(conversation: list):
    with open(LAST_CONVERSATION_FILE, "w") as f:
        json.dump(conversation, f)


def load_last_conversation():
    if os.path.exists(LAST_CONVERSATION_FILE):
        with open(LAST_CONVERSATION_FILE, "r") as f:
            return json.load(f)
    else:
        return []


class AIEngine:
    NAME = "base"

    SYSTEM_PROMPT = "system"
    USER_PROMPT = "user"
    ASSISTANT_PROMPT = "assistant"

    def __init__(self, system_prompt: str):
        self.engine = None
        self._system_prompt = system_prompt
        self._gen_command = None
        self._gen_explanations = []

    def generate_script(self, prompt: str, refine: bool) -> list:
        """Generate a script for generic AI service to execute."""

        if refine:
            conversation = load_last_conversation()
        else:
            conversation = self._generate_system_prompt(self._system_prompt)

        conversation.append((self.USER_PROMPT, prompt))

        return conversation

    def execute(self, prompt: str, refine: bool, max_token: int) -> str:
        """Call the AI service and return its response."""

        ai_script = self.generate_script(prompt, refine)
        service_script = self._generate_service_script(ai_script)

        response = self._call_service(service_script, max_token)

        ai_script.append((self.ASSISTANT_PROMPT, response))
        save_last_conversation(ai_script)

        return response

    def get_last_execution(self) -> str:
        return load_last_conversation()[-1][1]

    def _generate_system_prompt(self, system_prompt) -> list:
        return [(self.SYSTEM_PROMPT, self._system_prompt)]

    def _generate_service_script(self, script: list) -> object:
        raise NotImplementedError

    def _call_service(self, service_script: object, max_token: int) -> str:
        raise NotImplementedError


class OpenAIEngine(AIEngine):
    NAME = "openai"

    def __init__(self, system_prompt: str):
        super().__init__(system_prompt)
        import openai

        self.engine = openai
        self.engine.api_key = config["openai"]["service_key"]

    def _generate_service_script(self, script: list) -> object:
        service_script = []
        tt = {
            AIEngine.SYSTEM_PROMPT: "system",
            AIEngine.USER_PROMPT: "user",
            AIEngine.ASSISTANT_PROMPT: "assistant",
        }

        for role, content in script:
            service_script.append({"role": tt[role], "content": content})

        return service_script

    def _call_service(self, service_script: object, max_token: int) -> str:
        try:
            response = self.engine.ChatCompletion.create(
                model=config["openai"]["service_model"],
                messages=service_script,
                max_tokens=max_token,
                temperature=0.5,
            )
        except self.engine.error.RateLimitError:
            response_text = "Open AI service overloaded, try in a few minutes"
        else:
            response_text = response.choices[0].message["content"].strip()

        return response_text


class AnthropicEngine(AIEngine):
    NAME = "anthropic"

    def __init__(self, system_prompt: str):
        super().__init__(system_prompt)
        import anthropic

        self.engine = anthropic
        self.client = self.engine.Client(config["anthropic"]["service_key"])

    def _generate_system_prompt(self, system_prompt) -> list:
        conv = super()._generate_system_prompt(system_prompt)
        conv.append((self.ASSISTANT_PROMPT, "ok, I'm ready! Let's start."))
        return conv

    def _generate_service_script(self, script: list) -> list:
        service_script = ""
        tt = {
            AIEngine.SYSTEM_PROMPT: self.engine.HUMAN_PROMPT,
            AIEngine.USER_PROMPT: self.engine.HUMAN_PROMPT,
            AIEngine.ASSISTANT_PROMPT: self.engine.AI_PROMPT,
        }

        for role, content in script:
            service_script += f"{tt[role]} {content}"

        service_script += self.engine.AI_PROMPT
        return service_script

    def _call_service(self, service_script: object, max_token: int) -> str:
        model = config["anthropic"]["service_model"]

        response = self.client.completion(
            prompt=service_script,
            stop_sequences=[self.engine.HUMAN_PROMPT],
            model=config["anthropic"]["service_model"],
            max_tokens_to_sample=max_token,
        )
        if response["exception"]:
            raise Exception(response["exception"])

        response_text = response["completion"]

        return response_text


def get_engine(name: str) -> AIEngine:
    tt = {
        OpenAIEngine.NAME: OpenAIEngine,
        AnthropicEngine.NAME: AnthropicEngine,
    }

    return tt[name]
