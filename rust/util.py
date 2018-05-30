"""General utilities used by the Rust package."""

import sublime
import textwrap
import threading
import time
import os


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


def get_rustc_version(window, cwd, toolchain=None):
    """Returns the rust version for the given directory.

    :Returns: A string such as '1.16.0' or '1.17.0-nightly'.
    """
    from . import rust_proc
    cmd = ['rustc']
    if toolchain:
        cmd.append('+' + toolchain)
    cmd.append('--version')
    output = rust_proc.check_output(window, cmd, cwd)
    # Example outputs:
    # rustc 1.15.1 (021bd294c 2017-02-08)
    # rustc 1.16.0-beta.2 (bc15d5281 2017-02-16)
    # rustc 1.17.0-nightly (306035c21 2017-02-18)
    return output.split()[1]


def find_cargo_manifest(path):
    """Find the Cargo.toml file in the given path, or any of its parents.

    :Returns: The path where Cargo.toml is found, or None.
    """
    path = os.path.normpath(path)
    if os.path.isfile(path):
        path = os.path.dirname(path)
    while True:
        manifest = os.path.join(path, 'Cargo.toml')
        if os.path.exists(manifest):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            return None
        path = parent


def active_view_is_rust(window=None, view=None):
    """Determine if the current view is a Rust source file.

    :param window: The Sublime window (defaults to active window).
    :param view: The view to check (defaults to active view).

    :Returns: True if it is a Rust source file, False if not.
    """
    if view is None:
        if window is None:
            window = sublime.active_window()
        view = window.active_view()
    if not view:
        return False
    # Require it to be saved to disk.
    if not view.file_name():
        return False
    return 'source.rust' in view.scope_name(0)


def get_cargo_metadata(window, cwd, toolchain=None):
    """Load Cargo metadata.

    :returns: None on failure, otherwise a dictionary from Cargo:
        - packages: List of packages:
            - name
            - manifest_path: Path to Cargo.toml.
            - targets: List of target dictionaries:
                - name: Name of target.
                - src_path: Path of top-level source file.  May be a
                  relative path.
                - kind: List of kinds.  May contain multiple entries if
                  `crate-type` specifies multiple values in Cargo.toml.
                  Lots of different types of values:
                    - Libraries: 'lib', 'rlib', 'dylib', 'cdylib', 'staticlib',
                      'proc-macro'
                    - Executables: 'bin', 'test', 'example', 'bench'
                    - build.rs: 'custom-build'

    :raises ProcessTermiantedError: Process was terminated by another thread.
    """
    from . import rust_proc
    cmd = ['cargo']
    if toolchain:
        cmd.append('+' + toolchain)
    cmd.extend(['metadata', '--no-deps'])
    output = rust_proc.slurp_json(window,
                                  cmd,
                                  cwd=cwd)
    if output:
        return output[0]
    else:
        return None


def icon_path(level, res=None):
    """Return a path to a message-level icon."""
    if level not in ('error', 'warning', 'note', 'help', 'none'):
        return ''
    gutter_style = get_setting('rust_gutter_style', 'shape')
    package_name = __package__.split('.')[0]
    if gutter_style == 'none':
        return ''
    else:
        if res:
            res_suffix = '@%ix' % (res,)
        else:
            res_suffix = ''
        return 'Packages/%s/images/gutter/%s-%s%s.png' % (
            package_name, gutter_style, level, res_suffix)
