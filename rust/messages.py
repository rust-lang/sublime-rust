"""Module for storing/displaying Rust compiler messages."""

import sublime

import collections
import functools
import html
import itertools
import os
import re
import textwrap
import urllib.parse
import uuid
import webbrowser

from . import util, themes
from .batch import *

# Key is window id.
# Value is a dictionary: {
#     'paths': {path: [MessageBatch, ...]},
#     'batch_index': (path_idx, message_idx),
#     'hidden': bool
# }
# `paths` is an OrderedDict to handle next/prev message.
# `path` is the absolute path to the file.
# `hidden` indicates that all messages have been dismissed.
WINDOW_MESSAGES = {}


LINK_PATTERN = r'(https?://[-a-zA-Z0-9@:%._+~#=]{2,256}\.[a-zA-Z]{2,6}\b[-a-zA-Z0-9@:%_+.~#?&/=]*)'


class Message:

    """A diagnostic message.

    :ivar id: A unique uuid for this message.
    :ivar region_key: A string for the Sublime highlight region and phantom
        for this message.  Unique per view.
    :ivar text: The raw text of the message without any minihtml markup.  May
        be None if the content is raw markup (such as a minihtml link) or if
        it is an outline-only region (which happens with things such as
        dual-region messages added in 1.21).
    :ivar level: Message level as a string such as "error", or "info".
    :ivar span: Location of the message (0-based):
        `((line_start, col_start), (line_end, col_end))`
        May be `None` to indicate no particular spot.
    :ivar path: Absolute path to the file.
    :ivar code: Rust error code as a string such as 'E0001'.  May be None.
    :ivar output_panel_region: Optional Sublime Region object that indicates
        the region in the build output panel that corresponds with this
        message.
    :ivar primary: True if this is the primary message, False if a child.
    :ivar children: List of additional Message objects.  This is *not*
        recursive (children cannot have children).
    :ivar parent: The primary Message object if this a child.
    :iver hidden: If true, don't show this message.
    :ivar suggested_replacement: An optional string of text as a suggestion to
        replace at the given span.  If this is set, `text` will NOT be set.
    """
    region_key = None
    text = None
    level = None
    span = None
    path = None
    code = None
    output_panel_region = None
    primary = True
    parent = None
    hidden = False
    suggested_replacement = None

    def __init__(self):
        self.id = uuid.uuid4()
        self.children = []

    def lineno(self, first=False):
        """Return the line number of the message (0-based).

        :param first: If True, returns the line number of the start of the
            region.  Otherwise returns the last line of the region.
        """
        if self.span:
            if first:
                return self.span[0][0]
            else:
                return self.span[1][0]
        else:
            return 999999999

    def __iter__(self):
        """Convenience iterator for iterating over the message and its children."""
        yield self
        for child in self.children:
            yield child

    def escaped_text(self, view, indent):
        """Returns the minihtml markup of the message.

        :param indent: String used for indentation when the message spans
            multiple lines.  Typically a series of &nbsp; to get correct
            alignment.
        """
        if self.suggested_replacement is not None:
            return self._render_suggested_replacement()
        if not self.text:
            return ''

        # Call rstrip() because sometimes rust includes newlines at the
        # end of the message, which we don't want.
        text = self.text.rstrip()
        if not view.settings().get('word_wrap', False):
            # Rough assumption of using monospaced font, but should be
            # reasonable in most cases for proportional fonts.
            width = view.viewport_extent()[0] / view.em_width() - 5
            text = textwrap.fill(self.text, width=width,
                break_long_words=False, break_on_hyphens=False)

        def escape_and_link(i_txt):
            i, txt = i_txt
            if i % 2:
                return '<a href="%s">%s</a>' % (txt, txt)
            else:
                escaped = html.escape(txt, quote=False)
                return re.sub('^( +)', lambda m: '&nbsp;'*len(m.group()), escaped, flags=re.MULTILINE)\
                    .replace('\n', '<br>' + indent)

        parts = re.split(LINK_PATTERN, text)
        return ' '.join(map(escape_and_link, enumerate(parts)))

    def _render_suggested_replacement(self):
        replacement_template = util.multiline_fix("""
            <div class="rust-replacement"><a href="replace:%s" class="rust-button">Accept Replacement:</a> %s</div>
        """)
        html_suggestion = html.escape(self.suggested_replacement, quote=False)
        if '\n' in html_suggestion:
            # Start on a new line so the text doesn't look too weird.
            html_suggestion = '\n' + html_suggestion
        html_suggestion = html_suggestion\
            .replace(' ', '&nbsp;')\
            .replace('\n', '<br>\n')
        return replacement_template % (
            urllib.parse.urlencode({
                'id': self.id,
                'replacement': self.suggested_replacement,
            }),
            html_suggestion,
        )

    def suggestion_count(self):
        """Number of suggestions in this message.

        This is used to know once all suggestions have been accepted that a
        message can be dismissed.
        """
        if self.parent:
            return self.parent.suggestion_count()
        count = 0
        for m in self:
            if m.suggested_replacement is not None and not m.hidden:
                count += 1
        return count

    def is_similar(self, other):
        """Returns True if this message is essentially the same as the given
        message.  Used for deduplication."""
        keys = ('path', 'span', 'level', 'text', 'suggested_replacement')
        for key in keys:
            if getattr(other, key) != getattr(self, key):
                return False
        else:
            return True

    def sublime_region(self, view):
        """Returns a sublime.Region object for this message."""
        if self.span:
            regions = view.get_regions(self.region_key)
            if regions:
                self.span = (
                    view.rowcol(regions[0].a),
                    view.rowcol(regions[0].b)
                )
                return regions[0]
            else:
                return sublime.Region(
                    view.text_point(self.span[0][0], self.span[0][1]),
                    view.text_point(self.span[1][0], self.span[1][1])
                )
        else:
            # Place at bottom of file for lack of anywhere better.
            return sublime.Region(view.size())

    def __repr__(self):
        result = ['<Message\n']
        for key, value in self.__dict__.items():
            if key == 'parent':
                result.append('    parent=%r\n' % (value.id,))
            else:
                result.append('    %s=%r\n' % (key, value))
        result.append('>')
        return ''.join(result)


