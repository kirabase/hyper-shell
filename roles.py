import re

from settings import config
from brain import get_engine


# a class that is confifured with an ai prompt and can generate text
class HSInvalidRequest(Exception):
    pass


class Role:
    PANEL_TITLE = ""

    ROLE_PROMPT = []

    def __init__(self, refine: bool = False):
        Engine = get_engine(config["main"]["ai_service"])
        self.ai_engine = Engine(self._compile_prompt()[0])
        self.refine = refine
        self._gen_command = None
        self._gen_explanations = []

    def _compile_prompt(self) -> list[str]:
        return [p.format(config=config) for p in self.ROLE_PROMPT]

    def _get_max_tokens(self) -> int:
        return 500

    def _parse(self, explanation: str):
        # Structured mode
        sections = re.split(r"(^|\n)\w+:", explanation)
        sections = [s.strip() for s in sections if s.strip()]

        if len(sections) == 2:
            self._gen_command = sections[0].replace("`", "").strip()
            self._gen_explanations = sections[1].strip()
            return

        # Resilient mode
        match = re.search(r"`([^`]+)`", explanation)
        if match:
            self._gen_command = match.group(1).strip()
            self._gen_explanations = explanation.strip()
            return

        # Skip mode
        raise HSInvalidRequest(explanation)

    def execute(self, prompt: str):
        ai = self.ai_engine
        prompt = prompt.strip()
        if prompt:
            content = ai.execute(prompt, self.refine, self._get_max_tokens())
        else:
            content = ai.get_last_execution()

        self._parse(content)

    def get_command(self) -> str:
        return self._gen_command

    def get_explanations(self) -> list[dict]:
        # check if self._gen_explanations is a string
        if isinstance(self._gen_explanations, str):
            return [(self.PANEL_TITLE, self._gen_explanations)]
        return self._gen_explanations


class CompanionRole(Role):
    PANEL_TITLE = "Explanation"

    ROLE_PROMPT = [
        # System prompt
        """You are a helpful assistant that translates human language descriptions to {config[env][shell_type]} commands on {config[env][os_type]}. Make sure to follow these guidelines:
 - Add explanations in markdown to your commands: start with a generic description of the command, and add details in a bullet list if needed.
 - If a request doesn't make sense, still suggest a command and include guidance on how to fix it in the explanation.
 - Be capable of understanding and responding in multiple languages. Whenever the language of a request changes, change the language of your reply accordingly.

Examples: 
- Input: "List in a readable format all files in a directory"
- Output: "Command: ```ls -lh```\nExplanation: This command lists all files and directories in the current directory."

Input: "Search for 'artificial intelligence' words in all files in the current directory"
Output: "Command: ```grep -r "ciao" .```\nExplanation: grep is a command that searches for a given pattern in a file or directory.\n - r option tells grep to search recursively in all files and directories under the current directory.\n - "artificial intelligence" is the pattern we are searching for.\n - . specifies the current directory as the starting point of the search."

Input: "list all files here in a readable way" 
Output: "Command: ```ls -lh``\nExplanation: This command list all the files and directories in the current directory making the output more readable and informative.\n - ls is the command to list files and directories in the current directory.\n - The option -l (lowercase L) enables long format, which displays additional information such as file permissions, owner, size, and modification date.\n - The option -h (human-readable) makes the file sizes easier to read by displaying them in a format that uses units such as KB, MB, and GB."
"""
    ]

    def _get_max_tokens(self) -> int:
        return 500

    def execute(self, prompt: str):
        prompt = prompt.strip()
        if prompt:
            prompt = "The command: " + prompt
        super().execute(prompt)


class CoachRole(Role):
    PANEL_TITLE = "Advanced Explanation"

    ROLE_PROMPT = [
        # System prompt
        """You are a helpful instructor that translates human language descriptions to {config[env][shell_type]} commands on {config[env][os_type]} and teaches me how to use them in detail. 
about the output:
 - Format everything in markdown, each section starts with a title in h3 (###).
 - Be capable of understanding and responding in multiple languages. Whenever the language of a request changes, change the language of your reply accordingly.

In your reply, make sure to include these sections with corresponding title:
 - Explanation: Add a detailed explanation in markdown how what the command does. If a request doesn't make sense, help me what's wrong with it and how to fix it.
 - Detail: Break down the command into its individual components, such as flags, arguments, and subcommands, and provide explanations for each of them.
 - Common Mistakes: Highlight common mistakes or pitfalls associated with the command, and provide guidance on how to avoid them. This will help users execute the command correctly and prevent potential issues.
 - Examples: Include examples of how the command can be used in different contexts or scenarios. 
""",
        # Follow up prompt
        """Ok! now write these sections:
 - Performance and Security", "Explain any performance or security implications associated with the command, such as potential resource usage or potential vulnerabilities.
 - Alternatives: Include different ways to performe the same task, with different commands or command configuration.
 - FAQs: Include a list of frequently asked questions and answers that address common concerns, misconceptions, or challenges faced by new command line users.
""",
    ]

    def _get_max_tokens(self) -> int:
        return 500

    def _parse(self, explanation: str):
        super()._parse(explanation)

        sections = []
        explanations = [s for s in explanation.split("###") if s.strip()]
        for e in explanations:
            title, content = e.split("\n", 1)
            sections.append((title.strip(), content))

        self._gen_explanations = sections

    def get_explanations(self) -> list[dict]:
        sections = super().get_explanations()
        explanations = ""
        for title, content in sections:
            explanations += f"\n\n{title.upper()}:\n\n{content.strip()}"

        return [(self.PANEL_TITLE, explanations)]
