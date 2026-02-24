#!/usr/bin/env python3
"""
Minecraft Localization Pack Merger

Fetches resource packs from Modrinth, merges them into a unified pack,
and updates pack.mcmeta + README.md automatically.

Exit code 0 = updates were applied
Exit code 1 = no updates needed
"""

import json
import os
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MODRINTH_API = "https://api.modrinth.com/v2"
USER_AGENT = "misc-localization-packs/1.0.0 (github.com/zack-zzq/misc-localization-packs)"

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = REPO_ROOT / "config"
PACKS_CONFIG = CONFIG_DIR / "packs.json"
VERSIONS_FILE = CONFIG_DIR / "versions.json"
ASSETS_DIR = REPO_ROOT / "assets"
PACK_MCMETA = REPO_ROOT / "pack.mcmeta"
README_FILE = REPO_ROOT / "README.md"

# ---------------------------------------------------------------------------
# Modrinth API helpers
# ---------------------------------------------------------------------------


def api_get(path: str) -> dict | list:
    """Make a GET request to the Modrinth API and return parsed JSON."""
    url = f"{MODRINTH_API}{path}"
    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as exc:
        print(f"[ERROR] Modrinth API request failed: {url} -> {exc.code}")
        raise


def get_latest_version(slug: str) -> dict | None:
    """Return the latest release version object for a Modrinth project."""
    versions = api_get(f"/project/{slug}/version")
    # Filter to release versions only, sort by date descending
    releases = [v for v in versions if v.get("version_type") == "release"]
    if not releases:
        # Fall back to all versions if no releases found
        releases = versions
    if not releases:
        return None
    releases.sort(key=lambda v: v.get("date_published", ""), reverse=True)
    return releases[0]


def get_primary_file(version: dict) -> dict | None:
    """Return the primary download file from a version object."""
    files = version.get("files", [])
    if not files:
        return None
    for f in files:
        if f.get("primary", False):
            return f
    return files[0]


def download_file(url: str, dest: Path) -> None:
    """Download a file from a URL to a local path."""
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=120) as resp:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as fp:
            shutil.copyfileobj(resp, fp)
    print(f"  Downloaded -> {dest.name}")


# ---------------------------------------------------------------------------
# Pack merging
# ---------------------------------------------------------------------------


