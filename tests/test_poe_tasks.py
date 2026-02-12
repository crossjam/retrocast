"""Tests for poe task configurations."""

import subprocess
import sys


def test_type_task_without_castchat():
    """Test that poe type task works without castchat dependencies installed."""
    # This test assumes castchat dependencies are not installed
    # In CI, this would be the default state before installing extras

    result = subprocess.run(
        [sys.executable, "scripts/check_types.py"], capture_output=True, text=True
    )

    # The script should succeed (exit code 0) even without castchat deps
    assert result.returncode == 0, f"check_types.py failed: {result.stderr}"

    # Should indicate that castchat files are being excluded OR that all files are checked
    output = result.stdout + result.stderr
    assert (
        "Excluding castchat files" in output or
        "Checking all files" in output
    ), f"Unexpected output: {output}"


def test_check_types_script_exists():
    """Test that the check_types.py script exists and is executable."""
    import os

    script_path = "scripts/check_types.py"
    assert os.path.exists(script_path), f"Script not found: {script_path}"
    assert os.access(script_path, os.X_OK), f"Script not executable: {script_path}"
