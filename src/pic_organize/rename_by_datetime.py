"""
Script to propose renaming media files by date and time.

Scans a directory for images and videos, extracts or infers date/time,
and generates a proposal for renaming files to the format IMG_YYYYMMDD_HHMMSS.ext.
Files without date/time are flagged for manual review. No files are actually renamed.
"""

import os
import re
import sys
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from pic_organize.extract_tags import scan_media
from pic_organize.tag_info import MediaTagInfo

# Patterns for inferring date/time from filenames (e.g., IMG_20211231_235959.jpg)
FILENAME_PATTERNS = [
    re.compile(r"(\d{4})(\d{2})(\d{2})[_\-]?(\d{2})(\d{2})(\d{2})"),
    re.compile(r"(\d{4})-(\d{2})-(\d{2})[_\-]?(\d{2})-(\d{2})-(\d{2})"),
    re.compile(r"(\d{4})-(\d{2})-(\d{2})[_\-](\d{2})(\d{2})(\d{2})"),
]


def extract_datetime_from_tags(
    tags: Dict[str, Any], media_type: str
) -> Optional[datetime]:
    """
    Extract date/time from media tags.

    Args:
        tags (Dict[str, Any]): Extracted metadata tags.
        media_type (str): "image" or "video".

    Returns:
        Optional[datetime]: Extracted datetime if found, else None.
    """
    # Try EXIF DateTimeOriginal for images, creation date for videos
    date_fields = []
    if media_type == "image":
        date_fields = ["DateTimeOriginal", "DateTime"]
    elif media_type == "video":
        date_fields = ["Creation date", "Date/Time Original", "DateTimeOriginal"]
    for field in date_fields:
        value = tags.get(field)
        if value:
            # Try common EXIF date formats
            for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
                try:
                    return datetime.strptime(value, fmt)
                except Exception:
                    continue
    return None


def infer_datetime_from_filename(filename: str) -> Optional[datetime]:
    """
    Infer date/time from filename using regex patterns.

    Args:
        filename (str): The file name to parse.

    Returns:
        Optional[datetime]: Parsed datetime if found, else None.
    """
    base = os.path.basename(filename)
    for pattern in FILENAME_PATTERNS:
        m = pattern.search(base)
        if m:
            try:
                y, mo, d, h, mi, s = map(int, m.groups())
                return datetime(y, mo, d, h, mi, s)
            except Exception:
                continue
    return None


def extract_burst_tags(filename: str) -> str:
    """
    Extract burst/cover tags from filename and return as a string to append.

    Args:
        filename (str): The original filename.

    Returns:
        str: Tag string to append (e.g., '_BURST01_COVER_02_COVER'), or '' if none.
    """
    base = os.path.basename(filename)
    # Find all burst and cover tags in order of appearance
    pattern = re.compile(r"BURST(\d{0,3})(?:_COVER)?|(\d{1,3})_COVER", re.IGNORECASE)
    tags = []
    seen = set()
    for match in pattern.finditer(base):
        if match.group(0).startswith("BURST"):
            # BURST tag, possibly with number and _COVER
            num = match.group(1)
            tag = match.group(0)
            # If tag is exactly "BURST_COVER", pad to "BURST00_COVER"
            if tag.upper() == "BURST_COVER":
                tag = "BURST00_COVER"
            elif num is not None and num != "":
                padded = f"{int(num):02d}"
                tag = tag.replace(f"BURST{num}", f"BURST{padded}")
            elif tag.upper() == "BURST":
                tag = "BURST00"
        elif match.group(2):
            # _COVER tag, with number
            num = match.group(2)
            padded = f"{int(num):02d}"
            tag = f"{padded}_COVER"
        else:
            tag = match.group(0)
        if tag not in seen:
            tags.append(tag)
            seen.add(tag)
    if tags:
        return "_" + "_".join(tags)
    return ""


def propose_new_name(dt: datetime, ext: str, burst_tag: str = "") -> str:
    """
    Generate a new file name in the format IMG_YYYYMMDD_HHMMSS[_BURST...].ext.

    Args:
        dt (datetime): The date and time.
        ext (str): The file extension (including dot).
        burst_tag (str): Tag string to append before extension.

    Returns:
        str: Proposed new file name.
    """
    return f"IMG_{dt.strftime('%Y%m%d_%H%M%S')}{burst_tag}{ext}"


class RenameProposalItem(BaseModel):
    original: str
    proposed: str
    note: Optional[str] = None


def main():
    """
    CLI entry point for generating file renaming proposals.

    Scans the specified directory for media files, extracts or infers date/time,
    generates a renaming proposal and manual review list, and saves them as JSON files.
    No files are actually renamed.

    Usage:
        python rename_by_datetime.py [src_directory|src_json_file]
    """
    # Accept directory path as first command-line argument, default to "."
    if len(sys.argv) > 1:
        src = sys.argv[1]
    else:
        src = "."
    if src.endswith(".json"):
        with open(src, "r") as f:
            media_tags: List[MediaTagInfo] = [
                MediaTagInfo(**item) for item in json.load(f)
            ]
    else:
        media_tags: List[MediaTagInfo] = scan_media(src)
    proposal, manual_review = generate_rename_proposal(media_tags)

    with open("rename_proposal.json", "w") as f:
        json.dump(
            [item.model_dump(exclude_none=True) for item in proposal], f, indent=2
        )
    with open("manual_review.json", "w") as f:
        json.dump(manual_review, f, indent=2)
    print(
        "Proposal saved to rename_proposal.json. Manual review list saved to manual_review.json."
    )


def generate_rename_proposal(media_tags: List[MediaTagInfo]):
    """
    Generate a renaming proposal and manual review list from media_tags.
    Returns (proposal, manual_review).
    """
    proposal: List[RenameProposalItem] = []
    manual_review = []
    proposed_name_counts = {}

    for m in media_tags:
        dt = extract_datetime_from_tags(m.tags, m.media_type)
        if not dt:
            dt = infer_datetime_from_filename(m.filename)
        ext = os.path.splitext(m.filename)[1].lower()
        burst_tag = extract_burst_tags(m.filename)
        if dt:
            base_new_name = propose_new_name(dt, ext, burst_tag)
            dir_name = os.path.dirname(m.filename)
            base_name, ext_only = os.path.splitext(base_new_name)
            count = proposed_name_counts.get(base_new_name, 0)
            if count == 0:
                final_name = os.path.join(dir_name, base_new_name)
            else:
                postfix = f"_{count + 1:02d}"
                final_name = os.path.join(dir_name, f"{base_name}{postfix}{ext_only}")
            proposed_name_counts[base_new_name] = count + 1
            proposal.append(
                RenameProposalItem(original=m.filename, proposed=final_name)
            )
        else:
            manual_review.append(m.filename)
    return proposal, manual_review


if __name__ == "__main__":
    main()