def merge_zip_into_assets(zip_path: Path) -> None:
    """Extract resource pack zip and merge its assets/ into the repo's assets/."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp_path)

        # Find the assets directory inside the zip
        # It might be at root level or nested one directory deep
        source_assets = None
        if (tmp_path / "assets").is_dir():
            source_assets = tmp_path / "assets"
        else:
            # Check one level deep (some packs wrap in a folder)
            for child in tmp_path.iterdir():
                if child.is_dir() and (child / "assets").is_dir():
                    source_assets = child / "assets"
                    break

        if source_assets is None:
            print("  [WARN] No assets/ directory found in zip, skipping merge")
            return

        # Copy all files, overwriting existing ones
        for src_file in source_assets.rglob("*"):
            if src_file.is_file():
                rel = src_file.relative_to(source_assets)
                dst = ASSETS_DIR / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, dst)

        file_count = sum(1 for _ in source_assets.rglob("*") if _.is_file())
        print(f"  Merged {file_count} files into assets/")


# ---------------------------------------------------------------------------
# Metadata generation
# ---------------------------------------------------------------------------


def generate_pack_mcmeta(config: dict, pack_versions: dict) -> None:
    """Generate pack.mcmeta with pack info and source list."""
    source_names = []
    for pack in config["packs"]:
        slug = pack["slug"]
        if slug in pack_versions:
            source_names.append(pack["name"])

    description = config.get("description", "Misc Localization Packs")
    if source_names:
        description += f"\n包含: {', '.join(source_names)}"

    mcmeta = {
        "pack": {
            "pack_format": config.get("pack_format", 15),
            "description": description,
        }
    }

    with open(PACK_MCMETA, "w", encoding="utf-8") as fp:
        json.dump(mcmeta, fp, indent=2, ensure_ascii=False)
        fp.write("\n")
    print(f"Updated {PACK_MCMETA.name}")


def generate_readme(config: dict, pack_versions: dict) -> None:
    """Generate README.md with project info and source pack table."""
    mc_version = config.get("minecraft_version", "1.20.1")
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        "# Misc Localization Packs",
        "",
        "综合本地化资源包 — 自动合并多个 Modrinth 上的本地化资源包为一个统一资源包。",
        "",
        f"**目标 Minecraft 版本**: {mc_version}",
        f"**Pack Format**: {config.get('pack_format', 15)}",
        f"**最后更新**: {now_str}",
        "",
        "## 📦 包含的资源包",
        "",
        "| 资源包 | 说明 | 版本 | 发布日期 | Modrinth 链接 |",
        "| --- | --- | --- | --- | --- |",
    ]

    for pack in config["packs"]:
        slug = pack["slug"]
        name = pack.get("name", slug)
        desc = pack.get("description", "")
        link = f"https://modrinth.com/resourcepack/{slug}"

        ver_info = pack_versions.get(slug, {})
        version_num = ver_info.get("version_number", "—")
        date_pub = ver_info.get("date_published", "—")
        if date_pub != "—":
            # Format date nicely
            try:
                dt = datetime.fromisoformat(date_pub.replace("Z", "+00:00"))
                date_pub = dt.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                pass

        lines.append(f"| {name} | {desc} | {version_num} | {date_pub} | [链接]({link}) |")

    lines.extend([
        "",
        "## 🚀 使用方式",
        "",
        "1. 前往 [Releases](../../releases) 页面下载最新的资源包 `.zip` 文件",
        "2. 将 `.zip` 文件放入 Minecraft 的 `resourcepacks` 文件夹",
        "3. 在游戏内启用资源包",
        "",
        "## ➕ 添加新的资源包",
        "",
        "编辑 `config/packs.json`，在 `packs` 数组中添加新条目：",
        "",
        "```json",
        '{',
        '  "slug": "modrinth-project-slug",',
        '  "name": "资源包显示名称",',
        '  "description": "简短描述"',
        '}',
        "```",
        "",
        "提交后，GitHub Actions 会自动拉取并合并新的资源包。",
        "",
        "## ⚙️ 自动更新",
        "",
        "本项目通过 GitHub Actions 每 6 小时自动检查各源资源包是否有更新。",
        "如有新版本，会自动下载合并，更新本 README，并创建新的 Release。",
        "",
        "也支持在 Actions 页面手动触发更新。",
        "",
        "---",
        "",
        f"*本文件由 [merge_packs.py](scripts/merge_packs.py) 自动生成，最后更新于 {now_str}*",
        "",
    ])

    with open(README_FILE, "w", encoding="utf-8") as fp:
        fp.write("\n".join(lines))
    print(f"Updated {README_FILE.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    print("=" * 60)
    print("Minecraft Localization Pack Merger")
    print("=" * 60)

    # Load config
    if not PACKS_CONFIG.exists():
        print(f"[ERROR] Config not found: {PACKS_CONFIG}")
        return 1

    with open(PACKS_CONFIG, "r", encoding="utf-8") as fp:
        config = json.load(fp)

    # Load existing versions
    if VERSIONS_FILE.exists():
        with open(VERSIONS_FILE, "r", encoding="utf-8") as fp:
            versions = json.load(fp)
    else:
        versions = {}

    packs = config.get("packs", [])
    if not packs:
        print("[WARN] No packs configured")
        return 1

    has_updates = False

    for pack in packs:
        slug = pack["slug"]
        name = pack.get("name", slug)
        print(f"\n--- Checking: {name} ({slug}) ---")

        try:
            latest = get_latest_version(slug)
        except Exception as exc:
            print(f"  [ERROR] Failed to fetch versions: {exc}")
            continue

        if latest is None:
            print("  [WARN] No versions found")
            continue

        version_id = latest["id"]
        version_number = latest.get("version_number", "unknown")
        date_published = latest.get("date_published", "")

        old = versions.get(slug, {})
        if old.get("version_id") == version_id:
            print(f"  Already up to date (v{version_number})")
            continue

        print(f"  New version found: v{version_number} (was: v{old.get('version_number', 'N/A')})")

        # Download
        file_info = get_primary_file(latest)
        if file_info is None:
            print("  [ERROR] No downloadable file found")
            continue

        download_url = file_info["url"]
        filename = file_info.get("filename", f"{slug}.zip")

        with tempfile.TemporaryDirectory() as tmp_dir:
            zip_path = Path(tmp_dir) / filename
            download_file(download_url, zip_path)

            # Merge
            merge_zip_into_assets(zip_path)

        # Update version record
        file_hash = ""
        hashes = file_info.get("hashes", {})
        file_hash = hashes.get("sha512", hashes.get("sha1", ""))

        versions[slug] = {
            "version_id": version_id,
            "version_number": version_number,
            "date_published": date_published,
            "file_hash": file_hash,
        }
        has_updates = True

    # Save versions
    VERSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(VERSIONS_FILE, "w", encoding="utf-8") as fp:
        json.dump(versions, fp, indent=2, ensure_ascii=False)
        fp.write("\n")
    print(f"\nSaved {VERSIONS_FILE.name}")

    # Regenerate metadata files
    generate_pack_mcmeta(config, versions)
    generate_readme(config, versions)

    if has_updates:
        print("\n✅ Updates applied!")
        return 0
    else:
        print("\n✨ Everything is up to date.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
