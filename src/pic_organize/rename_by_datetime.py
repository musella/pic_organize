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
    # Original patterns
    re.compile(r"(\d{4})(\d{2})(\d{2})[_\-]?(\d{2})(\d{2})(\d{2})"),
    re.compile(r"(\d{4})-(\d{2})-(\d{2})[_\-]?(\d{2})-(\d{2})-(\d{2})"),
    re.compile(r"(\d{4})-(\d{2})-(\d{2})[_\-](\d{2})(\d{2})(\d{2})"),
    # New patterns from analysis
    re.compile(r"Screenshot from (\d{4})-(\d{2})-(\d{2}) (\d{2})-(\d{2})-(\d{2})"),
    re.compile(r"/(\d{4})-(\d{2})-(\d{2})[_\-]?(\d{2})?[_\-]?(\d{2})?[_\-]?(\d{2})?"),
    re.compile(r"/(\d{4})-(\d{2})[\-_]"),
    re.compile(r"/(\d{4})_(\d{2})_(\d{2})"),  # YYYY_MM_DD directory format
    re.compile(r"P([1-9A-C])(\d{2})(\d{4})"),
    re.compile(r"IMG_(\d{4})\.(MOV|JPG)", re.IGNORECASE),
    re.compile(r"(\d{2})\.(\d{2})\.(\d{2})"),
    re.compile(
        r"(\d{4})-(\d{2})-(\d{2}) (\d{2})\.(\d{2})\.(\d{2})"
    ),  # YYYY-MM-DD HH.MM.SS format
    re.compile(
        r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s*(\d{2})", re.IGNORECASE
    ),
]


