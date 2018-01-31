"""Tests for the context commands."""


from rust_test_common import *


class TestContext(TestBase):

    def test_pt_to_test_name(self):
        self._with_open_file('tests/multi-targets/tests/test_context.rs',
            self._test_pt_to_test_name)

    def _test_pt_to_test_name(self, view):
        expected = [
            ('test1', (3, 1), (7, 1)),
            ('expected_panic1', (8, 1), (15, 1)),
            ('test2', (16, 1), (22, 1)),
            ('test3', (22, 2), (26, 1)),
            ('test6', (36, 1), (39, 1)),
        ]
        for fn_name, (start_row, start_col), (end_row, end_col) in expected:
            start_pt = view.text_point(start_row - 1, start_col - 1)
            end_pt = view.text_point(end_row - 1, end_col - 1)
            for pt in range(start_pt, end_pt):
                name = plugin.cargo_build._pt_to_test_name('test', pt, view)
                self.assertEqual(name, fn_name,
                    'rowcol=%r' % (view.rowcol(pt),))

    def test_cargo_test_here(self):
        self._with_open_file('tests/multi-targets/tests/test_context.rs',
            self._test_cargo_test_here)

    def _test_cargo_test_here(self, view):
        pt = view.text_point(4, 0)
        x, y = view.text_to_window(pt)
        view.window().run_command('cargo_test_here', args={
            'event': {'x': x, 'y': y}
        })
        self._get_rust_thread().join()
        output = self._get_build_output(view.window())
        self.assertRegex(output,
            r'\[Running: cargo test --test test_context --message-format=json -- --exact test1\]')

    def test_cargo_test_at_cursor(self):
        self._with_open_file('tests/multi-targets/tests/test_context.rs',
            self._test_cargo_test_at_cursor)

    def _test_cargo_test_at_cursor(self, view):
        pt = view.text_point(12, 0)
        sel = view.sel()
        sel.clear()
        sel.add(sublime.Region(pt))
        view.run_command('cargo_test_at_cursor')
        self._get_rust_thread().join()
        output = self._get_build_output(view.window())
        self.assertRegex(output,
            r'\[Running: cargo test --test test_context --message-format=json -- --exact expected_panic1\]')

    def test_cargo_test_current_file(self):
        self._with_open_file('tests/multi-targets/tests/test_context.rs',
            self._test_cargo_test_current_file)

    def _test_cargo_test_current_file(self, view):
        view.window().run_command('cargo_test_current_file')
        self._get_rust_thread().join()
        output = self._get_build_output(view.window())
        self.assertRegex(output,
            r'\[Running: cargo test --test test_context --message-format=json\]')

    def test_cargo_bench_here(self):
        self._with_open_file('tests/multi-targets/benches/bench_context.rs',
            self._test_cargo_bench_here)

    def _test_cargo_bench_here(self, view):
        pt = view.text_point(15, 0)
        x, y = view.text_to_window(pt)
        view.window().run_command('cargo_bench_here', args={
            'event': {'x': x, 'y': y}
        })
        self._get_rust_thread().join()
        output = self._get_build_output(view.window())
        self.assertRegex(output,
            r'\[Running: cargo bench --bench bench_context --message-format=json -- --exact bench2\]')

    def test_cargo_bench_at_cursor(self):
        self._with_open_file('tests/multi-targets/benches/bench_context.rs',
            self._test_cargo_bench_at_cursor)

    def _test_cargo_bench_at_cursor(self, view):
        pt = view.text_point(15, 0)
        sel = view.sel()
        sel.clear()
        sel.add(sublime.Region(pt))
        view.run_command('cargo_bench_at_cursor')
        self._get_rust_thread().join()
        output = self._get_build_output(view.window())
        self.assertRegex(output,
            r'\[Running: cargo bench --bench bench_context --message-format=json -- --exact bench2\]')

    def test_cargo_bench_current_file(self):
        self._with_open_file('tests/multi-targets/benches/bench_context.rs',
            self._test_cargo_bench_current_file)

    def _test_cargo_bench_current_file(self, view):
        view.window().run_command('cargo_bench_current_file')
        self._get_rust_thread().join()
        output = self._get_build_output(view.window())
        self.assertRegex(output,
            r'\[Running: cargo bench --bench bench_context --message-format=json\]')

    def test_cargo_run_current_file(self):
        self._with_open_file('tests/multi-targets/examples/ex1.rs',
            self._test_cargo_run_current_file)

    def _test_cargo_run_current_file(self, view):
        view.window().run_command('cargo_run_current_file')
        self._get_rust_thread().join()
        output = self._get_build_output(view.window())
        self.assertRegex(output,
            r'\[Running: cargo run --example ex1 --message-format=json\]')

    def test_rust_list_messages(self):
        self._with_open_file('tests/message-order/examples/ex_warning1.rs',
            self._test_rust_list_messages)

    def _test_rust_list_messages(self, view):
        window = view.window()
        self._cargo_clean(view)
        window.run_command('cargo_exec', args={'command': 'auto'})
        self._get_rust_thread().join()
        sqp = window.__class__.show_quick_panel
        window.__class__.show_quick_panel = self._quick_panel
        try:
            self._test_rust_list_messages2(view)
        finally:
            window.__class__.show_quick_panel = sqp

    def _quick_panel(self, items, on_done, flags=0,
                     selected_index=-1, on_highlighted=None):
        self.assertEqual(items, self.quick_panel_items)
        on_done(self.quick_panel_index)

    def _test_rust_list_messages2(self, view):
        window = view.window()
        self.quick_panel_items = [
            ['function is never used: `unused_a`',
             os.path.join('tests', 'message-order', 'examples', 'warning1.rs') + ':1'],
            ['function is never used: `unused_b`',
             os.path.join('tests', 'message-order', 'examples', 'warning1.rs') + ':5'],
            ['function is never used: `unused_in_2`',
             os.path.join('tests', 'message-order', 'examples', 'warning2.rs') + ':82'],
        ]
        self.quick_panel_index = 2
        window.run_command('rust_list_messages')
        expected_path = os.path.normpath(
            os.path.join(plugin_path, 'tests/message-order/examples/warning2.rs'))
        # Give Sublime some time to switch views.
        for n in range(5):
            new_view = window.active_view()
            if new_view.file_name() == expected_path:
                break
            time.sleep(0.5)
        else:
            self.assertEqual(new_view.file_name(), expected_path)
        new_view.run_command('close_file')
