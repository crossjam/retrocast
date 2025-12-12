"""Tests for PoeThePoet task configuration."""

import subprocess
import sys
from pathlib import Path

# Get the project root directory (parent of tests directory)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_poe_tasks_are_configured():
    """Test that PoeThePoet tasks are properly configured."""
    result = subprocess.run(
        [sys.executable, "-m", "poethepoet", "--help"],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )

    assert result.returncode == 0
    output = result.stdout

    # Check that all expected tasks are listed
    expected_tasks = [
        "lint",
        "lint:fix",
        "type",
        "test",
        "test:cov",
        "test:quick",
        "test:collect",
        "qa",
    ]

    for task in expected_tasks:
        assert task in output, f"Task '{task}' not found in poe help output"


def test_lint_task_executes():
    """Test that the lint task can be executed."""
    result = subprocess.run(
        [sys.executable, "-m", "poethepoet", "lint"],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )

    # Should pass or fail, but not error out
    assert result.returncode in [0, 1], "Lint task should execute without errors"


def test_type_task_executes():
    """Test that the type checking task can be executed."""
    result = subprocess.run(
        [sys.executable, "-m", "poethepoet", "type"],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )

    # Should pass or fail, but not error out
    assert result.returncode in [0, 1], "Type task should execute without errors"


def test_test_task_executes():
    """Test that the test task can be executed."""
    # Use test:collect instead of test to avoid recursion
    # (test would run all tests including this one)
    result = subprocess.run(
        [sys.executable, "-m", "poethepoet", "test:collect"],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )

    # Should pass or fail, but not error out
    assert result.returncode in [0, 1], "Test collection task should execute without errors"