def load_exclude_patterns() -> List[str]:
    """Load exclude folder patterns from JSON file."""
    try:
        exclude_patterns_file = os.path.join(
            os.path.dirname(__file__), "..", "..", "data", "exclude_patterns.json"
        )
        with open(exclude_patterns_file, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        # Fallback to default patterns if file doesn't exist or is invalid
        print(f"Warning: Could not load exclude patterns from JSON file: {e}")
        return []


# Load exclude patterns from JSON file
EXCLUDE_FOLDER_PATTERNS = load_exclude_patterns()


def should_exclude_file(filepath: str) -> bool:
    """Check if file should be excluded from datetime extraction based on folder patterns."""
    for pattern in EXCLUDE_FOLDER_PATTERNS:
        if re.search(pattern, filepath):
            return True
    return False


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


def extract_screenshot_datetime(match) -> Optional[datetime]:
    """Extract datetime from 'Screenshot from YYYY-MM-DD HH-MM-SS' pattern."""
    year, month, day, hour, minute, second = match.groups()
    return datetime(
        int(year), int(month), int(day), int(hour), int(minute), int(second)
    )


def extract_directory_full_date(match, filepath: str) -> Optional[datetime]:
    """Extract date from directory names like '/2008-04-04_05_06'."""
    groups = match.groups()
    if len(groups) >= 3:
        year, month, day = groups[:3]
        hour = int(groups[3]) if len(groups) > 3 and groups[3] else 12
        minute = int(groups[4]) if len(groups) > 4 and groups[4] else 0
        second = int(groups[5]) if len(groups) > 5 and groups[5] else 0
        return datetime(int(year), int(month), int(day), hour, minute, second)
    return None


def extract_directory_year_month(match, filepath: str) -> Optional[datetime]:
    """Extract date from directory names like '/2007-01-Parigi'."""
    year, month = match.groups()
    return datetime(int(year), int(month), 1, 12, 0, 0)


def extract_directory_yyyy_mm_dd(match, filepath: str) -> Optional[datetime]:
    """Extract date from directory names like '/2022_02_LaThuille/'."""
    year, month, day = match.groups()
    return datetime(int(year), int(month), int(day), 12, 0, 0)


def extract_camera_p_pattern(
    match, filepath: str, media_tags_lookup: Optional[Dict] = None
) -> Optional[datetime]:
    """Extract date from camera patterns like P8051152.JPG."""
    filename = os.path.basename(filepath)

    # First try to get datetime from media_tags.json lookup if available
    if media_tags_lookup and filename in media_tags_lookup:
        datetime_str = media_tags_lookup[filename]
        try:
            # Parse EXIF datetime format: "2017:03:13 20:59:36"
            return datetime.strptime(datetime_str, "%Y:%m:%d %H:%M:%S")
        except ValueError:
            pass

    # Fallback to filename pattern analysis
    month_code = match.group(1).upper()
    numbers = match.group(2)

    # Month code mapping (P1=Jan, P2=Feb, ..., PA=Oct, PB=Nov, PC=Dec)
    month_map = {
        "1": 1,
        "2": 2,
        "3": 3,
        "4": 4,
        "5": 5,
        "6": 6,
        "7": 7,
        "8": 8,
        "9": 9,
        "A": 10,
        "B": 11,
        "C": 12,
    }

    if month_code not in month_map:
        return None

    month = month_map[month_code]

    # Extract day from numbers (first 1-2 digits typically)
    if len(numbers) >= 2:
        day = int(numbers[:2])
        if day < 1 or day > 31:
            day = int(numbers[0]) if numbers[0] != "0" else 1
    else:
        day = int(numbers[0]) if numbers and numbers[0] != "0" else 1

    # Default to reasonable year for this camera type
    year = 2012  # Typical for this camera model era

    return datetime(year, month, day, 12, 0, 0)


def extract_img_number_context(match, filepath: str) -> Optional[datetime]:
    """Extract date from IMG_XXXX.MOV patterns using directory context."""
    # Extract year from directory path
    year_pattern = re.compile(r"(19\d{2}|20\d{2})")
    year_matches = year_pattern.findall(filepath)
    if year_matches:
        year = int(year_matches[-1])

        # Look for month in directory path
        month_patterns = [
            (r"[\-_]01[\-_]", 1),
            (r"[\-_]02[\-_]", 2),
            (r"[\-_]03[\-_]", 3),
            (r"[\-_]04[\-_]", 4),
            (r"[\-_]05[\-_]", 5),
            (r"[\-_]06[\-_]", 6),
            (r"[\-_]07[\-_]", 7),
            (r"[\-_]08[\-_]", 8),
            (r"[\-_]09[\-_]", 9),
            (r"[\-_]10[\-_]", 10),
            (r"[\-_]11[\-_]", 11),
            (r"[\-_]12[\-_]", 12),
        ]

        month = 6  # default
        for pattern, m in month_patterns:
            if re.search(pattern, filepath):
                month = m
                break

        return datetime(year, month, 1, 12, 0, 0)

    return None


def extract_date_dots(match) -> Optional[datetime]:
    """Extract date from DD.MM.YY format."""
    day, month, year = match.groups()
    year_int = int(year)
    if year_int < 50:  # Assume 20xx
        year_int += 2000
    else:  # Assume 19xx
        year_int += 1900

    return datetime(year_int, int(month), int(day), 12, 0, 0)


def extract_date_time_with_dots(match) -> Optional[datetime]:
    """Extract date from 'YYYY-MM-DD HH.MM.SS' format."""
    year, month, day, hour, minute, second = match.groups()
    return datetime(
        int(year), int(month), int(day), int(hour), int(minute), int(second)
    )


def extract_month_year_text(match) -> Optional[datetime]:
    """Extract date from 'apr 17' style patterns."""
    month_map = {
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
    }

    month_str = match.group(1).lower()
    year_str = match.group(2)

    if month_str in month_map:
        year_int = 2000 + int(year_str)  # Assume 20xx
        return datetime(year_int, month_map[month_str], 15, 12, 0, 0)

    return None


def infer_datetime_from_filename(filename: str) -> Optional[datetime]:
    """
    Infer date/time from filename using regex patterns.

    Args:
        filename (str): The file name to parse.

    Returns:
        Optional[datetime]: Parsed datetime if found, else None.
    """
    # Check if file should be excluded based on folder patterns
    if should_exclude_file(filename):
        return None

    base = os.path.basename(filename)

    # Try each pattern in order
    for i, pattern in enumerate(FILENAME_PATTERNS):
        # Use full path for directory patterns, basename for others
        search_text = filename if i in [4, 5, 6] else base
        match = pattern.search(search_text)

        if match:
            try:
                if i == 3:  # Screenshot pattern
                    return extract_screenshot_datetime(match)
                elif i == 4:  # Directory full date pattern
                    return extract_directory_full_date(match, filename)
                elif i == 5:  # Directory year-month pattern
                    return extract_directory_year_month(match, filename)
                elif i == 6:  # Directory YYYY_MM_DD pattern
                    return extract_directory_yyyy_mm_dd(match, filename)
                elif i == 7:  # Camera P pattern
                    return extract_camera_p_pattern(match, filename)
                elif i == 8:  # IMG context pattern
                    return extract_img_number_context(match, filename)
                elif i == 9:  # Date dots pattern
                    return extract_date_dots(match)
                elif i == 10:  # Date time with dots pattern (YYYY-MM-DD HH.MM.SS)
                    return extract_date_time_with_dots(match)
                elif i == 11:  # Month year text pattern
                    return extract_month_year_text(match)
                else:  # Original patterns (0, 1, 2)
                    y, mo, d, h, mi, s = map(int, match.groups())
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
