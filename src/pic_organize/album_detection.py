"""
Album detection module for identifying album folders and extracting album names.

This module uses various heuristics to determine if a folder represents an album
and extracts meaningful album names from folder names or metadata.
"""

import os
import re
from typing import Tuple
from collections import Counter


class AlbumDetector:
    """Detects album folders using various heuristics."""

    def __init__(self):
        # Album keywords that suggest a folder is an album
        self.album_keywords = [
            "album",
            "vacation",
            "trip",
            "holiday",
            "wedding",
            "birthday",
            "party",
            "event",
            "festival",
            "concert",
            "graduation",
            "family",
            "christmas",
            "xmas",
            "easter",
            "thanksgiving",
            "new year",
            "anniversary",
            "celebration",
            "reunion",
            "picnic",
            "barbecue",
            "bbq",
            "camping",
            "hiking",
            "beach",
            "mountain",
            "city",
            "travel",
            "adventure",
            "safari",
            "cruise",
            "road trip",
            "honeymoon",
            "baby",
            "shower",
            "sport",
            "game",
            "match",
            "tournament",
            "conference",
            "meeting",
            "workshop",
            "seminar",
            "course",
            "school",
            "college",
            "university",
            "work",
            "office",
            "project",
        ]

        # Location patterns that suggest albums
        self.location_patterns = [
            r"(?i)\b(paris|london|tokyo|beijing|sydney|rome|madrid|berlin|amsterdam|vienna)\b",
            r"(?i)\b(new york|los angeles|san francisco|chicago|miami|boston|seattle|las vegas)\b",
            r"(?i)\b(italy|france|spain|germany|japan|australia|canada|mexico|brazil|india)\b",
            r"(?i)\b(europe|asia|america|africa|oceania)\b",
            r"(?i)\b(lake|mountain|beach|forest|desert|valley|river|ocean|sea)\b",
        ]

        # Date patterns to remove from album names
        self.date_patterns = [
            r"\b\d{4}[-_]\d{2}[-_]\d{2}\b",  # YYYY-MM-DD or YYYY_MM_DD
            r"\b\d{8}\b",  # YYYYMMDD
            r"\b\d{4}[-_]\d{2}\b",  # YYYY-MM or YYYY_MM
            r"\b\d{2}[-_]\d{2}[-_]\d{4}\b",  # DD-MM-YYYY or MM-DD-YYYY
            r"\b\d{1,2}[-_]\d{1,2}[-_]\d{2,4}\b",  # Various date formats
        ]

    def detect_album(self, folder_info) -> Tuple[bool, str]:
        """
        Detect if a folder represents an album and extract album name.

        Args:
            folder_info: FolderInfo object containing folder information

        Returns:
            Tuple of (is_album, album_name)
        """
        folder_name = os.path.basename(folder_info.path)

        # Skip if folder name is empty or just a date
        if not folder_name or self._is_pure_date_folder(folder_name):
            return False, ""

        # Check various album detection heuristics
        album_score = 0

        # Heuristic 1: Check for album keywords
        if self._contains_album_keywords(folder_name):
            album_score += 3

        # Heuristic 2: Check for location patterns
        if self._contains_location_patterns(folder_name):
            album_score += 2

        # Heuristic 3: Check for descriptive names (not just numbers/dates)
        if self._is_descriptive_name(folder_name):
            album_score += 2

        # Heuristic 4: Check metadata consistency (same camera, event, etc.)
        if self._has_consistent_metadata(folder_info.media_files):
            album_score += 1

        # Heuristic 5: Check for sequential naming patterns
        if self._has_sequential_files(folder_info.media_files):
            album_score += 1

        # Determine if it's an album (threshold-based decision)
        is_album = album_score >= 2

        if is_album:
            cleaned_name = self._extract_album_name(folder_name)
            return True, cleaned_name

        return False, ""

    def _is_pure_date_folder(self, folder_name: str) -> bool:
        """Check if folder name is purely a date pattern."""
        date_only_patterns = [
            r"^\d{4}[-_]\d{2}[-_]\d{2}$",
            r"^\d{8}$",
            r"^\d{4}[-_]\d{2}$",
            r"^\d{2}[-_]\d{2}[-_]\d{4}$",
            r"^\d{4}$",  # Just a year
        ]

        for pattern in date_only_patterns:
            if re.match(pattern, folder_name):
                return True
        return False

    def _contains_album_keywords(self, folder_name: str) -> bool:
        """Check if folder name contains album-related keywords."""
        folder_lower = folder_name.lower()
        return any(keyword in folder_lower for keyword in self.album_keywords)

    def _contains_location_patterns(self, folder_name: str) -> bool:
        """Check if folder name contains location patterns."""
        for pattern in self.location_patterns:
            if re.search(pattern, folder_name):
                return True
        return False

    def _is_descriptive_name(self, folder_name: str) -> bool:
        """Check if folder name is descriptive (contains meaningful text)."""
        # Remove dates and common separators
        cleaned = folder_name
        for pattern in self.date_patterns:
            cleaned = re.sub(pattern, "", cleaned)

        # Remove separators and check remaining content
        cleaned = re.sub(r"[-_\s]+", " ", cleaned).strip()

        # Must have at least some alphabetic characters
        if not re.search(r"[a-zA-Z]", cleaned):
            return False

        # Must have reasonable length after cleaning
        if len(cleaned) < 3:
            return False

        # Should not be just numbers
        if cleaned.isdigit():
            return False

        return True

    def _has_consistent_metadata(self, media_files) -> bool:
        """Check if media files have consistent metadata suggesting an album."""
        if len(media_files) < 3:  # Need at least 3 files for consistency check
            return False

        # Check for consistent camera model
        cameras = []
        for media_file in media_files:
            camera = (
                media_file.tags.get("Make", "") + " " + media_file.tags.get("Model", "")
            )
            if camera.strip():
                cameras.append(camera.strip())

        if len(cameras) >= len(media_files) * 0.7:  # 70% of files have camera info
            camera_counter = Counter(cameras)
            most_common_count = camera_counter.most_common(1)[0][1] if cameras else 0
            if most_common_count >= len(cameras) * 0.8:  # 80% same camera
                return True

        # Check for GPS coordinates (suggesting a trip/location)
        gps_files = 0
        for media_file in media_files:
            if any(key.startswith("GPS") for key in media_file.tags.keys()):
                gps_files += 1

        if gps_files >= len(media_files) * 0.3:  # 30% have GPS
            return True

        return False

    def _has_sequential_files(self, media_files) -> bool:
        """Check if files follow sequential naming patterns."""
        if len(media_files) < 5:  # Need at least 5 files for sequence check
            return False

        # Extract numeric sequences from filenames
        sequences = []
        for media_file in media_files:
            filename = os.path.basename(media_file.filename)
            # Look for numbers in filename
            numbers = re.findall(r"\d+", filename)
            if numbers:
                # Use the last (typically most significant) number
                sequences.append(int(numbers[-1]))

        if len(sequences) >= len(media_files) * 0.7:  # 70% have numbers
            sequences.sort()
            # Check if numbers are roughly sequential
            gaps = []
            for i in range(1, len(sequences)):
                gaps.append(sequences[i] - sequences[i - 1])

            # Most gaps should be small (1-10)
            small_gaps = sum(1 for gap in gaps if 1 <= gap <= 10)
            if small_gaps >= len(gaps) * 0.7:  # 70% of gaps are small
                return True

        return False

    def _extract_album_name(self, folder_name: str) -> str:
        """Extract clean album name from folder name."""
        # Start with the original name
        cleaned = folder_name

        # Remove date patterns
        for pattern in self.date_patterns:
            cleaned = re.sub(pattern, "", cleaned)

        # Remove leading/trailing separators
        cleaned = re.sub(r"^[-_\s]+|[-_\s]+$", "", cleaned)

        # Normalize separators to underscores
        cleaned = re.sub(r"[-_\s]+", "_", cleaned)

        # Remove non-alphanumeric characters except underscores
        cleaned = re.sub(r"[^\w_]", "", cleaned)

        # Capitalize words for readability
        if cleaned:
            parts = cleaned.split("_")
            capitalized_parts = []
            for part in parts:
                if part:
                    # Capitalize first letter, keep rest as-is to preserve acronyms
                    capitalized_parts.append(part[0].upper() + part[1:])
            cleaned = "_".join(capitalized_parts)

        # Limit length
        if len(cleaned) > 25:
            cleaned = cleaned[:25]

        # Fallback if nothing meaningful remains
        if not cleaned or len(cleaned) < 2:
            cleaned = "Album"

        return cleaned
