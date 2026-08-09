from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest
from PIL import Image, ImageChops, ImageDraw, ImageStat

ROOT = Path(__file__).parents[1]
PROMOTION = ROOT / "docs" / "assets" / "promotion"
SOCIAL_PREVIEW_SHA256 = "3e39ea5252c895ba21be484a92d3fc8ce09960cbf26f5cb0649966d5082ed95e"
HERO_COMPARISON_SHA256 = "e21c73ec693dec51c5053ccc0788d552b8e1f1e6a68e026aa8e9e0f1e1a5c4c4"

CASES = [
    ("k-on-source-721x406.jpg", (721, 406), "0cac28576ba219aeaec8bed9378f71dc3e0a7d31b1f4923acc0b72a0230052a3"),
    ("k-on-detail-comparison-4x.png", (1060, 590), "b316c65718f8ac2e6d14da6077406ee71766a75850b7a01e0469e845adbebe94"),
    ("k-on-wallpaper-2560x1600.jpg", (2560, 1600), "22cf61076f816038d3fa855ee18af7d616261c9b31c24bd2054ef14d731321c6"),
    ("k-on-desktop-comparison.png", (1280, 1710), "f6f5e4090d118704ff2054b38c645a8e5f5804648ea22cfdf9bfbf168523713e"),
]


@pytest.mark.parametrize(("name", "size", "digest"), CASES)
def test_checked_in_promotion_asset_matches_verified_source(
    name: str, size: tuple[int, int], digest: str
) -> None:
    path = PROMOTION / name
    assert path.is_file()
    assert sha256(path.read_bytes()).hexdigest() == digest
    with Image.open(path) as image:
        rendered = image.convert("RGB")
        assert rendered.size == size
        assert rendered.getbbox() is not None
        assert sum(ImageStat.Stat(rendered).var) > 100


def test_readmes_lead_with_the_4x_comparison() -> None:
    asset = PROMOTION / "anime-4x-comparison.png"
    assert sha256(asset.read_bytes()).hexdigest() == HERO_COMPARISON_SHA256
    with Image.open(asset) as image:
        rendered = image.convert("RGB")
        assert rendered.size == (1280, 720)
        assert rendered.getbbox() is not None
        assert sum(ImageStat.Stat(rendered).var) > 100

    expected_target = "(docs/assets/promotion/anime-4x-comparison.png)"
    for readme_name in ("README.md", "README.zh-CN.md"):
        lines = (ROOT / readme_name).read_text(encoding="utf-8").splitlines()
        first_image = next(line for line in lines if line.startswith("!["))
        assert expected_target in first_image


