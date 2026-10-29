"""Security verification tests for SSRF protection, environment scrubbing, and AST scanner."""

import pytest
import os
from dynamicmcp.ingestor.extractor import SpecIngestor
from dynamicmcp.verification.runner import VerificationRunner
from dynamicmcp.synthesizer.validator import ASTValidator
from dynamicmcp.sandbox.openshell import PolicyGenerator
from dynamicmcp.models.spec import ToolSpec, EndpointSpec, IngestType


def test_ssrf_protection():
    """Verify that SSRF targets (loopback, private networks, cloud metadata) are blocked."""
    # Cloud metadata endpoint
    safe, msg = SpecIngestor._is_safe_remote_url("http://169.254.169.254/latest/meta-data/")
    assert not safe
    assert "restricted" in msg or "prohibited" in msg

    # Localhost / loopback
    safe, msg = SpecIngestor._is_safe_remote_url("http://localhost:8080/openapi.json")
    assert not safe
    assert "prohibited" in msg

    safe, msg = SpecIngestor._is_safe_remote_url("http://127.0.0.1:5000/spec.json")
    assert not safe
    assert "prohibited" in msg

    # Unsupported protocol schemes
    safe, msg = SpecIngestor._is_safe_remote_url("file:///etc/passwd")
    assert not safe
    assert "Unsupported scheme" in msg

    safe, msg = SpecIngestor._is_safe_remote_url("gopher://127.0.0.1:70")
    assert not safe
    assert "Unsupported scheme" in msg


def test_subprocess_env_scrubbing(monkeypatch):
    """Verify host secrets and API keys are completely stripped before subprocess invocation."""
    test_env = {
        "PATH": "/usr/bin:/bin",
        "PYTHONPATH": "/tmp/test",
        "NEBIUS_API_KEY": "v1.super-secret-key",
        "NASA_API_KEY": "secret-nasa-key",
        "AWS_SECRET_ACCESS_KEY": "aws-secret",
        "GITHUB_TOKEN": "ghp_secret",
        "DB_PASSWORD": "mypassword",
    }

    for k, v in test_env.items():
        monkeypatch.setenv(k, v)

    sanitized = VerificationRunner._get_sanitized_env({"EXTRA_SAFE_VAR": "ok"})

    assert "PATH" in sanitized
    assert sanitized["EXTRA_SAFE_VAR"] == "ok"

    # All sensitive tokens must be absent
    assert "NEBIUS_API_KEY" not in sanitized
    assert "NASA_API_KEY" not in sanitized
    assert "AWS_SECRET_ACCESS_KEY" not in sanitized
    assert "GITHUB_TOKEN" not in sanitized
    assert "DB_PASSWORD" not in sanitized


def test_ast_validator_sandbox_escapes():
    """Verify that dangerous modules, reflective attributes, and aliased imports are blocked."""
    prohibited_snippets = [
        "import importlib; importlib.import_module('os')",
        "import ctypes; ctypes.string_at(0)",
        "import socket; s = socket.socket()",
        "import shutil; shutil.rmtree('/tmp')",
        "import pickle; pickle.loads(b'')",
        "x = ().__class__.__base__.__subclasses__()",
        "def foo():\n    return foo.__globals__",
        "os.system('id')",
        "os.popen('cat /etc/passwd')",
        "import os as my_os; my_os.system('whoami')",
        "from os import system; system('ls')",
        "eval('1 + 1')",
        "exec('import sys')",
    ]

    for snippet in prohibited_snippets:
        result = ASTValidator.validate(snippet)
        assert not result.valid, f"Expected validation failure for: {snippet}"
        assert len(result.errors) > 0


def test_nemoclaw_policy_domain_sanitization():
    """Verify policy generator cleans hostnames and strips port/path injections."""
    spec = ToolSpec(
        name="test_tool",
        description="Test",
        target_domain="api.example.com:8080/v1/test",
        base_url="https://api.example.com:8080",
        endpoints=[EndpointSpec(path="/ping", method="GET")],
        source_type=IngestType.TEXT,
        raw_input="test",
    )

    policy = PolicyGenerator.generate_policy(spec)
    assert "api.example.com" in policy
    assert "8080" not in policy
    assert "/v1/test" not in policy