def clear_messages(window, soft=False):
    """Remove all messages for the given window.

    :param soft: If True, the messages are kept in memory and can be
        resurrected with various commands (such as list messages, or
        next/prev).
    """
    if soft:
        winfo = WINDOW_MESSAGES.get(window.id(), {})
        winfo['hidden'] = True
    else:
        winfo = WINDOW_MESSAGES.pop(window.id(), {})

    for path, batches in winfo.get('paths', {}).items():
        view = window.find_open_file(path)
        if view:
            for batch in batches:
                for msg in batch:
                    view.erase_regions(msg.region_key)
                    view.erase_phantoms(msg.region_key)


def clear_all_messages():
    """Remove all messages in all windows."""
    for window in sublime.windows():
        if window.id() in WINDOW_MESSAGES:
            clear_messages(window)


def add_message(window, message):
    """Add a message to be displayed (ignores children).

    :param window: The Sublime window.
    :param message: The `Message` object to add.
    """
    _save_batches(window, [PrimaryBatch(message)], None)


def has_message_for_path(window, path):
    paths = WINDOW_MESSAGES.get(window.id(), {}).get('paths', {})
    return path in paths


def messages_finished(window):
    """This should be called after all messages have been added."""
    _sort_messages(window)


def _draw_region_highlights(view, batch):
    if util.get_setting('rust_region_style') == 'none':
        return

    # Collect message regions by level.
    regions = {
        'error': [],
        'warning': [],
        'note': [],
        'help': [],
    }
    if batch.hidden:
        return
    for msg in batch:
        region = msg.sublime_region(view)
        if msg.level not in regions:
            print('RustEnhanced: Unknown message level %r encountered.' % msg.level)
            msg.level = 'error'
        regions[msg.level].append((msg.region_key, region))

    # Do this in reverse order so that errors show on-top.
    for level in ['help', 'note', 'warning', 'error']:
        # Use scope names from color themes to drive the color of the outline.
        # 'invalid' typically is red.  We use 'info' for all other levels, which
        # is usually not defined in any color theme, and will end up showing as
        # the foreground color (white in dark themes).
        #
        # TODO: Consider using the new magic scope names added in build 3148
        # to manually specify colors:
        #     region.redish, region.orangish, region.yellowish,
        #     region.greenish, region.bluish, region.purplish and
        #     region.pinkish
        if level == 'error':
            scope = 'invalid'
        else:
            scope = 'info'
        icon = util.icon_path(level)
        for key, region in regions[level]:
            _sublime_add_regions(
                view, key, [region], scope, icon,
                sublime.DRAW_NO_FILL | sublime.DRAW_EMPTY)


