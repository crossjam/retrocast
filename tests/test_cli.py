import sys
import tempfile
import types
from pathlib import Path

try:
    import platformdirs  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - fallback for test envs without dependency
    platformdirs = types.ModuleType("platformdirs")

    def _user_data_dir(app_name: str, app_author: str) -> str:  # noqa: ARG001 - signature per library
        return str(Path(tempfile.gettempdir()) / "retrocast-tests")

    platformdirs.user_data_dir = _user_data_dir  # type: ignore[attr-defined]
    sys.modules["platformdirs"] = platformdirs

try:
    import rich.console  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - fallback for test envs without dependency
    rich_module = types.ModuleType("rich")
    rich_console_module = types.ModuleType("rich.console")

    class _Console:  # noqa: D401 - simple stub
        """Console stub used for tests when Rich is unavailable."""

        def print(self, *args: object, **kwargs: object) -> None:  # noqa: D401
            """Pretend to print output."""

    rich_console_module.Console = _Console  # type: ignore[attr-defined]
    sys.modules["rich"] = rich_module
    sys.modules["rich.console"] = rich_console_module

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from click.testing import CliRunner

from retrocast.cli import cli


ABOUT_MESSAGE_SNIPPET = (
    "Retrocast saves your Overcast listening history and related metadata"
    " to a local SQLite database."
)


def test_cli_default_runs_about() -> None:
    runner = CliRunner()

    result = runner.invoke(cli)

    assert result.exit_code == 0
    assert ABOUT_MESSAGE_SNIPPET in result.output


def test_cli_about_command_explicit() -> None:
    runner = CliRunner()

    result = runner.invoke(cli, ["about"])

    assert result.exit_code == 0
    assert ABOUT_MESSAGE_SNIPPET in result.output
