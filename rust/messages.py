"""Module for storing/displaying Rust compiler messages."""

import sublime

import collections
import html
import itertools
import os
import re
import webbrowser
from pprint import pprint

from . import util

# Key is window id.
# Value is a dictionary: {
#     'paths': {path: [msg_dict,...]},
#     'msg_index': (path_idx, message_idx)
# }
# `path` is the absolute path to the file.
# Each msg_dict has the following:
# - `level`: Message level as a string such as "error", or "info".
# - `span`: Location of the message (0-based):
#   `((line_start, col_start), (line_end, col_end))`
#   May be `None` to indicate no particular spot.
# - `is_main`: If True, this is a top-level message.  False is used for
#   attached detailed diagnostic information, child notes, etc.
# - `path`: Absolute path to the file.
# - `text`: The raw text of the message without any minihtml markup.
# - `phantom_text`: The string used for showing phantoms that includes the
#   minihtml markup.
# - `output_panel_region`: Optional Sublime Region object that indicates the
#   region in the build output panel that corresponds with this message.
WINDOW_MESSAGES = {}


LINK_PATTERN = r'(https?://[-a-zA-Z0-9@:%._+~#=]{2,256}\.[a-zA-Z]{2,6}\b[-a-zA-Z0-9@:%_+.~#?&/=]*)'


PHANTOM_TEMPLATE = """
<body id="rust-message">
    <style>
        span {{
            font-family: monospace;
        }}
        .rust-error {{
            color: {error_color};
        }}
        .rust-warning {{
            color: {warning_color};
        }}
        .rust-note {{
            color: {note_color};
        }}
        .rust-help {{
            color: {help_color};
        }}
        .rust-link {{
            background-color: var(--background);
            color: var(--bluish);
            text-decoration: none;
            border-radius: 0.5rem;
            padding: 0.1rem 0.3rem;
            border: 1px solid var(--bluish);
        }}
        .rust-links {{
            margin: 0.4rem 0rem;
        }}
        a {{
            text-decoration: inherit;
            padding: 0.35rem 0.5rem 0.45rem 0.5rem;
            position: relative;
            font-weight: bold;
        }}
    </style>
{content}
</body>
"""


def clear_messages(window):
    WINDOW_MESSAGES.pop(window.id(), None)
    for view in window.views():
        view.erase_phantoms('rust-syntax-phantom')
        view.erase_regions('rust-error')
        view.erase_regions('rust-warning')
        view.erase_regions('rust-note')
        view.erase_regions('rust-help')


def add_message(window, path, span, level, is_main, text, markup_text, msg_cb):
    """Add a message to be displayed.

    :param window: The Sublime window.
    :param path: The absolute path of the file to show the message for.
    :param span: Location of the message (0-based):
        `((line_start, col_start), (line_end, col_end))`
        May be `None` to indicate no particular spot.
    :param level: The Rust message level ('error', 'note', etc.).
    :param is_main: If True, this is a top-level message.  False is used for
        attached detailed diagnostic information, child notes, etc.
    :param text: The raw text of the message without any minihtml markup.
    :param markup_text: The message to display with minihtml markup.
    :param msg_cb: Callback that will be given the message.  May be None.
    """
    if 'macros>' in path:
        # Macros from external crates will be displayed in the console
        # via msg_cb.
        return
    wid = window.id()
    try:
        messages_by_path = WINDOW_MESSAGES[wid]['paths']
    except KeyError:
        # This is an OrderedDict to handle next/prev message.
        messages_by_path = collections.OrderedDict()
        WINDOW_MESSAGES[wid] = {
            'paths': messages_by_path,
            'msg_index': (-1, -1)
        }
    messages = messages_by_path.setdefault(path, [])

    if markup_text:
        phantom_text = PHANTOM_TEMPLATE.format(content=markup_text,
            error_color=util.get_setting('rust_syntax_error_color', 'var(--redish)'),
            warning_color=util.get_setting('rust_syntax_warning_color', 'var(--yellowish)'),
            note_color=util.get_setting('rust_syntax_note_color', 'var(--greenish)'),
            help_color=util.get_setting('rust_syntax_help_color', 'var(--bluish)'),
        )
    else:
        phantom_text = None
    to_add = {
        'path': path,
        'level': level,
        'span': span,
        'is_main': is_main,
        'text': text,
        'phantom_text': phantom_text,
    }
    if _is_duplicate(to_add, messages):
        # Don't add duplicates.
        return
    messages.append(to_add)
    view = window.find_open_file(path)
    if view:
        _show_phantom(view, level, span, phantom_text)
    if msg_cb:
        msg_cb(to_add)


