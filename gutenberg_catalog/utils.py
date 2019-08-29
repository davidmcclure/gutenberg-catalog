

import maya

from . import logger


class cached_property:

    @classmethod
    def safe(cls, func):
        return cls(func, True)

    def __init__(self, func, safe=False):
        self.__doc__ = getattr(func, "__doc__")
        self.func = func
        self.safe = safe

    def __get__(self, obj, cls):
        """Try to set a cached property. Catch and record errors.
        """
        if obj is None:
            return self

        try:
            # Replace function computed value.
            value = self.func(obj)
            obj.__dict__[self.func.__name__] = value
        except Exception as e:
            # If safe, log the error.
            if self.safe:
                logger.warn('%s | %s | %s' % (obj, self.func.__name__, e))
                value = None
            # Otherwise, throw the exception.
            else:
                raise

        return value


def parse_numeric(val):
    """Try to cast str -> int/float.

    Args:
        val (str)

    Returns: int|float|str
    """
    try: return int(val)
    except: pass

    try: return float(val)
    except: pass

    return val


def parse_datetime(val):
    """Try to cast str -> datetime.

    Args:
        val (str)

    Returns: datetime|str
    """
    try: return maya.parse(val).datetime()
    except: return val


def split_mime(text):
    return text.split(';')[0]
