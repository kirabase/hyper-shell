import os
import sys
from argparse import ArgumentParser

from typing import List, Tuple

from rich.console import Console
from rich.markdown import Markdown
from rich.text import Text
from rich.padding import Padding

from settings import config
from roles import CompanionRole, HSInvalidRequest


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
    parser.add_argument("-d", "--debug", action="store_true",
                        help="Run hyper-shell in debug mode.")

    # Get Ready with the arguments
    args = parser.parse_args()
    prompt = " ".join(args.prompt)
    config['debug'] = args.debug

    if not prompt and not args.execute:
        sys.exit(
            'Provide a command description, i.e: "List all the folders in this location".')

    # Command line interface
    console = Console()
    color_mode = "purple" if args.execute else "green"

    # > Generate the command
    with console.status(Text(" Generating Command ...", style=color_mode)) as status:
        agent = CompanionRole()
        command_explanation = agent.execute(prompt, args.refine)

    try:
        command, explanation = agent.parse(command_explanation)
    except HSInvalidRequest as e:
        console.print(Text("No suggestions:", style="bold red"), Text(str(e)))
        sys.exit(1)
    
    # > Print formatted results
    formatted_command = Text(command, style=("bold "+ color_mode))
    if args.execute:
        console.print(Text("Executing:"), formatted_command)    
    else:
        console.print("Command:", formatted_command)

    if not args.short:
        console.print(Padding(Markdown(explanation), 1, expand=False, style="#666699"))

    # Act upon the command
    if args.execute:
        os.system(command)

if __name__ == "__main__":
    main()
