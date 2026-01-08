"""
Unit tests for atomic rename operations.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

from src.pic_organize.atomic_rename import AtomicRenamer, RenameResult
from src.pic_organize.rename_by_datetime import RenameProposalItem
from src.pic_organize.tag_info import MediaTagInfo


class TestAtomicRenamer:
    """Test cases for AtomicRenamer class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_file1 = self.temp_dir / "test1.jpg"
        self.test_file2 = self.temp_dir / "test2.jpg"
        self.dest_file1 = self.temp_dir / "renamed1.jpg"
        self.dest_file2 = self.temp_dir / "renamed2.jpg"

        # Create test files
        self.test_file1.write_text("test content 1")
        self.test_file2.write_text("test content 2")

        # Create test media tags
        self.media_tags = [
            MediaTagInfo(
                filename=str(self.test_file1),
                media_type="image",
                tags={"DateTime": "2023:01:01 12:00:00"},
            ),
            MediaTagInfo(
                filename=str(self.test_file2),
                media_type="image",
                tags={"DateTime": "2023:01:02 12:00:00"},
            ),
        ]

        self.renamer = AtomicRenamer(self.media_tags)

    def teardown_method(self):
        """Clean up after each test method."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_init_empty(self):
        """Test initialization with no media tags."""
        renamer = AtomicRenamer()
        assert renamer.media_tags == []

    def test_init_with_media_tags(self):
        """Test initialization with media tags."""
        assert len(self.renamer.media_tags) == 2
        assert self.renamer.media_tags[0].filename == str(self.test_file1)

    def test_validate_operations_success(self):
        """Test validation of successful operations."""
        proposals = [
            RenameProposalItem(
                original=str(self.test_file1), proposed=str(self.dest_file1), note=""
            ),
            RenameProposalItem(
                original=str(self.test_file2), proposed=str(self.dest_file2), note=""
            ),
        ]

        operations, conflicts = self.renamer.validate_operations(proposals)

        assert len(operations) == 2
        assert len(conflicts) == 0
        assert operations[0][0] == self.test_file1
        assert operations[0][1] == self.dest_file1

    def test_validate_operations_missing_source(self):
        """Test validation with missing source file."""
        missing_file = self.temp_dir / "missing.jpg"
        proposals = [
            RenameProposalItem(
                original=str(missing_file), proposed=str(self.dest_file1), note=""
            )
        ]

        operations, conflicts = self.renamer.validate_operations(proposals)

        assert len(operations) == 0
        assert len(conflicts) == 1
        assert "Source file no longer exists" in conflicts[0]

    def test_validate_operations_destination_exists(self):
        """Test validation with existing destination file."""
        # Create destination file
        self.dest_file1.write_text("existing content")

        proposals = [
            RenameProposalItem(
                original=str(self.test_file1), proposed=str(self.dest_file1), note=""
            )
        ]

        operations, conflicts = self.renamer.validate_operations(proposals)

        assert len(operations) == 0
        assert len(conflicts) == 1
        assert "Destination already exists" in conflicts[0]

    def test_validate_operations_same_path(self):
        """Test validation with same source and destination path."""
        proposals = [
            RenameProposalItem(
                original=str(self.test_file1),
                proposed=str(self.test_file1),  # Same file
                note="",
            )
        ]

        operations, conflicts = self.renamer.validate_operations(proposals)

        # Should be no operations since paths are the same
        assert len(operations) == 0
        assert len(conflicts) == 0

    def test_validate_operations_directory_creation(self):
        """Test validation with directory creation needed."""
        subdir = self.temp_dir / "subdir" / "subsubdir"
        dest_file = subdir / "test.jpg"

        proposals = [
            RenameProposalItem(
                original=str(self.test_file1), proposed=str(dest_file), note=""
            )
        ]

        operations, conflicts = self.renamer.validate_operations(proposals)

        assert len(operations) == 1
        assert len(conflicts) == 0
        assert subdir.exists()  # Directory should be created

    def test_update_media_tags_success(self):
        """Test successful media tag update."""
        old_path = str(self.test_file1)
        new_path = str(self.dest_file1)

        result = self.renamer.update_media_tags(old_path, new_path)

        assert result is True
        assert self.renamer.media_tags[0].filename == new_path

    def test_update_media_tags_not_found(self):
        """Test media tag update for non-existent file."""
        result = self.renamer.update_media_tags("nonexistent.jpg", "new.jpg")

        assert result is False
        # Original tags should be unchanged
        assert self.renamer.media_tags[0].filename == str(self.test_file1)

    def test_save_media_tags(self):
        """Test saving media tags to JSON file."""
        output_file = self.temp_dir / "test_tags.json"

        self.renamer.save_media_tags(str(output_file))

        assert output_file.exists()
        # Check that file contains valid JSON
        import json

        with open(output_file) as f:
            data = json.load(f)
        assert len(data) == 2
        assert data[0]["filename"] == str(self.test_file1)

    def test_save_media_tags_empty(self):
        """Test saving empty media tags."""
        renamer = AtomicRenamer([])
        output_file = self.temp_dir / "empty_tags.json"

        renamer.save_media_tags(str(output_file))

        # File should not be created for empty tags
        assert not output_file.exists()

    def test_apply_renames_dry_run(self):
        """Test dry run mode."""
        proposals = [
            RenameProposalItem(
                original=str(self.test_file1), proposed=str(self.dest_file1), note=""
            )
        ]

        result = self.renamer.apply_renames(proposals, dry_run=True)

        assert result.success_count == 1
        assert len(result.failed_operations) == 0
        assert len(result.successful_operations) == 1
        assert len(result.conflicts) == 0

        # Original file should still exist
        assert self.test_file1.exists()
        assert not self.dest_file1.exists()

        # Tags should not be updated in dry run
        assert self.renamer.media_tags[0].filename == str(self.test_file1)

    def test_apply_renames_actual(self):
        """Test actual rename operations."""
        proposals = [
            RenameProposalItem(
                original=str(self.test_file1), proposed=str(self.dest_file1), note=""
            ),
            RenameProposalItem(
                original=str(self.test_file2), proposed=str(self.dest_file2), note=""
            ),
        ]

        result = self.renamer.apply_renames(proposals, dry_run=False)

        assert result.success_count == 2
        assert len(result.failed_operations) == 0
        assert len(result.successful_operations) == 2
        assert len(result.conflicts) == 0

        # Files should be moved
        assert not self.test_file1.exists()
        assert not self.test_file2.exists()
        assert self.dest_file1.exists()
        assert self.dest_file2.exists()

        # Tags should be updated
        assert self.renamer.media_tags[0].filename == str(self.dest_file1)
        assert self.renamer.media_tags[1].filename == str(self.dest_file2)

    def test_apply_renames_no_tag_update(self):
        """Test rename without tag updates."""
        proposals = [
            RenameProposalItem(
                original=str(self.test_file1), proposed=str(self.dest_file1), note=""
            )
        ]

        result = self.renamer.apply_renames(proposals, update_tags=False)

        assert result.success_count == 1
        assert self.dest_file1.exists()

        # Tags should not be updated
        assert self.renamer.media_tags[0].filename == str(self.test_file1)

    def test_apply_renames_with_conflicts(self):
        """Test rename operations with conflicts."""
        # Create destination file to cause conflict
        self.dest_file1.write_text("existing")

        proposals = [
            RenameProposalItem(
                original=str(self.test_file1), proposed=str(self.dest_file1), note=""
            ),
            RenameProposalItem(
                original=str(self.test_file2), proposed=str(self.dest_file2), note=""
            ),
        ]

        result = self.renamer.apply_renames(proposals)

        # Only one operation should succeed (test_file2 -> dest_file2)
        assert result.success_count == 1
        assert len(result.conflicts) == 1
        assert len(result.successful_operations) == 1

        # test_file2 should be renamed, test_file1 should remain
        assert self.test_file1.exists()
        assert not self.test_file2.exists()
        assert self.dest_file2.exists()

    def test_apply_renames_file_operation_error(self):
        """Test handling of file operation errors."""
        proposals = [
            RenameProposalItem(
                original=str(self.test_file1), proposed=str(self.dest_file1), note=""
            )
        ]

        # Mock shutil.move to raise an exception
        with patch("src.pic_organize.atomic_rename.shutil.move") as mock_move:
            mock_move.side_effect = PermissionError("Permission denied")

            result = self.renamer.apply_renames(proposals)

            assert result.success_count == 0
            assert len(result.failed_operations) == 1
            assert "Permission denied" in result.failed_operations[0][2]

    def test_apply_renames_no_operations(self):
        """Test apply_renames with no valid operations."""
        proposals = [
            RenameProposalItem(
                original=str(self.test_file1),
                proposed=str(self.test_file1),  # Same file
                note="",
            )
        ]

        result = self.renamer.apply_renames(proposals)

        assert result.success_count == 0
        assert len(result.failed_operations) == 0
        assert len(result.successful_operations) == 0
        assert len(result.conflicts) == 0


class TestRenameResult:
    """Test cases for RenameResult dataclass."""

    def test_rename_result_creation(self):
        """Test creation of RenameResult."""
        result = RenameResult(
            success_count=2,
            failed_operations=[(Path("a"), Path("b"), "error")],
            successful_operations=[(Path("c"), Path("d"))],
            conflicts=["conflict1"],
        )

        assert result.success_count == 2
        assert len(result.failed_operations) == 1
        assert len(result.successful_operations) == 1
        assert len(result.conflicts) == 1


if __name__ == "__main__":
    pytest.main([__file__])
