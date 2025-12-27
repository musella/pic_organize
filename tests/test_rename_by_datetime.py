from datetime import datetime
from pic_organize.rename_by_datetime import (
    extract_datetime_from_tags,
    infer_datetime_from_filename,
    propose_new_name,
    extract_burst_tags,
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
