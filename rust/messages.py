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
# - `level`
# - `span`
# - `is_main`
# - `message`
WINDOW_MESSAGES = {}


LINK_PATTERN = r'(https?://[-a-zA-Z0-9@:%._+~#=]{2,256}\.[a-zA-Z]{2,6}\b[-a-zA-Z0-9@:%_+.~#?&/=]*)'


def clear_messages(window):
    WINDOW_MESSAGES.pop(window.id(), None)
    for view in window.views():
        view.erase_phantoms('rust-syntax-phantom')
        view.erase_regions('rust-error')
        view.erase_regions('rust-info')


def add_message(window, path, level, span, is_main, message):
    """Add a message to be displayed.

    :param window: The Sublime window.
    :param path: The absolute path of the file to show the message for.
    :param level: The Rust message level ('error', 'note', etc.).
    :param span: Location of the message (0-based):
        `((line_start, col_start), (line_end, col_end))`
        May be `None` to indicate no particular spot.
    :param is_main: If True, this is a top-level message.  False is used for
        attached detailed diagnostic information, child notes, etc.
    :param message: The message to display.
    """
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
    to_add = {
        'level': level,
        'span': span,
        'is_main': is_main,
        'message': message,
    }
    if to_add in messages:
        # Don't add duplicates.
        return
    messages.append(to_add)
    view = window.find_open_file(path)
    if view:
        _show_phantom(view, level, span, message)


def has_message_for_path(window, path):
    paths = WINDOW_MESSAGES.get(window.id(), {}).get('paths', {})
    return path in paths


def draw_all_region_highlights(window):
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
    error_regions = []
    info_regions = []
    error_region_set = set()
    for message in messages:
        region = _span_to_region(view, message['span'])
        if message['level'] == 'error':
            error_regions.append(region)
            error_region_set.add((region.a, region.b))
        else:
            info_regions.append(region)
    # Filter out identical info regions.
    info_regions = list(filter(lambda x: (x.a, x.b) not in error_region_set,
                               info_regions))

    # Unfortunately you cannot specify colors, but instead scopes as
    # defined in the color theme.  If the scope is not defined, then it
    # will show up as foreground color (white in dark themes).  I just use
    # "info" as an undefined scope (empty string will remove regions).
    # "invalid" will typically show up as red.

    # Is DRAW_EMPTY necessary?  Is it possible to have a zero-length span?
    _sublime_add_regions(
        view, 'rust-error', error_regions, 'invalid', '',
        sublime.DRAW_NO_FILL | sublime.DRAW_EMPTY)
    _sublime_add_regions(
        view, 'rust-info', info_regions, 'info', '',
        sublime.DRAW_NO_FILL | sublime.DRAW_EMPTY)


def _show_phantom(view, level, span, message):
    if util.get_setting('rust_phantom_style', 'normal') == 'none':
        return
    region = _span_to_region(view, span)
    # For some reason, with LAYOUT_BELOW, if you have a multi-line
    # region, the phantom is only displayed under the first line.  I
    # think it makes more sense for the phantom to appear below the
    # last line.
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
        else:
            webbrowser.open_new(url)

    _sublime_add_phantom(
        view,
        'rust-syntax-phantom', region,
        message,
        sublime.LAYOUT_BELOW,
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


def show_next_message(window, levels):
    current_idx = _advance_next_message(window, levels)
    _show_message(window, levels, current_idx)


def show_prev_message(window, levels):
    current_idx = _advance_prev_message(window, levels)
    _show_message(window, levels, current_idx)


def _show_message(window, levels, current_idx):
    if current_idx is None:
        return
    try:
        window_info = WINDOW_MESSAGES[window.id()]
    except KeyError:
        return
    paths = window_info['paths']
    path, messages = _ith_iter_item(paths.items(), current_idx[0])
    view = window.find_open_file(path)
    if view:
        _scroll_to_message(view, messages, current_idx)
    else:
        # show_at_center is buggy with newly opened views (see
        # https://github.com/SublimeTextIssues/Core/issues/538).
        # ENCODED_POSITION is 1-based.
        msg = messages[current_idx[1]]
        row, col = msg['span'][0]
        view = window.open_file('%s:%d:%d' % (path, row + 1, col + 1),
                                sublime.ENCODED_POSITION)
        _show_message_wait(view, levels, messages, current_idx)


def _show_message_wait(view, levels, messages, current_idx):
    if view.is_loading():
        def f():
            _show_message_wait(view, levels, messages, current_idx)
        sublime.set_timeout(f, 10)
    # The on_load event handler will call show_messages_for_view which
    # should handle displaying the messages.


def _scroll_to_message(view, messages, current_idx):
    """Scroll view to the message."""
    view.window().focus_view(view)
    msg = messages[current_idx[1]]
    r = _span_to_region(view, msg['span'])
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
                      message['message'])
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


def add_rust_messages(window, cwd, info, target_path, msg_cb):
    """Add messages from Rust JSON to Sublime views.

    - `window`: Sublime Window object.
    - `cwd`: Directory where cargo/rustc was run.
    - `info`: Dictionary of messages from rustc or cargo.
    - `target_path`: Absolute path to the top-level source file of the target
      (lib.rs, main.rs, etc.).  May be None if it is not known.
    - `msg_cb`: Function called for each message (if not None).  Parameters
      are:
          - `path`: Full path to the file.  None if no file associated.
          - `span_region`: Sublime (0-based) offsets into the file for the
            region `((line_start, col_start), (line_end, col_end))`.  None if
            no region.
          - `is_main`: If True, a top-level message.
          - `message`: Text of the message.
          - `level`: Rust level ('error', 'warning', 'note', etc.)
    """
    # cargo check emits in a slightly different format.
    if 'reason' in info:
        if info['reason'] == 'compiler-message':
            info = info['message']
        else:
            # cargo may emit various other messages, like
            # 'compiler-artifact' or 'build-script-executed'.
            return
    _add_rust_messages(window, cwd, info, target_path, msg_cb, {})


