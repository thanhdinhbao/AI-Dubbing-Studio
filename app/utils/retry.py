import time
import logging
from typing import Callable, Any, Tuple, Type

logger = logging.getLogger("AIDubbingStudio.Retry")


def retry_call(
    func: Callable[..., Any],
    args: Tuple = (),
    kwargs: dict = None,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Any:
    """Execute a function with exponential backoff retry logic."""
    if kwargs is None:
        kwargs = {}

    delay = initial_delay
    last_exception = None

    for attempt in range(1, max_retries + 1):
        try:
            return func(*args, **kwargs)
        except exceptions as e:
            last_exception = e
            if attempt == max_retries:
                logger.error(f"Attempt {attempt}/{max_retries} failed permanently: {e}")
                raise last_exception
            logger.warning(
                f"Attempt {attempt}/{max_retries} failed with {type(e).__name__}: {e}. Retrying in {delay:.1f}s..."
            )
            time.sleep(delay)
            delay *= backoff_factor

    if last_exception:
        raise last_exception

