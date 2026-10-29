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

    BLOCKED_FUNCTIONS = {"eval", "exec", "compile", "__import__", "breakpoint"}
    BLOCKED_MODULES = {
        "subprocess",
        "pty",
        "commands",
        "importlib",
        "ctypes",
        "pickle",
        "shelve",
        "marshal",
        "shutil",
        "socket",
        "multiprocessing",
    }
    BLOCKED_ATTRIBUTES = {
        "__subclasses__",
        "__globals__",
        "__builtins__",
        "__code__",
        "__reduce__",
        "__reduce_ex__",
    }
    BLOCKED_OS_CALLS = {
        "system",
        "popen",
        "spawn",
        "spawnl",
        "spawnv",
        "execv",
        "execve",
        "execl",
        "fork",
        "kill",
        "remove",
        "unlink",
        "rmdir",
    }

    def __init__(self):
        self.violations: list[str] = []
        self.has_fastmcp_instance: bool = False
        self.tool_functions: list[str] = []

    def visit_Attribute(self, node: ast.Attribute):
        # Prohibit dangerous reflective attribute access
        if node.attr in self.BLOCKED_ATTRIBUTES:
            self.violations.append(
                f"Line {node.lineno}: Prohibited reflective attribute access '{node.attr}'"
            )
        self.generic_visit(node)

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
                if module_name == "os" and attr_name in self.BLOCKED_OS_CALLS:
                    self.violations.append(
                        f"Line {node.lineno}: Disallowed OS call 'os.{attr_name}()'"
                    )
                if module_name in self.BLOCKED_MODULES:
                    self.violations.append(
                        f"Line {node.lineno}: Disallowed invocation '{module_name}.{attr_name}()'"
                    )

        self.generic_visit(node)

    def _is_blocked_module(self, mod_name: Optional[str]) -> bool:
        if not mod_name:
            return False
        root = mod_name.split(".")[0]
        return root in self.BLOCKED_MODULES

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            if self._is_blocked_module(alias.name):
                self.violations.append(
                    f"Line {node.lineno}: Prohibited module import '{alias.name}'"
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if self._is_blocked_module(node.module):
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
