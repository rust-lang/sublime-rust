"""Tests to exercise interrupting rust threads."""

import sublime

import glob
import os
import time
import types
from rust_test_common import *


pattern = os.path.normpath(
    os.path.join(plugin_path, 'tests/slow-build/test-build'))


class TestInterrupt(TestBase):

    def setUp(self):
        super(TestInterrupt, self).setUp()
        self._cleanup()
        self.terminated = []

    def tearDown(self):
        super(TestInterrupt, self).tearDown()
        self._cleanup()

    def _cleanup(self):
        [os.unlink(x) for x in self._files()]

    def _wrap_terminate(self, r_thread):
        """Add wrapper around RustProc.terminate() to catch when it is
        terminated."""
        def terminate(s):
            self.terminated.append(s)
            return r_thread.__class__.terminate(s)
        r_thread.terminate = types.MethodType(terminate, r_thread)

    def test_slow_check(self):
        """Test interrupting syntax check.

        This works by launching a thread to start the test, waiting 1 second,
        then launching another thread which should interrupt the first.

        The slow-build crate has a build.rs which forces the build to take
        about 3 seconds to complete.

        Unfortunately there is not a simple way to check if the build process
        is running, so it just drops some files (like "test-build-start-#") to
        indicate that it started and stopped.  Not perfect, but it should
        work.

        This test is sensitive to timings, so it may fail on a slow/busy
        computer.  If it's a problem, the sleeps can be made longer.
        """
        self._with_open_file('tests/slow-build/src/lib.rs',
            self._test_slow_check)

    def _test_slow_check(self, view):
        self._cargo_clean(view)

        # Keep track of when a thread is terminated.
        t1 = plugin.SyntaxCheckPlugin.RustSyntaxCheckThread(view)
        t2 = plugin.SyntaxCheckPlugin.RustSyntaxCheckThread(view)
        self._wrap_terminate(t1)
        self._wrap_terminate(t2)

        # Start the syntax check threads.
        t1.start()

        self._wait_for_start()
        start = time.time()

        # Start a new thread to interrupt the first.
        t2.start()
        # Let the thread spin up.
        time.sleep(0.5)
        self.assertFalse(t1.is_alive())
        t1.join()
        t2.join()
        duration = time.time() - start
        self.assertAlmostEqual(duration, 4.0, delta=1.0)
        self.assertEqual(self.terminated, [t1])
        self.assertEqual(self._files(),
            [pattern + '-start-1',
             pattern + '-start-2',
             pattern + '-end-1'])

    def test_build_cancel(self):
        """Test manually canceling a build."""
        # So it doesn't hide the UnitTest output panel.
        self._with_open_file('tests/slow-build/src/lib.rs',
            self._test_build_cancel)

    def _test_build_cancel(self, view):
        self._cargo_clean(view)
        window = view.window()
        self._run_build()
        self._wait_for_start()
        t = self._get_rust_thread()
        self._wrap_terminate(t)
        window.run_command('rust_cancel')
        # Sleep long enough to make sure the build didn't continue running.
        time.sleep(4)
        self.assertEqual(self.terminated, [t])
        # Start, but no end.
        self.assertEqual(self._files(), [pattern + '-start-1'])

    def test_syntax_check_cancel(self):
        """Test manually canceling syntax check."""
        self._with_open_file('tests/slow-build/src/lib.rs',
            self._test_syntax_check_cancel)

    def _test_syntax_check_cancel(self, view):
        self._cargo_clean(view)
        t = plugin.SyntaxCheckPlugin.RustSyntaxCheckThread(view)
        self._wrap_terminate(t)
        t.start()
        self._wait_for_start()
        view.window().run_command('rust_cancel')
        # Sleep long enough to make sure the build didn't continue running.
        time.sleep(4)
        self.assertEqual(self.terminated, [t])
        # Start, but no end.
        self.assertEqual(self._files(), [pattern + '-start-1'])

    def test_syntax_check_while_build(self):
        """Test starting a syntax check while build is running."""
        self._with_open_file('tests/slow-build/src/lib.rs',
            self._test_syntax_check_while_build)

    def _test_syntax_check_while_build(self, view):
        self._cargo_clean(view)
        self._run_build()
        self._wait_for_start()
        build_t = self._get_rust_thread()
        self._wrap_terminate(build_t)
        # Start a syntax check, it should not be allowed to proceed.
        check_t = plugin.SyntaxCheckPlugin.RustSyntaxCheckThread(view)
        self._wrap_terminate(check_t)
        # This thread will silently exit without running.
        check_t.start()
        time.sleep(4)
        self.assertEqual(self.terminated, [])
        self.assertEqual(self._files(),
            [pattern + '-start-1',
             pattern + '-end-1'])

    def test_build_while_syntax_check(self):
        """Test starting a build while a syntax check is running."""
        self._with_open_file('tests/slow-build/src/lib.rs',
            self._test_build_while_syntax_check)

    def _test_build_while_syntax_check(self, view):
        self._cargo_clean(view)
        check_t = plugin.SyntaxCheckPlugin.RustSyntaxCheckThread(view)
        self._wrap_terminate(check_t)
        check_t.start()
        self._wait_for_start()
        # Should silently kill the syntax check thread.
        self._run_build()
        build_t = self._get_rust_thread()
        self._wrap_terminate(build_t)
        time.sleep(4)
        self.assertEqual(self.terminated, [check_t])
        self.assertEqual(self._files(),
            [pattern + '-start-1',
             pattern + '-start-2',
             pattern + '-end-1'])

    def test_build_with_save(self):
        """Test starting a build with a dirty file."""
        self._with_open_file('tests/slow-build/src/lib.rs',
            self._test_build_with_save)

    def _test_build_with_save(self, view):
        self._cargo_clean(view)
        # Trigger on_save for syntax checking.
        view.run_command('save')
        # Doing this immediately afterwards should cancel the syntax check
        # before it gets a chance to do much.
        self._run_build()
        build_t = self._get_rust_thread()
        self._wrap_terminate(build_t)
        time.sleep(4)
        self.assertEqual(self._files(),
            [pattern + '-start-1',
             pattern + '-end-1'])
        # Clear dirty flag so that closing the view does not pop up a
        # confirmation box.
        view.run_command('revert')

    def test_concurrent_build(self):
        """Test starting builds at the same time."""
        self._with_open_file('tests/slow-build/src/lib.rs',
            self._test_concurrent_build)

    def _test_concurrent_build(self, view):
        ok_value = True

        def ok_cancel_dialog(msg, ok_title=None):
            return ok_value

        orig_ok_cancel_dialog = sublime.ok_cancel_dialog
        sublime.ok_cancel_dialog = ok_cancel_dialog
        try:
            self._cargo_clean(view)
            self._run_build()
            self._wait_for_start()
            build_t = self._get_rust_thread()
            self._wrap_terminate(build_t)
            # Start a second build.
            self._run_build()
            time.sleep(1)
            self.assertEqual(self.terminated, [build_t])
            # Start again, but hit cancel.
            ok_value = False
            self._run_build()
            time.sleep(4)
            # Should not have interrupted.
            self.assertEqual(self.terminated, [build_t])
            self.assertEqual(self._files(),
                [pattern + '-start-1',
                 pattern + '-start-2',
                 pattern + '-end-1'])
        finally:
            sublime.ok_cancel_dialog = orig_ok_cancel_dialog

    def _wait_for_start(self):
        for _ in range(50):
            time.sleep(0.1)
            if self._files() == [pattern + '-start-1']:
                break
        else:
            raise AssertionError('Did not catch initial start: %r' % (
                self._files(),))

    def _files(self):
        files = glob.glob(pattern + '-*')
        files.sort(key=os.path.getctime)
        return files
