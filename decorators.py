def index_list_arg(func):
    """Decorator that converts the string input into an index list"""
    def index_list_convert(*args, **kwargs):
        # only apply the conversion to the first positional
        args = (args[0].split(), *args[1:])
        func(*args, **kwargs)
    return index_list_convert

def ignore_arg(func):
    """Decorator that ignores the argument"""
    def wrapper_ignore_arg(*args, **kwargs):
        # preserve only self
        if args:
            args = (args[0],)
        func(*args, **kwargs)
    return wrapper_ignore_arg