def message_popup(view, point, hover_zone):
    """Displays a popup if there is a message at the given point."""
    try:
        winfo = WINDOW_MESSAGES[view.window().id()]
    except KeyError:
        return
    if winfo['hidden']:
        return
    batches = winfo['paths'].get(view.file_name(), [])

    if hover_zone == sublime.HOVER_GUTTER:
        # Collect all messages on this line.
        row = view.rowcol(point)[0]

        def filter_row(batch):
            if batch.hidden:
                return False
            region = batch.first().sublime_region(view)
            batch_row_a = view.rowcol(region.begin())[0]
            batch_row_b = view.rowcol(region.end())[0]
            return row >= batch_row_a and row <= batch_row_b

        batches = filter(filter_row, batches)
    else:
        # Collect all messages covering this point.
        def filter_point(batch):
            if batch.hidden:
                return False
            for msg in batch:
                if not msg.hidden and msg.sublime_region(view).contains(point):
                    return True
            return False

        batches = filter(filter_point, batches)

    if batches:
        theme = themes.THEMES[util.get_setting('rust_message_theme')]
        minihtml = '\n'.join(theme.render(view, batch, for_popup=True) for batch in batches)
        if not minihtml:
            return
        on_nav = functools.partial(_click_handler, view, hide_popup=True)
        max_width = view.em_width() * 79
        _sublime_show_popup(view, minihtml, sublime.COOPERATE_WITH_AUTO_COMPLETE,
            point, max_width=max_width, on_navigate=on_nav)


def _click_handler(view, url, hide_popup=False):
    if url == 'hide':
        clear_messages(view.window(), soft=True)
        if hide_popup:
            view.hide_popup()
    elif url.startswith('file:///'):
        view.window().open_file(url[8:], sublime.ENCODED_POSITION)
    elif url.startswith('replace:'):
        info = urllib.parse.parse_qs(url[8:], keep_blank_values=True)
        _accept_replace(view, info['id'][0], info['replacement'][0])
        if hide_popup:
            view.hide_popup()
    else:
        webbrowser.open_new(url)


def _accept_replace(view, mid, replacement):
    def batch_and_msg():
        for batch in batches:
            for msg in batch:
                if str(msg.id) == mid:
                    return batch, msg
        raise ValueError('Rust Enhanced internal error: Could not find ID %r' % (mid,))
    batches = WINDOW_MESSAGES.get(view.window().id(), {})\
                             .get('paths', {})\
                             .get(view.file_name(), [])
    batch, msg = batch_and_msg()
    # Retrieve the updated region from Sublime (since it may have changed
    # since the messages were generated).
    regions = view.get_regions(msg.region_key)
    if not regions:
        print('Rust Enhanced internal error: Could not find region for suggestion.')
        return
    region = (regions[0].a, regions[0].b)
    view.run_command('rust_accept_suggested_replacement', {
        'region': region,
        'replacement': replacement
    })
    msg.hidden = True
    if msg.suggestion_count():
        # Additional suggestions still exist, re-render the phantom.
        view.erase_phantoms(batch.first().region_key)
        for m in batch:
            # Force `span` to be updated to the most recent value.
            m.sublime_region(view)
        _show_phantom(view, batch)
    else:
        # No more suggestions, just hide the diagnostic completely.
        batch.primary().dismiss(view.window())


def _show_phantom(view, batch):
    if util.get_setting('rust_phantom_style') != 'normal':
        return
    if batch.hidden:
        return

    first = batch.first()
    region = first.sublime_region(view)
    # For some reason if you have a multi-line region, the phantom is only
    # displayed under the first line.  I think it makes more sense for the
    # phantom to appear below the last line.
    start = view.rowcol(region.begin())
    end = view.rowcol(region.end())
    if start[0] != end[0]:
        # Spans multiple lines, adjust to the last line.
        region = sublime.Region(
            view.text_point(end[0], 0),
            region.end()
        )

    theme = themes.THEMES[util.get_setting('rust_message_theme')]
    content = theme.render(view, batch)
    if not content:
        return

    _sublime_add_phantom(
        view,
        first.region_key, region,
        content,
        sublime.LAYOUT_BLOCK,
        functools.partial(_click_handler, view)
    )


