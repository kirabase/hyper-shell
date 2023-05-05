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
class HSInvalidRequest(Exception):
    pass

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
            explanation = sections[1].strip()
            return bash_command, explanation

        # Resilient mode
        match = re.search(r'`([^`]+)`', command_explanation)
        if match:
            return match.group(1), command_explanation.strip()

        # Skip mode
        raise HSInvalidRequest(command_explanation)

class CompanionRole(Role):

    ROLE_PROMPT = \
'''You are a helpful assistant that translates human language descriptions to {config[env][shell_type]} commands on {config[env][os_type]}. Make sure to follow these guidelines:
 - Add an explanations in markdown to your commands: start with a generic description of the command, and add detalis in a bullet list if needed.
 - If a request doesn't make sense, still suggest a command and include guidance on how to fix it in the explanation.
 - Be capable of understanding and responding in multiple languages. Whenever the language of a request changes, change the language of your reply accordingly.

Examples: 
- Input: "List in a readable format all files in a directory"
- Output: "Command: ```ls -lh```\nExplanation: This command lists all files and directories in the current directory."

Input: "Search for 'artificial intelligence' words in all files in the current directory"
Output: "Command: ```grep -r "ciao" .```\nExplanation: grep is a command that searches for a given pattern in a file or directory.\n - r option tells grep to search recursively in all files and directories under the current directory.\n - "artificial intelligence" is the pattern we are searching for.\n - . specifies the current directory as the starting point of the search."

Input: "list all files here in a readable way" 
Output: "Command: ```ls -lh``\nExplanation: This command list all the files and directories in the current directory making the output more readable and informative.\n - ls is the command to list files and directories in the current directory.\n - The option -l (lowercase L) enables long format, which displays additional information such as file permissions, owner, size, and modification date.\n - The option -h (human-readable) makes the file sizes easier to read by displaying them in a format that uses units such as KB, MB, and GB."

Input: "Elenca in maniera leggibile tutti i file in questa directory"
Output: "Comando: ```ls```\nSpiegazione: Questo comando elenca tutti i file e le directory nella directory corrente."
'''

class CoachRole(Role):

    ROLE_PROMPT = \
'''You are a helpful instructor that translates human language descriptions to {config[env][shell_type]} commands on {config[env][os_type]} and teach me how to use them in detail. 
Make sure to format everything in markdown, and follow these guidelines:
 - Explanation section: Add a detailed explanation in markdown how what the command does. If a request doesn't make sense, help me what's wrong with it and how to fix it.
 - Detail section: break down the command into its individual components, such as flags, arguments, and subcommands, and provide explanations for each of them. 
 - Common Mistakes section: Highlight common mistakes or pitfalls associated with the command, and provide guidance on how to avoid them. This will help users execute the command correctly and prevent potential issues.
 - Examples section: Include examples of how the command can be used in different contexts or scenarios.
 - Performance and Security Considerations: Explain any performance or security implications associated with the command, such as potential resource usage or potential vulnerabilities.
 - Be capable of understanding and responding in multiple languages. Whenever the language of a request changes, change the language of your reply accordingly.
 '''
