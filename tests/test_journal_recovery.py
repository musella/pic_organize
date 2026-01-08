"""
Unit tests for journal recovery functionality in AtomicRenamer.
"""

import unittest
import json
from pathlib import Path
from unittest.mock import patch

from src.pic_organize.atomic_rename import AtomicRenamer
from src.pic_organize.tag_info import MediaTagInfo


class TestJournalRecovery(unittest.TestCase):
    """Test cases for journal recovery functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_media_tags = [
            MediaTagInfo(
                filename="test1.jpg", media_type="image", tags={"test": "value1"}
            ),
            MediaTagInfo(
                filename="test2.jpg", media_type="image", tags={"test": "value2"}
            ),
            MediaTagInfo(
                filename="test3.jpg", media_type="image", tags={"test": "value3"}
            ),
        ]

    def tearDown(self):
        """Clean up test artifacts."""
        # Clean up any journal files created during tests
        journal_path = Path("media_tags_journal.json")
        if journal_path.exists():
            journal_path.unlink()

        tags_path = Path("media_tags.json")
        if tags_path.exists():
            tags_path.unlink()

    def test_journal_entry_creation(self):
        """Test that journal entries are created correctly."""
        renamer = AtomicRenamer(self.test_media_tags.copy())

        # Write a journal entry
        renamer.write_journal_entry("tag_update", "test1.jpg", "renamed_test1.jpg")

        # Check that the journal entry was added to pending changes
        self.assertEqual(len(renamer.pending_changes), 1)

        entry = renamer.pending_changes[0]
        self.assertEqual(entry["operation"], "tag_update")
        self.assertEqual(entry["old_path"], "test1.jpg")
        self.assertEqual(entry["new_path"], "renamed_test1.jpg")
        self.assertIn("timestamp", entry)

        # Check that journal file was created
        journal_path = Path("media_tags_journal.json")
        self.assertTrue(journal_path.exists())

        # Verify journal file contents
        with open(journal_path, "r") as f:
            journal_data = json.load(f)

        self.assertEqual(len(journal_data), 1)
        self.assertEqual(journal_data[0]["operation"], "tag_update")

    def test_multiple_journal_entries(self):
        """Test that multiple journal entries are tracked correctly."""
        renamer = AtomicRenamer(self.test_media_tags.copy())

        # Write multiple journal entries
        renamer.write_journal_entry("tag_update", "test1.jpg", "renamed_test1.jpg")
        renamer.write_journal_entry("tag_update", "test2.jpg", "renamed_test2.jpg")
        renamer.write_journal_entry("tag_update", "test3.jpg", "renamed_test3.jpg")

        # Check that all entries were added
        self.assertEqual(len(renamer.pending_changes), 3)

        # Verify journal file contains all entries
        with open("media_tags_journal.json", "r") as f:
            journal_data = json.load(f)

        self.assertEqual(len(journal_data), 3)

        # Verify entries are in correct order
        expected_files = ["test1.jpg", "test2.jpg", "test3.jpg"]
        expected_renamed = [
            "renamed_test1.jpg",
            "renamed_test2.jpg",
            "renamed_test3.jpg",
        ]

        for i, entry in enumerate(journal_data):
            self.assertEqual(entry["old_path"], expected_files[i])
            self.assertEqual(entry["new_path"], expected_renamed[i])

    def test_journal_recovery_success(self):
        """Test successful recovery from journal file."""
        # Create a journal file manually
        journal_entries = [
            {
                "timestamp": 1234567890.0,
                "operation": "tag_update",
                "old_path": "test1.jpg",
                "new_path": "renamed_test1.jpg",
            },
            {
                "timestamp": 1234567891.0,
                "operation": "tag_update",
                "old_path": "test2.jpg",
                "new_path": "renamed_test2.jpg",
            },
        ]

        with open("media_tags_journal.json", "w") as f:
            json.dump(journal_entries, f)

        # Create renamer with original tags
        renamer = AtomicRenamer(self.test_media_tags.copy())

        # Mock the save_media_tags method to avoid creating actual files
        with patch.object(renamer, "save_media_tags") as mock_save:
            # Perform recovery
            recovered = renamer.recover_from_journal()

        # Verify recovery was successful
        self.assertTrue(recovered)
        mock_save.assert_called_once()

        # Verify that tags were updated
        self.assertEqual(renamer.media_tags[0].filename, "renamed_test1.jpg")
        self.assertEqual(renamer.media_tags[1].filename, "renamed_test2.jpg")
        self.assertEqual(renamer.media_tags[0].tags["renamed_from"], "test1.jpg")
        self.assertEqual(renamer.media_tags[1].tags["renamed_from"], "test2.jpg")

        # Verify journal file was cleaned up
        self.assertFalse(Path("media_tags_journal.json").exists())

    def test_journal_recovery_no_journal(self):
        """Test recovery when no journal file exists."""
        renamer = AtomicRenamer(self.test_media_tags.copy())

        # Ensure no journal file exists
        journal_path = Path("media_tags_journal.json")
        if journal_path.exists():
            journal_path.unlink()

        # Attempt recovery
        recovered = renamer.recover_from_journal()

        # Should return False since no journal exists
        self.assertFalse(recovered)

    def test_journal_recovery_empty_journal(self):
        """Test recovery with empty journal file."""
        # Create empty journal file
        with open("media_tags_journal.json", "w") as f:
            json.dump([], f)

        renamer = AtomicRenamer(self.test_media_tags.copy())

        # Attempt recovery
        recovered = renamer.recover_from_journal()

        # Should return False and clean up empty journal
        self.assertFalse(recovered)
        self.assertFalse(Path("media_tags_journal.json").exists())

    def test_journal_clear(self):
        """Test journal clearing functionality."""
        renamer = AtomicRenamer(self.test_media_tags.copy())

        # Add some journal entries
        renamer.write_journal_entry("tag_update", "test1.jpg", "renamed_test1.jpg")

        # Verify journal file exists
        self.assertTrue(Path("media_tags_journal.json").exists())
        self.assertEqual(len(renamer.pending_changes), 1)

        # Clear journal
        renamer.clear_journal()

        # Verify journal was cleared
        self.assertFalse(Path("media_tags_journal.json").exists())
        self.assertEqual(len(renamer.pending_changes), 0)

    def test_journal_error_handling(self):
        """Test journal error handling when file operations fail."""
        renamer = AtomicRenamer(self.test_media_tags.copy())

        # Mock open to raise an exception
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            # Should not raise exception, just print warning
            renamer.write_journal_entry("tag_update", "test1.jpg", "renamed_test1.jpg")

        # Pending changes should still be tracked in memory
        self.assertEqual(len(renamer.pending_changes), 1)

    def test_save_clears_journal(self):
        """Test that saving media tags clears the journal."""
        renamer = AtomicRenamer(self.test_media_tags.copy())

        # Add some journal entries
        renamer.write_journal_entry("tag_update", "test1.jpg", "renamed_test1.jpg")

        # Verify journal exists
        self.assertTrue(Path("media_tags_journal.json").exists())

        # Save media tags
        renamer.save_media_tags()

        # Verify journal was cleared
        self.assertFalse(Path("media_tags_journal.json").exists())
        self.assertEqual(len(renamer.pending_changes), 0)


if __name__ == "__main__":
    unittest.main()
