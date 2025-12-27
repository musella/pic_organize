import os
import sys
import json
from typing import List
from PIL import Image
from PIL.ExifTags import TAGS
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata

# Ensure parent directory is in sys.path for module imports
from pic_organize.tag_info import MediaTagInfo
from pic_organize.tag_stats import summarize_tags


def get_image_tags(filepath: str) -> dict[str, str]:
    """
    Extract EXIF tags from an image file.

    Args:
        filepath (str): Path to the image file.

    Returns:
        dict[str, str]: Dictionary of tag names and values.
    """
    tags: dict[str, str] = {}
    try:
        image = Image.open(filepath)
        exifdata = None
        # Use public getexif() if available (Pillow >=6.0.0)
        if hasattr(image, "getexif"):
            exifdata = image.getexif()
        if exifdata:
            for tag_id, value in exifdata.items():
                tag = TAGS.get(tag_id, tag_id)
                tags[str(tag)] = str(value)
    except Exception:
        pass
    return tags


def get_video_tags(filepath: str) -> dict[str, str]:
    """
    Extract metadata tags from a video file.

    Args:
        filepath (str): Path to the video file.

    Returns:
        dict[str, str]: Dictionary of tag names and values.
    """
    tags: dict[str, str] = {}
    parser = createParser(filepath)
    if not parser:
        return tags
    with parser:
        metadata = extractMetadata(parser)
        if metadata:
            for item in metadata.exportPlaintext():
                if ":" in item:
                    key, value = item.split(":", 1)
                    tags[key.strip()] = value.strip()
    return tags


def scan_media(directory: str) -> List[MediaTagInfo]:
    """
    Scan a directory for image and video files, extract their tags.

    Args:
        directory (str): Path to the directory to scan.

    Returns:
        List[MediaTagInfo]: List of extracted tag info objects.
    """
    media_tags: List[MediaTagInfo] = []
    for root, _, files in os.walk(directory):
        for fname in files:
            fpath = os.path.join(root, fname)
            ext = fname.lower().split(".")[-1]
            if ext in ["jpg", "jpeg", "png", "tiff"]:
                tags = get_image_tags(fpath)
                media_tags.append(
                    MediaTagInfo(filename=fpath, media_type="image", tags=tags)
                )
            elif ext in ["mp4", "mov", "avi", "mkv"]:
                tags = get_video_tags(fpath)
                media_tags.append(
                    MediaTagInfo(filename=fpath, media_type="video", tags=tags)
                )
    return media_tags


def main() -> None:
    """
    Main entry point for tag extraction and summary.

    Scans the media directory, extracts tags, summarizes statistics,
    and saves results to JSON files.
    """
    # Accept directory path as first command-line argument, default to "."
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = "."
    media_tags: List[MediaTagInfo] = scan_media(directory)
    stats = summarize_tags(media_tags)
    with open("media_tags.json", "w") as f:
        json.dump([m.model_dump() for m in media_tags], f, indent=2)
    with open("tag_summary.json", "w") as f:
        json.dump(stats, f, indent=2)
    print("Extraction complete. Results saved to media_tags.json and tag_summary.json.")


if __name__ == "__main__":
    main()
