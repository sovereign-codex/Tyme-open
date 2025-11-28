from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


class Archivist:
    """Persists Sovereign Architecture scrolls into the repository."""

    def _inject_visuals_section(
        self, scroll: str, visuals: Dict[str, str], version: Optional[str] = None
    ) -> str:
        visuals_section = [
            "## Architecture Visuals",
            f"![Architecture Diagram]({visuals.get('png','')})",
            f"[View SVG]({visuals.get('svg','')})",
            "",
        ]

        if visuals.get("topology"):
            visuals_section.extend(
                [
                    "## Lattice Graph",
                    f"[View Interactive Graph](/panel/lattice.html?version={version or 'latest'})",
                    "",
                ]
            )

        if not scroll.strip():
            title_line = f"# Sovereign Architecture v{version or 'unknown'}"
            return "\n".join([title_line, *visuals_section, ""])

        lines = scroll.splitlines()
        for idx, line in enumerate(lines):
            if line.startswith("#"):
                insert_at = idx + 1
                lines[insert_at:insert_at] = visuals_section
                return "\n".join(lines)

        title_line = f"# Sovereign Architecture v{version or 'unknown'}"
        return "\n".join([title_line, *visuals_section, ""] + lines)

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

    def archive(
        self,
        scroll: str,
        title: str,
        directory: str = "docs",
        visuals: Optional[Dict[str, str]] = None,
        version: Optional[str] = None,
    ) -> str:
        if visuals:
            scroll = self._inject_visuals_section(scroll, visuals, version)

        md = scroll

        md += "\n## Epoch Chronicle\n"
        md += f"[View Epoch Log](/chronicle/epoch-log.md)\n\n"

        return self.save_scroll(md, title, directory)