def _is_duplicate(to_add, messages):
    # Primarily to avoid comparing the `output_panel_region` key.
    for message in messages:
        for key, value in to_add.items():
            if message[key] != value:
                break
        else:
            return True
    return False


def has_message_for_path(window, path):
    paths = WINDOW_MESSAGES.get(window.id(), {}).get('paths', {})
    return path in paths


def messages_finished(window):
    """This should be called after all messages have been added."""
    _draw_all_region_highlights(window)
    _sort_messages(window)


def _draw_all_region_highlights(window):
    """Drawing region outlines must be deferred until all the messages have
    been received since Sublime does not have an API to incrementally add
    them."""
    paths = WINDOW_MESSAGES.get(window.id(), {}).get('paths', {})
    for path, messages in paths.items():
        view = window.find_open_file(path)
        if view:
            _draw_region_highlights(view, messages)


def _draw_region_highlights(view, messages):
    if util.get_setting('rust_region_style', 'outline') == 'none':
        return

    regions = {
        'error': [],
        'warning': [],
        'note': [],
        'help': [],
    }
    for message in messages:
        region = _span_to_region(view, message['span'])
        if message['level'] not in regions:
            print('RustEnhanced: Unknown message level %r encountered.' % message['level'])
            message['level'] = 'error'
        regions[message['level']].append(region)

    # Remove lower-level regions that are identical to higher-level regions.
    def filter_out(to_filter, to_check):
        def check_in(region):
            for r in regions[to_check]:
                if r == region:
                    return False
            return True
        regions[to_filter] = list(filter(check_in, regions[to_filter]))
    filter_out('help', 'note')
    filter_out('help', 'warning')
    filter_out('help', 'error')
    filter_out('note', 'warning')
    filter_out('note', 'error')
    filter_out('warning', 'error')

    package_name = __package__.split('.')[0]
    gutter_style = util.get_setting('rust_gutter_style', 'shape')

    # Do this in reverse order so that errors show on-top.
    for level in ['help', 'note', 'warning', 'error']:
        # Unfortunately you cannot specify colors, but instead scopes as
        # defined in the color theme.  If the scope is not defined, then it
        # will show up as foreground color (white in dark themes).  I just use
        # "info" as an undefined scope (empty string will remove regions).
        # "invalid" will typically show up as red.
        if level == 'error':
            scope = 'invalid'
        else:
            scope = 'info'
        key = 'rust-%s' % level
        if gutter_style == 'none':
            icon = ''
        else:
            icon = 'Packages/%s/images/gutter/%s-%s.png' % (
                package_name, gutter_style, level)
        if regions[level]:
            _sublime_add_regions(
                view, key, regions[level], scope, icon,
                sublime.DRAW_NO_FILL | sublime.DRAW_EMPTY)


def _show_phantom(view, level, span, message):
    if util.get_setting('rust_phantom_style', 'normal') == 'none':
        return
    if not message:
        return
    region = _span_to_region(view, span)
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

    def click_handler(url):
        if url == 'hide':
            clear_messages(view.window())
        elif url.startswith('file:///'):
            view.window().open_file(url[8:], sublime.ENCODED_POSITION)
        else:
            webbrowser.open_new(url)

    _sublime_add_phantom(
        view,
        'rust-syntax-phantom', region,
        message,
        sublime.LAYOUT_BLOCK,
        click_handler
    )


