#!/usr/bin/env python3

import re
import sys

def parse_env_template_to_markdown(filepath) -> dict:
    """
    Parses an environment template file and extracts Markdown structured information
    into a dictionary suitable for programatic use.

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
    env_var_pattern = re.compile(r'^([A-Z0-9_]+)=')

    for line in lines:
        stripped = line.strip()

        # Section heading (e.g., "# Section Name")
        if stripped.startswith("# ") and len(stripped) > 2 and stripped[2] != '`':
            temp_markdown['section'] = stripped[2:]

        # Question heading (e.g., "## Question?")
        elif stripped.startswith("## "):
            temp_markdown['question'] = stripped[3:]

        # Information heading (e.g., "### Info")
        elif stripped.startswith("### "):
            temp_markdown.setdefault('info', []).append(stripped[4:])

        # Regex heading (e.g., "# `regex`")
        elif stripped.startswith("# `"):
            regex_pattern = stripped[2:].strip('`')
            temp_markdown['regex'] = regex_pattern
            try:
                re.compile(regex_pattern)
            except re.error as e:
                temp_markdown['regex_error'] = f"Invalid regex: {e}"

        else:
            # Check for environment variable assignment (e.g., "VAR=value")
            match = env_var_pattern.match(stripped)
            if match:
                var_name = match.group(1)
                final_markdown[var_name] = temp_markdown.copy()
                final_markdown[var_name]['default'] = stripped.split('=', 1)[1] if '=' in stripped else None
                
                # Clear temp_markdown for the next variable
                temp_markdown.clear()

    return final_markdown

def main():
    # Allow filename to be passed as a command-line argument
    filename = sys.argv[1] if len(sys.argv) > 1 else ".env.template"
    md = parse_env_template_to_markdown(filename)
    print(md)

if __name__ == "__main__":
    main()