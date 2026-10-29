"""Data models for API and tool specifications."""

from enum import Enum
from typing import Any, Optional
import hashlib
import json
from pydantic import BaseModel, Field


class IngestType(str, Enum):
    CURL = "curl"
    OPENAPI = "openapi"
    CLI = "cli"
    TEXT = "text"


class ParameterLocation(str, Enum):
    QUERY = "query"
    PATH = "path"
    HEADER = "header"
    BODY = "body"


class ParameterSpec(BaseModel):
    """Specification of an input parameter for a tool."""
    name: str
    type: str = "string"  # "string", "integer", "float", "boolean", "array", "object"
    location: ParameterLocation = ParameterLocation.QUERY
    required: bool = False
    default: Optional[Any] = None
    description: str = ""
    enum_values: Optional[list[Any]] = None


class AuthType(str, Enum):
    NONE = "none"
    BEARER = "bearer"
    API_KEY = "api_key"
    BASIC = "basic"
    OAUTH2 = "oauth2"


class AuthSpec(BaseModel):
    """Authentication requirements for an API."""
    auth_type: AuthType = AuthType.NONE
    header_name: Optional[str] = "Authorization"
    key_name: Optional[str] = None
    secret_ref: Optional[str] = None


class EndpointSpec(BaseModel):
    """API endpoint specification."""
    path: str
    method: str = "GET"  # "GET", "POST", "PUT", "DELETE", etc.
    description: str = ""
    parameters: list[ParameterSpec] = Field(default_factory=list)
    request_body_schema: Optional[dict[str, Any]] = None
    response_schema: Optional[dict[str, Any]] = None


class ToolSpec(BaseModel):
    """Complete specification of a dynamically generated tool."""
    id: str = ""
    name: str
    description: str
    target_domain: str
    base_url: str
    endpoints: list[EndpointSpec] = Field(default_factory=list)
    auth: AuthSpec = Field(default_factory=AuthSpec)
    source_type: IngestType = IngestType.CURL
    raw_input: str = ""
    version: str = "1.0.0"

    def model_post_init(self, __context: Any) -> None:
        """Compute deterministic ID if not explicitly provided."""
        if not self.id:
            raw_hash_data = f"{self.name}:{self.target_domain}:{self.base_url}:{len(self.endpoints)}"
            self.id = hashlib.sha256(raw_hash_data.encode("utf-8")).hexdigest()[:16]

    def compute_version_hash(self, generated_code: str = "") -> str:
        """Compute content-addressable hash for this spec and its synthesized code."""
        content = f"{self.model_dump_json()}::{generated_code}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]