def _span_to_region(view, span):
    if span:
        return sublime.Region(
            view.text_point(span[0][0], span[0][1]),
            view.text_point(span[1][0], span[1][1])
        )
    else:
        # Place at bottom of file for lack of anywhere better.
        return sublime.Region(view.size())


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
    messages_by_path = window_info['paths']
    items = []
    for path, messages in messages_by_path.items():
        for message in messages:
            level = {
                'error': 0,
                'warning': 1,
                'note': 2,
                'help': 3,
            }.get(message['level'], 0)
            if message['span']:
                lineno = message['span'][0][0]
            else:
                lineno = 99999999
            items.append((level, path, lineno, message))
    items.sort(key=lambda x: x[:3])
    messages_by_path = collections.OrderedDict()
    for _, path, _, message in items:
        messages = messages_by_path.setdefault(path, [])
        messages.append(message)
    window_info['paths'] = messages_by_path


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
    paths = window_info['paths']
    path, messages = _ith_iter_item(paths.items(), current_idx[0])
    msg = messages[current_idx[1]]
    _scroll_build_panel(window, msg)
    view = None
    if not transient and not force_open:
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
        if msg['span']:
            # show_at_center is buggy with newly opened views (see
            # https://github.com/SublimeTextIssues/Core/issues/538).
            # ENCODED_POSITION is 1-based.
            row, col = msg['span'][0]
        else:
            row, col = (999999999, 1)
        view = window.open_file('%s:%d:%d' % (path, row + 1, col + 1),
                                flags)
        # Block until the view is loaded.
        _show_message_wait(view, messages, current_idx)


def _show_message_wait(view, messages, current_idx):
    if view.is_loading():
        def f():
            _show_message_wait(view, messages, current_idx)
        sublime.set_timeout(f, 10)
    # The on_load event handler will call show_messages_for_view which
    # should handle displaying the messages.


def _scroll_build_panel(window, message):
    """If the build output panel is open, scroll the output to the message
    selected."""
    if 'output_panel_region' in message:
        # Defer cyclic import.
        from . import opanel
        view = window.find_output_panel(opanel.PANEL_NAME)
        if view:
            view.sel().clear()
            region = message['output_panel_region']
            view.sel().add(region)
            view.show(region)
            # Force panel to update.
            view.add_regions('bug', [region], 'bug', 'dot', sublime.HIDDEN)
            view.erase_regions('bug')


def _scroll_to_message(view, message, transient):
    """Scroll view to the message."""
    if not transient:
        view.window().focus_view(view)
    r = _span_to_region(view, message['span'])
    view.sel().clear()
    view.sel().add(r.a)
    view.show_at_center(r)
    # Work around bug in Sublime where the visual of the cursor
    # does not update.  See
    # https://github.com/SublimeTextIssues/Core/issues/485
    view.add_regions('bug', [r], 'bug', 'dot', sublime.HIDDEN)
    view.erase_regions('bug')


def show_messages_for_view(view):
    """Adds all phantoms and region outlines for a view."""
    window = view.window()
    paths = WINDOW_MESSAGES.get(window.id(), {}).get('paths', {})
    messages = paths.get(view.file_name(), None)
    if messages:
        _show_messages_for_view(view, messages)


def _show_messages_for_view(view, messages):
    for message in messages:
        _show_phantom(view,
                      message['level'],
                      message['span'],
                      message['phantom_text'])
    _draw_region_highlights(view, messages)


def _ith_iter_item(d, i):
    return next(itertools.islice(d, i, None))


def _advance_next_message(window, levels, wrap_around=False):
    """Update global msg_index to the next index."""
    try:
        win_info = WINDOW_MESSAGES[window.id()]
    except KeyError:
        return None
    paths = win_info['paths']
    path_idx, msg_idx = win_info['msg_index']
    if path_idx == -1:
        # First time.
        path_idx = 0
        msg_idx = 0
    else:
        msg_idx += 1

    while path_idx < len(paths):
        messages = _ith_iter_item(paths.values(), path_idx)
        while msg_idx < len(messages):
            msg = messages[msg_idx]
            if _is_matching_level(levels, msg):
                current_idx = (path_idx, msg_idx)
                win_info['msg_index'] = current_idx
                return current_idx
            msg_idx += 1
        path_idx += 1
        msg_idx = 0
    if wrap_around:
        # No matching entries, give up.
        return None
    else:
        # Start over at the beginning of the list.
        win_info['msg_index'] = (-1, -1)
        return _advance_next_message(window, levels, wrap_around=True)