def _sublime_add_phantom(view, key, region, content, layout, on_navigate):
    """Pulled out to assist testing."""
    view.add_phantom(
        key, region,
        content,
        layout,
        on_navigate
    )


def _sublime_add_regions(view, key, regions, scope, icon, flags):
    """Pulled out to assist testing."""
    view.add_regions(key, regions, scope, icon, flags)


def _sublime_show_popup(view, content, *args, **kwargs):
    """Pulled out to assist testing."""
    view.show_popup(content, *args, **kwargs)


def _sort_messages(window):
    """Sorts messages so that errors are shown first when using Next/Prev
    commands."""
    # Undocumented config variable to disable sorting in case there are
    # problems with it.
    if not util.get_setting('rust_sort_messages', True):
        return
    wid = window.id()
    try:
        window_info = WINDOW_MESSAGES[wid]
    except KeyError:
        return
    batches_by_path = window_info['paths']
    items = []
    for path, batches in batches_by_path.items():
        for batch in batches:
            level = {
                'error': 0,
                'warning': 1,
                'note': 2,
                'help': 3,
            }.get(batch.first().level, 0)
            items.append((level, path, batch.first().lineno(), batch))
    items.sort(key=lambda x: x[:3])
    batches_by_path = collections.OrderedDict()
    for _, path, _, batch in items:
        batches = batches_by_path.setdefault(path, [])
        batches.append(batch)
    window_info['paths'] = batches_by_path


def show_next_message(window, levels):
    current_idx = _advance_next_message(window, levels)
    _show_message(window, current_idx)


def show_prev_message(window, levels):
    current_idx = _advance_prev_message(window, levels)
    _show_message(window, current_idx)


def _show_message(window, current_idx, transient=False, force_open=False):
    if current_idx is None:
        return
    try:
        window_info = WINDOW_MESSAGES[window.id()]
    except KeyError:
        return
    if window_info['hidden']:
        redraw_all_open_views(window)
    paths = window_info['paths']
    path, batches = _ith_iter_item(paths.items(), current_idx[0])
    batch = batches[current_idx[1]]
    msg = batch.first()
    _scroll_build_panel(window, msg)
    view = None
    if not transient and not force_open:
        active = window.active_view()
        if active.file_name() == path:
            # If a file is open in multiple views, try to stick to the current
            # view.  Otherwise it may jump to the other view which is a little
            # jarring.
            view = active
        else:
            view = window.find_open_file(path)
        if view:
            _scroll_to_message(view, msg, transient)
    if not view:
        flags = sublime.ENCODED_POSITION
        if transient:
            # FORCE_GROUP is undocumented.  It forces the view to open in the
            # current group, even if the view is already open in another
            # group.  This is necessary to prevent the quick panel from losing
            # focus. See:
            # https://github.com/SublimeTextIssues/Core/issues/1041
            flags |= sublime.TRANSIENT | sublime.FORCE_GROUP
        if msg.span:
            # show_at_center is buggy with newly opened views (see
            # https://github.com/SublimeTextIssues/Core/issues/538).
            # ENCODED_POSITION is 1-based.
            row, col = msg.span[0]
        else:
            row, col = (999999999, 1)
        view = window.open_file('%s:%d:%d' % (path, row + 1, col + 1),
                                flags)
        # Block until the view is loaded.
        _show_message_wait(view)


def _show_message_wait(view):
    if view.is_loading():
        def f():
            _show_message_wait(view)
        sublime.set_timeout(f, 10)
    # The on_load event handler will call show_messages_for_view which
    # should handle displaying the messages.


def _scroll_build_panel(window, message):
    """If the build output panel is open, scroll the output to the message
    selected."""
    if message.output_panel_region:
        # Defer cyclic import.
        from . import opanel
        view = window.find_output_panel(opanel.PANEL_NAME)
        if view:
            r = message.output_panel_region
            view.run_command('rust_scroll_to_region', {'region': (r.a, r.b)})


def _scroll_to_message(view, message, transient):
    """Scroll view to the message."""
    if not transient:
        view.window().focus_view(view)
    r = message.sublime_region(view)
    view.run_command('rust_scroll_to_region', {'region': (r.a, r.a)})


