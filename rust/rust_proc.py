"""Module for running cargo or rustc and parsing the output.

It is assumed a thread only ever has one process running at a time.
"""

import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
import shellenv

from . import util

# Map Sublime window ID to RustProc.
PROCS = {}
PROCS_LOCK = threading.Lock()

# Environment (as s dict) from the user's login shell.
USER_SHELL_ENV = None


class ProcessTerminatedError(Exception):
    """Process was terminated by another thread."""


class ProcListener(object):

    """Listeners are used to handle output events while a process is
    running."""

    def on_begin(self, proc):
        """Called just before the process is started."""
        pass

    def on_data(self, proc, data):
        """A line of text output by the process."""
        pass

    def on_error(self, proc, message):
        """Called when there is an error, such as failure to decode utf-8."""
        print('Rust Error: %s' % message)

    def on_json(self, proc, obj):
        """Parsed JSON output from the command."""
        pass

    def on_finished(self, proc, rc):
        """Called after all output has been processed."""
        pass

    def on_terminated(self, proc):
        """Called when the process is terminated by another thread.  Note that
        the process may still be running."""
        pass


class SlurpListener(ProcListener):

    def on_begin(self, proc):
        self.json = []
        self.data = []

    def on_json(self, proc, obj):
        self.json.append(obj)

    def on_data(self, proc, data):
        self.data.append(data)


def _slurp(window, cmd, cwd):
    p = RustProc()
    listener = SlurpListener()
    p.run(window, cmd, cwd, listener)
    rc = p.wait()
    return (rc, listener)


def slurp_json(window, cmd, cwd):
    """Run a command and return the JSON output from it.

    :param window: Sublime window.
    :param cmd: The command to run (list of strings).
    :param cwd: The directory where to run the command.

    :returns: List of parsed JSON objects.

    :raises ProcessTermiantedError: Process was terminated by another thread.
    """
    rc, listener = _slurp(window, cmd, cwd)
    if not listener.json and rc:
        print('Failed to run: %s' % cmd)
        print(''.join(listener.data))
    return listener.json


def check_output(window, cmd, cwd):
    """Run a command and return the text output from it.

    :param window: Sublime window.
    :param cmd: The command to run (list of strings).
    :param cwd: The directory where to run the command.

    :returns: A string of the command's output.

    :raises ProcessTermiantedError: Process was terminated by another thread.
    :raises subprocess.CalledProcessError: The command returned a nonzero exit
        status.
    """
    rc, listener = _slurp(window, cmd, cwd)
    output = ''.join(listener.data)
    if rc:
        raise subprocess.CalledProcessError(rc, cmd, output)
    return output


