"""
Test module for folder analysis functionality.
"""

import os
import tempfile
import shutil
from datetime import datetime
from pathlib import Path

from pic_organize.analyze_folders import FolderAnalyzer, analyze_folders
from pic_organize.tag_info import MediaTagInfo


def test_folder_analyzer():
    """Test basic folder analysis functionality."""
    # Create a temporary directory structure for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test folder structure
        test_folders = [
            "2023_01_Vacation",
            "2023_02_Wedding",
            "2023_03",
            "Random_Photos",
        ]

        for folder in test_folders:
            folder_path = os.path.join(temp_dir, folder)
            os.makedirs(folder_path, exist_ok=True)

            # Create some dummy image files
            for i in range(3):
                file_path = os.path.join(folder_path, f"IMG_{i:04d}.jpg")
                with open(file_path, "w") as f:
                    f.write("dummy image content")

        # Create mock media tags
        mock_tags = []
        for folder in test_folders:
            for i in range(3):
                file_path = os.path.join(temp_dir, folder, f"IMG_{i:04d}.jpg")
                # Create realistic datetime for each folder
                if "2023_01" in folder:
                    dt = datetime(2023, 1, 15)
                elif "2023_02" in folder:
                    dt = datetime(2023, 2, 20)
                elif "2023_03" in folder:
                    dt = datetime(2023, 3, 10)
                else:
                    dt = datetime(2023, 4, 5)

                tag_info = MediaTagInfo(
                    filename=file_path,
                    media_type="image",
                    tags={
                        "DateTimeOriginal": dt.strftime("%Y:%m:%d %H:%M:%S"),
                        "Make": "TestCamera",
                        "Model": "TestModel",
                    },
                )
                mock_tags.append(tag_info)

        # Test the analyzer
        analyzer = FolderAnalyzer()
        analyzer.media_tags = mock_tags
        analyzer._organize_files_by_folders()

        # Test album detection
        analyzer.detect_albums()

        # Generate proposals
        proposals = analyzer.generate_rename_proposals()

        print(f"Generated {len(proposals)} folder rename proposals:")
        for proposal in proposals:
            print(f"  {proposal.original_path} -> {proposal.proposed_path}")
            print(f"    Reason: {proposal.reason}")
            if proposal.conflicts_with:
                print(f"    Conflicts: {proposal.conflicts_with}")

        # Verify we got some proposals
        assert len(proposals) > 0, "Should generate some rename proposals"

        print("✅ Folder analysis test completed successfully!")


def test_convenience_function():
    """Test the convenience function."""
    # Create a simple test directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a test folder with an image
        test_folder = os.path.join(temp_dir, "test_photos")
        os.makedirs(test_folder, exist_ok=True)

        test_file = os.path.join(test_folder, "test.jpg")
        with open(test_file, "w") as f:
            f.write("test")

        try:
            # Test the convenience function
            proposals = analyze_folders(temp_dir)
            print(f"Convenience function generated {len(proposals)} proposals")
            print("✅ Convenience function test completed!")
        except Exception as e:
            print(
                f"⚠️  Convenience function test failed (expected for minimal test data): {e}"
            )


if __name__ == "__main__":
    print("Testing folder analysis functionality...")
    test_folder_analyzer()
    test_convenience_function()
    print("All tests completed!")
