from pathlib import Path

import pathspec
import pytest

from app.core.scanner import (
    EXCLUDE_DIRS,
    _detect_language,
    scan_repository,
    should_skip_path,
)


class TestShouldSkipPath:
    def test_excludes_hidden_and_build_dirs(self):
        spec = pathspec.PathSpec([])
        assert should_skip_path("node_modules/lib/index.js", spec) is True
        assert should_skip_path("src/__pycache__/x.pyc", spec) is True
        assert should_skip_path(".git/config", spec) is True

    def test_skips_compiled_artifacts(self):
        spec = pathspec.PathSpec([])
        assert should_skip_path("build/app.pyc", spec) is True
        assert should_skip_path("lib/x.min.js", spec) is True

    def test_normal_files_not_skipped(self):
        spec = pathspec.PathSpec([])
        assert should_skip_path("src/main.py", spec) is False

    def test_respects_gitignore(self):
        spec = pathspec.PathSpec.from_lines("gitwildmatch", ["*.log"])
        assert should_skip_path("out/server.log", spec) is True
        assert should_skip_path("src/main.py", spec) is False


class TestDetectLanguage:
    def test_maps_extensions(self):
        assert _detect_language(Path("a.py")) == "python"
        assert _detect_language(Path("a.js")) == "javascript"
        assert _detect_language(Path("a.jsx")) == "javascript"
        assert _detect_language(Path("a.ts")) == "typescript"
        assert _detect_language(Path("a.tsx")) == "typescript"

    def test_unknown_extension(self):
        assert _detect_language(Path("a.txt")) == "unknown"


class TestScanRepository:
    def _make_repo(self, root: Path):
        (root / "src").mkdir(parents=True)
        (root / "src").joinpath("main.py").write_text("def main():\n    pass\n")
        (root / "src").joinpath("helpers.js").write_text("function h() {}\n")
        (root / "node_modules").mkdir()
        (root / "node_modules").joinpath("dep.ts").write_text("export const x = 1;\n")
        (root / "dist").mkdir()
        (root / "dist").joinpath("bundle.js").write_text("console.log('x');\n")
        (root).joinpath("README.md").write_text("# docs\n")
        return root

    def test_scan_filters_supported_files_and_excluded_dirs(self, tmp_path: Path):
        root = self._make_repo(tmp_path / "repo")
        files = scan_repository(str(root))

        rel_paths = {f["relative_path"] for f in files}
        assert "src/main.py" in rel_paths
        assert "src/helpers.js" in rel_paths
        assert "node_modules/dep.ts" not in rel_paths
        assert "dist/bundle.js" not in rel_paths
        assert "README.md" not in rel_paths

    def test_scan_returns_metadata(self, tmp_path: Path):
        root = self._make_repo(tmp_path / "repo")
        files = scan_repository(str(root))
        main = next(f for f in files if f["relative_path"] == "src/main.py")
        assert main["language"] == "python"
        assert main["size"] > 0
        assert main["absolute_path"].endswith("main.py")

    def test_scan_raises_on_missing_directory(self, tmp_path: Path):
        with pytest.raises(ValueError):
            scan_repository(str(tmp_path / "nonexistent"))

    def test_exclude_dirs_constant_has_expected_entries(self):
        assert ".git" in EXCLUDE_DIRS
        assert "node_modules" in EXCLUDE_DIRS
        assert ".venv" in EXCLUDE_DIRS
