"""Tests for clicking on messages."""

import re

from rust_test_common import *


class TestClickHandler(TestBase):

    def test_accept_replacement(self):
        self._with_open_file('tests/error-tests/tests/cast-to-unsized-trait-object-suggestion.rs',
            self._test_accept_replacement)

    def _test_accept_replacement(self, view):
        def get_line(lineno):
            pt = view.text_point(lineno, 0)
            line_r = view.line(pt)
            return view.substr(line_r)

        with UiIntercept(passthrough=True) as ui:
            e = plugin.SyntaxCheckPlugin.RustSyntaxCheckEvent()
            self._cargo_clean(view)
            e.on_post_save(view)
            self._get_rust_thread().join()
            self.assertEqual(get_line(11), '    &1 as Send;')
            self.assertEqual(get_line(15), '    Box::new(1) as Send;')
            phantoms = ui.phantoms[view.file_name()]
            phantoms.sort(key=lambda x: x['region'])
            # Filter out just the "Accept Replacement" phantoms.
            phantoms = filter(lambda x: 'Replacement' in x['content'], phantoms)
            expected = ((11, '    &1 as &Send;'),
                        (15, '    Box::new(1) as Box<Send>;'))
            for phantom, (lineno, expected_line) in zip(phantoms, expected):
                url = re.search(r'<a .*href="(replace:[^"]+)"',
                    phantom['content']).group(1)
                phantom['on_navigate'](url)
                self.assertEqual(get_line(lineno), expected_line)
