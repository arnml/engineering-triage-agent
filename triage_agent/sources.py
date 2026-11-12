from pathlib import Path
import os
import re


SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "dist", "build", "__pycache__"}
TEXT_SUFFIXES = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs", ".cs",
    ".rb", ".php", ".sql", ".yaml", ".yml", ".toml", ".json", ".md", ".sh",
    ".env.example", ".txt",
}


def read_log_excerpt(path: str | None, terms: list[str], max_chars: int = 16000) -> str:
    if not path:
        return "No log file supplied."
    log_path = Path(path).expanduser().resolve()
    if not log_path.is_file():
        return f"Log file not found: {log_path}"
    # Read only the tail so a large log cannot overwhelm the model context.
    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-5000:]
    terms = [t.lower() for t in terms if t.strip()]
    selected = [line for line in lines if not terms or any(t in line.lower() for t in terms)]
    return "\n".join(selected[-300:])[-max_chars:] or "No matching log lines found."


def inspect_repository(path: str | None, terms: list[str], max_files: int, max_file_bytes: int) -> str:
    if not path:
        return "No repository path supplied."
    root = Path(path).expanduser().resolve()
    if not root.is_dir():
        return f"Repository directory not found: {root}"
    needles = {t.lower() for t in terms if len(t.strip()) > 1}
    matches: list[str] = []
    scanned = 0
    for current, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith("."))
        for name in sorted(files):
            file_path = Path(current, name)
            if file_path.suffix.lower() not in TEXT_SUFFIXES or file_path.stat().st_size > max_file_bytes:
                continue
            scanned += 1
            if scanned > max_files:
                break
            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            lines = content.splitlines()
            relevant = [i for i, line in enumerate(lines) if any(term in line.lower() for term in needles)]
            if relevant:
                blocks = []
                for i in relevant[:8]:
                    start, end = max(0, i - 2), min(len(lines), i + 3)
                    blocks.append("\n".join(f"{j + 1}: {lines[j]}" for j in range(start, end)))
                relative = file_path.relative_to(root)
                matches.append(f"--- {relative} ---\n" + "\n...\n".join(blocks))
        if scanned > max_files:
            break
    return "\n\n".join(matches)[:24000] or f"No source matches found (scanned up to {max_files} text files)."


def terms_from_incident(incident: str) -> list[str]:
    # Keep useful technical tokens while dropping common words and tiny fragments.
    tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_.-]{2,}", incident)
    stop = {"the", "and", "for", "with", "from", "this", "that", "when", "error", "failed"}
    return list(dict.fromkeys(t for t in tokens if t.lower() not in stop))[:8]
