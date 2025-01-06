import asyncio as a
import typing as t
import types as ts
import contextlib as c
import signal as s
import concurrent.futures as fut


FutureValue = t.TypeVar("FutureValue")


def _safe_set_future_result(future: a.Future[FutureValue], value: FutureValue) -> None:
    if not future.done():
        future.set_result(value)


@c.contextmanager
def _event_loop(
    event_loop_factory: t.Callable[[], a.AbstractEventLoop],
) -> t.Generator[a.AbstractEventLoop, None, None]:
    event_loop = event_loop_factory()
    a.set_event_loop(event_loop)
    try:
        yield event_loop
    finally:
        a.set_event_loop(None)
        event_loop.close()


@c.contextmanager
def _register_signals(
    event_loop: a.AbstractEventLoop,
    termination: a.Future[None],
) -> t.Generator[None, None, None]:
    def _exit_handler(
        _signal_num: int,
        _frame: ts.FrameType | None,
    ) -> None:
        event_loop.call_soon(_safe_set_future_result, termination, None)

    def _restore_signal_handler(
        _signal_num: int,
        _previous_handler: t.Callable[[int, ts.FrameType | None], None] | int | None,
    ) -> None:
        s.signal(signalnum=_signal_num, handler=_previous_handler)

    with c.ExitStack() as signals:
        for signal_num in (s.SIGINT, s.SIGTERM):
            signals.callback(
                _restore_signal_handler,
                signal_num,
                s.signal(signalnum=signal_num, handler=_exit_handler),
            )
        yield


@c.contextmanager
def _setup_resources(
    event_loop: a.AbstractEventLoop,
    default_executor: fut.ThreadPoolExecutor | None,
) -> t.Generator[None, None, None]:
    if default_executor is not None:
        event_loop.set_default_executor(default_executor)
    try:
        yield
    finally:
        unstopped_tasks = a.all_tasks(event_loop)
        for task in unstopped_tasks:
            task.cancel()
        event_loop.run_until_complete(
            a.gather(*unstopped_tasks, return_exceptions=True)
        )
        for task in unstopped_tasks:
            if task.cancelled():
                continue
            if task.exception() is not None:
                event_loop.call_exception_handler(
                    {
                        "message": "unhandled exception during go() shutdown",
                        "exception": task.exception(),
                        "task": task,
                    }
                )
        event_loop.run_until_complete(event_loop.shutdown_asyncgens())
        event_loop.run_until_complete(event_loop.shutdown_default_executor())


class EntrypointProtocol(t.Protocol):
    def __call__(
        self, termination: a.Future[None]
    ) -> t.Coroutine[t.Any, t.Any, t.Any]: ...


def go(
    entrypoint: EntrypointProtocol,
    event_loop_factory: t.Callable[[], a.AbstractEventLoop] = a.new_event_loop,
    exit_timeout: float | None = None,
    default_executor: fut.ThreadPoolExecutor | None = None,
) -> t.Any:
    with _event_loop(event_loop_factory) as event_loop:
        termination: a.Future[None] = event_loop.create_future()
        with (
            _register_signals(
                event_loop=event_loop,
                termination=termination,
            ),
            _setup_resources(
                event_loop=event_loop,
                default_executor=default_executor,
            ),
        ):
            entrypoint_task = event_loop.create_task(
                entrypoint(termination=termination)
            )
            done, pending = event_loop.run_until_complete(
                a.wait((termination, entrypoint_task), return_when=a.FIRST_COMPLETED)
            )

            if termination in pending:
                event_loop.call_soon(_safe_set_future_result, termination, None)
            event_loop.run_until_complete(termination)

            if entrypoint_task in done:
                return event_loop.run_until_complete(entrypoint_task)
            else:
                try:
                    return event_loop.run_until_complete(
                        a.wait_for(fut=entrypoint_task, timeout=exit_timeout)
                    )
                except a.TimeoutError as error:
                    event_loop.call_exception_handler(
                        {
                            "message": "entrypoint out of timeout",
                            "exception": error,
                            "task": entrypoint_task,
                        }
                    )
