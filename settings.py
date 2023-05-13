import sys
import os
import platform

from configparser import ConfigParser

# Install the distro package with `pip install distro` if you're using Linux
if sys.platform.startswith("linux"):
    import distro


def load_config() -> dict:
    config = ConfigParser()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.ini")
    config.read(config_path)

    config_dict = {
        "main": {
            "ai_service": config.get("main", "ai_service", fallback="openai"),
            "ai_personality": config.get("main", "ai_personality", fallback="none"),
        },
    }

    for service in ["openai"]:
        config_dict[service] = {
            "service_key": config.get(service, "service_key", fallback=None),
            "service_model": config.get(
                service, "service_model", fallback="gpt-3.5-turbo"
            ),
        }

    return config_dict


def get_environment_info():
    shell_type = "Unknown"
    if sys.platform == "win32":
        if "powershell" in sys.executable.lower():
            shell_type = "PowerShell"
        else:
            shell_type = "CMD"
    elif sys.platform.startswith("linux") or sys.platform == "darwin":
        shell = os.environ.get("SHELL", "Unknown")
        if "zsh" in shell.lower():
            shell_type = "Zsh"
        elif "bash" in shell.lower():
            shell_type = "Bash"

    os_type = platform.system()
    if os_type == "Darwin":
        os_type = "macOS"
    os_name = platform.release()

    if os_type == "Linux":
        os_name_version = distro.linux_distribution(full_distribution_name=False)
    elif os_type == "Windows":
        os_name_version = (os_name, platform.win32_ver()[1])
    elif os_type == "Darwin":
        os_name_version = (os_name, platform.mac_ver()[0])
    else:
        os_name_version = (os_name, "Unknown")

    return {
        "shell_type": shell_type,
        "os_type": os_type,
        "os_name_version": os_name_version,
    }


def get_api_key() -> str:
    # If not found in the configuration file, try to read it from the environment variable
    if "OPENAI_API_KEY" in os.environ:
        return os.environ["OPENAI_API_KEY"]

    if config["openai"]["service_key"]:
        return config["openai"]["service_key"]

    # If not found in the environment variable, ask the user for the API key
    api_key = input("Please enter your OpenAI API key: ")
    os.environ["OPENAI_API_KEY"] = api_key

    return api_key


config = load_config()

config["env"] = get_environment_info()

OPEN_AI_KEY = "" or get_api_key()

LAST_CONVERSATION_FILE = os.path.join(
    os.path.expanduser("~"), ".dodo_last_conversation.json"
)
