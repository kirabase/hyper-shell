import os
import sys
from argparse import ArgumentParser

from typing import List, Tuple

from rich.console import Console
from rich.markdown import Markdown
from rich.text import Text

from settings import config
from roles import CompanionRole


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
    agent = CompanionRole()

    # create the prompt
    command_explanation = agent.execute(prompt, args.refine)
    bash_command, explanation = agent.parse(command_explanation)

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