def redraw_all_open_views(window):
    """Re-display phantoms/regions after being hidden."""
    try:
        winfo = WINDOW_MESSAGES[window.id()]
    except KeyError:
        return
    winfo['hidden'] = False
    for path, batches in winfo['paths'].items():
        view = window.find_open_file(path)
        if view:
            show_messages_for_view(view)


def show_messages_for_view(view):
    """Adds all phantoms and region outlines for a view."""
    try:
        winfo = WINDOW_MESSAGES[view.window().id()]
    except KeyError:
        return
    if winfo['hidden']:
        return
    batches = winfo['paths'].get(view.file_name(), [])
    for batch in batches:
        _show_phantom(view, batch)
        _draw_region_highlights(view, batch)


def _ith_iter_item(d, i):
    return next(itertools.islice(d, i, None))


def _advance_next_message(window, levels, wrap_around=False):
    """Update global batch_index to the next index."""
    try:
        win_info = WINDOW_MESSAGES[window.id()]
    except KeyError:
        return None
    paths = win_info['paths']
    path_idx, batch_idx = win_info['batch_index']
    if path_idx == -1:
        # First time.
        path_idx = 0
        batch_idx = 0
    else:
        batch_idx += 1

    while path_idx < len(paths):
        batches = _ith_iter_item(paths.values(), path_idx)
        while batch_idx < len(batches):
            batch = batches[batch_idx]
            if _is_matching_level(levels, batch.first()):
                current_idx = (path_idx, batch_idx)
                win_info['batch_index'] = current_idx
                return current_idx
            batch_idx += 1
        path_idx += 1
        batch_idx = 0
    if wrap_around:
        # No matching entries, give up.
        return None
    else:
        # Start over at the beginning of the list.
        win_info['batch_index'] = (-1, -1)
        return _advance_next_message(window, levels, wrap_around=True)


def _last_index(paths):
    path_idx = len(paths) - 1
    msg_idx = len(_ith_iter_item(paths.values(), path_idx)) - 1
    return (path_idx, msg_idx)


def _advance_prev_message(window, levels, wrap_around=False):
    """Update global batch_index to the previous index."""
    try:
        win_info = WINDOW_MESSAGES[window.id()]
    except KeyError:
        return None
    paths = win_info['paths']
    path_idx, batch_idx = win_info['batch_index']
    if path_idx == -1:
        # First time, start at the end.
        path_idx, batch_idx = _last_index(paths)
    else:
        batch_idx -= 1

    while path_idx >= 0:
        batches = _ith_iter_item(paths.values(), path_idx)
        while batch_idx >= 0:
            batch = batches[batch_idx]
            if _is_matching_level(levels, batch.first()):
                current_idx = (path_idx, batch_idx)
                win_info['batch_index'] = current_idx
                return current_idx
            batch_idx -= 1
        path_idx -= 1
        if path_idx >= 0:
            batch_idx = len(_ith_iter_item(paths.values(), path_idx)) - 1
    if wrap_around:
        # No matching entries, give up.
        return None
    else:
        # Start over at the end of the list.
        win_info['batch_index'] = (-1, -1)
        return _advance_prev_message(window, levels, wrap_around=True)


def _is_matching_level(levels, message):
    if not message.primary:
        # Only navigate to top-level messages.
        return False
    if levels == 'all':
        return True
    elif levels == 'error' and message.level == 'error':
        return True
    elif levels == 'warning' and message.level != 'error':
        # Warning, Note, Help
        return True
    else:
        return False


def _relative_path(window, path):
    """Convert an absolute path to a relative path used for a truncated
    display."""
    for folder in window.folders():
        if path.startswith(folder):
            return os.path.relpath(path, folder)
    return path


def list_messages(window):
    """Show a list of all messages."""
    try:
        win_info = WINDOW_MESSAGES[window.id()]
    except KeyError:
        # XXX: Or dialog?
        window.show_quick_panel(["No messages available"], None)
        return
    if win_info['hidden']:
        redraw_all_open_views(window)
    panel_items = []
    jump_to = []
    for path_idx, (path, batches) in enumerate(win_info['paths'].items()):
        for batch_idx, batch in enumerate(batches):
            if not isinstance(batch, PrimaryBatch):
                continue
            message = batch.primary_message
            jump_to.append((path_idx, batch_idx))
            if message.span:
                path_label = '%s:%s' % (
                    _relative_path(window, path),
                    message.span[0][0] + 1)
            else:
                path_label = _relative_path(window, path)
            item = [message.text, path_label]
            panel_items.append(item)

    def on_done(idx):
        _show_message(window, jump_to[idx], force_open=True)

    def on_highlighted(idx):
        _show_message(window, jump_to[idx], transient=True)

    window.show_quick_panel(panel_items, on_done, 0, 0, on_highlighted)