class RustProc(object):

    """Launches and controls a subprocess."""

    # Set to True when the process is finished running.
    finished = False
    # Set to True if the process was forcefully terminated.
    terminated = False
    # Command to run as a list of strings.
    cmd = None
    # The directory where the command is being run.
    cwd = None
    # Environment dictionary used in the child.
    env = None
    # subprocess.Popen object
    proc = None
    # Time when the process was started.
    start_time = None
    # Number of seconds it took to run.
    elapsed = None
    # The thread used for reading output.
    _stdout_thread = None

    def run(self, window, cmd, cwd, listener, env=None,
            decode_json=True, json_stop_pattern=None):
        """Run the process.

        :param window: Sublime window.
        :param cmd: The command to run (list of strings).
        :param cwd: The directory where to run the command.
        :param listener: `ProcListener` to receive the output.
        :param env: Dictionary of environment variables to add.
        :param decode_json: If True, will check for lines starting with `{` to
            decode as a JSON message.
        :param json_stop_pattern: Regular expression used to detect when it
            should stop looking for JSON messages.  This is used by `cargo
            run` so that it does not capture output from the user's program
            that might start with an open curly brace.

        :raises ProcessTermiantedError: Process was terminated by another
            thread.
        """
        self.cmd = cmd
        self.cwd = cwd
        self.listener = listener
        self.start_time = time.time()
        self.window = window
        self.decode_json = decode_json
        self.json_stop_pattern = json_stop_pattern

        from . import rust_thread
        try:
            t = rust_thread.THREADS[window.id()]
        except KeyError:
            pass
        else:
            if t.should_exit:
                raise ProcessTerminatedError()

        with PROCS_LOCK:
            PROCS[window.id()] = self
        listener.on_begin(self)

        # Configure the environment.
        self.env = os.environ.copy()
        if util.get_setting('rust_include_shell_env', True):
            global USER_SHELL_ENV
            if USER_SHELL_ENV is None:
                USER_SHELL_ENV = shellenv.get_env()[1]
            self.env.update(USER_SHELL_ENV)

        rust_env = util.get_setting('rust_env')
        if rust_env:
            for k, v in rust_env.items():
                rust_env[k] = os.path.expandvars(v)
            self.env.update(rust_env)

        if env:
            self.env.update(env)

        # XXX: Debug config.
        util.debug('Rust running: %s', self.cmd)

        if sys.platform == 'win32':
            # Prevent a console window from popping up.
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            self.proc = subprocess.Popen(
                self.cmd,
                cwd=self.cwd,
                env=self.env,
                startupinfo=startupinfo,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
        else:
            # Make the process the group leader so we can easily kill all its
            # children.
            self.proc = subprocess.Popen(
                self.cmd,
                cwd=self.cwd,
                preexec_fn=os.setpgrp,
                env=self.env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )

        self._stdout_thread = threading.Thread(target=self._read_stdout,
            name='%s: Stdout' % (threading.current_thread().name,))
        self._stdout_thread.start()

    def terminate(self):
        """Kill the process.

        Termination may not happen immediately.  Use wait() if you need to
        ensure when it is finished.
        """
        if self.finished:
            return
        self.finished = True
        self.terminated = True
        if sys.platform == 'win32':
            # Use taskkill to kill the entire tree (terminate only kills top
            # process).
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            # /T - Kill tree
            # /F - Force kill
            subprocess.Popen(
                'taskkill /T /F /PID ' + str(self.proc.pid),
                startupinfo=startupinfo)
        else:
            # Must kill the entire process group.  The rustup wrapper won't
            # forward the signal to cargo, and cargo doesn't forward signals
            # to any processes it spawns.
            os.killpg(os.getpgid(self.proc.pid), signal.SIGTERM)
        # stdout reader should catch the end of the stream and perform
        # cleanup.
        self.listener.on_terminated(self)

    def wait(self):
        """Wait for the process to finish.

        :return: The returncode of the process.

        :raises ProcessTerminatedError: Process was interrupted by another
            thread.
        """
        # stdout_thread is responsible for cleanup, setting `finished`, etc.
        if self._stdout_thread:
            self._stdout_thread.join()
        rc = self.proc.wait()
        if self.terminated:
            raise ProcessTerminatedError()
        return rc

    def _read_stdout(self):
        while True:
            line = self.proc.stdout.readline()
            if not line:
                rc = self._cleanup()
                self.listener.on_finished(self, rc)
                break
            try:
                line = line.decode('utf-8')
            except:
                self.listener.on_error(self,
                    '[Error decoding UTF-8: %r]' % line)
                continue
            if self.decode_json and line.startswith('{'):
                try:
                    result = json.loads(line)
                except:
                    self.listener.on_error(self,
                        '[Error loading JSON from rust: %r]' % line)
                else:
                    try:
                        self.listener.on_json(self, result)
                    except:
                        self._cleanup()
                        raise
            else:
                print('Checking pattern %r to line %r' % (self.json_stop_pattern, line))
                if self.json_stop_pattern and \
                        re.match(self.json_stop_pattern, line):
                    # Stop looking for JSON open curly bracket.
                    self.decode_json = False
                # Sublime always uses \n internally.
                line = line.replace('\r\n', '\n')
                self.listener.on_data(self, line)

    def _cleanup(self):
        self.elapsed = time.time() - self.start_time
        self.finished = True
        self._stdout_thread = None
        self.proc.stdout.close()
        rc = self.proc.wait()
        with PROCS_LOCK:
            p = PROCS[self.window.id()]
            if p is self:
                del PROCS[self.window.id()]
        return rc
