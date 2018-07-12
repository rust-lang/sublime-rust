"""Themes for different message styles."""

from . import util
from .batch import *


POPUP_CSS = 'body { margin: 0.25em; }'


def _help_link(code):
    if code:
        return ' <a href="https://doc.rust-lang.org/error-index.html#%s" class="rust-help-link">?</a>' % (
            code,)
    else:
        return ''


class Theme:

    """Base class for themes."""

    def render(self, view, batch, for_popup=False):
        """Return a minihtml string of the content in the message batch."""
        raise NotImplementedError()


class ClearTheme(Theme):

    """Theme with a clear background, and colors matching the user's color
    scheme."""

    TMPL = util.multiline_fix("""
        <style>
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
            .rust-button {{
                color: var(--bluish);
                text-decoration: none;
                border-radius: 0.3rem;
                padding: 0.2rem 0.5rem;
                border: 1px solid var(--bluish);
            }}
            .rust-links {{
                margin: 0.4rem 0rem;
            }}
            .rust-replacement {{
                padding: 0.5rem 0 0.5rem 2rem;
            }}
            .rust-close-link {{
                font-family: var(--font-mono);
                font-weight: bold;
                padding: 0rem 0.5rem;
                text-decoration: none;
            }}
            .rust-help-link {{
                font-weight: bold;
            }}

            {extra_css}
        </style>
        <body id="rust-message">
        {content}
        </body>
    """)

    MSG_TMPL = util.multiline_fix("""
        <div class="rust-{level}">
            {level_text}{text}{help_link}{close_link}
        </div>
    """)

    LINK_TMPL = util.multiline_fix("""
        <div class="rust-links">
            <a href="{url}" class="rust-link">{text} {path}</a>
        </div>
    """)

    def render(self, view, batch, for_popup=False):
        if for_popup:
            extra_css = POPUP_CSS
        else:
            extra_css = ''

        # Collect all the messages for this batch.
        msgs = []
        last_level = None
        for i, msg in enumerate(batch):
            text = msg.escaped_text(view, '')
            if not text:
                continue
            if msg.minihtml_text:
                level_text = ''
            else:
                if msg.level == last_level:
                    level_text = '&nbsp;' * (len(msg.level) + 2)
                else:
                    level_text = '%s: ' % (msg.level,)
            last_level = msg.level
            if i == 0:
                # Only show close link on first message of a batch.
                close_link = '&nbsp;<a class="rust-close-link" href="hide">\xD7</a>'
            else:
                close_link = ''
            msgs.append(self.MSG_TMPL.format(
                level=msg.level,
                level_text=level_text,
                text=text,
                help_link=_help_link(msg.code),
                close_link=close_link,
            ))

        # Add cross-links.
        if isinstance(batch, PrimaryBatch):
            for url, path in batch.child_links:
                msgs.append(self.LINK_TMPL.format(
                    url=url, text='See Also:', path=path))
        else:
            if batch.back_link:
                msgs.append(self.LINK_TMPL.format(
                    url=batch.back_link[0],
                    text='See Primary:',
                    path=batch.back_link[1]))

        return self.TMPL.format(
            error_color=util.get_setting('rust_syntax_error_color'),
            warning_color=util.get_setting('rust_syntax_warning_color'),
            note_color=util.get_setting('rust_syntax_note_color'),
            help_color=util.get_setting('rust_syntax_help_color'),
            content=''.join(msgs),
            extra_css=extra_css)