def add_rust_messages(window, base_path, info, target_path, msg_cb):
    """Add messages from Rust JSON to Sublime views.

    :param window: Sublime Window object.
    :param base_path: Base path used for resolving relative paths from Rust.
    :param info: Dictionary of messages from rustc or cargo.
    :param target_path: Absolute path to the top-level source file of the
      target (lib.rs, main.rs, etc.).  May be None if it is not known.
    :param msg_cb: Callback that will be given the message object (and each
        child separately).
    """
    # cargo check emits in a slightly different format.
    if 'reason' in info:
        if info['reason'] == 'compiler-message':
            info = info['message']
        else:
            # cargo may emit various other messages, like
            # 'compiler-artifact' or 'build-script-executed'.
            return

    primary_message = Message()

    _collect_rust_messages(window, base_path, info, target_path, msg_cb, {},
        primary_message)
    if not primary_message.path:
        return
    if _is_duplicate_message(window, primary_message):
        return
    batches = _batch_and_cross_link(primary_message)
    _save_batches(window, batches, msg_cb)


def _is_duplicate_message(window, primary_message):
    batches = WINDOW_MESSAGES.get(window.id(), {})\
                             .get('paths', {})\
                             .get(primary_message.path, [])
    for batch in batches:
        if isinstance(batch, PrimaryBatch):
            if batch.primary_message.is_similar(primary_message):
                return True
    return False


