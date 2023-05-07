import os
import sys
from argparse import ArgumentParser

from typing import List, Tuple

from rich.console import Console
from rich.markdown import Markdown
from rich.text import Text
from rich.padding import Padding
from rich.panel import Panel

from settings import config
from roles import CompanionRole, CoachRole, HSInvalidRequest


def main():
    parser = ArgumentParser(
        description="Generate, refine or execute bash commands from a natural language description.")
    parser.add_argument("prompt", nargs="*",
                        help="A description of the desired bash command.")
    parser.add_argument("-r", "--refine", action="store_true",
                        help="Refine the command using the conversational feature of ChatGPT.")    
    parser.add_argument("-c", "--coach", action="store_true",
                        help="Give a detailed explanation of how to use the command.")
    parser.add_argument("-s", "--short", action="store_true",
                        help="Don't show the explanation.")
    parser.add_argument("-x", "--execute", action="store_true",
                        help="Execute the suggested command.")

    # Get Ready with the arguments
    args = parser.parse_args()
    prompt = " ".join(args.prompt)

    if not prompt and not args.execute:
        sys.exit('Provide a command description, i.e: "List all the folders in this location".')

    console = Console()
    color_mode = "purple" if args.execute else "green"

    # Generate the command
    with console.status(Text(" Generating Command ...", style=color_mode)) as status:
        agent = CompanionRole() if not args.coach else CoachRole()
        command_explanation = agent.execute(prompt, args.refine)

    # Parse the command
    try:
        agent.parse(command_explanation)
    except HSInvalidRequest as e:
        console.print(Text("No suggestions:", style="bold red"), Text(str(e)))
        sys.exit(1)
    
    # OUTPUT: Suggested Commands
    command = agent.get_command()
    formatted_command = Text(f"{command}\n", style=("bold "+ color_mode))
    if args.execute:
        console.print(Text("Executing:"), formatted_command)    
    else:
        console.print("Command:", formatted_command)

    # OUTPUT: Suggested Command Explanation
    sections = agent.get_explanations()
    
    if not args.short:
        for title, content in sections:
            panel = Panel.fit(Markdown(content, style="#666699"), 
                title=title, title_align="left",padding=1)
            console.print(panel)
        console.print("\n")
    
    # Act upon the command
    if args.execute:
        os.system(command)

if __name__ == "__main__":
    main()
