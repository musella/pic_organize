"""
Atomic rename operations for media files with validation and rollback capabilities.
"""

import shutil
import json
from typing import List, Tuple, Optional
from pathlib import Path
from dataclasses import dataclass

from .rename_by_datetime import RenameProposalItem
from .tag_info import MediaTagInfo


@dataclass
class RenameResult:
    """Result of a rename operation."""

    success_count: int
    failed_operations: List[Tuple[Path, Path, str]]
    successful_operations: List[Tuple[Path, Path]]
    conflicts: List[str]


class AtomicRenamer:
    """Handles atomic rename operations with validation and tag updates."""

    def __init__(self, media_tags: Optional[List[MediaTagInfo]] = None):
        """
        Initialize the atomic renamer.

        Args:
            media_tags: Optional list of media tags to update during renames
        """
        self.media_tags = media_tags or []

    def validate_operations(
        self, proposals: List[RenameProposalItem]
    ) -> Tuple[List[Tuple[Path, Path, RenameProposalItem]], List[str]]:
        """
        Validate rename operations and return valid operations and conflicts.

        Args:
            proposals: List of rename proposals to validate

        Returns:
            Tuple of (valid_operations, conflicts)
        """
        operations = []
        conflicts = []

        for proposal in proposals:
            src_path = Path(proposal.original)
            dst_path = Path(proposal.proposed)

            # Check source file exists
            if not src_path.exists():
                conflicts.append(f"Source file no longer exists: {src_path}")
                continue

            # Create destination directory if needed
            try:
                dst_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                conflicts.append(f"Cannot create directory for {dst_path}: {e}")
                continue

            # Check for destination conflicts
            if dst_path.exists() and dst_path != src_path:
                conflicts.append(f"Destination already exists: {dst_path}")
                continue

            # Only include if paths are actually different
            if src_path != dst_path:
                operations.append((src_path, dst_path, proposal))

        return operations, conflicts

    def update_media_tags(self, old_path: str, new_path: str) -> bool:
        """
        Update media tags with new file path.

        Args:
            old_path: Original file path
            new_path: New file path

        Returns:
            True if tag was updated, False otherwise
        """
        for tag in self.media_tags:
            if tag.filename == old_path:
                tag.filename = new_path
                return True
        return False

    def save_media_tags(self, output_path: str = "media_tags.json") -> None:
        """
        Save media tags to JSON file.

        Args:
            output_path: Path to save the JSON file
        """
        if self.media_tags:
            media_tags_data = [tag.model_dump() for tag in self.media_tags]
            with open(output_path, "w") as f:
                json.dump(media_tags_data, f, indent=2)

    def apply_renames(
        self,
        proposals: List[RenameProposalItem],
        dry_run: bool = False,
        update_tags: bool = True,
    ) -> RenameResult:
        """
        Apply rename operations atomically.

        Args:
            proposals: List of rename proposals to apply
            dry_run: If True, simulate operations without actually renaming files
            update_tags: If True, update media tags with new file paths

        Returns:
            RenameResult with operation details
        """
        # Validate all operations first
        operations, conflicts = self.validate_operations(proposals)

        if not operations:
            return RenameResult(
                success_count=0,
                failed_operations=[],
                successful_operations=[],
                conflicts=conflicts,
            )

        # Apply operations
        success_count = 0
        failed_operations = []
        successful_operations = []

        for src_path, dst_path, proposal in operations:
            try:
                if dry_run:
                    # In dry run mode, just simulate the operation
                    success_count += 1
                    successful_operations.append((src_path, dst_path))
                else:
                    # Actual rename operation
                    shutil.move(str(src_path), str(dst_path))
                    success_count += 1
                    successful_operations.append((src_path, dst_path))

                    # Update media tags if requested
                    if update_tags:
                        self.update_media_tags(str(src_path), str(dst_path))

            except Exception as e:
                failed_operations.append((src_path, dst_path, str(e)))

        return RenameResult(
            success_count=success_count,
            failed_operations=failed_operations,
            successful_operations=successful_operations,
            conflicts=conflicts,
        )
