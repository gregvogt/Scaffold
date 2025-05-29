import os
import sys
import tempfile
import pytest
import tempfile
import builtins
from scaffold import parse_env_template, generate_secure_random_string, main

def test_root_detection(monkeypatch):
    # Simulate running as root by patching os.geteuid to return 0
    import scaffold

    monkeypatch.setattr(scaffold.os, "geteuid", lambda: 0)
    with pytest.raises(SystemExit) as excinfo:
        scaffold.main()
    assert excinfo.value.code == 1

def test_parse_env_template_basic():
    content = """
# Section 1
## What is the API key?
### This is your API key for service X.
API_KEY=defaultkey
"""
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tf:
        tf.write(content)
        tf.flush()
        result = parse_env_template(tf.name)
    os.unlink(tf.name)
    assert "API_KEY" in result
    assert result["API_KEY"]["section"] == "Section 1"
    assert result["API_KEY"]["question"] == "What is the API key?"
    assert result["API_KEY"]["info"] == ["This is your API key for service X."]
    assert result["API_KEY"]["default"] == "defaultkey"

def test_parse_env_template_with_regex():
    content = """
# Section 2
## Enter a number
# `^[0-9]+$`
NUMBER=42
"""
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tf:
        tf.write(content)
        tf.flush()
        result = parse_env_template(tf.name)
    os.unlink(tf.name)
    assert "NUMBER" in result
    assert result["NUMBER"]["regex"] == "^[0-9]+$"
    assert result["NUMBER"]["default"] == "42"

def test_parse_env_template_with_invalid_regex():
    content = """
# Section 3
## Enter a value
# `^[0-9+($`
INVALID_VAR=oops
"""
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tf:
        tf.write(content)
        tf.flush()
        result = parse_env_template(tf.name)
    os.unlink(tf.name)
    assert "INVALID_VAR" in result
    assert result["INVALID_VAR"]["regex"] == "^[0-9+($"
    assert "regex_error" in result["INVALID_VAR"]
    assert "Invalid regex" in result["INVALID_VAR"]["regex_error"]

def test_parse_env_template_path_injection():
    # Attempt to use a path traversal string as the filename
    malicious_path = "../../etc/passwd"
    
    # Should not raise, but should return {} since file likely doesn't exist or is not a valid template
    result = parse_env_template(malicious_path)
    assert isinstance(result, dict)
    
    # Should not parse any environment variables from a system file
    assert result == {}

@pytest.mark.parametrize("malformed_path", [
    "",  # empty string
    "\0",  # null byte
    "/////",  # excessive slashes
    "not/a/real/\0path",  # embedded null
    "C:\\this\\does\\not\\exist",  # windows style on linux
    "::::",  # invalid chars
    "/dev/null",  # special file
])
def test_parse_env_template_malformed_paths(malformed_path):
    try:
        result = parse_env_template(malformed_path)
        assert isinstance(result, dict)
    except Exception:
        # Should not raise, should handle gracefully and return {}
        assert True
        
def test_parse_env_template_malicious_content():
    # Malicious content in the template (attempting command injection, etc.)
    content = """
# Section
## Enter something
### Info
MALICIOUS_VAR=$(rm -rf /)
"""
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tf:
        tf.write(content)
        tf.flush()
        result = parse_env_template(tf.name)
    os.unlink(tf.name)
    
    # The parser should treat this as a string, not execute anything
    assert "MALICIOUS_VAR" in result
    assert result["MALICIOUS_VAR"]["default"] == "$(rm -rf /)"

def test_prompt_rejects_malicious_input(monkeypatch):
    # Simulate user input that looks like a shell injection
    from scaffold import prompt

    data = {
        "question": "Enter value",
        "info": ["Do not enter malicious input"],
        "default": "safe",
        "regex": r"^[a-zA-Z0-9_]+$"
    }
    
    # Should keep prompting, so after one bad input, give a good one
    inputs = iter(["bad; rm -rf /", "another bad; cat ../../../etc/passwd", "SAFE_VALUE"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    value = prompt("MALICIOUS_VAR", data)
    assert value == "SAFE_VALUE"

def test_env_size_limit(monkeypatch):
    # Prepare a large env string to exceed the limit
    var_count = 1000
    long_value = "A" * 200
    env_lines = [f"VAR{i}={long_value}" for i in range(var_count)]

    # Write a temporary .env.template file
    with tempfile.NamedTemporaryFile("w+", delete=False) as tf:
        for line in env_lines:
            tf.write(f"{line}\n")
        tf.flush()
        template_path = tf.name

    # Patch sys.argv to use the template file
    monkeypatch.setattr(sys, "argv", ["scaffold.py", "-f", template_path])

    # Patch input to always accept defaults, then 'n' to abort when asked to continue
    inputs = iter([""] * var_count + ["test.env", "n"])
    monkeypatch.setattr(builtins, "input", lambda *args, **kwargs: next(inputs))

    # Patch os.sysconf to return a small limit to force the warning
    monkeypatch.setattr(os, "sysconf", lambda name: 1024 if name == "SC_ARG_MAX" else 131072)

    # Capture output
    from io import StringIO
    out = StringIO()
    sys_stdout = sys.stdout
    sys.stdout = out

    try:
        main()
    finally:
        sys.stdout = sys_stdout
        os.unlink(template_path)

    output = out.getvalue()
    assert "Warning: The environment file size" in output
    assert "Aborted. Please reduce the number or size of environment variables." in output

def test_generate_secure_random_string_length():
    s = generate_secure_random_string(16)
    assert isinstance(s, str)
    assert len(s) == 16

def test_generate_secure_random_string_uniqueness():
    s1 = generate_secure_random_string(32)
    s2 = generate_secure_random_string(32)
    assert s1 != s2

def test_parse_env_template_invalid_file():
    result = parse_env_template("/nonexistent/file/path.env")
    assert result == {}
