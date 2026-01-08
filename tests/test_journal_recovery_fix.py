#!/usr/bin/env python3
"""
Test script to verify the journal recovery bug fix.

This script simulates the bug scenario and verifies it's fixed.
"""

import json
import tempfile
import os
from pic_organize.atomic_rename import AtomicRenamer
from pic_organize.tag_info import MediaTagInfo


def test_journal_recovery_preserves_existing_tags():
    """Test that journal recovery doesn't overwrite existing tags file."""

    # Save original directory
    original_dir = os.getcwd()

    try:
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            print(f"Testing in directory: {temp_dir}")

            # 1. Create a sample existing tags file
            existing_tags = [
                MediaTagInfo(
                    filename="test1.jpg",
                    media_type="image",
                    tags={"DateTime": "2023:01:01 12:00:00", "Make": "Canon"},
                ),
                MediaTagInfo(
                    filename="test2.jpg",
                    media_type="image",
                    tags={"DateTime": "2023:01:02 12:00:00", "Make": "Nikon"},
                ),
            ]

            # Save existing tags to file
            with open("media_tags.json", "w") as f:
                json.dump([tag.model_dump() for tag in existing_tags], f, indent=2)

            print("✓ Created existing media_tags.json with 2 entries")

            # 2. Create a journal file to simulate an interrupted session
            journal_entries = [
                {
                    "timestamp": 1234567890.0,
                    "operation": "tag_update",
                    "old_path": "test1.jpg",
                    "new_path": "2023-01-01_120000_test1.jpg",
                }
            ]

            with open("media_tags_journal.json", "w") as f:
                json.dump(journal_entries, f, indent=2)

            print("✓ Created journal file with 1 entry")

            # 3. Test the old behavior (create AtomicRenamer with empty tags)
            # This should NOT overwrite the existing file anymore
            empty_renamer = AtomicRenamer()  # No media tags provided

            print("✓ Created AtomicRenamer with empty tags (simulating old bug)")

            # 4. Trigger recovery (this was causing the bug before)
            recovery_happened = empty_renamer.recover_from_journal()

            print(f"✓ Recovery performed: {recovery_happened}")

            # 5. Check that the existing tags file still exists and has content
            if os.path.exists("media_tags.json"):
                with open("media_tags.json", "r") as f:
                    saved_data = json.load(f)

                if len(saved_data) > 0:
                    print(
                        f"✅ SUCCESS: media_tags.json preserved with {len(saved_data)} entries"
                    )
                    print("   The bug has been fixed!")
                else:
                    print("❌ FAILURE: media_tags.json was overwritten with empty data")
                    print("   The bug still exists!")
                    return False
            else:
                print("❌ FAILURE: media_tags.json was deleted")
                print("   The bug still exists!")
                return False

            # 6. Test the new correct behavior
            print("\n--- Testing correct recovery behavior ---")

            # Load existing tags first
            with open("media_tags.json", "r") as f:
                data = json.load(f)
            loaded_tags = [MediaTagInfo(**item) for item in data]

            # Create journal again for another test
            with open("media_tags_journal.json", "w") as f:
                json.dump(journal_entries, f, indent=2)

            # Create renamer with existing tags (the correct way)
            correct_renamer = AtomicRenamer(loaded_tags)
            recovery_happened = correct_renamer.recover_from_journal()

            print(f"✓ Recovery with loaded tags performed: {recovery_happened}")

            # Verify the tags were updated correctly
            if os.path.exists("media_tags.json"):
                with open("media_tags.json", "r") as f:
                    final_data = json.load(f)

                # Should have the updated filename from journal
                updated_entry = None
                for entry in final_data:
                    if entry["filename"] == "2023-01-01_120000_test1.jpg":
                        updated_entry = entry
                        break

                if updated_entry:
                    print("✅ SUCCESS: Journal recovery correctly updated the tags")
                    print(f"   Updated entry: {updated_entry['filename']}")
                else:
                    print("❌ Journal recovery did not apply the changes correctly")
                    return False

            print("\n✅ All tests passed! The bug has been fixed.")
            return True

    finally:
        # Restore original directory
        os.chdir(original_dir)


if __name__ == "__main__":
    test_journal_recovery_preserves_existing_tags()
