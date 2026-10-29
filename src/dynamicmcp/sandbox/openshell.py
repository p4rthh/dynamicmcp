"""NVIDIA OpenShell & NemoClaw declarative security policy generator."""

from pathlib import Path
from typing import Optional
import yaml
from dynamicmcp.models.spec import ToolSpec, AuthType
from dynamicmcp.config import settings


class PolicyGenerator:
    """Generates declarative NemoClaw security policies enforcing strict egress and filesystem isolation."""

    @staticmethod
    def _sanitize_domain(domain: str) -> Optional[str]:
        """Sanitize domain string removing protocols, paths, and port numbers."""
        if not domain:
            return None
        cleaned = domain.strip().lower()
        if "://" in cleaned:
            cleaned = cleaned.split("://", 1)[1]
        cleaned = cleaned.split("/", 1)[0]
        cleaned = cleaned.split(":", 1)[0]
        # Reject cloud metadata IP
        if cleaned in ("169.254.169.254", "metadata.google.internal"):
            return None
        return cleaned if cleaned else None

    @classmethod
    def generate_policy(cls, spec: ToolSpec, output_path: Optional[Path | str] = None) -> str:
        """Generate a NemoClaw policy YAML string and optionally persist it."""
        clean_domain = cls._sanitize_domain(spec.target_domain)
        allowed_domains = []
        if clean_domain:
            allowed_domains.append(clean_domain)

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

        # Add zero-trust credentials injection rule only if clean_domain is valid and auth spec specifies secrets
        if clean_domain and spec.auth and spec.auth.auth_type != AuthType.NONE:
            policy_dict["security_policy"]["credentials"] = {
                "injection_mode": "header",
                "inject_only_for": [
                    {
                        "domain": clean_domain,
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
