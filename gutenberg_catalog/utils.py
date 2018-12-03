

import maya

from . import logger


class safe_property:

    @classmethod
    def cached(cls, func):
        return cls(func, True)

    def __init__(self, func, cached=False):
        self.cached = cached
        self.__doc__ = getattr(func, "__doc__")
        self.func = func

    def __get__(self, obj, cls):
        """Try to set a cached property. Catch and record errors.
        """
        if obj is None:
            return self

        try:
            value = self.func(obj)
        except Exception as e:
            logger.warn('%s | %s | %s' % (obj, self.func.__name__, e))
            value = None

        # Replace attribute with computed value.
        if self.cached:
            obj.__dict__[self.func.__name__] = value

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
