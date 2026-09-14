#!/usr/bin/env python3
"""Validate the public skill package and make a reproducible source archive."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import subprocess
import tarfile
from typing import Iterable

import diagram


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "topoform"
PACKAGE_VERSION = "1.0.0"
SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
TAG = re.compile(r"^v(?P<version>.+)$")

REQUIRED_FILES = {
    "SKILL.md",
    "README.md",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "CONTRIBUTING.md",
    "assets/diagram.schema.json",
    "assets/viewer.html",
    "assets/viewer.js",
    "assets/icons/manifest.json",
    "assets/vendor/manifest.json",
    "assets/showcases/ai-retrieval.png",
    "assets/showcases/aws-commerce.png",
    "assets/showcases/cicd-rollback.png",
    "assets/showcases/creative-production.png",
    "assets/showcases/oauth-oidc.png",
    "assets/showcases/order-to-cash.png",
    "scripts/browser_check.py",
    "scripts/acceptance.py",
    "scripts/deliver.py",
    "scripts/diagram.py",
    "scripts/import_icon.py",
    "scripts/release.py",
    "scripts/vendor_from_npm.py",
    "references/composition.md",
    "references/icons.md",
    "references/model.md",
    "references/quality-and-limits.md",
    "references/sources.md",
}
PUBLIC_ROOTS = {".github", "assets", "evals", "examples", "references", "scripts", "tests"}
PUBLIC_ROOT_FILES = {
    ".gitignore",
    "CONTRIBUTING.md",
    "LICENSE",
    "README.md",
    "SKILL.md",
    "THIRD_PARTY_NOTICES.md",
}

FORBIDDEN_PARTS = {
    ".agents",
    ".codex",
    ".git",
    ".scratch",
    ".venv",
    "__pycache__",
    "dist",
    "evidence",
    "node_modules",
    "output",
}
FORBIDDEN_NAMES = {
    ".DS_Store",
    "AGENTS.md",
    "CONTEXT.md",
    "TEST_REPORT.md",
    "browser-report.json",
    "delivery-receipt.json",
    "regression-report.json",
    "unit-tests.log",
    "visual-review.json",
}
FORBIDDEN_TEXT = ("cytoscape-" + "elk-diagrams", "arch" + "ify", "tt-" + "a1i")
HOST_PATH = re.compile(r"(?:/(?:Users|private|home/[^/]+|var/|tmp/)|[A-Za-z]:[\\/]Users[\\/])")


class PackageError(ValueError):
    """Raised when an archive cannot be made from an invalid package."""


def _add(errors: list[dict[str, str]], code: str, subject: str, message: str) -> None:
    item = {"code": code, "subject": subject, "message": message}
    if item not in errors:
        errors.append(item)


def _candidate_paths(root: Path) -> tuple[list[Path], list[Path]]:
    """Return tracked public paths, or an explicit pre-Git public allowlist."""
    tracked: list[Path] | None = None
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            check=True,
            capture_output=True,
        )
        tracked = [root / Path(value) for value in result.stdout.decode().split("\0") if value]
    except (OSError, UnicodeDecodeError, subprocess.CalledProcessError):
        tracked = None
    if tracked is None:
        tracked = []
        for path in root.rglob("*"):
            relative = path.relative_to(root)
            if not relative.parts or (relative.parts[0] not in PUBLIC_ROOTS and relative.as_posix() not in PUBLIC_ROOT_FILES):
                continue
            # Ignore local caches and reports before Git exists, but leave
            # generated files in public directories visible to the gate.
            if any(part in FORBIDDEN_PARTS for part in relative.parts) or relative.name in FORBIDDEN_NAMES or relative.suffix == ".pyc":
                continue
            tracked.append(path)
    paths = sorted(tracked, key=lambda p: p.relative_to(root).as_posix())
    files = [p for p in paths if p.is_file() and not p.is_symlink()]
    return paths, files


def _blocked(rel: Path) -> str | None:
    if any(part in FORBIDDEN_PARTS for part in rel.parts):
        return "internal or generated path"
    if rel.name in FORBIDDEN_NAMES or rel.suffix == ".pyc":
        return "internal or generated file"
    if rel.parts and rel.parts[0] == "examples" and rel.suffix.lower() in {".html", ".htm"}:
        return "generated example HTML"
    return None


def _safe_relative(base: Path, value: object) -> Path | None:
    if not isinstance(value, str) or not value or "\\" in value:
        return None
    rel = Path(value)
    if rel.is_absolute() or ".." in rel.parts:
        return None
    candidate = (base / rel).resolve()
    if not candidate.is_relative_to(base.resolve()):
        return None
    return rel


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _frontmatter(skill: Path, errors: list[dict[str, str]]) -> tuple[str | None, str | None]:
    try:
        text = skill.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        _add(errors, "METADATA_READ", "SKILL.md", str(exc))
        return None, None
    if not text.startswith("---\n"):
        _add(errors, "METADATA", "SKILL.md", "The skill must start with YAML frontmatter.")
        return None, None
    end = text.find("\n---\n", 4)
    if end < 0:
        _add(errors, "METADATA", "SKILL.md", "The YAML frontmatter is not closed.")
        return None, None
    frontmatter = text[4:end]
    name_match = re.search(r"(?m)^name:\s*([A-Za-z0-9][A-Za-z0-9_-]*)\s*$", frontmatter)
    version_match = re.search(
        r"(?m)^\s+version:\s*[\"']?([^\"'#\s]+)[\"']?\s*$", frontmatter
    )
    name = name_match.group(1) if name_match else None
    version = version_match.group(1) if version_match else None
    if name != PACKAGE_NAME:
        _add(errors, "NAME", "SKILL.md", f"Expected root skill name {PACKAGE_NAME!r}; got {name!r}.")
    if version != PACKAGE_VERSION or not (version and SEMVER.fullmatch(version)):
        _add(errors, "VERSION", "SKILL.md", f"Expected metadata version {PACKAGE_VERSION!r}; got {version!r}.")
    return name, version


def _validate_manifest_files(
    root: Path, candidate_files: set[str], errors: list[dict[str, str]], *, icons: bool
) -> None:
    directory = root / "assets" / ("icons" if icons else "vendor")
    manifest_path = directory / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _add(errors, "MANIFEST", manifest_path.relative_to(root).as_posix(), str(exc))
        return

    if icons:
        if not isinstance(manifest, dict):
            _add(errors, "MANIFEST", "assets/icons/manifest.json", "Icon manifest must be an object.")
            return
        entries: Iterable[tuple[str, object]] = manifest.items()
    else:
        if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), list):
            _add(errors, "MANIFEST", "assets/vendor/manifest.json", "Vendor manifest needs a files array.")
            return
        if not isinstance(manifest.get("versions"), dict) or not manifest["versions"]:
            _add(errors, "MANIFEST", "assets/vendor/manifest.json", "Vendor manifest needs pinned versions.")
        if not isinstance(manifest.get("provenance"), dict) or not manifest["provenance"]:
            _add(errors, "MANIFEST", "assets/vendor/manifest.json", "Vendor manifest needs provenance.")
        entries = ((str(i), value) for i, value in enumerate(manifest.get("files", [])))

    seen: set[str] = set()
    for identifier, item in entries:
        if not isinstance(item, dict):
            _add(errors, "MANIFEST_ENTRY", identifier, "Manifest entry must be an object.")
            continue
        path_value = item.get("path")
        relative = _safe_relative(directory, path_value)
        subject = f"{directory.relative_to(root).as_posix()}/{identifier}"
        if relative is None:
            _add(errors, "MANIFEST_PATH", subject, "Asset path must be relative and stay in its manifest directory.")
            continue
        relative_text = relative.as_posix()
        if relative_text in seen:
            _add(errors, "MANIFEST_DUPLICATE", subject, f"Asset path {relative_text!r} is listed more than once.")
        seen.add(relative_text)
        asset = directory / relative
        asset_name = directory.relative_to(root).joinpath(relative).as_posix()
        if asset_name not in candidate_files or not asset.is_file() or asset.is_symlink():
            _add(errors, "ASSET_MISSING", subject, f"Missing regular file {relative_text!r}.")
            continue
        expected = item.get("sha256")
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            _add(errors, "ASSET_HASH", subject, "Asset needs a lowercase SHA-256 digest.")
        elif _sha256(asset) != expected:
            _add(errors, "ASSET_HASH", subject, "Asset SHA-256 does not match the manifest.")
        if icons:
            for key in ("pack", "version", "source", "license", "attribution", "modifications"):
                if not isinstance(item.get(key), str) or not item[key].strip():
                    _add(errors, "ICON_METADATA", subject, f"Icon entry needs {key} metadata.")
            source = item.get("source", "")
            if not diagram.safe_url(source, ("https",)):
                _add(errors, "ICON_SOURCE", subject, "Icon source must be an explicit HTTP(S) URL.")

    prefix = directory.relative_to(root).as_posix() + "/"
    expected_files = {
        path[len(prefix):]
        for path in candidate_files
        if path.startswith(prefix)
        and "/" not in path[len(prefix):]
        and path[len(prefix):] != "manifest.json"
        and (not icons or path.endswith(".svg"))
    }
    missing = expected_files - seen
    orphaned = seen - expected_files
    for path in sorted(missing):
        _add(errors, "MANIFEST_MISSING", directory.relative_to(root).joinpath(path).as_posix(), "File is not listed in the manifest.")
    for path in sorted(orphaned):
        _add(errors, "MANIFEST_ORPHAN", directory.relative_to(root).joinpath(path).as_posix(), "Manifest points to a file outside the package directory.")


def _validate_models(root: Path, candidate_files: set[str], errors: list[dict[str, str]]) -> int:
    models = sorted(
        root / relative
        for relative in candidate_files
        if relative.startswith("examples/") and "/" not in relative.removeprefix("examples/") and relative.endswith(".json")
    )
    if len(models) < 5:
        _add(errors, "SHOWCASES", "examples", "The public package needs at least five editable showcase models.")
    try:
        icon_manifest = diagram.read_json(root / "assets/icons/manifest.json")
        icon_ids = set(icon_manifest) if isinstance(icon_manifest, dict) else set()
        for model_path in models:
            try:
                result = diagram.validate(diagram.read_json(model_path), icon_ids)
            except (OSError, ValueError, TypeError) as exc:
                _add(errors, "MODEL", model_path.relative_to(root).as_posix(), str(exc))
                continue
            if not result.get("ok"):
                _add(errors, "MODEL", model_path.relative_to(root).as_posix(), "Showcase model failed semantic validation.")
    except (ImportError, OSError, ValueError, TypeError) as exc:
        _add(errors, "MODEL_CHECK", "scripts/diagram.py", str(exc))
    return len(models)


def validate_package(root: Path = ROOT, tag: str | None = None) -> dict[str, object]:
    """Return a machine-readable package report without changing ``root``."""
    root = Path(root).resolve()
    errors: list[dict[str, str]] = []
    if not root.is_dir():
        _add(errors, "ROOT", str(root), "Package root is not a directory.")
        return {"ok": False, "name": PACKAGE_NAME, "version": PACKAGE_VERSION, "files": 0, "errors": errors}

    paths, files = _candidate_paths(root)
    for path in paths:
        relative = path.relative_to(root)
        reason = _blocked(relative)
        if reason:
            _add(errors, "FORBIDDEN_PATH", relative.as_posix(), reason)
        if path.is_symlink():
            _add(errors, "SYMLINK", relative.as_posix(), "Release packages contain regular files only.")

    present = {p.relative_to(root).as_posix() for p in files if not _blocked(p.relative_to(root))}
    for required in sorted(REQUIRED_FILES):
        if required not in present:
            _add(errors, "REQUIRED_FILE", required, "Required public package file is missing.")

    name, version = _frontmatter(root / "SKILL.md", errors)
    if tag is not None:
        match = TAG.fullmatch(tag)
        tag_version = match.group("version") if match else None
        if not tag_version or not SEMVER.fullmatch(tag_version):
            _add(errors, "TAG", tag, "Release tags must be semantic versions with a v prefix.")
        elif version != tag_version:
            _add(errors, "TAG_VERSION", tag, f"Tag version {tag_version!r} does not match SKILL.md version {version!r}.")

    diagram_path = root / "scripts/diagram.py"
    if diagram_path.is_file():
        match = re.search(r"(?m)^VERSION\s*=\s*['\"]([^'\"]+)['\"]", diagram_path.read_text(encoding="utf-8"))
        if not match or match.group(1) != version:
            _add(errors, "VERSION", "scripts/diagram.py", "Runtime VERSION must match SKILL.md metadata.")

    for path in files:
        relative = path.relative_to(root)
        if _blocked(relative):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        lowered = text.casefold()
        for term in FORBIDDEN_TEXT:
            if term in lowered:
                _add(errors, "FORBIDDEN_TEXT", relative.as_posix(), f"Obsolete public reference {term!r} remains.")
        if HOST_PATH.search(text):
            _add(errors, "HOST_PATH", relative.as_posix(), "Creation-host or local absolute path remains.")

    candidate_files = {p.relative_to(root).as_posix() for p in files if not _blocked(p.relative_to(root))}
    try:
        readme = (root / "README.md").read_text(encoding="utf-8")
        for source in re.findall(r"<img\b[^>]*\bsrc=[\"']([^\"']+)[\"']", readme, re.IGNORECASE):
            relative = _safe_relative(root, source)
            if relative is None or relative.as_posix() not in candidate_files:
                _add(errors, "README_ASSET", source, "README image must be a packaged local file.")
    except (OSError, UnicodeError) as exc:
        _add(errors, "README", "README.md", str(exc))
    _validate_manifest_files(root, candidate_files, errors, icons=True)
    _validate_manifest_files(root, candidate_files, errors, icons=False)
    showcase_count = _validate_models(root, candidate_files, errors)
    return {
        "ok": not errors,
        "name": name or PACKAGE_NAME,
        "version": version or PACKAGE_VERSION,
        "tag": tag,
        "files": len(files),
        "showcases": showcase_count,
        "errors": errors,
    }


def _archive_files(root: Path) -> list[Path]:
    _, files = _candidate_paths(root)
    return [path for path in files if not _blocked(path.relative_to(root))]


def _version(value: str) -> str:
    candidate = value[1:] if value.startswith("v") else value
    if not SEMVER.fullmatch(candidate):
        raise PackageError(f"Invalid semantic version: {value}")
    return candidate


def create_archive(root: Path = ROOT, output: Path = ROOT / "dist", version: str = PACKAGE_VERSION) -> dict[str, object]:
    """Validate ``root`` and write ``topoform-VERSION.tar.gz`` and ``SHA256SUMS``."""
    root = Path(root).resolve()
    normalized = _version(version)
    report = validate_package(root, f"v{normalized}")
    if not report["ok"]:
        raise PackageError(json.dumps(report, ensure_ascii=False))
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"{PACKAGE_NAME}-{normalized}.tar.gz"
    with archive.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as bundle:
                for path in _archive_files(root):
                    relative = path.relative_to(root).as_posix()
                    data = path.read_bytes()
                    info = tarfile.TarInfo(f"{PACKAGE_NAME}-{normalized}/{relative}")
                    info.size = len(data)
                    info.mtime = 0
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    info.mode = 0o755 if path.stat().st_mode & 0o111 else 0o644
                    bundle.addfile(info, io.BytesIO(data))
    digest = _sha256(archive)
    checksums = output / "SHA256SUMS"
    checksums.write_text(f"{digest}  {archive.name}\n", encoding="utf-8", newline="\n")
    return {
        "ok": True,
        "name": PACKAGE_NAME,
        "version": normalized,
        "archive": str(archive),
        "archiveSha256": digest,
        "checksums": str(checksums),
        "files": len(_archive_files(root)),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", aliases=["validate"], help="validate a public package")
    check.add_argument("root", nargs="?", type=Path, default=ROOT)
    check.add_argument("--tag", help="semantic release tag, for example v1.0.0")
    archive = commands.add_parser("archive", aliases=["package"], help="validate and create release artifacts")
    archive.add_argument("--root", type=Path, default=ROOT)
    archive.add_argument("--output", type=Path, required=True)
    archive.add_argument("--version", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command in {"check", "validate"}:
            report = validate_package(args.root, args.tag)
        else:
            report = create_archive(args.root, args.output, args.version)
    except (OSError, PackageError, ValueError, TypeError) as exc:
        report = {"ok": False, "errors": [{"code": "RELEASE", "subject": args.command, "message": str(exc)}]}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
