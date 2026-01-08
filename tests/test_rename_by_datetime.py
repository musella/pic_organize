from datetime import datetime
import os
from pic_organize.rename_by_datetime import (
    extract_datetime_from_tags,
    infer_datetime_from_filename,
    propose_new_name,
    extract_burst_tags,
    generate_rename_proposal,
)


def test_extract_datetime_from_tags_image():
    tags = {"DateTimeOriginal": "2021:12:31 23:59:59"}
    dt = extract_datetime_from_tags(tags, "image")
    assert dt == datetime(2021, 12, 31, 23, 59, 59)


def test_extract_datetime_from_tags_video():
    tags = {"Creation date": "2022-01-01 12:00:01"}
    dt = extract_datetime_from_tags(tags, "video")
    assert dt == datetime(2022, 1, 1, 12, 0, 1)


def test_extract_datetime_from_tags_missing():
    tags = {}
    dt = extract_datetime_from_tags(tags, "image")
    assert dt is None


def test_infer_datetime_from_filename_standard():
    fname = "IMG_20211231_235959.jpg"
    dt = infer_datetime_from_filename(fname)
    assert dt == datetime(2021, 12, 31, 23, 59, 59)


def test_infer_datetime_from_filename_dash_format():
    fname = "2022-01-01_120001.mov"
    dt = infer_datetime_from_filename(fname)
    assert dt == datetime(2022, 1, 1, 12, 0, 1)


def test_infer_datetime_from_filename_no_match():
    fname = "randomfile.txt"
    dt = infer_datetime_from_filename(fname)
    assert dt is None


def test_propose_new_name():
    dt = datetime(2023, 3, 15, 8, 7, 6)
    ext = ".jpg"
    # No burst tag
    name = propose_new_name(dt, ext)
    assert name == "IMG_20230315_080706.jpg"
    # With burst tag
    name2 = propose_new_name(dt, ext, "_BURST001")
    assert name2 == "IMG_20230315_080706_BURST001.jpg"
    # With multiple tags
    name3 = propose_new_name(dt, ext, "_BURST001_COVER_002_COVER")
    assert name3 == "IMG_20230315_080706_BURST001_COVER_002_COVER.jpg"


def test_duplicate_postfix_proposal():
    # Use generate_rename_proposal to test duplicate handling
    from pic_organize.tag_info import MediaTagInfo

    dt = datetime(2023, 1, 2, 3, 4, 5)
    filenames = [
        "a1.jpg",
        "a2.jpg",
        "a3.jpg",
    ]
    media_tags = [
        MediaTagInfo(
            filename=f,
            tags={"DateTimeOriginal": dt.strftime("%Y:%m:%d %H:%M:%S")},
            media_type="image",
        )
        for f in filenames
    ]
    proposal, _ = generate_rename_proposal(media_tags)
    proposed_names = [os.path.basename(item.proposed) for item in proposal]
    assert proposed_names[0] == "IMG_20230102_030405.jpg"
    assert proposed_names[1] == "IMG_20230102_030405_02.jpg"
    assert proposed_names[2] == "IMG_20230102_030405_03.jpg"


def test_duplicate_postfix_different_folders():
    # Simulate two files in different folders that would get the same new name
    from pic_organize.tag_info import MediaTagInfo

    dt = datetime(2024, 4, 5, 6, 7, 8)
    files = [
        "folder1/original1.png",
        "folder2/original2.png",
    ]
    media_tags = [
        MediaTagInfo(
            filename=f,
            tags={"DateTimeOriginal": dt.strftime("%Y:%m:%d %H:%M:%S")},
            media_type="image",
        )
        for f in files
    ]
    proposal, _ = generate_rename_proposal(media_tags)
    proposed_names = [item.proposed for item in proposal]
    assert proposed_names[0] == os.path.join("folder1", "IMG_20240405_060708.png")
    assert proposed_names[1] == os.path.join("folder2", "IMG_20240405_060708_02.png")


