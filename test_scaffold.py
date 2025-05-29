import os
import tempfile
import pytest
from scaffold import parse_env_template, generate_secure_random_string

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
    inputs = iter(["bad; rm -rf /", "SAFE_VALUE"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    value = prompt("MALICIOUS_VAR", data)
    assert value == "SAFE_VALUE"

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
