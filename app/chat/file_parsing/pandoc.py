"""
解析docx, pptx, xlsx, html

自动安装并使用pandoc
"""

import os
import shutil
import subprocess
from typing import Literal

import requests

PANDOC_FORMAT = frozenset(("docx", "pptx", "xlsx", "html"))

# 没有pandoc自动安装最新版本
if not shutil.which("pandoc"):
    # 获取架构
    arch = os.uname().machine
    match arch:
        case "x86_64" | "amd64":
            arch = "amd64"
        case "arm64" | "aarch64":
            arch = "arm64"

    # 获取.deb
    url = "https://api.github.com/repos/jgm/pandoc/releases/latest"
    response = requests.get(url)
    release = response.json()
    for asset in release["assets"]:
        if asset["name"].endswith(".deb") and arch in asset["name"]:
            deb_asset = asset["browser_download_url"]
            break

    # 下载安装
    deb_file = asset["name"]
    with requests.get(deb_asset, stream=True) as r:
        r.raise_for_status()
        with open(deb_file, "wb") as f:
            for chunk in r.iter_content(chunk_size=None):
                f.write(chunk)
    subprocess.run(["dpkg", "-i", deb_file], check=True)
    os.remove(deb_file)


def pandoc_parse(data: bytes, format: Literal["docx", "pptx", "xlsx", "html"]) -> str:
    process = subprocess.run(
        ["pandoc", "-f", format, "-t", "markdown"],
        input=data,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return process.stdout.decode("utf-8")
