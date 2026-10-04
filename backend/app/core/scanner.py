import os
from pathlib import Path

import pathspec
import structlog

logger = structlog.get_logger()

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

SKIP_SUFFIXES = (".pyc", ".pyo", ".so", ".o", ".min.js", ".min.css")


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
        if part.endswith(SKIP_SUFFIXES):
            return True

    if gitignore.match_file(rel_path):
        return True

    return False


def scan_repository(repo_path: str) -> list[dict]:
    """Scan a repository and return file metadata for supported files.

    Uses os.walk so we can prune excluded directories. rglob cannot prune: it
    descends into node_modules and .venv, then throws the results away. Walking
    the tree that way took 12 minutes under the Docker bind mount.
    """
    root = Path(repo_path).resolve()
    if not root.is_dir():
        raise ValueError(f"Not a directory: {repo_path}")

    gitignore = load_gitignore(root)
    files = []

    for dirpath, dirnames, filenames in os.walk(root, onerror=_ignore_walk_error):
        # Filter dirnames in place so os.walk skips these subtrees.
        dirnames[:] = [
            d
            for d in dirnames
            if d not in EXCLUDE_DIRS
            and not d.endswith(".egg-info")
            and not d.endswith(SKIP_SUFFIXES)
        ]

        for filename in filenames:
            if filename.endswith(SKIP_SUFFIXES):
                continue
            if Path(filename).suffix not in SUPPORTED_EXTENSIONS:
                continue

            file_path = Path(dirpath) / filename
            rel_path = str(file_path.relative_to(root)).replace("\\", "/")

            if should_skip_path(rel_path, gitignore):
                continue

            try:
                size = file_path.stat().st_size
            except OSError:
                continue

            if size == 0 or size > MAX_FILE_SIZE:
                continue

            files.append(
                {
                    "absolute_path": str(file_path),
                    "relative_path": rel_path,
                    "language": _detect_language(file_path),
                    "size": size,
                }
            )

    files.sort(key=lambda f: f["relative_path"])
    return files


def _ignore_walk_error(error: OSError) -> None:
    # A permission error or broken symlink shouldn't kill the scan.
    logger.debug("scan_walk_skipped_dir", error=str(error))


def _detect_language(file_path: Path) -> str:
    ext_map = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
    }
    return ext_map.get(file_path.suffix, "unknown")