def _last_index(paths):
    path_idx = len(paths) - 1
    msg_idx = len(_ith_iter_item(paths.values(), path_idx)) - 1
    return (path_idx, msg_idx)


def _advance_prev_message(window, levels, wrap_around=False):
    """Update global msg_index to the previous index."""
    try:
        win_info = WINDOW_MESSAGES[window.id()]
    except KeyError:
        return None
    paths = win_info['paths']
    path_idx, msg_idx = win_info['msg_index']
    if path_idx == -1:
        # First time, start at the end.
        path_idx, msg_idx = _last_index(paths)
    else:
        msg_idx -= 1

    while path_idx >= 0:
        messages = _ith_iter_item(paths.values(), path_idx)
        while msg_idx >= 0:
            msg = messages[msg_idx]
            if _is_matching_level(levels, msg):
                current_idx = (path_idx, msg_idx)
                win_info['msg_index'] = current_idx
                return current_idx
            msg_idx -= 1
        path_idx -= 1
        if path_idx >= 0:
            msg_idx = len(_ith_iter_item(paths.values(), path_idx)) - 1
    if wrap_around:
        # No matching entries, give up.
        return None
    else:
        # Start over at the end of the list.
        win_info['msg_index'] = (-1, -1)
        return _advance_prev_message(window, levels, wrap_around=True)


def _is_matching_level(levels, msg_dict):
    if not msg_dict['is_main']:
        # Only navigate to top-level messages.
        return False
    level = msg_dict['level']
    if levels == 'all':
        return True
    elif levels == 'error' and level == 'error':
        return True
    elif levels == 'warning' and level != 'error':
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
    panel_items = []
    jump_to = []
    for path_idx, (path, msgs) in enumerate(win_info['paths'].items()):
        for msg_idx, msg_dict in enumerate(msgs):
            if not msg_dict['is_main']:
                continue
            jump_to.append((path_idx, msg_idx))
            if msg_dict['span']:
                path_label = '%s:%s' % (
                    _relative_path(window, path),
                    msg_dict['span'][0][0] + 1)
            else:
                path_label = _relative_path(window, path)
            item = [msg_dict['text'], path_label]
            panel_items.append(item)

    def on_done(idx):
        _show_message(window, jump_to[idx], force_open=True)

    def on_highlighted(idx):
        _show_message(window, jump_to[idx], transient=True)

    window.show_quick_panel(panel_items, on_done, 0, 0, on_highlighted)


