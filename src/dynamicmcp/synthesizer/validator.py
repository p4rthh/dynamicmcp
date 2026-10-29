"""AST-based security and conformance validator for synthesized FastMCP server code."""

import ast
from typing import Optional
from pydantic import BaseModel, Field


class ValidationResult(BaseModel):
    """Result of an AST validation scan."""
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    tool_names: list[str] = Field(default_factory=list)


class SecurityNodeVisitor(ast.NodeVisitor):
    """Walks the AST to detect prohibited system calls and unsafe constructs."""

    BLOCKED_FUNCTIONS = {"eval", "exec", "compile", "__import__"}
    BLOCKED_MODULES = {"subprocess", "pty", "commands"}

    def __init__(self):
        self.violations: list[str] = []
        self.has_fastmcp_instance: bool = False
        self.tool_functions: list[str] = []

    def visit_Call(self, node: ast.Call):
        # Check direct function calls: eval(...), exec(...)
        if isinstance(node.func, ast.Name):
            if node.func.id in self.BLOCKED_FUNCTIONS:
                self.violations.append(
                    f"Line {node.lineno}: Disallowed builtin call '{node.func.id}()'"
                )
            if node.func.id == "FastMCP":
                self.has_fastmcp_instance = True

        # Check attribute calls: os.system(...), subprocess.Popen(...)
        elif isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                module_name = node.func.value.id
                attr_name = node.func.attr
                if module_name == "os" and attr_name in ("system", "popen", "spawn", "execv", "execl"):
                    self.violations.append(
                        f"Line {node.lineno}: Disallowed OS call 'os.{attr_name}()'"
                    )
                if module_name in self.BLOCKED_MODULES:
                    self.violations.append(
                        f"Line {node.lineno}: Disallowed subprocess invocation '{module_name}.{attr_name}()'"
                    )
            # Check attribute access to __subclasses__, __globals__
            if node.func.attr in ("__subclasses__", "__globals__", "__builtins__"):
                self.violations.append(
                    f"Line {node.lineno}: Disallowed reflective call '{node.func.attr}()'"
                )

        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            if alias.name in self.BLOCKED_MODULES:
                self.violations.append(
                    f"Line {node.lineno}: Prohibited module import '{alias.name}'"
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module in self.BLOCKED_MODULES:
            self.violations.append(
                f"Line {node.lineno}: Prohibited from-import of module '{node.module}'"
            )
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._check_tool_decorator(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._check_tool_decorator(node)
        self.generic_visit(node)

    def _check_tool_decorator(self, node):
        for dec in node.decorator_list:
            if isinstance(dec, ast.Call):
                if isinstance(dec.func, ast.Attribute) and dec.func.attr == "tool":
                    self.tool_functions.append(node.name)
            elif isinstance(dec, ast.Attribute) and dec.attr == "tool":
                self.tool_functions.append(node.name)


class ASTValidator:
    """Validates Python source code for security compliance and FastMCP conformance."""

    @staticmethod
    def validate(code: str) -> ValidationResult:
        errors: list[str] = []
        warnings: list[str] = []

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return ValidationResult(
                valid=False,
                errors=[f"Syntax error on line {e.lineno}: {e.msg}"],
            )

        visitor = SecurityNodeVisitor()
        visitor.visit(tree)

        errors.extend(visitor.violations)

        if not visitor.tool_functions:
            warnings.append(
                "No tool function found with @mcp.tool() decorator. Server may not expose any tools."
            )

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            tool_names=visitor.tool_functions,
        )
