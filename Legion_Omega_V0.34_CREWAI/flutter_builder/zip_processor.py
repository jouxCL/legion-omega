import os
import zipfile
import shutil
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SUPPORTED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".svg", ".webp", ".ico"}
SUPPORTED_FONT_EXTS  = {".ttf", ".otf", ".woff", ".woff2"}


def process_brand_zip(zip_path: str, output_dir: str) -> dict:
    """
    Extracts a brand .zip and categorizes assets.
    Returns dict with colors, fonts, logo_path, raw_files.
    """
    assets_dir = os.path.join(output_dir, "brand_assets")
    os.makedirs(assets_dir, exist_ok=True)

    result = {
        "colors": [],
        "fonts": [],
        "logo_path": "",
        "raw_files": []
    }

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(assets_dir)
        logger.info(f"Extracted {len(zf.namelist())} files to {assets_dir}")

    for root, _, files in os.walk(assets_dir):
        for fname in files:
            fpath = os.path.join(root, fname)
            ext = Path(fname).suffix.lower()
            rel_path = os.path.relpath(fpath, assets_dir)

            if ext in SUPPORTED_IMAGE_EXTS:
                result["raw_files"].append(rel_path)
                name_lower = fname.lower()
                if any(kw in name_lower for kw in ["logo", "icon", "brand"]):
                    result["logo_path"] = fpath
                    logger.info(f"Logo detected: {fname}")

            elif ext in SUPPORTED_FONT_EXTS:
                result["fonts"].append({"name": Path(fname).stem, "path": fpath})
                logger.info(f"Font detected: {fname}")

            elif ext == ".txt" and "color" in fname.lower():
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith("#") and len(line) in (7, 9):
                                result["colors"].append(line)
                except Exception as e:
                    logger.warning(f"Could not read colors from {fname}: {e}")

    return result
