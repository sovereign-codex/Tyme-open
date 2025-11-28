class Guardian:
    """Validates artifacts produced by the Fabricator."""

    def validate_scroll(self, scroll: str) -> None:
        if not scroll or not scroll.strip():
            raise ValueError("Guardian rejected the scroll because it is empty.")
        if "Sovereign" not in scroll:
            raise ValueError("Guardian requires the scroll to declare Sovereign provenance.")

    def enforce(self, scroll: str) -> None:
        self.validate_scroll(scroll)
