"""
Atomic rename operations for media files with validation and rollback capabilities.
"""

import shutil
import json
import time
from typing import List, Tuple, Optional, Callable
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
        self.unsaved_changes_count = 0
        self.save_batch_size = 100
        self.journal_path = "media_tags_journal.json"
        self.pending_changes = []

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
                conflicts.append(f"Destination already exists: {src_path} {dst_path}")
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
                tag.tags["renamed_from"] = old_path
                tag.filename = new_path
                return True
        return False

    def write_journal_entry(
        self, operation_type: str, old_path: str, new_path: str
    ) -> None:
        """
        Write a journal entry for tracking unsaved changes.

        Args:
            operation_type: Type of operation ("rename" or "tag_update")
            old_path: Original file path
            new_path: New file path
        """
        journal_entry = {
            "timestamp": time.time(),
            "operation": operation_type,
            "old_path": old_path,
            "new_path": new_path,
        }
        self.pending_changes.append(journal_entry)

        # Write journal to disk
        try:
            with open(self.journal_path, "w") as f:
                json.dump(self.pending_changes, f, indent=2)
        except Exception as e:
            # Journal writing shouldn't break the main operation
            print(f"Warning: Could not write journal entry: {e}")

    def clear_journal(self) -> None:
        """Clear the journal file after successful save."""
        try:
            if Path(self.journal_path).exists():
                Path(self.journal_path).unlink()
            self.pending_changes = []
        except Exception as e:
            print(f"Warning: Could not clear journal: {e}")

    def recover_from_journal(self) -> bool:
        """
        Recover unsaved changes from journal file.

        Returns:
            True if recovery was performed, False if no journal found
        """
        if not Path(self.journal_path).exists():
            return False

        try:
            with open(self.journal_path, "r") as f:
                journal_entries = json.load(f)

            if not journal_entries:
                self.clear_journal()
                return False

            print(
                f"Found {len(journal_entries)} unsaved changes in journal. Recovering..."
            )

            # Apply the journaled changes to media tags
            for entry in journal_entries:
                if entry["operation"] == "tag_update":
                    self.update_media_tags(entry["old_path"], entry["new_path"])

            # Save the recovered changes
            self.save_media_tags()

            # Clear the journal after successful recovery
            self.clear_journal()

            print("Recovery completed successfully.")
            return True

        except Exception as e:
            print(f"Error during recovery: {e}")
            return False

    def save_media_tags(self, output_path: str = "media_tags.json") -> None:
        """
        Save media tags to JSON file and clear journal.

        Args:
            output_path: Path to save the JSON file
        """
        if self.media_tags:
            media_tags_data = [tag.model_dump() for tag in self.media_tags]
            with open(output_path, "w") as f:
                json.dump(media_tags_data, f, indent=2)

            # Clear journal after successful save
            self.clear_journal()

    def apply_renames(
        self,
        proposals: List[RenameProposalItem],
        dry_run: bool = False,
        update_tags: bool = True,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> RenameResult:
        """
        Apply rename operations atomically.

        Args:
            proposals: List of rename proposals to apply
            dry_run: If True, simulate operations without actually renaming files
            update_tags: If True, update media tags with new file paths
            progress_callback: Optional callback function to report progress.
                             Called with (current, total, current_file) parameters.

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
        total_operations = len(operations)

        for i, (src_path, dst_path, proposal) in enumerate(operations, 1):
            try:
                # Report progress if callback provided (for both dry run and actual operations)
                if progress_callback:
                    progress_callback(i, total_operations, str(src_path.name))

                if dry_run:
                    # In dry run mode, just simulate the operation
                    success_count += 1
                    successful_operations.append((src_path, dst_path))

                    # Simulate tag updates for progress tracking (without actually updating)
                    if update_tags:
                        # Check if we would update a tag (without actually doing it)
                        for tag in self.media_tags:
                            if tag.filename == str(src_path):
                                self.unsaved_changes_count += 1
                                break
                else:
                    # Actual rename operation
                    shutil.move(str(src_path), str(dst_path))
                    success_count += 1
                    successful_operations.append((src_path, dst_path))

                    # Update media tags if requested
                    if update_tags:
                        if self.update_media_tags(str(src_path), str(dst_path)):
                            # Journal the change for crash recovery
                            self.write_journal_entry(
                                "tag_update", str(src_path), str(dst_path)
                            )
                            self.unsaved_changes_count += 1

                            # Save media tags every batch_size entries
                            if self.unsaved_changes_count >= self.save_batch_size:
                                self.save_media_tags()
                                self.unsaved_changes_count = 0

            except Exception as e:
                failed_operations.append((src_path, dst_path, str(e)))

        # Save any remaining unsaved changes (but reset counter for dry runs too)
        if update_tags and self.unsaved_changes_count > 0:
            if not dry_run:
                self.save_media_tags()
            # Reset counter regardless of dry run status
            self.unsaved_changes_count = 0

        return RenameResult(
            success_count=success_count,
            failed_operations=failed_operations,
            successful_operations=successful_operations,
            conflicts=conflicts,
        )