class SolidTheme(Theme):

    """Theme with a solid background color."""

    TMPL = util.multiline_fix("""
        <style>
            .rust-block {{
                padding: 0.4rem 0.7rem;
                border-radius: 0.3rem;
                margin: 0.2rem 0;
                color: #ffffff;
            }}
            .rust-links {{
                padding: 0.4rem 0.7rem 0.2rem 0.7rem;
                color: #ffffff;
            }}
            .rust-secondary-block {{
                border-radius: 0.3rem;
                padding: 0.0rem 0.2rem 0.4rem 0.2rem;
                color: #ffffff;
            }}
            .rust-error {{
                background-color: #652a2a;
            }}
            .rust-warning {{
                background-color: #61532e;
            }}
            .rust-note {{
                background-color: #568003;
            }}
            .rust-help {{
                background-color: #387580;
            }}
            .rust-close-link {{
                background-color: color(#000000 alpha(0.6));
                color: #ffffff;
                border-radius: 100rem;
                font-family: var(--font-mono);
                padding: 0.05rem 0.3rem 0.15rem 0.3rem;
                line-height: 1rem;
                text-decoration: none;
            }}
            .rust-button {{
                background-color: color(#000000 alpha(0.6));
                padding: 0.07rem 0.5rem;
                border-radius: 0.3rem;
                color: #ffffff;
                text-decoration: none;
            }}
            .rust-replacement {{
                display: inline;
            }}
            .rust-level-icon {{
                width: 1rem;
                height: 1rem;
            }}
            .rust-help-link {{
                font-weight: bold;
            }}

            {extra_css}

        </style>
        <body id="rust-message">
        {content}
        </body>
    """)

    PRIMARY_MSG_TMPL = util.multiline_fix("""
        <div class="rust-block rust-{level}">
            {icon}&nbsp;{text}{help_link}&nbsp;<a class="rust-close-link" href="hide">\xD7</a>
            {children}
            {links}
        </div>
    """)

    SECONDARY_MSG_TMPL = util.multiline_fix("""
        <div class="rust-secondary-block rust-{level}">
            {children}
            {links}
        </div>
    """)

    CHILD_TMPL = util.multiline_fix("""
        <div class="rust-block rust-{level}">{icon}&nbsp;{text}</div>
    """)

    LINK_TMPL = util.multiline_fix("""
        <div class="rust-links"><a href="{url}" class="rust-button">{text} {path}</a></div>
    """)

    def render(self, view, batch, for_popup=False):

        def icon(level):
            # minihtml does not support switching resolution for images based on DPI.
            # Always use the @2x images, and downscale on 1x displays.  It doesn't
            # look as good, but is close enough.
            # See https://github.com/SublimeTextIssues/Core/issues/2228
            path = util.icon_path(level, res=2)
            if not path:
                return ''
            else:
                return '<img class="rust-level-icon" src="res://%s">' % (path,)

        if for_popup:
            extra_css = POPUP_CSS
        else:
            extra_css = ''

        # Collect all the child messages together.
        children = []
        for child in batch.children:
            # Don't show the icon for children with the same level as the
            # primary message.
            if isinstance(batch, PrimaryBatch) and child.level == batch.primary_message.level:
                child_icon = icon('none')
            else:
                child_icon = icon(child.level)
            minihtml_text = child.escaped_text(view, '&nbsp;' + icon('none'))
            if minihtml_text:
                txt = self.CHILD_TMPL.format(level=child.level,
                                             icon=child_icon,
                                             text=minihtml_text)
                children.append(txt)

        if isinstance(batch, PrimaryBatch):
            links = []
            for url, path in batch.child_links:
                links.append(
                    self.LINK_TMPL.format(
                        url=url, text='See Also:', path=path))
            text = batch.primary_message.escaped_text(view, '')
            if not text and not children:
                return None
            content = self.PRIMARY_MSG_TMPL.format(
                level=batch.primary_message.level,
                icon=icon(batch.primary_message.level),
                text=text,
                help_link=_help_link(batch.primary_message.code),
                children=''.join(children),
                links=''.join(links))
        else:
            if batch.back_link:
                link = self.LINK_TMPL.format(url=batch.back_link[0],
                                             text='See Primary:',
                                             path=batch.back_link[1])
            else:
                link = ''
            content = self.SECONDARY_MSG_TMPL.format(
                level=batch.primary_batch.primary_message.level,
                icon=icon(batch.primary_batch.primary_message.level),
                children=''.join(children),
                links=link)

        return self.TMPL.format(content=content, extra_css=extra_css)


class TestTheme(Theme):

    """Theme used by tests for verifying which messages are displayed."""

    def __init__(self):
        self.path_messages = {}

    def render(self, view, batch, for_popup=False):
        from .messages import Message
        messages = self.path_messages.setdefault(batch.first().path, [])
        for msg in batch:
            # Region-only messages will get checked by the region-checking
            # code.
            if msg.text or msg.minihtml_text:
                messages.append(msg)

        # Create fake messages for the links to simplify the test code.
        def add_fake(msg, text):
            fake = Message()
            fake.text = text
            fake.span = msg.span
            fake.path = msg.path
            fake.level = ''
            messages.append(fake)

        if isinstance(batch, PrimaryBatch):
            for link in batch.child_links:
                add_fake(batch.primary_message, 'See Also: ' + link[1])
        else:
            if batch.back_link:
                add_fake(batch.first(), 'See Primary: ' + batch.back_link[1])
        return None


THEMES = {
    'clear': ClearTheme(),
    'solid': SolidTheme(),
    'test': TestTheme(),
}
