import json
import os
import re
from typing import List, Tuple

import openai

from settings import config, OPEN_AI_KEY, LAST_CONVERSATION_FILE


def save_last_conversation(conversation: List):
    with open(LAST_CONVERSATION_FILE, "w") as f:
        json.dump(conversation, f)


def load_last_conversation():
    if os.path.exists(LAST_CONVERSATION_FILE):
        with open(LAST_CONVERSATION_FILE, "r") as f:
            return json.load(f)
    else:
        return []


# Set up your OpenAI API key
openai.api_key = OPEN_AI_KEY


# a class that is confifured with an ai prompt and can generate text

class Role:

    ROLE_PROMPT = ''

    def __init__(self):
        self.system_prompt = self._compile_prompt()

    def _compile_prompt(self) -> str:
        return self.ROLE_PROMPT.format(config=config)

    def _get_generation_script(self, prompt: str, continue_mode: bool = False) -> List:
        conversation = []

        if continue_mode:
            conversation = load_last_conversation()
        else:
            conversation = [{"role": "system", "content": self.system_prompt}]

        conversation.append({"role": "user", "content": prompt})

        return conversation

    def _execute_script(self, script: List, refine: bool = False) -> str:
        try:
            response = openai.ChatCompletion.create(
                model=config['openai']['service_model'],
                messages=script,
                max_tokens=500,
                temperature=0.5,
            )
        except openai.error.RateLimitError:
            response_text = "Open AI service overloaded, try in a few minutes"
        else:
            response_text = response.choices[0].message['content'].strip()
        script.append({"role": "assistant", "content": response_text})

        return response_text

    def execute(self, prompt: str, refine: bool = False) -> str:
        if prompt:
            script = self._get_generation_script(prompt, refine)
            content = self._execute_script(script, refine)
            save_last_conversation(script)
        else:
            content = load_last_conversation()[-1]["content"]
        return content

    def parse(self, command_explanation) -> Tuple[str, str]:

        # Structured mode
        sections = re.split(r'(^|\n)\w+:', command_explanation)
        sections = [s.strip() for s in sections if s.strip()]

        if len(sections) == 2:
            bash_command = sections[0].replace('`', "").strip()
            explanation = sections[1]
            return bash_command, explanation

        # Resilient mode
        match = re.search(r'`([^`]+)`', command_explanation)
        if match:
            return match.group(1), command_explanation

        # Skip mode
        exit('AI is not the solution this time!')


class CompanionRole(Role):

    ROLE_PROMPT = '''You are a helpful assistant that translates human language descriptions to {config[env][shell_type]} commands on {config[env][os_type]}. Make sure to follow these guidelines:
    - Long explanations are presented in a bullet points format.
    - If a request doesn't make sense, still suggest a command and include guidance on how to fix it in the explanation.
    - Be capable of understanding and responding in multiple languages. Whenever the language of a request changes, change the language of your reply accordingly.

    Examples:
    - Input: "List in a readable format all files in a directory"
    Output: "Command: ```ls -lh```\nExplanation: This command lists all files and directories in the current directory."

    - Input: "Elenca in maniera leggibile tutti i file in una directory"
    Output: "Comando: ```ls```\nSpiegazione: Questo comando elenca tutti i file e le directory nella directory corrente."
    '''
