"""Store-level errors the API maps onto stable HTTP codes."""


class NotFoundError(Exception):
    """A requested business resource does not exist; carries the resource kind."""

    def __init__(self, resource: str, identifier: str) -> None:
        self.resource = resource
        self.identifier = identifier
        super().__init__(f"{resource} not found: {identifier}")
