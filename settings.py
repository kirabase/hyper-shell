import sys
import os
import platform

from configparser import ConfigParser

# Install the distro package with `pip install distro` if you're using Linux
if sys.platform.startswith("linux"):
    import distro

AI_SERVICES = [
    ("openai", "gpt-3.5-turbo"),
    ("anthropic", "claude-v1"),
]

DEFAULT_AI_SERVICE = AI_SERVICES[0][0]


def load_config() -> dict:
    config = ConfigParser()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.ini")
    config.read(config_path)

    config_dict = {
        "main": {
            "ai_service": config.get(
                "main", "ai_service", fallback=DEFAULT_AI_SERVICE
            ).lower(),
        },
    }

    for service, model in AI_SERVICES:
        config_dict[service] = {
            "service_key": config.get(service, "service_key", fallback=None),
            "service_model": config.get(service, "service_model", fallback=model),
        }

    return config_dict


def instrument_config(config):
    config["env"] = get_environment_info()
    for service, model in AI_SERVICES:
        config[service]["service_key"] = get_api_key(service)


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


def get_api_key(ai_service) -> str:
    # Check for an environment variable first
    key_tag = f"{ai_service.upper()}_API_KEY"
    if key_tag in os.environ:
        return os.environ[key_tag]

    # Check for a config file
    if config[ai_service]["service_key"]:
        return config[ai_service]["service_key"]

    # Ask the user for the key
    if config["main"]["ai_service"] == ai_service:
        api_key = input(f"Please enter your {ai_service} API key: ")
        os.environ[key_tag] = api_key
        return api_key

    return None


config = load_config()
instrument_config(config)

LAST_CONVERSATION_FILE = os.path.join(
    os.path.expanduser("~"), ".dodo_last_conversation.json"
)
