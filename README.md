# 😈 What the heck?
aioGo is the tiny helper library that doing two simple thinks: 
- run your async code

and
- correct terminate your async code

Default python asyncio have troubles with this: when you hit Ctrl+C asyncio just cancel all your coroutines.

This can lead to many race conditions and hanging your application at exit point.

# 📘 How to use?

Install from pypi:

```shell
pip install aiogo
```

or, if you prefer poetry:

```shell
poetry add aiogo
```

And just:

```python
from asyncio import Future
from aiogo import go

async def main(termination: Future[None]) -> None:
    await termination

if __name__ == "__main__":
    go(main)
```

That's all. You just wait while termination future was resolved (when your application got SIGINT or SIGTERM).

When you will be use this library in real world, just: 
```python
from asyncio import Future, wait, FIRST_COMPLETED, get_running_loop

async def main(termination: Future[None]) -> None:
    your_awesome_read_task = get_running_loop().create_future()
    done, _ = wait((termination, your_awesome_read_task), return_when=FIRST_COMPLETED)
```
and check done set.

## I want custom event loop (uvloop)!
That I have! Again, just:

```python
from asyncio import Future

import uvloop  # noqa
from aiogo import go

async def main(termination: Future[None]) -> None:
    ...

go(main, event_loop_factory=uvloop.new_event_loop)
```

## I want forced exit!
If you can't write correct exit behaviour, well... Do that:

```python
from asyncio import Future

from aiogo import go

async def main(termination: Future[None]) -> None:
    ...

go(main, exit_timeout=10)
```
And all your coroutines will be got CancelledError, as doing old good asyncio.run.


## I want use threads inside my async application

If you needed, you can make your own pool executor to use it as default executor, like this:

```python
from asyncio import Future
from concurrent.futures import ThreadPoolExecutor

from aiogo import go

async def main(termination: Future[None]) -> None:
    ...


with ThreadPoolExecutor() as pool_executor:
    go(main, default_executor=pool_executor)
```

_Warning! Passed pool will be closed after main routine was has been terminated_


## I want pass additionally argument to my main coroutine

Just use functools.partial method to bind coroutine to arguments

```python
from asyncio import Future
from functools import partial
from aiogo import go

async def main(terminate: Future[None], value: int) -> None:
    await terminate

go(partial(main, value=42))
```

BTW any value, that you return from main coroutine will be returned from go function.

# 🌎 Hot to contribute?
- Make a repository fork
- Apply your changes (don't forget install pre-commit before making commit)
- Make a pull request
