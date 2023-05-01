import json
import os
import re
import sys
from argparse import ArgumentParser

from typing import List, Tuple

import openai
from rich.console import Console
from rich.markdown import Markdown
from rich.text import Text

from settings import config, open_ai_key

# Set up your OpenAI API key
openai.api_key = open_ai_key

COMPANION_ROLE = f'''You are a helpful assistant that translates human language descriptions to {config['env']['shell_type']} commands on {config['env']['os_type']}. Make sure to follow these guidelines:
- Long explanations are presented in a bullet points format.
- If a request doesn't make sense, still suggest a command and include guidance on how to fix it in the explanation.
- Be capable of understanding and responding in multiple languages. Whenever the language of a request changes, change the language of your reply accordingly.

Examples:
- Input: "List in a readable format all files in a directory"
  Output: "Command: ```ls -lh```\nExplanation: This command lists all files and directories in the current directory."

- Input: "Elenca in maniera leggibile tutti i file in una directory"
  Output: "Comando: ```ls```\nSpiegazione: Questo comando elenca tutti i file e le directory nella directory corrente."
'''

LAST_CONVERSATION_FILE = os.path.join(
    os.path.expanduser("~"), ".dodo_last_conversation.json")


def save_last_conversation(conversation):
    with open(LAST_CONVERSATION_FILE, "w") as f:
        json.dump(conversation, f)


def load_last_conversation():
    if os.path.exists(LAST_CONVERSATION_FILE):
        with open(LAST_CONVERSATION_FILE, "r") as f:
            return json.load(f)
    else:
        return []


def get_generation_script(role: str, prompt: str, continue_mode: bool = False):
    conversation = []

    if continue_mode:
        conversation = load_last_conversation()
    else:
        conversation = [{"role": "system", "content": role}]

    conversation.append({"role": "user", "content": prompt})

    return conversation


def execute_script(script: List[dict]) -> str:
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


def parse_explanation(command_explanation) -> Tuple[str, str]:
    # Structured explanation
    sections = re.split(r'(^|\n)\w+:', command_explanation)
    sections = [s.strip() for s in sections if s.strip()]
    if len(sections) == 2:
        bash_command = sections[0].replace('`', "").strip()
        explanation = sections[1]
        return bash_command, explanation

    # Unstructured explanation
    match = re.search(r'`([^`]+)`', command_explanation)
    if match:
        return match.group(1), command_explanation

    exit('AI is not the solution this time!')


def main():
    parser = ArgumentParser(
        description="Generate, refine or execute bash commands from a natural language description.")
    parser.add_argument("prompt", nargs="*",
                        help="A description of the desired bash command.")
    parser.add_argument("-s", "--short", action="store_true",
                        help="Don't show the explanation.")
    parser.add_argument("-e", "--execute", action="store_true",
                        help="Execute the suggested command.")
    parser.add_argument("-c", "--continue", dest="refine", action="store_true",
                        help="Refine the command using the conversational feature of ChatGPT.")

    args = parser.parse_args()
    prompt = " ".join(args.prompt)

    if not prompt and not args.execute:
        sys.exit(
            'Provide a command description, i.e: "List all the folders in this location".')

    # Generate the command
    if prompt:
        script = get_generation_script(COMPANION_ROLE, prompt, args.refine)
        command_explanation = execute_script(script)
        save_last_conversation(script)
    else:
        command_explanation = load_last_conversation()[-1]["content"]
    bash_command, explanation = parse_explanation(command_explanation)

    # Highlight the command
    console = Console()
    if bash_command:
        command_text = Text(f"{bash_command}",
                            style="purple" if args.execute else "green")
    else:
        command_text = Text(f"Unknown Command", style="red")
    console.print(command_text)

    if not args.short:
        console.print(Markdown(explanation))

    # Act upon the command
    if args.execute:
        os.system(bash_command)


if __name__ == "__main__":
    main()
