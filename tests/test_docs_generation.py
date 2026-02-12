"""Tests for automated CLI documentation generation."""

import subprocess
import sys
from pathlib import Path


def test_docs_cli_directory_exists():
    """Test that docs/cli directory exists with documentation files."""
    docs_cli_dir = Path("docs/cli")
    assert docs_cli_dir.exists(), "docs/cli directory should exist"
    assert docs_cli_dir.is_dir(), "docs/cli should be a directory"

    # Check for key documentation files
    expected_files = [
        "README.md",
        "index.md",
        "about.md",
        "castchat.md",
        "config.md",
        "download.md",
        "meta.md",
        "sql.md",
        "sync.md",
        "transcription.md",
    ]

    for filename in expected_files:
        file_path = docs_cli_dir / filename
        assert file_path.exists(), f"{filename} should exist in docs/cli"
        assert file_path.is_file(), f"{filename} should be a file"


def test_cog_installed():
    """Test that cogapp package is available."""
    result = subprocess.run(
        [sys.executable, "-m", "cogapp", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, "cogapp should be installed and available"
    output = result.stdout + result.stderr
    assert "cog" in output.lower(), "cogapp help should mention cog"


def test_docs_check_command():
    """Test that docs:check poe task works (verifies docs are up to date)."""
    # Run the docs:check task
    result = subprocess.run(
        [sys.executable, "-m", "cogapp", "--check", "docs/cli/*.md"],
        capture_output=True,
        text=True,
        shell=True,
    )

    # The command should succeed if docs are up to date
    # Note: This test might fail if CLI help text changes but docs aren't regenerated
    assert (
        result.returncode == 0
    ), f"docs:check failed, documentation may be out of date: {result.stderr}"


def test_cog_directives_present():
    """Test that documentation files contain cog directives."""
    docs_cli_dir = Path("docs/cli")

    # Check a few key files for cog directives
    files_to_check = ["index.md", "config.md", "download.md"]

    for filename in files_to_check:
        file_path = docs_cli_dir / filename
        content = file_path.read_text()

        # Check for cog start marker
        assert "[[[cog" in content, f"{filename} should contain cog directives"

        # Check for cog end marker
        assert "[[[end]]]" in content, f"{filename} should contain cog end markers"

        # Check for CliRunner import
        assert (
            "from click.testing import CliRunner" in content
        ), f"{filename} should import CliRunner"

        # Check for cli import
        assert (
            "from retrocast.cli import cli" in content
        ), f"{filename} should import cli"


def test_generated_help_present():
    """Test that generated help text is present in documentation."""
    docs_cli_dir = Path("docs/cli")
    index_path = docs_cli_dir / "index.md"

    content = index_path.read_text()

    # Check for expected CLI content
    assert "Usage:" in content, "Generated help should include Usage"
    assert "Commands:" in content, "Generated help should include Commands"
    assert "Options:" in content, "Generated help should include Options"


def test_all_command_groups_documented():
    """Test that all main command groups have documentation files."""
    docs_cli_dir = Path("docs/cli")

    # These are the main command groups from the CLI
    command_groups = [
        "about",
        "castchat",
        "config",
        "download",
        "meta",
        "sql",
        "sync",
        "transcription",
    ]

    for command in command_groups:
        doc_file = docs_cli_dir / f"{command}.md"
        assert (
            doc_file.exists()
        ), f"Documentation file {command}.md should exist for {command} command"
