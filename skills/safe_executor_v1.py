"""Error handling: safe function execution"""

def safe_executor(func: Callable, *args, default_value: Any = None, **kwargs) -> Any:
    """
    Execute function with exception handling.

    Args:
        func: Function to execute
        *args: Function arguments
        default_value: Value to return on error
        **kwargs: Function keyword arguments

    Returns:
        Function result or default_value on error
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Error executing {func.__name__}: {e}")
        return default_value
