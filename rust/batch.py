"""Classes used for aggregating messages that are on the same line."""


class MessageBatch:

    """Abstract base class for a set of messages that apply to the same line.

    :ivar children: List of additional messages, may be empty.
    :ivar hidden: Boolean if this message should be displayed.
    """

    hidden = False

    def __init__(self):
        self.children = []

    def __iter__(self):
        """Iterates over all messages in the batch."""
        raise NotImplementedError()

    def path(self):
        """Returns the file path of the batch."""
        raise NotImplementedError()

    def first(self):
        """Returns the first message of the batch."""
        raise NotImplementedError()

    def dismiss(self):
        """Permanently remove this message and all its children from the
        view."""
        raise NotImplementedError()

    def _dismiss(self, window):
        # There is a awkward problem with Sublime and
        # add_regions/erase_regions. The regions are part of the undo stack,
        # which means even after we erase them, they can come back from the
        # dead if the user hits undo. We simply mark these as "hidden" to
        # ensure that `clear_messages` can erase any of these zombie regions.
        # See https://github.com/SublimeTextIssues/Core/issues/1121
        # This is imperfect, since the user could do the following:
        # 1) Build 2) Type some text 3) Clear Messages 4) Undo
        # which will resurrect the regions without an easy way to remove them
        # (user has to close and reopen the file).  I don't know of any good
        # workarounds.
        for msg in self:
            view = window.find_open_file(msg.path)
            if view:
                view.erase_regions(msg.region_key)
                view.erase_phantoms(msg.region_key)


class PrimaryBatch(MessageBatch):

    """A batch of messages with the primary message.

    :ivar primary_message: The primary message object.
    :ivar child_batches: List of `ChildBatch` batches associated with this
        batch.
    :ivar child_links: List of `(url, text)` tuples for links to child batches
        that are "far away".
    """

    primary_message = None

    def __init__(self, primary_message):
        super(PrimaryBatch, self).__init__()
        self.primary_message = primary_message
        self.child_batches = []
        self.child_links = []

    def __iter__(self):
        yield self.primary_message
        for child in self.children:
            yield child

    def path(self):
        return self.primary_message.path

    def first(self):
        return self.primary_message

    def dismiss(self, window):
        self.hidden = True
        self._dismiss(window)
        for batch in self.child_batches:
            batch._dismiss(window)


class ChildBatch(MessageBatch):

    """A batch of messages that are associated with a primary message.

    :ivar primary_batch: The `PrimaryBatch` this is associated with.
    :ivar back_link: Tuple of `(url, text)` of the link to the primary batch
        if it is "far away" (otherwise None).
    """

    primary_batch = None
    back_link = None

    def __init__(self, primary_batch):
        super(ChildBatch, self).__init__()
        self.primary_batch = primary_batch

    def __iter__(self):
        for child in self.children:
            yield child

    def path(self):
        return self.children[0].path

    def first(self):
        return self.children[0]

    def dismiss(self, window):
        self.hidden = True
        self.primary_batch.dismiss(window)
