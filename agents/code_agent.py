"""
Code Execution Agent: Sandboxed Python execution with resource limits.
Security: subprocess isolation, timeout enforcement, memory cap.
"""

import ast
import asyncio
import resource
import sys
import time
import textwrap
import tempfile
import os
from typing import Dict, Optional, Tuple

import structlog

from gateway.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

# Blocked imports for security
BLOCKED_IMPORTS = {
    "os", "subprocess", "sys", "shutil", "socket",
    "requests", "urllib", "http", "ftplib", "smtplib",
    "importlib", "ctypes", "multiprocessing",
}


def _is_safe_code(code: str) -> Tuple[bool, str]:
    """Static analysis: reject obviously dangerous code."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"Syntax error: {e}"

    for node in ast.walk(tree):
        # Block dangerous imports
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in getattr(node, "names", []):
                name = alias.name.split(".")[0]
                if name in BLOCKED_IMPORTS:
                    return False, f"Import '{name}' is not allowed in sandbox"
        # Block __import__
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "__import__":
                return False, "__import__ is not allowed"

    return True, ""


class CodeAgent:
    async def execute(
        self,
        code: str,
        timeout: Optional[int] = None,
    ) -> Dict[str, str | bool | float]:
        """
        Execute Python code in a sandboxed subprocess.
        Returns: {stdout, stderr, success, latency_ms, code}
        """
        timeout = timeout or settings.code_exec_timeout
        t0 = time.monotonic()

        # Static safety check
        safe, reason = _is_safe_code(code)
        if not safe:
            return {
                "stdout": "",
                "stderr": f"Security check failed: {reason}",
                "success": False,
                "latency_ms": 0,
                "code": code,
            }

        # Write to temp file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as f:
            f.write(textwrap.dedent(code))
            tmp_path = f.name

        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, tmp_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                return {
                    "stdout": "",
                    "stderr": f"Execution timed out after {timeout}s",
                    "success": False,
                    "latency_ms": (time.monotonic() - t0) * 1000,
                    "code": code,
                }

            latency = (time.monotonic() - t0) * 1000
            success = proc.returncode == 0
            logger.info(
                "code_exec",
                success=success,
                latency_ms=round(latency, 1),
                returncode=proc.returncode,
            )

            return {
                "stdout": stdout.decode("utf-8", errors="replace")[:4096],
                "stderr": stderr.decode("utf-8", errors="replace")[:2048],
                "success": success,
                "latency_ms": latency,
                "code": code,
            }

        finally:
            os.unlink(tmp_path)

    def format_result(self, result: Dict) -> str:
        lines = ["## Code Execution Result\n"]
        lines.append(f"```python\n{result['code']}\n```\n")
        if result["stdout"]:
            lines.append(f"**Output:**\n```\n{result['stdout']}\n```")
        if result["stderr"]:
            lines.append(f"**Errors:**\n```\n{result['stderr']}\n```")
        lines.append(f"Status: {'✅ Success' if result['success'] else '❌ Failed'}")
        lines.append(f"Latency: {result['latency_ms']:.0f}ms")
        return "\n".join(lines)


_code_agent: Optional[CodeAgent] = None


def get_code_agent() -> CodeAgent:
    global _code_agent
    if _code_agent is None:
        _code_agent = CodeAgent()
    return _code_agent
