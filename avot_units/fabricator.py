from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Fabrication:
    summary: str
    notes: Optional[str]
    created_at: datetime


class Fabricator:
    """Generates Sovereign Architecture scroll content."""

    def create_scroll(self, summary: str, notes: Optional[str] = None) -> str:
        timestamp = datetime.utcnow().isoformat() + "Z"
        header = ["# Sovereign Architecture Scroll", f"Generated at: {timestamp}"]
        body = ["## Summary", summary.strip() or "No summary provided."]
        if notes:
            body.append("\n## Fabricator Notes")
            body.append(notes.strip())
        footer = ["\n---", "Prepared by the AVOT Fabricator."]
        return "\n\n".join(header + body + footer)
