import subprocess
import sys
from pathlib import Path


FUNC_PS1 = Path(r"C:\Users\maxbush\AppData\Roaming\npm\func.ps1")


def _run_func(*args: str) -> subprocess.CompletedProcess[str]:
    """Run Azure Functions Core Tools via the func.ps1 script."""
    cmd = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(FUNC_PS1),
        *args,
    ]
    return subprocess.run(cmd, capture_output=True, text=True)


def test_func_core_tools_available() -> None:
    """func --version should run successfully."""
    result = _run_func("--version")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() != ""


def test_azure_functions_package_imports() -> None:
    """azure.functions should be importable in the venv."""
    result = subprocess.run([sys.executable, "-c", "import azure.functions"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_placeholder_functions_host_starts() -> None:
    """Smoke test placeholder: ensure func command exists.

    Full host-start tests are better done via integration scripts; this just
    verifies the CLI is callable in CI/local env.
    """
    result = _run_func("--help")
    assert result.returncode == 0, result.stderr