"""Publish validated artifacts only for the exact tagged commit; never overwrite a public release."""
import json
import os
from pathlib import Path
import subprocess


def gh(*args):
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True, encoding="utf-8").stdout.strip()


def main():
    repository = os.environ["GITHUB_REPOSITORY"]
    tag = os.environ["GITHUB_REF_NAME"]
    if not tag.startswith("v"):
        raise RuntimeError("Release publication requires a version tag")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    tagged = gh("api", f"repos/{repository}/commits/{tag}", "--jq", ".sha")
    if head != tagged:
        raise RuntimeError("Refusing to publish artifacts for a different commit than the release tag")
    files = [
        Path("dist/DownloaderVideo-1.0.0-windows-x64-setup.exe"),
        Path("dist/DownloaderVideo-1.0.0-windows-x64-portable.zip"),
        Path("dist/DownloaderVideo-1.0.0-source.zip"),
        Path("dist/SHA256SUMS.txt"),
    ]
    if any(not file.is_file() or not file.stat().st_size for file in files):
        raise RuntimeError("Missing or empty release artifact")
    existing = subprocess.run(["gh", "release", "view", tag, "--repo", repository, "--json", "isDraft"], capture_output=True, text=True)
    if existing.returncode == 0:
        if not json.loads(existing.stdout)["isDraft"]:
            raise RuntimeError("This release is already public; its artifacts will not be overwritten")
    else:
        gh("release", "create", tag, "--repo", repository, "--verify-tag", "--draft", "--title", "DownloaderVideo 1.0.0", "--notes-file", "docs/RELEASE_NOTES.md")
    gh("release", "upload", tag, *[str(file) for file in files], "--repo", repository, "--clobber")
    gh("release", "edit", tag, "--repo", repository, "--draft=false", "--latest", "--notes-file", "docs/RELEASE_NOTES.md")
    url = gh("release", "view", tag, "--repo", repository, "--json", "url", "--jq", ".url")
    print(url)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as output:
            output.write(f"\nRelease publicada: {url}\n\nBuild Windows, suíte de testes, download/conversão no executável, ZIP extraído e instalação/desinstalação silenciosa verificados.\n")


if __name__ == "__main__":
    main()
