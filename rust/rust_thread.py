"""Manage threads used for running Rust processes."""

from . import util, rust_proc

import sublime
import threading

# Map Sublime window ID to RustThread.
THREADS = {}
THREADS_LOCK = threading.Lock()


class RustThread(object):

    """A thread for running Rust processes.

    Subclasses should implement run to define the code to run.

    Subclasses should check `should_exit` around any long-running steps.
    """

    # threading.Thread instance
    thread = None
    # If this is true, then it is OK to kill this thread to start a new one.
    silently_interruptible = True
    # Set to True when the thread should terminate.
    should_exit = False
    # Sublime window this thread is attached to.
    window = None
    # Name of the thread.
    name = None

    def __init__(self, window):
        self.window = window

    def start(self):
        """Start the thread."""
        self.thread = threading.Thread(name=self.name,
            target=self._thread_run)
        self.thread.start()

    @property
    def current_proc(self):
        """The current `RustProc` being executed by this thread, or None."""
        return rust_proc.PROCS.get(self.window.id(), None)

    def describe(self):
        """Returns a string with the name of the thread."""
        p = self.current_proc
        if p:
            return '%s: %s' % (self.name, ' '.join(p.cmd))
        else:
            return self.name

    def _thread_run(self):
        # Determine if this thread is allowed to run.
        while True:
            with THREADS_LOCK:
                t = THREADS.get(self.window.id(), None)
                if not t or not t.is_alive():
                    THREADS[self.window.id()] = self
                    break

            # Another thread is already running for this window.
            if t.should_exit:
                t.join()
            elif t.silently_interruptible:
                t.terminate()
                t.join()
            elif self.silently_interruptible:
                # Never allowed to interrupt.
                return
            else:
                # Neither is interruptible (the user started a Build
                # while one is already running).
                msg = """
                    Rust Build

                    The following Rust command is still running, do you want to cancel it?
                    %s""" % self.describe()
                if sublime.ok_cancel_dialog(util.multiline_fix(msg),
                                            'Stop Running Command'):
                    t.terminate()
                    t.join()
                else:
                    # Allow the original process to finish.
                    return
            # Try again.

        try:
            self.run()
        finally:
            with THREADS_LOCK:
                t = THREADS.get(self.window.id(), None)
                if t is self:
                    del THREADS[self.window.id()]

    def run(self):
        raise NotImplementedError()

    def terminate(self):
        """Asks the thread to exit.

        If the thread is running a process, the process will be killed.
        """
        self.should_exit = True
        p = self.current_proc
        if p and not p.finished:
            p.terminate()

    def is_alive(self):
        return self.thread.is_alive()

    def join(self, timeout=None):
        return self.thread.join(timeout=timeout)