def _collect_rust_messages(window, base_path, info, target_path,
                           msg_cb, parent_info,
                           message):
    """
    - `info`: The dictionary from Rust has the following structure:

        - 'message': The message to display.
        - 'level': The error level ('error', 'warning', 'note', 'help')
                   (XXX I think an ICE shows up as 'error: internal compiler
                   error')
        - 'code': If not None, contains a dictionary of extra information
          about the error.
            - 'code': String like 'E0001'
            - 'explanation': Optional string with a very long description of
              the error.  If not specified, then that means nobody has gotten
              around to describing the error, yet.
        - 'spans': List of regions with diagnostic information.  May be empty
          (child messages attached to their parent, or global messages like
          "main not found"). Each element is:

            - 'file_name': Filename for the message.  For spans located in the
              'expansion' section, this will be the name of the expanded macro
              in the format '<macroname macros>'.
            - 'byte_start':
            - 'byte_end':
            - 'line_start':
            - 'line_end':
            - 'column_start':
            - 'column_end':
            - 'is_primary': If True, this is the primary span where the error
              started.  Note: It is possible (though rare) for multiple spans
              to be marked as primary (for example, 'immutable borrow occurs
              here' and 'mutable borrow ends here' can be two separate spans
              both "primary").  Top (parent) messages should always have at
              least one primary span (unless it has 0 spans).  Child messages
              may have 0 or more primary spans.  AFAIK, spans from 'expansion'
              are never primary.
            - 'text': List of dictionaries showing the original source code.
            - 'label': A message to display at this span location.  May be
              None (AFAIK, this only happens when is_primary is True, in which
              case the main 'message' is all that should be displayed).
            - 'suggested_replacement':  If not None, a string with a
              suggestion of the code to replace this span.
            - 'expansion': If not None, a dictionary indicating the expansion
              of the macro within this span.  The values are:

                - 'span': A span object where the macro was applied.
                - 'macro_decl_name': Name of the macro ("print!" or
                  "#[derive(Eq)]")
                - 'def_site_span': Span where the macro was defined (may be
                  None if not known).

        - 'children': List of attached diagnostic messages (following this
          same format) of associated information.  AFAIK, these are never
          nested.
        - 'rendered': Optional string (may be None).

          Before 1.23: Used by suggested replacements.  If
          'suggested_replacement' is set, then this is rendering of how the
          line should be written.

          After 1.23:  This contains the ASCII-art rendering of the message as
          displayed by rustc's normal console output.

    - `parent_info`: Dictionary used for tracking "children" messages.
      Currently only has 'span' key, the span of the parent to display the
      message (for children without spans).
    - `message`: `Message` object where we store the message information.
    """
    # Include "notes" tied to errors, even if warnings are disabled.
    if (info['level'] != 'error' and
        util.get_setting('rust_syntax_hide_warnings') and
        not parent_info
       ):
        return

    def make_span_path(span):
        return os.path.realpath(os.path.join(base_path, span['file_name']))

    def make_span_region(span):
        # Sublime text is 0 based whilst the line/column info from
        # rust is 1 based.
        if span.get('line_start'):
            return ((span['line_start'] - 1, span['column_start'] - 1),
                    (span['line_end'] - 1, span['column_end'] - 1))
        else:
            return None

    def set_primary_message(span, text):
        parent_info['span'] = span
        # Not all codes have explanations (yet).
        if info['code'] and info['code']['explanation']:
            message.code = info['code']['code']
        message.path = make_span_path(span)
        message.span = make_span_region(span)
        message.text = text
        message.level = info['level']

    def add_additional(span, text, level, suggested_replacement=None):
        child = Message()
        child.text = text
        child.suggested_replacement = suggested_replacement
        child.level = level
        child.primary = False
        if 'macros>' in span['file_name']:
            # Nowhere to display this, just send it to the console via msg_cb.
            msg_cb(child)
        else:
            child.path = make_span_path(span)
            if not os.path.exists(child.path):
                # Sometimes rust gives messages that link to libstd in the
                # directory where it was built (such as on Travis).
                return
            child.span = make_span_region(span)
            if any(map(lambda m: m.is_similar(child), message.children)):
                # Duplicate message, skip.  This happens with some of the
                # macro help messages.
                return
            child.parent = message
            message.children.append(child)

    if len(info['spans']) == 0:
        if parent_info:
            # This is extra info attached to the parent message.
            add_additional(parent_info['span'], info['message'], info['level'])
        else:
            # Messages without spans are global session messages (like "main
            # function not found").
            #
            # Some of the messages are not very interesting, though.
            imsg = info['message']
            if not (imsg.startswith('aborting due to') or
                    imsg.startswith('cannot continue') or
                    imsg.startswith('Some errors occurred') or
                    imsg.startswith('For more information about')):
                if target_path:
                    # Display at the bottom of the root path (like main.rs)
                    # for lack of a better place to put it.
                    fake_span = {'file_name': target_path}
                    set_primary_message(fake_span, imsg)
                else:
                    # Not displayed as a phantom since we don't know where to
                    # put it.
                    if msg_cb:
                        tmp_msg = Message()
                        tmp_msg.level = info['level']
                        tmp_msg.text = imsg
                        msg_cb(tmp_msg)

    def find_span_r(span, expansion=None):
        if span['expansion']:
            return find_span_r(span['expansion']['span'], span['expansion'])
        else:
            return span, expansion

    for span in info['spans']:
        if 'macros>' in span['file_name']:
            # Rust gives the chain of expansions for the macro, which we don't
            # really care about.  We want to find the site where the macro was
            # invoked.  I'm not entirely confident this is the best way to do
            # this, but it seems to work.  This is roughly emulating what is
            # done in librustc_errors/emitter.rs fix_multispan_in_std_macros.
            target_span, expansion = find_span_r(span)
            if not target_span:
                continue
            updated = target_span.copy()
            updated['is_primary'] = span['is_primary']
            updated['label'] = span['label']
            updated['suggested_replacement'] = span['suggested_replacement']
            span = updated

            if 'macros>' in span['file_name']:
                # Macros from extern crates do not have 'expansion', and thus
                # we do not have a location to highlight.  Place the result at
                # the bottom of the primary target path.
                macro_name = span['file_name']
                if target_path:
                    span['file_name'] = target_path
                    span['line_start'] = None
                # else, messages will be shown in console via msg_cb.
                add_additional(span,
                    'Errors occurred in macro %s from external crate' % (macro_name,),
                    info['level'])
                text = ''.join([x['text'] for x in span['text']])
                add_additional(span,
                    'Macro text: %s' % (text,),
                    info['level'])
            else:
                if not expansion or not expansion['def_site_span'] \
                        or 'macros>' in expansion['def_site_span']['file_name']:
                    add_additional(span,
                        'this error originates in a macro outside of the current crate',
                        info['level'])

        # Add a message for macro invocation site if available in the local
        # crate.
        if span['expansion'] and \
                'macros>' not in span['file_name'] and \
                not span['expansion']['macro_decl_name'].startswith('#['):
            invoke_span, expansion = find_span_r(span)
            add_additional(invoke_span, 'in this macro invocation', 'help')

        if span['is_primary']:
            if parent_info:
                # Primary child message.
                add_additional(span, info['message'], info['level'])
            else:
                set_primary_message(span, info['message'])

        label = span['label']
        # Some spans don't have a label.  These seem to just imply
        # that the main "message" is sufficient, and always seems
        # to happen when the span is_primary.
        #
        # This can also happen for macro expansions.
        #
        # Label with an empty string can happen for messages that have
        # multiple spans (starting in 1.21).
        if label is not None:
            # Display the label for this Span.
            add_additional(span, label, info['level'])
        if span['suggested_replacement'] is not None:
            # The "suggested_replacement" contains the code that should
            # replace the span.
            add_additional(span, None, 'help',
                suggested_replacement=span['suggested_replacement'])

    # Recurse into children (which typically hold notes).
    for child in info['children']:
        _collect_rust_messages(window, base_path, child, target_path,
                               msg_cb, parent_info.copy(),
                               message)


