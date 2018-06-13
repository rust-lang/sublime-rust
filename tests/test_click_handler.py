"""Tests for clicking on messages."""

import re

from rust_test_common import *


REPLACEMENT_TESTS = [
    ('tests/error-tests/tests/cast-to-unsized-trait-object-suggestion.rs', None,
        # Before
        ((11, '    &1 as Send;'),
         (15, '    Box::new(1) as Send;')),
        # After
        ((11, '    &1 as &Send;'),
         (15, '    Box::new(1) as Box<Send>;')),
    ),
    ('tests/error-tests/tests/impl-generic-mismatch.rs', '>=1.28.0-beta',
        # Before
        ((20, '    fn foo<U: Debug>(&self, _: &U) { }'),
         (39, '    fn bar(&self, _: &impl Debug) { }')),
        # After
        ((20, '    fn foo(&self, _: &U) { }'),
         (20, '    fn foo(&self, _: &impl Debug) { }'),
         (39, '    fn bar(&self, _: &U) { }'),
         (39, '    fn bar<U: Debug>(&self, _: &U) { }')),
    ),
]


class TestClickHandler(TestBase):

    def test_accept_replacement(self):
        rustc_version = util.get_rustc_version(sublime.active_window(), plugin_path)
        for filename, version, before, after in REPLACEMENT_TESTS:
            if not version or semver.match(rustc_version, version):
                self._with_open_file(filename,
                    self._test_accept_replacement, before=before, after=after)

    def _test_accept_replacement(self, view, before, after):
        def get_line(lineno):
            pt = view.text_point(lineno, 0)
            line_r = view.line(pt)
            return view.substr(line_r)

        with UiIntercept(passthrough=True) as ui:
            e = plugin.SyntaxCheckPlugin.RustSyntaxCheckEvent()
            self._cargo_clean(view)
            e.on_post_save(view)
            self._get_rust_thread().join()
            for lineno, text in before:
                self.assertEqual(get_line(lineno), text)
            phantoms = ui.phantoms[view.file_name()]
            phantoms.sort(key=lambda x: x['region'])
            # Filter out just the "Accept Replacement" phantoms.
            click_urls = []
            for phantom in phantoms:
                click_urls.extend(re.findall(r'<a .*href="(replace:[^"]+)"',
                    phantom['content']))
            self.assertEqual(len(click_urls), len(after))
            for url, (lineno, expected_line) in zip(click_urls, after):
                phantom['on_navigate'](url)
                self.assertEqual(get_line(lineno), expected_line)
