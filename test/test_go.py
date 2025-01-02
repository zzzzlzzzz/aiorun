import asyncio as a
import functools as f
import signal as s
import logging as l
import time as tm

from aiogo import go
import pytest


@pytest.mark.parametrize("signal_num", (s.SIGINT, s.SIGTERM))
def test_go_exit_success(caplog, signal_num) -> None:
    a_arg_value = 1
    b_arg_value = "xoxo"
    alive_delay = 1
    alive_offset = 0.5
    cancelled_task: a.Task | None = None

    async def main_task(
        termination: a.Future[bool],
        a_arg: int,
        b_arg: str = "mmmm",
    ) -> None:
        nonlocal cancelled_task
        assert a_arg == a_arg_value and b_arg == b_arg_value

        async def terminate() -> None:
            await a.sleep(alive_delay)
            s.getsignal(signal_num)(signal_num, None)

        async def cancelled() -> None:
            await a.sleep(1000)

        terminate_task = a.create_task(terminate())
        cancelled_task = a.create_task(cancelled())
        await terminate_task
        await termination

    with caplog.at_level(l.ERROR):
        run_at = tm.monotonic()
        go(f.partial(main_task, a_arg=a_arg_value, b_arg=b_arg_value))
        assert (
            (alive_delay - alive_offset)
            <= tm.monotonic() - run_at
            <= (alive_delay + alive_offset)
        )
    assert len(caplog.records) == 0
    assert cancelled_task.cancelled()


@pytest.mark.parametrize("signal_num", (s.SIGINT, s.SIGTERM))
def test_go_exit_with_some_delay_success(caplog, signal_num) -> None:
    a_arg_value = 1
    b_arg_value = "xoxo"
    alive_delay = 1
    alive_offset = 0.5

    async def main_task(
        termination: a.Future[bool],
        a_arg: int,
        b_arg: str = "mmmm",
    ) -> None:
        assert a_arg == a_arg_value and b_arg == b_arg_value

        async def terminate() -> None:
            await a.sleep(alive_delay)
            s.getsignal(signal_num)(signal_num, None)

        terminate_task = a.create_task(terminate())
        await terminate_task
        await termination
        await a.sleep(alive_delay)

    with caplog.at_level(l.ERROR):
        run_at = tm.monotonic()
        go(f.partial(main_task, a_arg=a_arg_value, b_arg=b_arg_value))
        assert (
            (2 * alive_delay - alive_offset)
            <= tm.monotonic() - run_at
            <= (2 * alive_delay + alive_offset)
        )
    assert len(caplog.records) == 0


@pytest.mark.parametrize("signal_num", (s.SIGINT, s.SIGTERM))
def test_go_exit_success_without_wait_termination(caplog, signal_num) -> None:
    a_arg_value = 1
    b_arg_value = "xoxo"

    async def main_task(
        termination: a.Future[bool],
        a_arg: int,
        b_arg: str = "mmmm",
    ) -> None:
        assert a_arg == a_arg_value and b_arg == b_arg_value

    with caplog.at_level(l.ERROR):
        go(f.partial(main_task, a_arg=a_arg_value, b_arg=b_arg_value))
    assert len(caplog.records) == 0


@pytest.mark.parametrize("signal_num", (s.SIGINT, s.SIGTERM))
def test_go_exit_with_some_delay_exception(caplog, signal_num) -> None:
    a_arg_value = 1
    b_arg_value = "xoxo"
    alive_delay = 1
    alive_offset = 0.5

    async def main_task(
        termination: a.Future[bool],
        a_arg: int,
        b_arg: str = "mmmm",
    ) -> None:
        assert a_arg == a_arg_value and b_arg == b_arg_value

        async def terminate() -> None:
            await a.sleep(alive_delay)
            s.getsignal(signal_num)(signal_num, None)

        terminate_task = a.create_task(terminate())
        await terminate_task
        await termination
        raise ValueError()

    with caplog.at_level(l.ERROR):
        run_at = tm.monotonic()
        with pytest.raises(ValueError):
            go(f.partial(main_task, a_arg=a_arg_value, b_arg=b_arg_value))
        assert (
            (alive_delay - alive_offset)
            <= tm.monotonic() - run_at
            <= (alive_delay + alive_offset)
        )
    assert len(caplog.records) == 0


@pytest.mark.parametrize("signal_num", (s.SIGINT, s.SIGTERM))
def test_go_exit_with_some_delay_out_of_timeout(caplog, signal_num) -> None:
    a_arg_value = 1
    b_arg_value = "xoxo"
    alive_delay = 1
    alive_offset = 0.5

    async def main_task(
        termination: a.Future[bool],
        a_arg: int,
        b_arg: str = "mmmm",
    ) -> None:
        assert a_arg == a_arg_value and b_arg == b_arg_value

        async def terminate() -> None:
            await a.sleep(alive_delay)
            s.getsignal(signal_num)(signal_num, None)

        terminate_task = a.create_task(terminate())
        await terminate_task
        await termination
        await a.sleep(10 * alive_delay)

    with caplog.at_level(l.ERROR):
        run_at = tm.monotonic()
        go(
            f.partial(main_task, a_arg=a_arg_value, b_arg=b_arg_value),
            exit_timeout=alive_delay,
        )
        assert (
            (2 * alive_delay - alive_offset)
            <= tm.monotonic() - run_at
            <= (2 * alive_delay + alive_offset)
        )
    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == l.getLevelName(l.ERROR)
    assert "entrypoint out of timeout" in caplog.records[0].message
