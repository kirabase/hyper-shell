import os
import sys
from enum import Enum
from argparse import ArgumentParser

from typing import List, Tuple

from rich.console import Console
from rich.markdown import Markdown
from rich.text import Text
from rich.padding import Padding
from rich.panel import Panel

from settings import config
from roles import CompanionRole, CoachRole, HSInvalidRequest


class Mode(Enum):
    COPILOT = 1
    EXECUTE = 2
    COACH = 3


class ConsoleApp:
    def __init__(self, mode: Mode):
        self.console = Console()
        self.mode = mode

    def get_color_mode(self):
        if self.mode == Mode.EXECUTE:
            return "purple"
        else:
            return "green"

    def wait(self, action: callable):
        color_mode = self.get_color_mode()
        with self.console.status(
            Text(" Generating Command ...", style=color_mode)
        ) as status:
            try:
                action()
            except HSInvalidRequest as e:
                self.render_unsupportive(e)
                sys.exit(1)
            except KeyboardInterrupt:
                self.render_unsupportive("Interrupted by user.")
                sys.exit(1)

    def render_command(self, command: str):
        if self.mode == Mode.EXECUTE:
            label = "Executing"
        else:
            label = "Command"

        color = self.get_color_mode()

        fCommand = Text(f"{command}", style=f"bold {color}")
        self.console.print(f"{label}:", fCommand, "\n")

    def render_explanation(self, sections: List[Tuple[str, str]]):
        for title, content in sections:
            panel = Panel.fit(
                Markdown(content, style="#666699"),
                title=title,
                title_align="left",
                padding=1,
            )
            self.console.print(panel)

    def render_unsupportive(self, error):
        self.console.print(Text("No suggestions:", style="bold red"), Text(str(error)))


def main():
    parser = ArgumentParser(
        description="Generate, refine or execute bash commands from a natural language description."
    )
    parser.add_argument(
        "prompt", nargs="*", help="A description of the desired bash command."
    )
    parser.add_argument(
        "-s", "--silent", action="store_true", help="Don't show the explanation."
    )
    parser.add_argument(
        "-r",
        "--refine",
        action="store_true",
        help="Refine the command using the conversational feature of ChatGPT.",
    )
    parser.add_argument(
        "-c",
        "--coach",
        action="store_true",
        help="Give a detailed explanation of how to use the command.",
    )
    parser.add_argument(
        "-x", "--execute", action="store_true", help="Execute the suggested command."
    )
    parser.add_argument(
        "-m",
        "--model",
        action="store",
        help="Force the use of a different AI model for the command.",
    )

    # Get Ready with the arguments
    args = parser.parse_args()
    if args.model:
        config["main"]["ai_service"] = args.model

    if args.coach:
        mode = Mode.COACH
        agent = CoachRole(args.refine)
    elif args.execute:
        mode = Mode.EXECUTE
        agent = CompanionRole(args.refine)
    else:
        mode = Mode.COPILOT
        agent = CompanionRole(args.refine)

    prompt = " ".join(args.prompt)
    if not prompt and mode == Mode.COPILOT:
        sys.exit(
            'Provide a command description, i.e: "List all the folders in this location".'
        )

    # Generate the command
    console = ConsoleApp(mode)
    console.wait(lambda: agent.execute(prompt))

    # Render the command and the explanation
    command = agent.get_command()
    console.render_command(command)

    if not args.silent:
        explanations = agent.get_explanations()
        console.render_explanation(explanations)

        if len(agent.ROLE_PROMPT) > 1:
            agent.refine = True
            follow_prompt = agent.ROLE_PROMPT[1]
            console.wait(lambda: agent.execute(follow_prompt))
            explanations = agent.get_explanations()
            console.render_explanation(explanations)

    # Act upon the command
    if args.execute:
        os.system(command)


if __name__ == "__main__":
    main()