def _add_rust_messages(window, cwd, info, target_path,
                       msg_cb, parent_info):
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
              to be marked as primary.
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
          same format) of associated information.
        - 'rendered': Optional string (may be None).  Currently only used by
          suggested replacements.  If a child has a span with
          'suggested_replacement' set, then this a suggestion of how the line
          should be written.

    - `parent_info`: Dictionary used for tracking "children" messages.
      Includes 'view' and 'region' keys to indicate where a child message
      should be displayed.
    """
    error_colour = util.get_setting('rust_syntax_error_color', 'var(--redish)')
    warning_colour = util.get_setting('rust_syntax_warning_color', 'var(--yellowish)')

    # Include "notes" tied to errors, even if warnings are disabled.
    if (info['level'] != 'error' and
        util.get_setting('rust_syntax_hide_warnings', False) and
        not parent_info
       ):
        return

    # TODO: Consider matching the colors used by rustc.
    # - error: red
    #     `bug` appears as "error: internal compiler error"
    # - warning: yellow
    # - note: bright green
    # - help: cyan
    is_error = info['level'] == 'error'
    if is_error:
        base_color = error_colour
    else:
        base_color = warning_colour

    msg_template = """
        <body id="rust-message">
            <style>
                span {{
                    font-family: monospace;
                }}
                .rust-error {{
                    color: %s;
                }}
                .rust-additional {{
                    color: var(--yellowish);
                }}
                a {{
                    text-decoration: inherit;
                    padding: 0.35rem 0.5rem 0.45rem 0.5rem;
                    position: relative;
                    font-weight: bold;
                }}
            </style>
            <span class="{cls}">{level}: {msg} {extra}<a href="hide">\xD7</a></span>
        </body>""" % (base_color,)

    def _add_message(path, span_region, is_main, message, extra=''):
        if info['level'] == 'error':
            cls = 'rust-error'
        else:
            cls = 'rust-additional'

        # Rust performs some pretty-printing for things like suggestions,
        # attempt to retain some of the formatting.  This isn't perfect
        # (doesn't line up perfectly), not sure why.
        def escape_and_link(i_txt):
            i, txt = i_txt
            if i % 2:
                return '<a href="%s">%s</a>' % (txt, txt)
            else:
                return html.escape(txt, quote=False).\
                    replace('\n', '<br>').replace(' ', '&nbsp;')
        parts = re.split(LINK_PATTERN, message)
        escaped_message = ''.join(map(escape_and_link, enumerate(parts)))
        content = msg_template.format(
            cls=cls,
            level=info['level'],
            msg=escaped_message,
            extra=extra
        )
        add_message(window, path, info['level'], span_region,
                    is_main, content)
        if msg_cb:
            msg_cb(path, span_region, is_main, message, info['level'])

    def add_primary_message(path, span_region, is_main, message):
        parent_info['path'] = path
        parent_info['span'] = span_region
        # Not all codes have explanations (yet).
        if info['code'] and info['code']['explanation']:
            # TODO
            # This could potentially be a link that opens a Sublime popup, or
            # a new temp buffer with the contents of 'explanation'.
            # (maybe use sublime-markdown-popups)
            extra = ' <a href="https://doc.rust-lang.org/error-index.html#%s">?</a>' % (info['code']['code'],)
        else:
            extra = ''
        _add_message(path, span_region, is_main, message, extra)

    if len(info['spans']) == 0:
        if parent_info:
            # This is extra info attached to the parent message.
            add_primary_message(parent_info['path'],
                                parent_info['span'],
                                False,
                                info['message'])
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
                    add_primary_message(target_path, None, True, imsg)
                else:
                    if msg_cb:
                        msg_cb(None, None, True, imsg, info['level'])

    for span in info['spans']:
        is_primary = span['is_primary']

        if 'macros>' in span['file_name']:
            # Rust gives the chain of expansions for the macro, which we don't
            # really care about.  We want to find the site where the macro was
            # invoked.  I'm not entirely confident this is the best way to do
            # this, but it seems to work.  This is roughly emulating what is
            # done in librustc_errors/emitter.rs fix_multispan_in_std_macros.
            def find_span_r(span):
                if span['expansion']:
                    return find_span_r(span['expansion']['span'])
                else:
                    return span
            span = find_span_r(span)
            if span is None:
                continue

        span_path = os.path.realpath(os.path.join(cwd, span['file_name']))
        # Sublime text is 0 based whilst the line/column info from
        # rust is 1 based.
        span_region = ((span['line_start'] - 1, span['column_start'] - 1),
                       (span['line_end'] - 1, span['column_end'] - 1))

        label = span['label']
        # Some spans don't have a label.  These seem to just imply
        # that the main "message" is sufficient, and always seems
        # to happen when the span is_primary.
        #
        # This can also happen for macro expansions.
        if label:
            # Display the label for this Span.
            _add_message(span_path, span_region, False, label)
        if is_primary:
            # Show the overall error message.
            add_primary_message(span_path, span_region, True, info['message'])
        if span['suggested_replacement']:
            # The "suggested_replacement" contains the code that
            # should replace the span.  However, it can be easier to
            # read if you repeat the entire line (from "rendered").
            _add_message(span_path, span_region, False, info['rendered'])

    # Recurse into children (which typically hold notes).
    for child in info['children']:
        _add_rust_messages(window, cwd, child, target_path,
                           msg_cb, parent_info.copy())
