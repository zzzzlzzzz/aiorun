# 😈 What the heck?
aioGo is the tiny helper library that doing two simple thinks: 
- run your async code

and
- correct terminate your async code

Default python asyncio have troubles with this: when you hit Ctrl+C asyncio just cancel all your coroutines.

This can lead to many race conditions and hanging your application at exit point.

# 📘 How to use?

Just:

```python
from asyncio import Future
from aiogo import go

async def main(termination: Future[bool]) -> None:
    await termination

if __name__ == "__main__":
    go(main)
```

That's all. You just wait while termination future was resolved (when your application got SIGINT or SIGTERM).

When you will be use this library in real world, just: 
```python
import asyncio

async def main(termination: asyncio.Future[bool]) -> None:
    done, _ = asyncio.wait((termination, your_awesome_read_task), return_when=asyncio.FIRST_COMPLETED)
```
and check done set.

## I want custom event loop (uvloop)!
That I have! Again, just:

```python
import uvloop
from aiogo import go

go(main, event_loop_factory=uvloop.new_event_loop)
```

## I want forced exit!
If you can't write correct exit behaviour, well... Do that:

```python
from aiogo import go
go(main, exit_timeout=10)
```
And all your coroutines will be got CancelledError, as doing old good asyncio.run.