def test_extract_burst_tags():
    # Single burst (should pad to BURST00)
    assert extract_burst_tags("IMG_20211231_235959_BURST.jpg") == "_BURST00"
    # Burst with number (pad to 2 digits)
    assert extract_burst_tags("IMG_20211231_235959_BURST1.jpg") == "_BURST01"
    assert extract_burst_tags("IMG_20211231_235959_BURST01.jpg") == "_BURST01"
    assert extract_burst_tags("IMG_20211231_235959_BURST9.jpg") == "_BURST09"
    assert extract_burst_tags("IMG_20211231_235959_BURST10.jpg") == "_BURST10"
    # Burst with cover (no number, pad to BURST00_COVER)
    assert extract_burst_tags("IMG_20211231_235959_BURST_COVER.jpg") == "_BURST00_COVER"
    # Burst with number and cover
    assert (
        extract_burst_tags("IMG_20211231_235959_BURST1_COVER.jpg") == "_BURST01_COVER"
    )
    assert (
        extract_burst_tags("IMG_20211231_235959_BURST09_COVER.jpg") == "_BURST09_COVER"
    )
    # Only cover pattern (pad to 2 digits)
    assert extract_burst_tags("IMG_20211231_235959_2_COVER.jpg") == "_02_COVER"
    assert extract_burst_tags("IMG_20211231_235959_12_COVER.jpg") == "_12_COVER"
    # Both burst and cover
    assert (
        extract_burst_tags("IMG_20211231_235959_BURST2_3_COVER.jpg")
        == "_BURST02_03_COVER"
    )
    # Multiple tags, order preserved
    assert (
        extract_burst_tags("IMG_BURST2_3_COVER_BURST_COVER.jpg")
        == "_BURST02_03_COVER_BURST00_COVER"
    )
    # No tag
    assert extract_burst_tags("IMG_20211231_235959.jpg") == ""


def test_screenshot_pattern():
    """Test screenshot datetime extraction."""
    filename = "Screenshot from 2021-01-21 21-52-18.png"
    result = infer_datetime_from_filename(filename)
    expected = datetime(2021, 1, 21, 21, 52, 18)
    assert result == expected


def test_directory_full_date_pattern():
    """Test directory-based full date extraction."""
    filepath = "/media/Pictures/2008-04-04_05_06/P4051152.JPG"
    result = infer_datetime_from_filename(filepath)
    expected = datetime(2008, 4, 4, 5, 6, 0)
    assert result == expected


def test_directory_year_month_pattern():
    """Test directory-based year-month extraction."""
    filepath = "/media/Pictures/2007-01-Parigi/IMG_1234.JPG"
    result = infer_datetime_from_filename(filepath)
    expected = datetime(2007, 1, 1, 12, 0, 0)
    assert result == expected


def test_directory_yyyy_mm_dd_pattern():
    """Test YYYY_MM_DD directory format extraction."""
    filepath = "/media/Pictures/2022_02_03/IMG_6191.JPG"
    result = infer_datetime_from_filename(filepath)
    expected = datetime(2022, 2, 3, 12, 0, 0)  # Day extracted from directory pattern
    assert result == expected


def test_camera_p_pattern():
    """Test camera P-pattern extraction."""
    filename = "P8051152.JPG"
    result = infer_datetime_from_filename(filename)
    expected = datetime(2012, 8, 5, 12, 0, 0)  # Month 8, day 5
    assert result == expected

    # Test different month codes
    assert infer_datetime_from_filename("P1151152.JPG") == datetime(
        2012, 1, 15, 12, 0, 0
    )
    assert infer_datetime_from_filename("PA051152.JPG") == datetime(
        2012, 10, 5, 12, 0, 0
    )
    assert infer_datetime_from_filename("PB251152.JPG") == datetime(
        2012, 11, 25, 12, 0, 0
    )
    assert infer_datetime_from_filename("PC311152.JPG") == datetime(
        2012, 12, 31, 12, 0, 0
    )


