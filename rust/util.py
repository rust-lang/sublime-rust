"""General utilities used by the Rust package."""

import sublime
import textwrap
import threading
import time


def index_with(l, cb):
    """Find the index of a value in a sequence using a callback.

    :param l: The sequence to search.
    :param cb: Function to call, should return true if the given value matches
        what you are searching for.
    :returns: Returns the index of the match, or -1 if no match.
    """
    for i, v in enumerate(l):
        if cb(v):
            return i
    return -1


def multiline_fix(s):
    """Remove indentation from a multi-line string."""
    return textwrap.dedent(s).lstrip()


def get_setting(name, default=None):
    """Retrieve a setting from Sublime settings."""
    pdata = sublime.active_window().project_data()
    if pdata:
        v = pdata.get('settings', {}).get(name)
        if v is not None:
            return v
    settings = sublime.load_settings('RustEnhanced.sublime-settings')
    v = settings.get(name)
    if v is not None:
        return v
    settings = sublime.load_settings('Preferences.sublime-settings')
    # XXX: Also check "Distraction Free"?
    return settings.get(name, default)


_last_debug = time.time()


def debug(msg, *args):
    """Display a general debug message."""
    global _last_debug
    t = time.time()
    d = t - _last_debug
    _last_debug = t
    n = threading.current_thread().name
    print('%s +%.3f ' % (n, d), end='')
    print(msg % args)
