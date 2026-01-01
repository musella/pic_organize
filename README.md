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

# Pic Organize - Streamlit Interface

A Streamlit web application for reviewing and applying media file rename changes based on extracted metadata tags.

## Features

The application provides a complete workflow for organizing media files:

1. **Extract Tags** - Scan directory and extract EXIF/metadata tags from images and videos
2. **Generate Proposals** - Create rename proposals based on datetime information from tags or filenames
3. **Review Proposals** - Interactive interface to review, search, and select/deselect rename operations
4. **Apply Changes** - Atomically apply selected rename operations to the file system

## Installation

1. Install dependencies:
   ```bash
   poetry install
   ```

2. Run the application:
   ```bash
   poetry run streamlit run streamlit_app.py
   ```

3. Open your browser to the displayed URL (typically `http://localhost:8501`)

## Usage

### Step 1: Configure Directory
- In the sidebar, enter the path to your media directory
- The default is the current directory (`.`)
- The application will show an error if the directory doesn't exist

### Project State Management
- **Save State**: Saves all current data (media tags, rename proposals, selected items) to JSON files
- **Load State**: Loads complete project state from JSON files
- **Load Tags**: Load only media_tags.json
- **Load Proposals**: Load only rename_proposal.json and manual_review.json

### Step 2: Extract Tags
- Click "1. Extract Tags" to scan the directory for media files
- The application will extract EXIF data from images and metadata from videos
- Progress and results are shown in the sidebar status section

### Step 3: Generate Proposals
- Click "2. Generate Proposals" to create rename suggestions
- The application will attempt to extract datetime information from:
  - EXIF DateTimeOriginal for images
  - Creation date metadata for videos  
  - Filename patterns (e.g., IMG_20231225_140530.jpg)
- Files without datetime information are flagged for manual review

### Step 4: Review Proposals
- All proposals are selected by default
- Use the search box to filter proposals
- Use "Select All", "Deselect All", or "Invert Selection" buttons for bulk operations
- Click individual checkboxes to select/deselect specific proposals
- Expand each proposal to see full paths and details

### Step 5: Apply Changes
- Click "⚠️ Confirm and Apply Changes" to execute selected renames
- All operations are performed atomically
- Success/failure feedback is provided for each operation
- The application will re-extract tags after successful operations

## File Naming Convention

The application renames files to the format: `IMG_YYYYMMDD_HHMMSS[_BURST...].[ext]`

Examples:
- `IMG_20231225_140530.jpg`
- `IMG_20231225_140530_BURST01.jpg`
- `IMG_20231225_140530_02_COVER.jpg`

## Error Handling

- **File not found**: Source file doesn't exist
- **Destination exists**: Target filename already exists
- **Permission errors**: Insufficient permissions to rename files
- **Directory creation**: Destination directories are created automatically

## Safety Features

- **No direct file operations**: All operations go through the code's data models
- **Atomic operations**: All renames in a batch are validated before any are applied
- **Conflict detection**: Checks for existing destination files
- **Progress tracking**: Clear feedback on operation success/failure
- **Manual review**: Files without datetime are flagged for human review

## Manual Review Files

Files that couldn't be automatically renamed are listed separately:
- No datetime information found in EXIF/metadata
- No recognizable datetime pattern in filename
- These files require manual intervention or different organization strategy

## Saved Files

The application saves/loads the following JSON files:

- **media_tags.json**: Extracted EXIF/metadata from all media files
- **rename_proposal.json**: Generated rename proposals with original → proposed mappings
- **manual_review.json**: List of files that couldn't be automatically renamed
- **project_state.json**: Application configuration (directory path, selected proposals)

These files allow you to:
- Resume work on a project later
- Share proposals with others for review
- Keep backups of analysis results
- Work with pre-generated data from CLI tools

## Technical Details

- Built with Streamlit for the web interface
- Uses the existing `pic_organize` codebase for core functionality
- Session state management for workflow persistence
- Pandas DataFrames for proposal display and filtering
- Path validation and error handling throughout the process
- JSON serialization using Pydantic models for type safety
