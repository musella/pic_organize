#!/usr/bin/env python3
"""
Test script to verify the fixes for folder analysis issues.
"""

import os
from pic_organize.analyze_folders import FolderAnalyzer
from pic_organize.tag_info import MediaTagInfo


def test_hidden_and_trash_folders_ignored():
    """Test that hidden folders (starting with .) and Trash folder are ignored."""
    print("Testing hidden and Trash folder handling...")

    analyzer = FolderAnalyzer()

    # Create mock media tags with hidden folder
    analyzer.media_tags = [
        MediaTagInfo(
            filename="/test/.hidden_folder/image1.jpg",
            media_type="image",
            tags={"DateTime": "2023:05:15 10:30:00"},
        ),
        MediaTagInfo(
            filename="/test/visible_folder/image2.jpg",
            media_type="image",
            tags={"DateTime": "2023:05:15 10:30:00"},
        ),
        MediaTagInfo(
            filename="/test/Trash/image3.jpg",
            media_type="image",
            tags={"DateTime": "2023:05:15 10:30:00"},
        ),
    ]

    analyzer._organize_files_by_folders()

    # Should only have visible folder
    folder_paths = list(analyzer.folder_infos.keys())
    print(f"Found folders: {folder_paths}")

    assert len(folder_paths) == 1
    assert "/test/visible_folder" in folder_paths
    assert "/test/.hidden_folder" not in folder_paths
    assert "/test/Trash" not in folder_paths
    print("✓ Hidden and Trash folders are ignored")


def test_album_name_cleaning_and_year_range():
    """Test that album names are cleaned and full year ranges are preserved."""
    print("\nTesting album name cleaning and year range preservation...")

    analyzer = FolderAnalyzer()

    # Create mock media tags for multi-year album
    analyzer.media_tags = [
        MediaTagInfo(
            filename="/test/pre_2013/image1.jpg",
            media_type="image",
            tags={"DateTime": "2011:10:29 10:30:00"},
        ),
        MediaTagInfo(
            filename="/test/pre_2013/image2.jpg",
            media_type="image",
            tags={"DateTime": "2013:06:23 14:20:00"},
        ),
    ]

    analyzer._organize_files_by_folders()
    analyzer.detect_albums()

    # Get the folder info
    folder_info = analyzer.folder_infos["/test/pre_2013"]
    folder_info.is_album = True
    folder_info.album_name = "16_30_Pre_2013"

    # Generate folder name
    new_name, reason = analyzer.generate_folder_name(folder_info)
    print(f"Generated name: {new_name}")
    print(f"Reason: {reason}")

    # Should clean numbers and preserve the full time range
    assert "2011_10" in new_name
    assert "2013_06" in new_name
    assert "Pre_2013" in new_name
    assert "16_30" not in new_name
    assert "Pre_2013" in new_name
    print("✓ Album name cleaned, preserved, and not truncated")


def test_same_month_merging_with_full_path():
    """Test that folders for the same month are suggested for merging, considering full path."""
    print("\nTesting same-month folder merging with full path...")

    analyzer = FolderAnalyzer()

    # Create mock media tags for two folders with same month
    analyzer.media_tags = [
        MediaTagInfo(
            filename="/test/folder1/image1.jpg",
            media_type="image",
            tags={"DateTime": "2023:05:15 10:30:00"},
        ),
        MediaTagInfo(
            filename="/test/folder2/image2.jpg",
            media_type="image",
            tags={"DateTime": "2023:05:20 14:20:00"},
        ),
        MediaTagInfo(
            filename="/test/other_folder/folder1/image3.jpg",
            media_type="image",
            tags={"DateTime": "2023:05:15 10:30:00"},
        ),
    ]

    analyzer._organize_files_by_folders()
    proposals = analyzer.generate_rename_proposals()

    # Should have proposals that merge into same name
    print(f"Number of proposals: {len(proposals)}")
    for proposal in proposals:
        print(
            f"  {os.path.basename(proposal.original_path)} -> {os.path.basename(proposal.proposed_path)}: {proposal.reason}"
        )

    # Only folders in the same path should merge
    proposed_paths = [p.proposed_path for p in proposals]
    assert "/test/2023_05" in proposed_paths
    assert "/test/other_folder/2023_05" in proposed_paths
    print("✓ Same-month folders are merged, considering full path")


def test_long_album_name():
    """Test that long album names are handled correctly."""
    print("\nTesting long album name handling...")

    analyzer = FolderAnalyzer()

    # Create mock media tags for a folder with a long album name
    analyzer.media_tags = [
        MediaTagInfo(
            filename="/test/long_album_name/image1.jpg",
            media_type="image",
            tags={"DateTime": "2023:01:15 10:30:00"},
        )
    ]

    analyzer._organize_files_by_folders()

    # Get the folder info
    folder_info = analyzer.folder_infos["/test/long_album_name"]
    folder_info.is_album = True
    folder_info.album_name = (
        "ThisIsAnExtremelyLongAlbumNameThatShouldBeHandledProperlyWithoutTruncation"
    )

    # Generate folder name
    new_name, reason = analyzer.generate_folder_name(folder_info)
    print(f"Generated name: {new_name}")
    print(f"Reason: {reason}")

    # Ensure the long album name is preserved
    assert (
        "ThisIsAnExtremelyLongAlbumNameThatShouldBeHandledProperlyWithoutTruncation"
        in new_name
    )
    print("✓ Long album name handled correctly")


if __name__ == "__main__":
    print("Running folder analysis fix tests...")

    test_hidden_and_trash_folders_ignored()
    test_album_name_cleaning_and_year_range()
    test_same_month_merging_with_full_path()

    print("\n🎉 All fixes validated successfully!")
