from datetime import datetime
from pic_organize.rename_by_datetime import (
    extract_datetime_from_tags,
    infer_datetime_from_filename,
    propose_new_name,
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
    name = propose_new_name(dt, ext)
    assert name == "IMG_20230315_080706.jpg"
