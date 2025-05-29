<div align="center">

# Scaffold Environment Generator

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

A Python utility to generate `.env` files from a Markdown-annotated template, with interactive prompts, validation, and secure random value generation.

</div>

## Features

- Parses a `.env.template` file with Markdown-style comments for documentation and validation.
- Prompts the user for each environment variable, showing helpful info and default values.
- Supports regex validation for variable values.
- Can generate secure random strings for secrets.
- Prevents accidental overwrites of existing `.env` files.

## Usage

1. **Prepare your template:**  
   Edit `.env.template` to define your environment variables, questions, info, and regex patterns.

2. **Run the generator:**
   ```sh
   python scaffold.py
   ```
   - Use `-f` or `--filename` to specify a different template file.
   - Use `-d` or `--debug` for verbose output.

3. **Follow the prompts:**  
   The script will ask you for each variable, validate your input, and write the results to `.env` (or a file you specify).

## Example

```
# Application settings

## What is your application name?
### This will be used in various places like logs, error messages, etc.
### Ensure your selection is alphanumeric and does not contain spaces.
# `[a-zA-Z0-9]+$`
APP_NAME=YourAppName

APP_ENV=development
APP_PORT=3000
...
```

## Command-Line Options

- `-f, --filename` &nbsp; Path to the template file (default: `.env.template`)
- `-d, --debug` &nbsp; Enable debug output

## Requirements

- Python 3.7+

## Files

- [`scaffold.py`](scaffold.py): Main script.
- [`test_scaffold.py`](test_scaffold.py) Make sure everything works.
- [`.env.template`](.env.template): Example template.
- [`.env`](.env): Generated output (ignored by git).
- [`.gitignore`](.gitignore): Ignores `.env` and virtual environments.
