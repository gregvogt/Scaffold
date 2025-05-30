#!/usr/bin/env python3

# A Python utility to generate `.env` files from a Markdown-annotated
# template, with interactive prompts, validation, and secure random value generation.
#
# Scaffold Environment Generator is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Scaffold Environment Generator is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Scaffold Environment Generator. If not, see <https://www.gnu.org/licenses/>.
#
# @package Scaffold Environment Generator
# @author  Greg Vogt <contact@gregvogt.net>
# @license https://www.gnu.org/licenses/gpl-3.0.html GNU General Public License v3.0
# @link    https://gregvogt.net/projects

import re
import os
import sys
import argparse
import secrets
import string
import shutil
import signal
import random
import ctypes
from datetime import datetime


def random_goodbye():
    messages = [
        "Goodbye!",
        "See you next time!",
        "Exiting. Have a great day!",
        "Bye for now!",
        "Take care!",
        "Scaffold signing off!",
        "👋 Goodbye!",
        "Thanks for using Scaffold!",
    ]
    return random.choice(messages)


def handle_exit(signum, frame):
    print(f"{os.linesep}{signal.Signals(signum).name}: {random_goodbye()}")
    sys.exit(0)


# Register signal handlers at the top-level (before main)
signal.signal(signal.SIGINT, handle_exit)  # Handle Ctrl+C
signal.signal(signal.SIGTERM, handle_exit)  # Handle kill/terminate

if hasattr(signal, "SIGHUP"):
    signal.signal(signal.SIGHUP, handle_exit)  # Handle terminal hangup


def parse_env_template(filepath) -> dict[str, dict]:
    """
    Parses an environment template file and extracts Markdown structured information
    into a dictionary suitable for programmatic use.

    Args:
        filepath (str): Path to the .env template file.

    Returns:
        dict: Mapping of environment variable names to their metadata.
    """
    try:
        with open(filepath) as f:
            lines = f.readlines()
    except (OSError, IOError) as e:
        print(f"Error opening file {filepath}: {e}")
        return {}

    temp_markdown = {}
    final_markdown = {}
    env_var_pattern = re.compile(r"^([A-Z0-9_]+)=")

    for line in lines:
        stripped = line.strip()

        # Section heading (e.g., "# Section Name")
        if stripped.startswith("# ") and len(stripped) > 2 and stripped[2] != "`":
            temp_markdown["section"] = stripped[2:]

        # Question heading (e.g., "## Question?")
        elif stripped.startswith("## "):
            temp_markdown["question"] = stripped[3:]

        # Information heading (e.g., "### Info")
        elif stripped.startswith("### "):
            temp_markdown.setdefault("info", []).append(stripped[4:])

        # Regex heading (e.g., "# `regex`")
        elif stripped.startswith("# `"):
            regex_pattern = stripped[2:].strip("`")
            temp_markdown["regex"] = regex_pattern
            try:
                re.compile(regex_pattern)
            except re.error as e:
                temp_markdown["regex_error"] = f"Invalid regex: {e}"

        else:
            # Check for environment variable assignment (e.g., "VAR=value")
            match = env_var_pattern.match(stripped)
            if match:
                var_name = match.group(1)
                final_markdown[var_name] = temp_markdown.copy()
                final_markdown[var_name]["default"] = (
                    stripped.split("=", 1)[1] if "=" in stripped else None
                )

                # Clear temp_markdown for the next variable
                temp_markdown.clear()

    return final_markdown


