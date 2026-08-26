from pathlib import Path

import pathspec

EXCLUDE_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    "venv",
    ".venv",
    "env",
    ".env",
    "build",
    "dist",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    "target",
    "vendor",
    ".next",
    ".nuxt",
    "coverage",
    ".eggs",
    "*.egg-info",
}

SUPPORTED_EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".jsx"}
MAX_FILE_SIZE = 100_000  # 100KB


def load_gitignore(repo_path: Path) -> pathspec.PathSpec:
    gitignore_path = repo_path / ".gitignore"
    if gitignore_path.exists():
        patterns = gitignore_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        return pathspec.PathSpec.from_lines("gitwildmatch", patterns)
    return pathspec.PathSpec([])


def should_skip_path(rel_path: str, gitignore: pathspec.PathSpec) -> bool:
    parts = Path(rel_path).parts

    for part in parts:
        if part in EXCLUDE_DIRS:
            return True
        if any(part.endswith(ext) for ext in (".pyc", ".pyo", ".so", ".o", ".min.js", ".min.css")):
            return True

    if gitignore.match_file(rel_path):
        return True

    return False


def scan_repository(repo_path: str) -> list[dict]:
    """Scan a repository and return file metadata for supported files."""
    root = Path(repo_path).resolve()
    if not root.is_dir():
        raise ValueError(f"Not a directory: {repo_path}")

    gitignore = load_gitignore(root)
    files = []

    for file_path in root.rglob("*"):
        if not file_path.is_file():
            continue

        rel_path = str(file_path.relative_to(root)).replace("\\", "/")

        if should_skip_path(rel_path, gitignore):
            continue

        if file_path.suffix not in SUPPORTED_EXTENSIONS:
            continue

        try:
            size = file_path.stat().st_size
        except OSError:
            continue

        if size > MAX_FILE_SIZE:
            continue

        if size == 0:
            continue

        language = _detect_language(file_path)

        files.append(
            {
                "absolute_path": str(file_path),
                "relative_path": rel_path,
                "language": language,
                "size": size,
            }
        )

    return files


def _detect_language(file_path: Path) -> str:
    ext_map = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
    }
    return ext_map.get(file_path.suffix, "unknown")
