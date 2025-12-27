"""Functions for summarizing tag statistics from media files."""

from collections import Counter
from typing import List, Dict, Any
from pic_organize.tag_info import MediaTagInfo


def summarize_tags(media_tags: List[MediaTagInfo]) -> Dict[str, Any]:
    """
    Summarize tag statistics from a list of MediaTagInfo objects.

    Args:
        media_tags (List[MediaTagInfo]): List of media tag info objects.

    Returns:
        Dict[str, Any]: Dictionary with tag type counts, tag value counts, and total file count.
    """
    tag_type_counter: Counter[str] = Counter()
    tag_value_counter: Counter[str] = Counter()
    for item in media_tags:
        for tag, value in item.tags.items():
            tag_type_counter[tag] += 1
            tag_value_counter[f"{tag}:{str(value)}"] += 1
    return {
        "tag_type_counts": dict(tag_type_counter),
        "tag_value_counts": dict(tag_value_counter),
        "total_files": len(media_tags),
    }