def generate_secure_random_string(length: int) -> str:
    """
    Generates a cryptographically secure random string of the specified length.

    Args:
        length (int): The length of the random string.

    Returns:
        str: A random string.
    """
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def prompt(var, data, current_question=None, total_questions=None) -> str:
    """
    Prompt the user for an environment variable value, with optional regex validation.

    Args:
        var (str): The environment variable name.
        data (dict): Metadata for the variable, including 'default', 'question', 'info', and optional 'regex'.

    Returns:
        str: The value entered by the user (or default).
    """

    user_value = data.get("default", "")
    question = data.get("question", "No question provided")
    info_lines = data.get("info", []) or ["No additional info provided"]

    try:
        term_width = shutil.get_terminal_size((80, 20)).columns
    except Exception:
        term_width = 80

    box_lines = []
    content_lines = [question] + [""] + info_lines
    max_line_length = max(len(line) for line in content_lines)
    box_width = min(max_line_length + 4, term_width - 2)

    indicator = ""
    if current_question is not None and total_questions is not None:
        indicator = f" ({current_question}/{total_questions})"
        horizontal = "─" * max(1, box_width - 2 - len(indicator))
        top = f"┌{horizontal}{indicator}┐"
    else:
        horizontal = "─" * max(1, box_width - 2)
        top = f"┌{horizontal}┐"
    bottom = f"└{'─' * max(1, box_width - 2)}┘"

    box_lines.append(top)
    for line in content_lines:
        padded = line.center(box_width - 2)
        box_lines.append(f"│{padded}│")
    box_lines.append(bottom)

    for line in box_lines:
        print(line.center(term_width))

    prompt_str = f"{var} (default: {user_value}): "
    left_padding = max(0, (term_width - len(prompt_str)) // 2)
    input_str = input(" " * left_padding + prompt_str).strip() or user_value

    if input_str.startswith("random"):
        match = re.match(r"random\((\d+)\)", input_str)
        length = int(match.group(1)) if match else 32
        input_str = generate_secure_random_string(length)

    if "regex" in data:
        while not re.fullmatch(data["regex"], input_str):
            print(f"Input does not match regex: {data['regex']}".center(term_width))
            input_str = input(prompt_str.center(term_width)).strip() or user_value

    # Attempt to clear the terminal in a cross-platform way
    clear_cmd = "cls" if os.name == "nt" else "clear"
    if sys.stdout.isatty():
        os.system(clear_cmd)

    return input_str


def main():
    """
    Main entry point for the .env template parser and generator.
    It processes the template file, prompts the user for environment variable values (with validation and defaults),
    and writes the resulting environment file to disk, handling file overwrite checks.
    Steps performed:
    1. Parse command-line arguments for input filename and debug mode.
    2. Parse the .env template file using Markdown structure.
    3. If debug mode is enabled, print detailed information about each variable.
    4. For each environment variable, prompt the user for input, validate using regex if specified, and collect values.
    5. Prompt the user for the output filename, check for overwrite if the file exists.
    6. Write the collected environment variables to the specified output file.
    Returns:
        None
    """

    # Exit if running as root (Unix) or as Administrator (Windows)
    if os.name != "nt":
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            print(
                "Error: This script should not be run as root for safety reasons. Exiting."
            )
            sys.exit(1)
    else:
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            is_admin = False
        if is_admin:
            print(
                "Error: This script should not be run as Administrator for safety reasons. Exiting."
            )
            sys.exit(1)

    parser = argparse.ArgumentParser(
        description="Parse a .env template file with Markdown structure."
    )
    parser.add_argument(
        "-f",
        "--filename",
        type=str,
        default=".env.template",
        help="Path to the .env template file (default: .env.template)",
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", help="Enable debug output"
    )
    args = parser.parse_args()

    print(f"Parsing file: {args.filename}")
    parsed_env = parse_env_template(args.filename)

    if not parsed_env:
        print("No valid environment variables found or file could not be parsed.")
        return

    if args.debug:
        for var, data in parsed_env.items():
            print(f"Variable: {var}")
            print(f"  Section: {data.get('section', 'N/A')}")
            print(f"  Question: {data.get('question', 'N/A')}")
            print(
                f"  Info: {', '.join(data.get('info', [])) if data.get('info') else 'N/A'}"
            )
            print(f"  Default: {data.get('default', 'N/A')}")
            if "regex" in data:
                print(f"  Regex: {data['regex']}")
                if "regex_error" in data:
                    print(f"  Regex Error: {data['regex_error']}")
            print()
            print("-" * 40)

    env_file_content = []
    total_questions = len(parsed_env)
    for idx, (var, data) in enumerate(parsed_env.items(), 1):
        user_input = prompt(var, data, idx, total_questions)
        env_file_content.append(f"{var}={user_input}")

    env_file_string = os.linesep.join(env_file_content)

    # Check environment variable size limit
    if os.name == "nt":
        # On Windows, the maximum size of the environment block is 32767 characters
        max_env_size = 32767
    else:
        try:
            max_env_size = os.sysconf("SC_ARG_MAX")
        except (AttributeError, ValueError):
            max_env_size = 131072  # Fallback to 128K if sysconf not available

    env_length = len(env_file_string.encode("utf-8"))
    print(
        f"Total environment file size: {env_length} bytes (system max: {max_env_size} bytes)"
    )

    if env_length > max_env_size:

        print(
            f"Warning: The environment file size ({env_length} bytes) exceeds the system's max allocatable size ({max_env_size} bytes)."
        )
        print(
            "Continuing may result in undefined behavior in some shells or applications."
        )
        if os.name == "nt":
            print("NOTE: Unknown if Windows limit applies to WSL/Docker.")

        proceed = input("Would you like to continue anyway? (y/N): ").strip().lower()
        if proceed != "y":
            print("Aborted. Please reduce the number or size of environment variables.")
            return

    # Ask for output filename
    output_filename = input("Enter output filename (default: .env): ").strip() or ".env"

    # Check if file exists and ask to overwrite
    if os.path.exists(output_filename):
        overwrite = (
            input(f"File '{output_filename}' exists. Overwrite? (y/N): ")
            .strip()
            .lower()
        )
        if overwrite != "y":
            print("Aborted. File not overwritten.")
            return

    try:
        with open(output_filename, "w") as f:
            now = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
            f.write(f"# Generated by Scaffold Environment Generator on {now}{os.linesep}")
            f.write(f"# Do not edit this file directly; use the template instead.{os.linesep}")
            f.write(env_file_string)
        print(f"Environment file written to '{output_filename}'.")
    except (OSError, IOError) as e:
        print(f"Error writing to file '{output_filename}': {e}")


if __name__ == "__main__":
    main()
