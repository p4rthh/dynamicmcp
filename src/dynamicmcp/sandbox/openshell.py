"""NVIDIA OpenShell & NemoClaw declarative security policy generator."""

from pathlib import Path
from typing import Optional
import yaml
from dynamicmcp.models.spec import ToolSpec, AuthType
from dynamicmcp.config import settings


class PolicyGenerator:
    """Generates declarative NemoClaw security policies enforcing strict egress and filesystem isolation."""

    @staticmethod
    def generate_policy(spec: ToolSpec, output_path: Optional[Path | str] = None) -> str:
        """Generate a NemoClaw policy YAML string and optionally persist it."""
        allowed_domains = [spec.target_domain] if spec.target_domain != "localhost" else ["127.0.0.1", "localhost"]
        # Remove empty or wildcard
        allowed_domains = [d for d in allowed_domains if d]

        policy_dict = {
            "version": "1.0",
            "sandbox": {
                "name": f"sandbox-{spec.name.replace('_', '-')}",
                "agent_harness": "hermes",
                "description": spec.description or f"NemoClaw policy for {spec.name}",
            },
            "security_policy": {
                "default_action": "deny",
                "filesystem": {
                    "readonly_paths": [
                        "/usr",
                        "/lib",
                        "/lib64",
                        "/etc/ssl",
                        "/etc/resolv.conf",
                    ],
                    "writable_paths": [
                        "/tmp/workspace",
                    ],
                    "blocked_paths": [
                        "/home/*/.ssh",
                        "/home/*/.env",
                        "/home/*/.config",
                        "/home/*/.gnupg",
                        "/proc/*/environ",
                        "/etc/shadow",
                        "/etc/passwd",
                    ],
                    "blocked_patterns": [
                        "**/.*token*",
                        "**/.*secret*",
                        "**/.*credential*",
                        "**/.*key.pem",
                    ],
                },
                "network": {
                    "allowed_domains": allowed_domains,
                    "allowed_ports": [443, 80],
                    "blocked_domains": [
                        "*.internal",
                        "metadata.google.internal",
                        "169.254.169.254",
                    ],
                    "dns_allowed": True,
                },
                "process": {
                    "allowed_binaries": [
                        "/usr/bin/python3",
                        "/usr/local/bin/python3",
                    ],
                    "max_processes": 4,
                    "max_memory_mb": 512,
                    "max_cpu_seconds": 30,
                },
                "presets": [
                    {"name": "python-runtime", "enabled": True},
                    {"name": "dns-resolution", "enabled": True},
                    {"name": "shell-access", "enabled": False},
                ],
            },
            "audit": {
                "log_level": "info",
                "log_destination": "/tmp/workspace/audit.jsonl",
                "record_network_requests": True,
                "record_file_access": True,
            },
        }

        # Add zero-trust credentials injection rule if auth spec specifies a secret ref or header
        if spec.auth and spec.auth.auth_type != AuthType.NONE:
            policy_dict["security_policy"]["credentials"] = {
                "injection_mode": "header",
                "inject_only_for": [
                    {
                        "domain": spec.target_domain,
                        "header": spec.auth.header_name or "Authorization",
                        "secret_ref": spec.auth.secret_ref or f"vault://{spec.name}/token",
                    }
                ],
            }

        yaml_content = yaml.dump(policy_dict, sort_keys=False, default_flow_style=False)

        if output_path:
            p = Path(output_path).expanduser()
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(yaml_content, encoding="utf-8")

        return yaml_content
