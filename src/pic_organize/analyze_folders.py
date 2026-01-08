"""
Folder analysis module for organizing media folders by time ranges or album names.

This module scans directory structures containing media files and generates
proposals for renaming folders based on the date/time metadata of their contents.
"""

import os
import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

from .extract_tags import scan_media
from .rename_by_datetime import extract_datetime_from_tags, infer_datetime_from_filename
from .tag_info import MediaTagInfo


@dataclass
class FolderInfo:
    """Information about a folder containing media files."""

    path: str
    media_files: List[MediaTagInfo]
    min_date: Optional[datetime]
    max_date: Optional[datetime]
    album_name: Optional[str] = None
    is_album: bool = False


@dataclass
class FolderRenameProposal:
    """Proposal for renaming a folder."""

    original_path: str
    proposed_path: str
    reason: str
    folder_info: FolderInfo
    conflicts_with: List[str] = field(default_factory=list)


class FolderAnalyzer:
    """Analyzes folders containing media files and generates rename proposals."""

    def __init__(self):
        self.media_tags: List[MediaTagInfo] = []
        self.folder_infos: Dict[str, FolderInfo] = {}

    def scan_directory(self, root_directory: str) -> None:
        """
        Scan directory for media files and organize by folders.

        Args:
            root_directory: Root directory to scan for media files
        """
        self.media_tags = scan_media(root_directory)
        self._organize_files_by_folders()

    def _organize_files_by_folders(self) -> None:
        """Group media files by their containing folders."""
        folder_files = defaultdict(list)

        for media_file in self.media_tags:
            folder_path = os.path.dirname(media_file.filename)

            # Skip hidden folders (starting with .) and Trash folder
            folder_name = os.path.basename(folder_path)
            if folder_name.startswith(".") or folder_name.lower() == "trash":
                continue

            folder_files[folder_path].append(media_file)

        # Create FolderInfo objects
        for folder_path, files in folder_files.items():
            if not files:  # Skip empty folders
                continue

            dates = []
            for file_info in files:
                # Extract datetime from metadata or filename
                dt = extract_datetime_from_tags(file_info.tags, file_info.media_type)
                if not dt:
                    dt = infer_datetime_from_filename(file_info.filename)
                if dt:
                    dates.append(dt)

            min_date = min(dates) if dates else None
            max_date = max(dates) if dates else None

            folder_info = FolderInfo(
                path=folder_path,
                media_files=files,
                min_date=min_date,
                max_date=max_date,
            )

            self.folder_infos[folder_path] = folder_info

    def detect_albums(self) -> None:
        """Detect which folders represent albums and extract album names."""
        from .album_detection import AlbumDetector

        detector = AlbumDetector()

        for folder_path, folder_info in self.folder_infos.items():
            is_album, album_name = detector.detect_album(folder_info)
            folder_info.is_album = is_album
            folder_info.album_name = album_name

    def generate_folder_name(self, folder_info: FolderInfo) -> Tuple[str, str]:
        """
        Generate new folder name based on time range or album information.

        Args:
            folder_info: Information about the folder

        Returns:
            Tuple of (new_folder_name, reason)
        """
        if not folder_info.min_date:
            return os.path.basename(folder_info.path), "No date information found"

        if folder_info.is_album and folder_info.album_name:
            # Album format: preserve time range for multi-year albums
            clean_album_name = self._clean_album_name(folder_info.album_name)

            # Check if album spans multiple years or months
            if folder_info.max_date and (
                folder_info.min_date.year != folder_info.max_date.year
                or folder_info.min_date.month != folder_info.max_date.month
            ):
                # Multi-period album: use full time range with album name
                if folder_info.min_date.year == folder_info.max_date.year:
                    # Same year: YYYY_MMstart-MMend_AlbumName
                    year = folder_info.min_date.year
                    month_start = folder_info.min_date.month
                    month_end = folder_info.max_date.month
                    new_name = f"{year:04d}_{month_start:02d}-{month_end:02d}_{clean_album_name}"
                else:
                    # Cross-year: YYYYstart_MMstart-YYYYend_MMend_AlbumName
                    new_name = f"{folder_info.min_date.year:04d}_{folder_info.min_date.month:02d}-{folder_info.max_date.year:04d}_{folder_info.max_date.month:02d}_{clean_album_name}"
            else:
                # Single period album: YYYY_MM_AlbumName
                year = folder_info.min_date.year
                month = folder_info.min_date.month
                new_name = f"{year:04d}_{month:02d}_{clean_album_name}"

            reason = f"Album detected: {folder_info.album_name}"

        elif folder_info.min_date == folder_info.max_date or not folder_info.max_date:
            # Single date: YYYY_MM
            year = folder_info.min_date.year
            month = folder_info.min_date.month
            new_name = f"{year:04d}_{month:02d}"
            reason = "Single month time range"

        else:
            # Check if dates span the same month
            if (
                folder_info.min_date.year == folder_info.max_date.year
                and folder_info.min_date.month == folder_info.max_date.month
            ):
                # Same month: YYYY_MM
                year = folder_info.min_date.year
                month = folder_info.min_date.month
                new_name = f"{year:04d}_{month:02d}"
                reason = "Single month time range"
            else:
                # Different months: YYYY_MMstart-MMend or handle year crossing
                if folder_info.min_date.year == folder_info.max_date.year:
                    # Same year: YYYY_MMstart-MMend
                    year = folder_info.min_date.year
                    month_start = folder_info.min_date.month
                    month_end = folder_info.max_date.month
                    new_name = f"{year:04d}_{month_start:02d}-{month_end:02d}"
                    reason = (
                        f"Multi-month time range ({month_start:02d} to {month_end:02d})"
                    )
                else:
                    # Crossing years: use start year and month range
                    year = folder_info.min_date.year
                    month_start = folder_info.min_date.month
                    month_end = folder_info.max_date.month
                    new_name = f"{year:04d}_{month_start:02d}-{folder_info.max_date.year}_{month_end:02d}"
                    reason = f"Cross-year time range ({folder_info.min_date.year}-{month_start:02d} to {folder_info.max_date.year}-{month_end:02d})"

        return new_name, reason

    def _clean_album_name(self, album_name: str) -> str:
        """Clean album name for use in folder names."""
        # Extract album name starting from the first letter
        match = re.search(r"[a-zA-Z]", album_name)
        if match:
            return album_name[match.start() :]
        return "Album"

    def generate_rename_proposals(self) -> List[FolderRenameProposal]:
        """
        Generate folder rename proposals with merging for same-named folders.

        Returns:
            List of folder rename proposals
        """
        proposals = []
        name_to_folders = defaultdict(list)

        # Group folders by their proposed full paths
        for folder_path, folder_info in self.folder_infos.items():
            current_name = os.path.basename(folder_path)
            parent_dir = os.path.dirname(folder_path)

            new_name, reason = self.generate_folder_name(folder_info)

            # Use full path as the key to avoid conflicts
            full_proposed_path = os.path.join(parent_dir, new_name)
            name_to_folders[full_proposed_path].append(
                (folder_path, folder_info, reason, parent_dir, current_name)
            )

        # Process groups: merge same-named folders or add counters for albums
        for new_name, folder_group in name_to_folders.items():
            if len(folder_group) == 1:
                # Single folder, no conflict
                folder_path, folder_info, reason, parent_dir, current_name = (
                    folder_group[0]
                )

                if new_name != current_name:
                    new_path = (
                        os.path.join(parent_dir, new_name) if parent_dir else new_name
                    )
                    proposal = FolderRenameProposal(
                        original_path=folder_path,
                        proposed_path=new_path,
                        reason=reason,
                        folder_info=folder_info,
                    )
                    proposals.append(proposal)

            else:
                # Multiple folders want the same name
                # Check if they're all non-album time-based folders (can be merged)
                all_non_album = all(
                    not folder_info.is_album for _, folder_info, _, _, _ in folder_group
                )

                if all_non_album:
                    # These are time-based folders for the same period - suggest merging
                    # Create proposals that indicate they should be merged
                    primary_folder = folder_group[0]  # Use first as primary target
                    folder_path, folder_info, reason, parent_dir, current_name = (
                        primary_folder
                    )

                    if new_name != current_name:
                        new_path = (
                            os.path.join(parent_dir, new_name)
                            if parent_dir
                            else new_name
                        )

                        # Combine all files from conflicting folders for the proposal
                        all_files = []
                        all_dates = []
                        for _, fi, _, _, _ in folder_group:
                            all_files.extend(fi.media_files)
                            if fi.min_date:
                                all_dates.append(fi.min_date)
                            if fi.max_date:
                                all_dates.append(fi.max_date)

                        # Create a combined folder info
                        combined_folder_info = FolderInfo(
                            path=folder_path,
                            media_files=all_files,
                            min_date=min(all_dates) if all_dates else None,
                            max_date=max(all_dates) if all_dates else None,
                            album_name=folder_info.album_name,
                            is_album=folder_info.is_album,
                        )

                        merge_reason = f"{reason} (merging {len(folder_group)} folders with same time period)"

                        proposal = FolderRenameProposal(
                            original_path=folder_path,
                            proposed_path=new_path,
                            reason=merge_reason,
                            folder_info=combined_folder_info,
                        )
                        proposals.append(proposal)

                        # Create proposals for other folders to be merged into this one
                        for (
                            other_folder_path,
                            other_folder_info,
                            _,
                            other_parent_dir,
                            other_current_name,
                        ) in folder_group[1:]:
                            if new_name != other_current_name:
                                merge_proposal = FolderRenameProposal(
                                    original_path=other_folder_path,
                                    proposed_path=new_path,  # Same destination
                                    reason=f"Merge into {new_name}",
                                    folder_info=other_folder_info,
                                )
                                proposals.append(merge_proposal)

                else:
                    # Albums or mixed types - add counters to distinguish
                    for i, (
                        folder_path,
                        folder_info,
                        reason,
                        parent_dir,
                        current_name,
                    ) in enumerate(folder_group):
                        if folder_info.is_album:
                            # For albums, append counter before album name
                            parts = new_name.split("_")
                            if (
                                len(parts) >= 3 and i > 0
                            ):  # YYYY_MM_AlbumName, but keep first unchanged
                                counter_name = (
                                    f"{parts[0]}_{parts[1]}_{i+1:02d}_{parts[2]}"
                                )
                            else:
                                counter_name = (
                                    new_name if i == 0 else f"{new_name}_{i+1:02d}"
                                )
                        else:
                            # For time ranges, append counter
                            counter_name = (
                                new_name if i == 0 else f"{new_name}_{i+1:02d}"
                            )

                        if counter_name != current_name:
                            new_path = (
                                os.path.join(parent_dir, counter_name)
                                if parent_dir
                                else counter_name
                            )
                            proposal = FolderRenameProposal(
                                original_path=folder_path,
                                proposed_path=new_path,
                                reason=reason,
                                folder_info=folder_info,
                            )
                            proposals.append(proposal)

        return proposals

    def validate_proposals(
        self, proposals: List[FolderRenameProposal]
    ) -> List[FolderRenameProposal]:
        """
        Validate rename proposals and check for conflicts.

        Args:
            proposals: List of rename proposals to validate

        Returns:
            List of validated proposals with conflict information
        """
        validated_proposals = []
        existing_paths = set()

        # Collect all existing directory names
        for folder_path in self.folder_infos.keys():
            existing_paths.add(folder_path)

        for proposal in proposals:
            conflicts = []

            # Check if destination already exists (and isn't the source)
            if (
                os.path.exists(proposal.proposed_path)
                and proposal.proposed_path != proposal.original_path
            ):
                conflicts.append(
                    f"Destination already exists: {proposal.proposed_path}"
                )

            # Check for conflicts with other proposals
            for other_proposal in proposals:
                if (
                    other_proposal != proposal
                    and other_proposal.proposed_path == proposal.proposed_path
                ):
                    conflicts.append(
                        f"Conflict with another rename: {other_proposal.original_path}"
                    )

            proposal.conflicts_with = conflicts
            validated_proposals.append(proposal)

        return validated_proposals


def analyze_folders(root_directory: str) -> List[FolderRenameProposal]:
    """
    Convenience function to analyze folders and generate rename proposals.

    Args:
        root_directory: Root directory to scan for media files

    Returns:
        List of folder rename proposals
    """
    analyzer = FolderAnalyzer()
    analyzer.scan_directory(root_directory)
    analyzer.detect_albums()
    proposals = analyzer.generate_rename_proposals()
    return analyzer.validate_proposals(proposals)
