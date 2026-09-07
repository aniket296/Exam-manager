import asyncio
import functools
import inspect
import logging
import time
from typing import Callable, Any, Type, Tuple

logger = logging.getLogger(__name__)

def retry_with_backoff(
    retries: int = 3,
    initial_delay: float = 0.5,
    backoff_factor: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    Decorator for retrying functions with exponential backoff.
    Works for both synchronous and asynchronous functions.
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                delay = initial_delay
                last_exc = None
                for attempt in range(1, retries + 1):
                    try:
                        return await func(*args, **kwargs)
                    except exceptions as e:
                        last_exc = e
                        logger.warning(
                            f"Attempt {attempt}/{retries} for {func.__name__} failed: {e}. Retrying in {delay}s..."
                        )
                        if attempt == retries:
                            break
                        await asyncio.sleep(delay)
                        delay *= backoff_factor
                raise last_exc
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                delay = initial_delay
                last_exc = None
                for attempt in range(1, retries + 1):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        last_exc = e
                        logger.warning(
                            f"Attempt {attempt}/{retries} for {func.__name__} failed: {e}. Retrying in {delay}s..."
                        )
                        if attempt == retries:
                            break
                        time.sleep(delay)
                        delay *= backoff_factor
                raise last_exc
            return sync_wrapper
    return decorator