def test_promotion_evidence_and_notice_are_explicit() -> None:
    evidence_path = ROOT / "docs" / "release" / "evidence" / "k-on-promotion-run.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert evidence == {
        "capturedAt": "2026-07-27T16:32:44+08:00",
        "source": {
            "title": "K-ON!",
            "episode": "not provided by the source contributor",
            "timestamp": "not provided by the source contributor",
            "size": [721, 406],
            "sha256": CASES[0][2],
        },
        "inference": {
            "engine": "official realesrgan-ncnn-vulkan",
            "model": "realesrgan-x4plus-anime",
            "scale": 4,
            "target": [2560, 1600],
            "mode": "preserve",
            "gpu": "NVIDIA GeForce RTX 5070 Ti Laptop GPU",
        },
        "outputs": {
            "rawUpscale": {
                "size": [2884, 1624],
                "sha256": "8d1d214233adccb36371ccfce83a0299b308ed9e84ab46f6dbb48b79e8561dfa",
            },
            "wallpaper": {
                "path": "docs/assets/promotion/k-on-wallpaper-2560x1600.jpg",
                "size": [2560, 1600],
                "sha256": CASES[2][2],
            },
            "detailComparison": {
                "path": "docs/assets/promotion/k-on-detail-comparison-4x.png",
                "size": [1060, 590],
                "sha256": CASES[1][2],
            },
            "desktopComparison": {
                "path": "docs/assets/promotion/k-on-desktop-comparison.png",
                "size": [1280, 1710],
                "sha256": CASES[3][2],
                "layout": "vertical",
                "lowerBorder": "none",
            },
        },
        "verification": {
            "sourceCopyMatches": True,
            "rawUpscaleIsExact4x": True,
            "fullFramePreserved": True,
            "allImagesNonblank": True,
            "succeeded": 1,
            "failed": 0,
            "visualInspection": "passed",
        },
    }

    notice = (PROMOTION / "NOTICE.md").read_text(encoding="utf-8")
    normalized_notice = " ".join(notice.split())
    assert (
        "These images are **not licensed for redistribution under this repository's MIT "
        "License**. Anime Wallpaper Upscaler is not affiliated with, sponsored by, or endorsed "
        "by the creators, publisher, animation studio, broadcaster, production committee, or "
        "other rightsholders."
        in normalized_notice
    )
    assert (
        "This notice does not create permission, establish fair use, prevent a DMCA request, or "
        "eliminate liability."
        in normalized_notice
    )
    assert (
        "For a removal request, open a GitHub Issue: "
        "https://github.com/zc4578980-tech/anime-wallpaper-upscaler/issues"
        in normalized_notice
    )
    assert (
        "Remove `k-on-source-721x406.jpg`, `k-on-detail-comparison-4x.png`, "
        "`k-on-wallpaper-2560x1600.jpg`, `k-on-desktop-comparison.png`, the derived "
        "`../social-preview.jpg`, and every other derived social or documentation image. Replace "
        "them with the deterministic project-owned demo documented in `../NOTICE.md`."
        in normalized_notice
    )

    parent_notice = (ROOT / "docs" / "assets" / "NOTICE.md").read_text(encoding="utf-8")
    normalized_parent_notice = " ".join(parent_notice.split())
    assert (
        "The three assets listed in the table above are covered by the repository MIT License."
        in normalized_parent_notice
    )
    assert (
        "Files under `docs/assets/promotion/` and the derived `docs/assets/social-preview.jpg` are "
        "not project-owned MIT assets. Their separate notice records source uncertainty, "
        "non-affiliation, the contact route, and the removal map. The repository MIT License does "
        "not relicense those images."
        in normalized_parent_notice
    )
    assert "These repository-owned assets are covered" not in normalized_parent_notice


def test_promotion_social_preview_has_exact_dimensions(tmp_path: Path) -> None:
    from scripts.build_promotion_assets import build_social_preview

    detail = tmp_path / "detail.png"
    wallpaper = tmp_path / "wallpaper.png"
    output = tmp_path / "social.jpg"
    Image.new("RGB", (1060, 590), "#e84855").save(detail)
    wallpaper_image = Image.new("RGB", (2560, 1600), "#2a9d8f")
    wallpaper_draw = ImageDraw.Draw(wallpaper_image)
    wallpaper_draw.rectangle((0, 0, 255, 1599), fill="#e84855")
    wallpaper_draw.rectangle((2304, 0, 2559, 1599), fill="#4267d5")
    wallpaper_image.save(wallpaper)

    build_social_preview(detail, wallpaper, output)

    with Image.open(output) as image:
        rendered = image.convert("RGB")
        assert rendered.size == (1280, 640)
        assert sum(ImageStat.Stat(rendered).var) > 100
        assert rendered.getpixel((835, 389))[0] > 150
        assert rendered.getpixel((1230, 389))[2] > 150


def test_checked_in_social_preview_uses_selected_comparison_assets(tmp_path: Path) -> None:
    from scripts.build_promotion_assets import build_social_preview

    rebuilt = tmp_path / "social-preview.jpg"
    build_social_preview(
        PROMOTION / "k-on-detail-comparison-4x.png",
        PROMOTION / "k-on-desktop-comparison.png",
        rebuilt,
    )

    checked_in = ROOT / "docs" / "assets" / "social-preview.jpg"
    assert sha256(checked_in.read_bytes()).hexdigest() == SOCIAL_PREVIEW_SHA256

    with Image.open(checked_in) as checked_image, Image.open(rebuilt) as rebuilt_image:
        checked = checked_image.convert("RGB")
        regenerated = rebuilt_image.convert("RGB")

    assert checked.size == regenerated.size == (1280, 640)
    for box in ((42, 174, 802, 604), (828, 174, 1238, 604)):
        difference = ImageChops.difference(checked.crop(box), regenerated.crop(box))
        assert max(ImageStat.Stat(difference).mean) < 8