def add_rust_messages(window, cwd, info, target_path, msg_cb):
    """Add messages from Rust JSON to Sublime views.

    - `window`: Sublime Window object.
    - `cwd`: Directory where cargo/rustc was run.
    - `info`: Dictionary of messages from rustc or cargo.
    - `target_path`: Absolute path to the top-level source file of the target
      (lib.rs, main.rs, etc.).  May be None if it is not known.
    - `msg_cb`: Function called for each message (if not None).  It is given a
      single parameter, a dictionary of the message to display with the
      following keys:
        - `path`: Full path to the file.  None if no file associated.
        - `span`: Sublime (0-based) offsets into the file for the region
          `((line_start, col_start), (line_end, col_end))`.  None if no
          region.
        - `level`: Rust level ('error', 'warning', 'note', etc.)
        - `is_main`: If True, a top-level message.
        - `text`: Raw text of the message without markup.
    """
    # cargo check emits in a slightly different format.
    if 'reason' in info:
        if info['reason'] == 'compiler-message':
            info = info['message']
        else:
            # cargo may emit various other messages, like
            # 'compiler-artifact' or 'build-script-executed'.
            return

    # Each message dictionary contains the following:
    # - 'text': The text of the message.
    # - 'level': The level (a string such as 'error').
    # - 'span_path': Absolute path to the file for this message.
    # - 'span_region': Sublime region where the message is.  Tuple of
    #   ((line_start, column_start), (line_end, column_end)), 0-based.  None
    #   if no region.
    # - 'is_main': Boolean of whether or not this is the main message.  Only
    #   the `main_message` should be True.
    # - 'help_link': Optional string of an HTML link for additional
    #   information on the message.
    # - 'links': Optional string of HTML code that contains links to other
    #   messages (populated by _create_cross_links).  Should only be set in
    #   `main_message`.
    # - 'back_link': Optional string of HTML code that is a link back to the
    #   main message (populated by _create_cross_links).
    main_message = {}
    # List of message dictionaries, belonging to the main message.
    additional_messages = []
    _collect_rust_messages(window, cwd, info, target_path, msg_cb, {},
        main_message, additional_messages)

    messages = _create_cross_links(main_message, additional_messages)

    content_template = '<div class="{cls}">{level}{msg}{help_link}{back_link}<a href="hide">\xD7</a></div>'
    links_template = '<div class="rust-links">{indent}{links}</div>'

    last_level = None
    last_path = None
    for message in messages:
        level = message['level']
        cls = {
            'error': 'rust-error',
            'warning': 'rust-warning',
            'note': 'rust-note',
            'help': 'rust-help',
        }.get(level, 'rust-error')
        indent = '&nbsp;' * (len(level) + 2)
        if level == last_level and message['span_path'] == last_path:
            level_text = indent
        else:
            level_text = '%s: ' % (level,)
        last_level = level
        last_path = message['span_path']

        def escape_and_link(i_txt):
            i, txt = i_txt
            if i % 2:
                return '<a href="%s">%s</a>' % (txt, txt)
            else:
                return html.escape(txt, quote=False).\
                    replace('\n', '<br>' + indent)
        parts = re.split(LINK_PATTERN, message['text'])
        escaped_text = ''.join(map(escape_and_link, enumerate(parts)))

        content = content_template.format(
            cls=cls,
            level=level_text,
            msg=escaped_text,
            help_link=message.get('help_link', ''),
            back_link=message.get('back_link', ''),
        )
        add_message(window, message['span_path'], message['span_region'],
                    level, message['is_main'], message['text'], content,
                    msg_cb)

    if main_message.get('links'):
        content = links_template.format(
            indent='&nbsp;' * (len(main_message['level']) + 2),
            links=main_message['links']
        )
        add_message(window,
                    main_message['span_path'],
                    main_message['span_region'],
                    main_message['level'],
                    False, None, content, None)


