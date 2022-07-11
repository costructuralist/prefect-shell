import logging
import os

import pytest
from prefect import flow

from prefect_shell.commands import shell_run_command


def test_shell_run_command_error(caplog):
    @flow
    def test_flow():
        return shell_run_command(command="ls this/is/invalid")

    match = "No such file or directory"
    with pytest.raises(RuntimeError, match=match):
        test_flow().result(raise_on_failure=True)
    for record in caplog.records:
        if record.levelname == "ERROR":
            assert match in record


def test_shell_run_command():
    @flow
    def test_flow():
        return shell_run_command(command="echo work!")

    assert test_flow().result().result() == "work!"


def test_shell_run_command_stream_level(caplog):
    @flow
    def test_flow():
        return shell_run_command(
            command="echo work!",
            stream_level=logging.WARNING,
        )

    test_flow()
    for record in caplog.records:
        assert record.levelname == "DEBUG"


def test_shell_run_command_helper_command():
    @flow
    def test_flow():
        return shell_run_command(command="pwd", helper_command="cd $HOME")

    assert test_flow().result().result() == os.path.expandvars("$HOME")


def test_shell_run_command_return_all():
    @flow
    def test_flow():
        return shell_run_command(command="echo work! && echo yes!", return_all=True)

    assert test_flow().result().result() == ["work!", "yes!"]
