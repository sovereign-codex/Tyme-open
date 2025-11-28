from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass
class PullRequestPayload:
    title: str
    body: str
    head: str
    base: str


class PRGenerator:
    """Builds pull request payloads from Sovereign Architecture scrolls."""

    def generate(
        self,
        title: str,
        summary: str,
        head: str,
        base: str,
        scroll_path: str,
        notes: Optional[str] = None,
    ) -> Dict[str, str]:
        body = self._render_body(summary=summary, scroll_path=scroll_path, notes=notes)
        payload = PullRequestPayload(title=title, body=body, head=head, base=base)
        return payload.__dict__

    def _render_body(self, summary: str, scroll_path: str, notes: Optional[str]) -> str:
        lines = ["## Sovereign Architecture Summary", summary.strip()]
        if notes:
            lines.append("\n## Fabrication Notes")
            lines.append(notes.strip())
        resolved_path = Path(scroll_path).as_posix()
        lines.append("\n## Archivist Scroll")
        lines.append(f"Scroll saved at `{resolved_path}`. Please review the artifact within the repository.")
        return "\n\n".join(lines)
