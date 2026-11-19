import fnmatch
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles.finders import BaseFinder
from django.core.files.storage import FileSystemStorage


ROOT_ASSET_EXTENSIONS = {
    ".css",
    ".ico",
    ".jpeg",
    ".jpg",
    ".mp4",
    ".png",
    ".svg",
    ".webp",
    ".woff",
    ".woff2",
}


class ProjectRootAssetsFinder(BaseFinder):
    def __init__(self, *args, **kwargs):
        self.base_dir = Path(settings.BASE_DIR)
        self.storage = FileSystemStorage(location=self.base_dir)
        super().__init__(*args, **kwargs)

    def check(self, **kwargs):
        return []

    def find(self, path, find_all=False, **kwargs):
        if kwargs:
            find_all = self._check_deprecated_find_param(**kwargs)

        normalized_path = path.replace("\\", "/")
        parts = normalized_path.split("/")
        if not parts or any(part in {"", ".", ".."} for part in parts):
            return [] if find_all else None

        suffix = Path(parts[-1]).suffix.lower()
        is_root_asset = len(parts) == 1 and suffix in ROOT_ASSET_EXTENSIONS
        is_javascript_asset = len(parts) == 2 and parts[0] == "js" and suffix == ".js"
        if not (is_root_asset or is_javascript_asset):
            return [] if find_all else None

        if not self.storage.exists(normalized_path):
            return [] if find_all else None
        result = self.storage.path(normalized_path)
        return [result] if find_all else result

    def list(self, ignore_patterns):
        patterns = ignore_patterns or ()
        for path in self.base_dir.iterdir():
            if path.is_file() and path.suffix.lower() in ROOT_ASSET_EXTENSIONS:
                name = path.name
                if not any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns):
                    yield name, self.storage

        javascript_dir = self.base_dir / "js"
        if javascript_dir.is_dir():
            for path in javascript_dir.glob("*.js"):
                name = f"js/{path.name}"
                if not any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns):
                    yield name, self.storage
