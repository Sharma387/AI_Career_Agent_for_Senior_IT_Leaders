"""
Utility functions for web scraping operations.
"""
import asyncio
import random
import time
from typing import Any, Callable, TypeVar, Awaitable

T = TypeVar('T')


async def retry_with_exponential_backoff(
    func: Callable[..., Awaitable[T]],
    *args,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    **kwargs
) -> T:
    """
    Retry a function with exponential backoff.

    Args:
        func: Async function to retry
        *args: Arguments to pass to func
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        jitter: Whether to add random jitter to delay
        **kwargs: Keyword arguments to pass to func

    Returns:
        Result of func if successful

    Raises:
        Exception: If all retries are exhausted
    """
    num_retries = 0
    delay = base_delay

    while True:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            num_retries += 1
            if num_retries > max_retries:
                raise e

            # Calculate delay with exponential backoff
            delay = min(base_delay * (exponential_base ** (num_retries - 1)), max_delay)

            # Add jitter if enabled
            if jitter:
                delay *= (0.5 + random.random() * 0.5)  # jitter between 0.5 and 1.0

            # Wait before retrying
            await asyncio.sleep(delay)


def add_rate_limiting_delay(last_request_time: float, min_interval: float = 1.0) -> float:
    """
    Calculate and apply rate limiting delay.

    Args:
        last_request_time: Timestamp of last request
        min_interval: Minimum interval between requests in seconds

    Returns:
        Time to sleep before next request
    """
    elapsed = time.time() - last_request_time
    if elapsed < min_interval:
        return min_interval - elapsed
    return 0.0


def extract_text_safely(element, default: str = "") -> str:
    """
    Safely extract text from a BeautifulSoup element.

    Args:
        element: BeautifulSoup element
        default: Default value if element is None or has no text

    Returns:
        Text content or default value
    """
    if element is None:
        return default
    text = element.get_text(strip=True)
    return text if text else default


def extract_attribute_safely(element, attribute: str, default: str = "") -> str:
    """
    Safely extract attribute from a BeautifulSoup element.

    Args:
        element: BeautifulSoup element
        attribute: Attribute name to extract
        default: Default value if element is None or attribute missing

    Returns:
        Attribute value or default
    """
    if element is None:
        return default
    value = element.get(attribute, default)
    return value if value is not None else default


def build_url_with_params(base_url: str, params: dict) -> str:
    """
    Build URL with query parameters.

    Args:
        base_url: Base URL
        params: Dictionary of query parameters

    Returns:
        URL with query parameters
    """
    from urllib.parse import urlencode

    # Filter out None values
    filtered_params = {k: v for k, v in params.items() if v is not None}

    if not filtered_params:
        return base_url

    query_string = urlencode(filtered_params)
    separator = '&' if '?' in base_url else '?'
    return f"{base_url}{separator}{query_string}"