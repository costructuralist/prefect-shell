import glob
import logging
import os
import sys
from pathlib import Path

import pytest
from prefect import flow
from prefect.testing.utilities import AsyncMock

from prefect_shell.commands import shell_run_command

if sys.platform != "win32":
    pytest.skip(reason="see test_commands.py", allow_module_level=True)


def test_shell_run_command_error_windows(prefect_task_runs_caplog):
    @flow
    def test_flow():
        return shell_run_command(command="throw", return_all=True, shell="powershell")

    with pytest.raises(RuntimeError, match="Exception:"):
        test_flow()

    assert len(prefect_task_runs_caplog.records) == 0


def test_shell_run_command_windows(prefect_task_runs_caplog):
    prefect_task_runs_caplog.set_level(logging.INFO)
    echo_msg = "_THIS_ IS WORKING!!!!"

    @flow
    def test_flow():
        msg = shell_run_command(
            command=f"echo {echo_msg}", return_all=True, shell="powershell"
        )
        return " ".join(word.replace("\r", "") for word in msg)

    print(prefect_task_runs_caplog.text)

    assert test_flow() == echo_msg
    for record in prefect_task_runs_caplog.records:
        if echo_msg in record.msg:
            break  # it's in the records
    else:
        raise AssertionError


def test_shell_run_command_stream_level_windows(prefect_task_runs_caplog):
    prefect_task_runs_caplog.set_level(logging.WARNING)
    echo_msg = "_THIS_ IS WORKING!!!!"

    @flow
    def test_flow():
        msg = shell_run_command(
            command=f"echo {echo_msg}",
            stream_level=logging.WARNING,
            return_all=True,
            shell="powershell",
        )
        return " ".join(word.replace("\r", "") for word in msg)

    print(prefect_task_runs_caplog.text)

    assert test_flow() == echo_msg
    for record in prefect_task_runs_caplog.records:
        if echo_msg in record.msg:
            break  # it's in the records
    else:
        raise AssertionError


def test_shell_run_command_helper_command_windows():
    @flow
    def test_flow():
        return shell_run_command(
            command="Get-Location",
            helper_command="cd $env:USERPROFILE",
            shell="powershell",
        )

    assert test_flow() == os.path.expandvars("$USERPROFILE")


def test_shell_run_command_cwd():
    @flow
    def test_flow():
        return shell_run_command(
            command="Get-Location",
            shell="powershell",
            cwd=Path.home(),
        )

    assert test_flow() == os.fspath(Path.home())


def test_shell_run_command_return_all():
    @flow
    def test_flow():
        return shell_run_command(
            command="echo 'work!'; echo 'yes!'", return_all=True, shell="powershell"
        )

    result = test_flow()
    assert result[0].rstrip() == "work!"
    assert result[1].rstrip() == "yes!"


def test_shell_run_command_no_output_windows():
    @flow
    def test_flow():
        return shell_run_command(command="sleep 1", shell="powershell")

    assert test_flow() == ""


def test_shell_run_command_uses_current_env_windows():
    @flow
    def test_flow():
        return shell_run_command(
            command="echo $env:USERPROFILE", return_all=True, shell="powershell"
        )

    result = test_flow()
    assert result[0].rstrip() == os.environ["USERPROFILE"]


def test_shell_run_command_update_current_env_windows():
    @flow
    def test_flow():
        return shell_run_command(
            command="echo $env:USERPROFILE ; echo $env:TEST_VAR",
            helper_command="$env:TEST_VAR = 'test value'",
            env={"TEST_VAR": "test value"},
            return_all=True,
            shell="powershell",
        )

    result = test_flow()
    assert result[0] == os.environ["USERPROFILE"]
    assert result[1] == "test value"


def test_shell_run_command_ensure_suffix_ps1():
    @flow
    def test_flow():
        return shell_run_command(command="1 + 1", shell="powershell", extension=".zzz")

    result = test_flow()
    assert result == "2"


def test_shell_run_command_ensure_tmp_file_removed():
    @flow
    def test_flow():
        return shell_run_command(
            command="echo 'clean up after yourself!'", shell="powershell"
        )

    test_flow()
    temp_dir = os.environ["TEMP"]
    assert len(glob.glob(f"{temp_dir}\\prefect-*.ps1")) == 0


class AsyncIter:
    def __init__(self, items):
        self.items = items

    async def __aiter__(self):
        for item in self.items:
            yield item


@pytest.mark.parametrize("shell", [None, "powershell", "powershell.exe"])
def test_shell_run_command_override_shell(shell, monkeypatch):
    open_process_mock = AsyncMock()
    stdout_mock = AsyncMock()
    stdout_mock.receive.side_effect = lambda: b"received"
    open_process_mock.return_value.__aenter__.return_value = AsyncMock(
        stdout=stdout_mock
    )
    open_process_mock.return_value.__aenter__.return_value.returncode = 0
    monkeypatch.setattr("prefect_shell.commands.open_process", open_process_mock)
    monkeypatch.setattr("prefect_shell.commands.TextReceiveStream", AsyncIter)

    @flow
    def test_flow():
        return shell_run_command(
            command="echo 'testing'",
            shell=shell,
        )

    test_flow()
    assert open_process_mock.call_args_list[0][0][0][0] == shell or "powershell"
