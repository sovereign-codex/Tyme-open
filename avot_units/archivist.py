from datetime import datetime
from pathlib import Path


class Archivist:
    """Persists Sovereign Architecture scrolls into the repository."""

    def save_scroll(self, scroll: str, title: str, directory: str = "docs") -> str:
        if not scroll.strip():
            raise ValueError("Archivist cannot store an empty scroll.")
        target_dir = Path(directory)
        target_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        safe_title = title.strip().lower().replace(" ", "-") or "scroll"
        filename = f"{safe_title}-{timestamp}.md"
        destination = target_dir / filename
        destination.write_text(scroll)
        return str(destination)

    def archive(self, scroll: str, title: str, directory: str = "docs") -> str:
        return self.save_scroll(scroll, title, directory)