def _batch_and_cross_link(primary_message):
    """Creates a list of MessageBatch objects with appropriate cross links."""
    def make_file_path(msg):
        if msg.span:
            return 'file:///%s:%s:%s' % (
                msg.path.replace('\\', '/'),
                msg.span[1][0] + 1,
                msg.span[1][1] + 1,
            )
        else:
            # Arbitrarily large line number to force it to the bottom of the
            # file, since we don't know ahead of time how large the file is.
            return 'file:///%s:999999999' % (msg.path,)

    # Group messages by line.
    primary_batch = PrimaryBatch(primary_message)
    path_line_map = collections.OrderedDict()
    key = (primary_message.path, primary_message.lineno())
    path_line_map[key] = primary_batch
    for msg in primary_message.children:
        key = (msg.path, msg.lineno())
        try:
            batch = path_line_map[key]
        except KeyError:
            batch = ChildBatch(primary_batch)
            primary_batch.child_batches.append(batch)
            path_line_map[key] = batch
        batch.children.append(msg)

    def make_link_text(msg, other):
        # text for msg -> other
        if msg.path == other.path:
            if msg.lineno() < other.lineno():
                filename = '\u2193'  # down arrow
            else:
                filename = '\u2191'  # up arrow
        else:
            filename = os.path.basename(other.path)
        if other.span:
            return '%s:%s' % (filename, other.lineno() + 1,)
        else:
            return filename

    # Create cross links.
    back_url = make_file_path(primary_message)

    for (path, lineno), batch in path_line_map.items():
        if batch == primary_batch:
            continue
        # Only include a link if the message is "far away".
        msg = batch.first()
        if msg.path != primary_message.path or \
           abs(msg.lineno() - primary_message.lineno()) > 5:
            url = make_file_path(msg)
            text = make_link_text(primary_message, msg)
            primary_batch.child_links.append((url, text))
            back_text = make_link_text(msg, primary_message)
            batch.back_link = (back_url, back_text)

    return list(path_line_map.values())


def _save_batches(window, batches, msg_cb):
    """Save the batches.  This does several things:

    - Saves batches to WINDOW_MESSAGES global.
    - Updates the region_key for each message.
    - Displays phantoms if a view is already open.
    - Calls `msg_cb` for each individual message.
    """
    wid = window.id()
    try:
        path_to_batches = WINDOW_MESSAGES[wid]['paths']
    except KeyError:
        path_to_batches = collections.OrderedDict()
        WINDOW_MESSAGES[wid] = {
            'paths': path_to_batches,
            'batch_index': (-1, -1),
            'hidden': False,
        }

    for batch in batches:
        path_batches = path_to_batches.setdefault(batch.path(), [])
        # Flatten to a list of messages so each message gets a unique ID.
        num = len(list(itertools.chain.from_iterable(path_batches)))
        path_batches.append(batch)
        for i, msg in enumerate(batch):
            msg.region_key = 'rust-%i' % (num + i,)
        view = window.find_open_file(batch.path())
        if view:
            _show_phantom(view, batch)
            _draw_region_highlights(view, batch)
        if msg_cb:
            for msg in batch:
                msg_cb(msg)