def test_img_context_pattern():
    """Test IMG context-based extraction."""
    filepath = "/media/Pictures/2023_01_06/IMG_1464.MOV"
    result = infer_datetime_from_filename(filepath)
    expected = datetime(
        2023, 1, 6, 12, 0, 0
    )  # Year 2023, month 1, day 6 (from directory)
    assert result == expected

    # Test with different year/month combinations
    filepath2 = "/media/Pictures/2020_05_vacation/IMG_9876.MOV"
    result2 = infer_datetime_from_filename(filepath2)
    expected2 = datetime(2020, 5, 1, 12, 0, 0)
    assert result2 == expected2


def test_date_dots_pattern():
    """Test DD.MM.YY format extraction."""
    filename = "05.03.17.JPG"
    result = infer_datetime_from_filename(filename)
    expected = datetime(2017, 3, 5, 12, 0, 0)
    assert result == expected

    # Test 19xx year
    filename2 = "25.12.95.JPG"
    result2 = infer_datetime_from_filename(filename2)
    expected2 = datetime(1995, 12, 25, 12, 0, 0)
    assert result2 == expected2


def test_month_year_text_pattern():
    """Test month abbreviation extraction."""
    filename = "IMG 0199 apr 17.JPG"
    result = infer_datetime_from_filename(filename)
    expected = datetime(2017, 4, 15, 12, 0, 0)
    assert result == expected

    # Test different months
    assert infer_datetime_from_filename("photo jan 20.jpg") == datetime(
        2020, 1, 15, 12, 0, 0
    )
    assert infer_datetime_from_filename("test DEC 19.png") == datetime(
        2019, 12, 15, 12, 0, 0
    )


def test_pattern_priority():
    """Test that patterns are applied in correct priority order."""
    # Original patterns should still work
    filename1 = "IMG_20211231_235959.jpg"
    result1 = infer_datetime_from_filename(filename1)
    assert result1 == datetime(2021, 12, 31, 23, 59, 59)

    # Screenshot pattern should work
    filename2 = "Screenshot from 2021-01-21 21-52-18.png"
    result2 = infer_datetime_from_filename(filename2)
    assert result2 == datetime(2021, 1, 21, 21, 52, 18)


def test_date_time_with_dots_pattern():
    """Test YYYY-MM-DD HH.MM.SS format extraction."""
    filename = "2012-01-10 15.38.59.jpg"
    result = infer_datetime_from_filename(filename)
    expected = datetime(2012, 1, 10, 15, 38, 59)
    assert result == expected


def test_folder_exclusion():
    """Test that files in excluded folders return None."""
    # Test excluded folders
    assert (
        infer_datetime_from_filename("/Pictures/2011-04-23-Matrimonio/IMG_1234.JPG")
        is None
    )
    assert infer_datetime_from_filename("/Pictures/Da_Titti/P8051152.JPG") is None
    assert infer_datetime_from_filename("/Pictures/echographie_baby/scan.jpg") is None
    assert (
        infer_datetime_from_filename("/Pictures/echographie_2023/ultrasound.jpg")
        is None
    )

    # Test that normal files still work
    assert infer_datetime_from_filename(
        "/Pictures/normal/IMG_20211231_235959.jpg"
    ) == datetime(2021, 12, 31, 23, 59, 59)


def test_no_match_edge_cases():
    """Test edge cases that should not match."""
    # Invalid P pattern
    assert infer_datetime_from_filename("PX051152.JPG") is None

    # Invalid date
    assert infer_datetime_from_filename("32.13.99.JPG") is None

    # Invalid month abbreviation
    assert infer_datetime_from_filename("xyz 17.jpg") is None

    # Random file
    assert infer_datetime_from_filename("randomfile.txt") is None
