import json
import os
import re
import sys
from argparse import ArgumentParser
from configparser import ConfigParser
from typing import List, Tuple

import openai
from rich.console import Console
from rich.markdown import Markdown
from rich.text import Text

# Set up your OpenAI API key
def get_openai_api_key()-> str:
    # Try to read the API key from the configuration file
    config_file = "config.ini"
    if os.path.exists(config_file):
        config = ConfigParser()
        config.read(config_file)

        if config.has_option("openai", "api_key"):
            return config.get("openai", "api_key")

    # If not found in the configuration file, try to read it from the environment variable
    if "OPENAI_API_KEY" in os.environ:
        return os.environ["OPENAI_API_KEY"]

    # If not found in the environment variable, ask the user for the API key
    api_key = input("Please enter your OpenAI API key: ")
    os.environ["OPENAI_API_KEY"] = api_key

    return api_key

# Set up your OpenAI API key
openai.api_key = "" or get_openai_api_key()

# File to store the last command and explanation


BASH_ROLE = '''You are a helpful assistant that translates human language descriptions to bash commands. If a request doesn't make sense, you still suggest a reasonable one. Your reply is formatted in markdown and structured this way:         
[Example 1]
Command: 
```ls -lh```

Explanation:
This command will output a list of all the directories in the current directory, along with
their sizes and other details. 

The arguments used work this way:
- The -l option tells ls to use the long listing format, which includes details such as file 
permissions, ownership, and size. 
- The -h option tells ls to display file sizes in a human-readable format, such as "10K" for 10 kilobytes, instead of in bytes.

[Example 2]
Command: 
```ls -d */```

Explanation: 
The command lists all the directories in the current working directory.
The arguments used work this way:
- ls is the command to list directory contents.                                                                                  
- d option is used to list only directories.                                                                                    
- */ is a pattern that matches all directories in the current directory. The * is a wildcard that matches any character and the / specifies that only directories should be matched. 
'''

LAST_CONVERSATION_FILE = os.path.join(os.path.expanduser("~"), ".dodo_last_conversation.json")

def save_last_conversation(conversation):
    with open(LAST_CONVERSATION_FILE, "w") as f:
        json.dump(conversation, f)

def load_last_conversation():
    if os.path.exists(LAST_CONVERSATION_FILE):
        with open(LAST_CONVERSATION_FILE, "r") as f:
            return json.load(f)
    else:
        return []

def get_generation_script(role: str, prompt: str, continue_mode: bool=False):
    conversation = [] 

    if continue_mode:
        conversation = load_last_conversation()
    else:
        conversation = [ {"role": "system", "content": role} ]

    conversation.append({"role": "user", "content": prompt})  

    return conversation  

def execute_script(script: List[dict]) -> str:
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=script,
        max_tokens=300,
        temperature=0.5,
    )

    response_text = response.choices[0].message['content'].strip()
    script.append({"role": "assistant", "content": response_text})
    return response_text 


def parse_explanation(command_explanation) -> Tuple[str, str]:
    ok_card = "Command:"
    if ok_card in command_explanation:
        bash_command, explanation = command_explanation.split(ok_card,1)[1].split("Explanation:",1)
        bash_command = bash_command.replace("```","").strip()
    else:
        bash_command = None
        explanation = command_explanation

    return bash_command, explanation.strip()

def main():
    parser = ArgumentParser(description="Generate, refine or execute bash commands from a natural language description.")
    parser.add_argument("prompt", nargs="*", help="A description of the desired bash command.")
    parser.add_argument("-s", "--short", action="store_true", help="Don't show the explanation.")
    parser.add_argument("-e", "--execute", action="store_true", help="Execute the suggested command.")
    parser.add_argument("-c", "--continue", dest="refine", action="store_true", help="Refine the command using the conversational feature of ChatGPT.")

    args = parser.parse_args()
    prompt = " ".join(args.prompt)
    
    if not prompt and not args.execute:
        sys.exit('Provide a command description, i.e: "List all the folders in this location".')

    # Generate the command
    if prompt:
        script = get_generation_script(BASH_ROLE, prompt, args.refine)
        command_explanation = execute_script(script)
        save_last_conversation(script)
    else:
        command_explanation = load_last_conversation()[-1]["content"]
    bash_command, explanation = parse_explanation(command_explanation)

    # Highlight the command
    console = Console()
    if bash_command:
        command_text = Text(f"{bash_command}", style="bold green")
    else:
        command_text = Text(f"Unknown Command", style="bold red")
    console.print(command_text)
    if not args.short:
        console.print(Markdown(explanation))
    
    # Act upon the command
    if args.execute:
        os.system(bash_command)

if __name__ == "__main__":
    main()
