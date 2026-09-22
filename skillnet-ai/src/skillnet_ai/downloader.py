"""Download GitHub files completely before publishing a local installation."""
import logging
import shutil
import tempfile
import time
import uuid
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Optional
from urllib.parse import quote, unquote, urlencode, urlsplit

import requests

from skillnet_ai.core.config import resolve_settings
from skillnet_ai.core.validation import validate_skill

logger = logging.getLogger(__name__)


class GitHubAPIError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code, self.message = status_code, message
        super().__init__(f"GitHub API Error [{status_code}]: {message}")


def _safe_relative(path: str) -> PurePosixPath:
    parts = PurePosixPath(path)
    if (not path or "\\" in path or "\x00" in path or parts.is_absolute()
            or PureWindowsPath(path).drive or any(p in {".", ".."} for p in path.split("/"))
            or any(any(c in p for c in '<>:"|?*') or p.endswith((".", " "))
                   or PureWindowsPath(p).is_reserved() for p in parts.parts)):
        raise ValueError("GitHub file path is not a portable relative path.")
    return parts


class SkillDownloader:
    def __init__(self, api_token: Optional[str] = None, mirror_url: Optional[str] = None,
                 timeout: int = 15, max_retries: int = 3):
        settings = resolve_settings(github_token=api_token, github_mirror=mirror_url)
        self.api_token, self.mirror_url = settings.github_token, settings.github_mirror
        self.timeout, self.max_retries = timeout, max_retries
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/vnd.github+json"})

    def download(self, folder_url: str, target_dir: str = ".", *,
                 overwrite: bool = False, require_skill: bool = False) -> str:
        owner, repo, ref, dir_path, folder_name = self._parse_github_url(folder_url)
        parent = Path(target_dir).expanduser().resolve()
        final = parent / folder_name
        self._check_destination(final, overwrite)
        files = self._get_file_tree(owner, repo, ref, dir_path)
        if not files:
            raise ValueError("No downloadable files found at the GitHub path.")
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".skillnet-download-", dir=parent) as temporary:
            staging = Path(temporary)
            package = staging / folder_name
            package.mkdir()
            seen = set()
            for item in files:
                relative = self._relative_file(item["path"], dir_path)
                key = relative.as_posix().casefold()
                if key in seen:
                    raise ValueError("GitHub tree contains colliding file paths.")
                seen.add(key)
                if not self._download_single_file(owner, repo, ref, dir_path, item,
                                                  folder_name, str(staging)):
                    raise RuntimeError(f"Download incomplete: {relative}. Existing installation was preserved.")
            if require_skill:
                result = validate_skill(package)
                if not result["valid"]:
                    raise ValueError("Downloaded skill is invalid: " + "; ".join(result["errors"]))
            self._check_destination(final, overwrite)
            # Keep the backup outside auto-cleaned staging: if restoration itself
            # fails (permissions/concurrent activity), the old files must survive.
            backup = parent / f".{folder_name}.backup-{uuid.uuid4().hex}"
            had_previous = final.exists()
            if had_previous:
                final.rename(backup)
            try:
                package.rename(final)
            except OSError:
                if had_previous:
                    try:
                        backup.rename(final)
                    except OSError as exc:
                        raise RuntimeError(f"Installation failed; previous files are preserved at {backup}.") from exc
                raise
            if had_previous:
                try:
                    shutil.rmtree(backup)
                except OSError:
                    logger.warning("Installed new skill; previous files remain at %s.", backup)
        return str(final)

    @staticmethod
    def _check_destination(final, overwrite):
        if final.is_symlink() or (final.exists() and not final.is_dir()):
            raise ValueError("Download destination must be a directory, not a symlink or file.")
        if final.exists() and not overwrite:
            raise FileExistsError("Destination exists; use overwrite=True / --overwrite to replace it.")

    @staticmethod
    def _relative_file(file_path: str, dir_path: str) -> PurePosixPath:
        full = _safe_relative(file_path)
        if file_path == dir_path:
            return _safe_relative(full.name)
        try:
            relative = full.relative_to(PurePosixPath(dir_path)) if dir_path else full
        except ValueError as exc:
            raise ValueError("GitHub tree contains a file outside the requested directory.") from exc
        return _safe_relative(relative.as_posix())

    def _parse_github_url(self, url: str):
        parsed = urlsplit(url)
        if (parsed.scheme != "https" or parsed.netloc.lower() != "github.com"
                or parsed.query or parsed.fragment):
            raise ValueError("Use an HTTPS github.com tree URL or a SKILL.md blob URL.")
        parts = parsed.path.strip("/").split("/")
        if len(parts) < 4 or parts[2] not in {"tree", "blob"}:
            raise ValueError("Expected https://github.com/owner/repo/tree/ref/skill-folder.")
        owner, repo = parts[:2]
        _safe_relative(owner)
        _safe_relative(repo)
        ref = unquote(parts[3])
        _safe_relative(ref)
        dir_path = unquote("/".join(parts[4:]))
        if dir_path:
            _safe_relative(dir_path)
        if parts[2] == "blob" and PurePosixPath(dir_path).name == "SKILL.md":
            dir_path = str(PurePosixPath(dir_path).parent)
            if dir_path == ".":
                dir_path = ""
        folder_name = PurePosixPath(dir_path).name if dir_path else repo
        _safe_relative(folder_name)
        return owner, repo, ref, dir_path, folder_name

    def _request_with_retry(self, url: str, timeout=None, max_retries=None,
                            base_delay: float = 1.0, *, raw: bool = False):
        headers = {"Accept": "application/vnd.github.raw+json"} if raw else {}
        if urlsplit(url).hostname == "api.github.com" and self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        attempts = self.max_retries if max_retries is None else max_retries
        for attempt in range(max(1, attempts)):
            try:
                response = self.session.get(url, headers=headers, timeout=timeout or self.timeout,
                                            allow_redirects=False)
                if response.status_code not in {429, 500, 502, 503, 504} or attempt + 1 >= attempts:
                    return response
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                if attempt + 1 >= attempts:
                    return None
            if attempt + 1 < attempts:
                time.sleep(min(base_delay * 2 ** attempt, 8))
        return None

    def _build_mirror_url(self, original_url: str) -> Optional[str]:
        # Authenticated requests may involve private content; never mirror them.
        if self.api_token or not self.mirror_url or urlsplit(original_url).hostname != "raw.githubusercontent.com":
            return None
        return f"{self.mirror_url.rstrip('/')}/{original_url}"

    @staticmethod
    def _contents_url(owner, repo, ref, path):
        return (f"https://api.github.com/repos/{quote(owner, safe='')}/{quote(repo, safe='')}/contents/"
                f"{quote(path, safe='/')}?{urlencode({'ref': ref})}")

    def _get_file_tree(self, owner: str, repo: str, ref: str, dir_path: str):
        response = self._request_with_retry(self._contents_url(owner, repo, ref, dir_path))
        if response is None:
            raise GitHubAPIError(0, "Request timed out or connection failed.")
        if response.status_code != 200:
            raise GitHubAPIError(response.status_code, "Cannot list repository files. Check URL, access and GitHub rate limits.")
        contents = response.json()
        if isinstance(contents, dict) and contents.get("type") == "file":
            contents = [contents]
        if not isinstance(contents, list):
            raise ValueError("GitHub returned an invalid file listing.")
        if len(contents) >= 1000:
            raise ValueError("GitHub directory listing reached its 1000-entry limit; complete download cannot be verified.")
        files = []
        for item in contents:
            path = item.get("path", "")
            self._relative_file(path, dir_path)
            if item.get("type") == "file":
                files.append({"path": path, "download_url": item.get("download_url")})
            elif item.get("type") == "dir":
                if path == dir_path:
                    raise ValueError("GitHub returned a recursive directory entry.")
                files.extend(self._get_file_tree(owner, repo, ref, path))
            else:
                raise ValueError("GitHub symlinks and submodules are not supported in skill downloads.")
        return files

    def _download_single_file(self, owner, repo, ref, dir_path, file_info, folder_name, target_dir):
        relative = self._relative_file(file_info["path"], dir_path)
        destination = Path(target_dir) / folder_name / str(relative)
        raw_url = file_info.get("download_url") or (
            f"https://raw.githubusercontent.com/{quote(owner, safe='')}/{quote(repo, safe='')}/"
            f"{quote(ref, safe='')}/{quote(file_info['path'], safe='/')}")
        if urlsplit(raw_url).scheme != "https" or urlsplit(raw_url).netloc != "raw.githubusercontent.com":
            raise ValueError("GitHub returned an unexpected content host.")
        if self.api_token:
            response = self._request_with_retry(
                self._contents_url(owner, repo, ref, file_info["path"]), raw=True)
        else:
            response = self._request_with_retry(raw_url)
            mirror = self._build_mirror_url(raw_url)
            if (response is None or response.status_code != 200) and mirror:
                response = self._request_with_retry(mirror)
        if response is None or response.status_code != 200:
            return False
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(response.content)
        return True
