"""Tests for `rust_phantom_style` settings."""

from rust_test_common import *


class TestPhantomStyle(TestBase):

    def test_style_none(self):
        self._override_setting('rust_phantom_style', 'none')
        self._with_open_file('tests/error-tests/tests/cast-to-unsized-trait-object-suggestion.rs',
            self._test_style_none)

    def _test_style_none(self, view):
        with UiIntercept(passthrough=True) as ui:
            e = plugin.SyntaxCheckPlugin.RustSyntaxCheckEvent()
            self._cargo_clean(view)
            e.on_post_save(view)
            self._get_rust_thread().join()
            self.assertEqual(len(ui.phantoms), 0)
            regions = ui.view_regions[view.file_name()]
            # Extremely basic check, the number of unique regions displayed.
            rs = [(r.a, r.b) for r in regions]
            self.assertEqual(len(set(rs)), 4)

    def test_style_popup(self):
        self._override_setting('rust_phantom_style', 'popup')
        self._with_open_file('tests/error-tests/tests/cast-to-unsized-trait-object-suggestion.rs',
            self._test_style_popup)

    def _test_style_popup(self, view):
        with UiIntercept(passthrough=True) as ui:
            e = plugin.SyntaxCheckPlugin.RustSyntaxCheckEvent()
            self._cargo_clean(view)
            e.on_post_save(view)
            self._get_rust_thread().join()
            self.assertEqual(len(ui.phantoms), 0)
            regions = ui.view_regions[view.file_name()]
            # Extremely basic check, the number of unique regions displayed.
            rs = [(r.a, r.b) for r in regions]
            self.assertEqual(len(set(rs)), 4)
            # Trigger popup.
            self.assertEqual(len(ui.popups), 0)
            for region in regions:
                messages.message_popup(view, region.begin(), sublime.HOVER_TEXT)
                popups = ui.popups[view.file_name()]
                self.assertEqual(len(popups), 1)
                self.assertIn('cast to unsized type', popups[0]['content'])
                ui.popups.clear()

            # Trigger gutter hover.
            for lineno in (12, 16):
                pt = view.text_point(lineno - 1, 0)
                messages.message_popup(view, pt, sublime.HOVER_GUTTER)
                popups = ui.popups[view.file_name()]
                self.assertEqual(len(popups), 1)
                self.assertIn('cast to unsized type', popups[0]['content'])
                ui.popups.clear()