def _collect_rust_messages(window, cwd, info, target_path,
                           msg_cb, parent_info,
                           main_message, additional_messages):
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
              suggestion of the code to replace this span.  If this is set, we
              actually display the 'rendered' value instead, because it's
              easier to read.
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
        - 'rendered': Optional string (may be None).  Currently only used by
          suggested replacements.  If a child has a span with
          'suggested_replacement' set, then this a suggestion of how the line
          should be written.

    - `parent_info`: Dictionary used for tracking "children" messages.
      Currently only has 'span' key, the span of the parent to display the
      message (for children without spans).
    - `main_message`: Dictionary where we store the main message information.
    - `additional_messages`:  List where we add dictionaries of messages that
      are associated with the main message.
    """
    # Include "notes" tied to errors, even if warnings are disabled.
    if (info['level'] != 'error' and
        util.get_setting('rust_syntax_hide_warnings', False) and
        not parent_info
       ):
        return

    def make_span_path(span):
        return os.path.realpath(os.path.join(cwd, span['file_name']))

    def make_span_region(span):
        # Sublime text is 0 based whilst the line/column info from
        # rust is 1 based.
        if span.get('line_start'):
            return ((span['line_start'] - 1, span['column_start'] - 1),
                    (span['line_end'] - 1, span['column_end'] - 1))
        else:
            return None

    def set_primary_message(span, message):
        parent_info['span'] = span
        # Not all codes have explanations (yet).
        if info['code'] and info['code']['explanation']:
            # TODO
            # This could potentially be a link that opens a Sublime popup, or
            # a new temp buffer with the contents of 'explanation'.
            # (maybe use sublime-markdown-popups)
            main_message['help_link'] = \
                ' <a href="https://doc.rust-lang.org/error-index.html#%s">?</a>' % (
                    info['code']['code'],)
        main_message['span_path'] = make_span_path(span)
        main_message['span_region'] = make_span_region(span)
        main_message['text'] = message
        main_message['level'] = info['level']
        main_message['is_main'] = True

    def add_additional(span, text, level):
        additional_messages.append({
            'span_path': make_span_path(span),
            'span_region': make_span_region(span),
            'text': text,
            'level': level,
            'is_main': False,
        })

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
                    imsg.startswith('cannot continue')):
                if target_path:
                    # Display at the bottom of the root path (like main.rs)
                    # for lack of a better place to put it.
                    fake_span = {'file_name': target_path}
                    set_primary_message(fake_span, imsg)
                else:
                    # Not displayed as a phantom since we don't know where to
                    # put it.
                    if msg_cb:
                        msg_cb({
                            'path': None,
                            'level': info['level'],
                            'span': None,
                            'is_main': True,
                            'text': imsg,
                        })

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
                # Check if the main message is already set since there might
                # be multiple spans that are primary (in which case, we
                # arbitrarily show the main message on the first one).
                if not main_message:
                    set_primary_message(span, info['message'])

        label = span['label']
        # Some spans don't have a label.  These seem to just imply
        # that the main "message" is sufficient, and always seems
        # to happen when the span is_primary.
        #
        # This can also happen for macro expansions.
        if label:
            # Display the label for this Span.
            add_additional(span, label, info['level'])
        if span['suggested_replacement']:
            # The "suggested_replacement" contains the code that
            # should replace the span.  However, it can be easier to
            # read if you repeat the entire line (from "rendered").
            add_additional(span, info['rendered'], 'help')

    # Recurse into children (which typically hold notes).
    for child in info['children']:
        _collect_rust_messages(window, cwd, child, target_path,
                               msg_cb, parent_info.copy(),
                               main_message, additional_messages)


def _create_cross_links(main_message, additional_messages):
    """Returns a list of dictionaries of messages to be displayed.

    This is responsible for creating links from the main message to any
    additional messages.
    """
    if not main_message:
        return []

    def make_file_path(msg):
        if msg['span_region']:
            return 'file:///%s:%s:%s' % (
                msg['span_path'].replace('\\', '/'),
                msg['span_region'][0][0] + 1,
                msg['span_region'][0][1] + 1,
            )
        else:
            # Arbitrarily large line number to force it to the bottom of the
            # file, since we don't know ahead of time how large the file is.
            return 'file:///%s:999999999' % (msg['span_path'],)

    back_link = '<a href="%s">\u2190</a>' % (make_file_path(main_message),)

    def get_lineno(msg):
        if msg['span_region']:
            return msg['span_region'][0][0]
        else:
            return 999999999

    link_set = set()
    links = []
    link_template = '<a href="{url}" class="rust-link">Note: {filename}{lineno}</a>'
    for msg in additional_messages:
        msg_lineno = get_lineno(msg)
        seen_key = (msg['span_path'], msg_lineno)
        # Only include a link if it is not close to the main message.
        if msg['span_path'] != main_message['span_path'] or \
           abs(msg_lineno - get_lineno(main_message)) > 5:
            if seen_key in link_set:
                continue
            link_set.add(seen_key)
            if msg['span_region']:
                lineno = ':%s' % (msg_lineno + 1,)
            else:
                # AFAIK, this code path is not possible, but leaving it here
                # to be safe.
                lineno = ''
            if msg['span_path'] == main_message['span_path']:
                if get_lineno(msg) < get_lineno(main_message):
                    filename = '\u2191'  # up arrow
                else:
                    filename = '\u2193'  # down arrow
            else:
                filename = os.path.basename(msg['span_path'])
            links.append(link_template.format(
                url=make_file_path(msg),
                filename=filename,
                lineno=lineno,
            ))
            msg['back_link'] = back_link

    if links:
        link_text = '\n'.join(links)
    else:
        link_text = ''
    main_message['links'] = link_text

    result = additional_messages[:]
    result.insert(0, main_message)
    return result
