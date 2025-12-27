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


def propose_new_name(dt: datetime, ext: str) -> str:
    """
    Generate a new file name in the format IMG_YYYYMMDD_HHMMSS.ext.

    Args:
        dt (datetime): The date and time.
        ext (str): The file extension (including dot).

    Returns:
        str: Proposed new file name.
    """
    return f"IMG_{dt.strftime('%Y%m%d_%H%M%S')}{ext}"


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
    proposal: List[RenameProposalItem] = []
    manual_review = []

    for m in media_tags:
        dt = extract_datetime_from_tags(m.tags, m.media_type)
        if not dt:
            dt = infer_datetime_from_filename(m.filename)
        ext = os.path.splitext(m.filename)[1].lower()
        if dt:
            new_name = propose_new_name(dt, ext)
            # Use full path for proposed
            proposed_full_path = os.path.join(os.path.dirname(m.filename), new_name)
            proposal.append(
                RenameProposalItem(original=m.filename, proposed=proposed_full_path)
            )
        else:
            manual_review.append(m.filename)

    # Ensure uniqueness of proposed names within the proposal
    seen = set()
    for item in proposal:
        name = item.proposed
        if name in seen:
            item.note = "DUPLICATE_NAME"
        seen.add(name)

    with open("rename_proposal.json", "w") as f:
        json.dump(
            [item.model_dump(exclude_none=True) for item in proposal], f, indent=2
        )
    with open("manual_review.json", "w") as f:
        json.dump(manual_review, f, indent=2)
    print(
        "Proposal saved to rename_proposal.json. Manual review list saved to manual_review.json."
    )


if __name__ == "__main__":
    main()
