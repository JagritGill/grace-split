"""Strict bounded JSON from a stable regular local file."""
import json
import os
import stat
from .core import InputError

MAX_BYTES = 32768


def _object(items):
    result = {}
    for key, value in items:
        if key in result:
            raise InputError('duplicate JSON object key')
        result[key] = value
    return result


def _constant(_):
    raise InputError('non-finite JSON value')


def load(path):
    try:
        if stat.S_ISLNK(os.lstat(path).st_mode):
            raise InputError('input must not be a symlink')
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, 'O_NOFOLLOW', 0))
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
                raise InputError('input must be a regular file of at most 32768 bytes')
            data = stream.read(MAX_BYTES+1)
        if len(data) > MAX_BYTES:
            raise InputError('input exceeds 32768 bytes')
        return json.loads(data.decode('utf-8'), object_pairs_hook=_object, parse_constant=_constant)
    except InputError:
        raise
    except (OSError, ValueError, RecursionError) as exc:
        raise InputError('cannot read bounded UTF-8 JSON') from exc
