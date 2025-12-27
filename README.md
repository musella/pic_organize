# pic_organize

A basic Python project structure managed with Poetry.

## Getting Started

### Install Poetry
If you don't have Poetry installed, follow the [official instructions](https://python-poetry.org/docs/#installation) or run:

```bash
pipx install poetry
```

### Install dependencies
```bash
poetry install
```

### Run the project
```bash
poetry run python src/main.py
```

## Project Structure

- `src/` - Source code
- `tests/` - Test files
- `pyproject.toml` - Poetry configuration

## Media Tag Extraction

This project includes a script to extract tag information from images and videos, summarize tag statistics, and save results to JSON.

### Usage

1. **Install dependencies** (if not already done):
    ```bash
    poetry install
    ```

2. **Run the extraction script** (default main):
    ```bash
    poetry run python src/extract_tags.py
    ```
    This will scan the current directory for media files, extract tags, and save results to `media_tags.json` and `tag_summary.json`.

3. **Output files**:
    - `media_tags.json`: List of extracted tags for each media file.
    - `tag_summary.json`: Summary statistics of tag types and values.

### Supported Formats

- **Images**: jpg, jpeg, png, tiff
- **Videos**: mp4, mov, avi, mkv

### How it works

- Scans the current directory and subdirectories for supported media files.
- Extracts EXIF tags from images and metadata from videos.
- Stores results using a Pydantic model.
- Outputs summary statistics of tag types and values.

### Example

```python
from src.extract_tags import scan_media, summarize_tags

media_tags = scan_media("/path/to/media")
stats = summarize_tags(media_tags)
```

## Renaming Files by Date and Time

The script `src/pic_organize/rename_by_datetime.py` scans a directory for image and video files, extracts or infers their date and time, and generates a proposal to rename them in the format `IMG_YYYYMMDD_HHMMSS.ext`. Files without a determinable date/time are flagged for manual review.

### Burst/Cover Tag Preservation

If the original filename contains a burst or cover tag, the tag(s) are preserved in the proposed new filename. This helps keep burst photo sequences identifiable after renaming.

**Recognized patterns:**
- `BURST\d{0,3}(?:_COVER)?` (e.g., `BURST`, `BURST001`, `BURST_COVER`, `BURST001_COVER`)
- `\d{3}_COVER` (e.g., `001_COVER`)

**Behavior:**
- All burst/cover tags found in the original filename are appended (in order of appearance) before the file extension in the new name.
- If both types are present, both are preserved in order.
- Non-burst files are not affected.

**Example:**
| Original Filename                         | Proposed Filename                       |
|-------------------------------------------|-----------------------------------------|
| IMG_20211231_235959_BURST.jpg             | IMG_20211231_235959_BURST.jpg           |
| IMG_20211231_235959_BURST001_COVER.jpg    | IMG_20211231_235959_BURST001_COVER.jpg  |
| IMG_20211231_235959_002_COVER.jpg         | IMG_20211231_235959_002_COVER.jpg       |
| IMG_BURST2_003_COVER_BURST_COVER.jpg      | IMG_YYYYMMDD_HHMMSS_BURST2_003_COVER_BURST_COVER.jpg |

**Features:**
- Extracts date/time from EXIF or video metadata.
- Infers date/time from filenames if metadata is missing.
- Generates a proposal (`rename_proposal.json`) mapping original to proposed names.
- Files needing manual review are listed in `manual_review.json`.
- No files are actually renamed until reviewed and approved.

**Usage:**
```bash
python src/pic_organize/rename_by_datetime.py [directory]
```
If no directory is specified, the current directory is used.

**Outputs:**
- `rename_proposal.json`: List of proposed renaming actions.
- `manual_review.json`: List of files requiring manual review.
