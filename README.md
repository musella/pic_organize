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
- Infers date/time from filenames using advanced pattern recognition.
- Generates a proposal (`rename_proposal.json`) mapping original to proposed names.
- Files needing manual review are listed in `manual_review.json`.
- No files are actually renamed until reviewed and approved.
- **Folder exclusion system** to skip problematic directories.

### Advanced Datetime Pattern Recognition

The system now supports **9 different datetime extraction patterns** to maximize automatic file processing:

1. **Standard formats**: `IMG_YYYYMMDD_HHMMSS.jpg`, `YYYY-MM-DD_HH-MM-SS.mov`
2. **Screenshot patterns**: `Screenshot from YYYY-MM-DD HH-MM-SS.png`
3. **Directory-based dates**: 
   - `/YYYY-MM-DD_HH_MM_SS/filename.jpg` (full datetime from path)
   - `/YYYY-MM-location/filename.jpg` (year-month from path)
   - `/YYYY_MM_DD/filename.jpg` (underscore format)
4. **Camera patterns**: `P8051152.JPG` (month+day encoded, P8=August, 05=day)
5. **IMG context**: `IMG_1464.MOV` (uses directory date context)
6. **Date dots**: `05.03.17.JPG` (DD.MM.YY format)
7. **Date with spaces**: `2012-01-10 15.38.59.jpg` (YYYY-MM-DD HH.MM.SS)
8. **Month abbreviations**: `IMG 0199 apr 17.JPG` (month text with year)

**Coverage Improvement**: From ~20% to 66.9% automatic processing (excludes problematic folders)

### Folder Exclusion System

Certain folders can be excluded from automatic datetime extraction to avoid processing:
- **Wedding/Event photos**: `/2011-04-23-Matrimonio/`
- **Personal collections**: `/Da_Titti/`  
- **Medical scans**: `/echographie_*/` (any echography folder)

Files in excluded folders are automatically sent to manual review for appropriate handling.

**Configuration**: Edit `EXCLUDE_FOLDER_PATTERNS` in `src/pic_organize/rename_by_datetime.py`

### Pattern Priority and Validation

Patterns are applied in priority order for optimal results:
1. Original standard formats (highest precision)
2. Screenshot patterns (exact timestamps)
3. Directory-based patterns (contextual dating)
4. Camera-specific patterns (brand/model specific)
5. Fallback patterns (dots, text months)

**Validation Tools**:
- Run `poetry run python tests/validate_pattern_improvements.py` for coverage analysis
- Exports detailed CSV results for manual review
- Pattern breakdown statistics
- Before/after comparison metrics

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

## Performance and Crash Recovery

### Batched Saving
The application now uses **batched saving** for improved performance during large rename operations:

- **Saves media tags every 100 entries** instead of after each individual rename
- **Configurable batch size** (default: 100) via `save_batch_size` property
- **100x fewer disk writes** for large operations, significantly improving performance
- **Final save guarantee** ensures no data loss for remaining unsaved changes

### Journal-Based Crash Recovery
The application includes robust crash recovery to protect against data loss:

- **Automatic journaling**: All tag updates are logged to `media_tags_journal.json`
- **Crash recovery**: On startup, the application automatically detects and recovers unsaved changes
- **Safe operation**: Journal writing errors don't break the main rename process
- **Automatic cleanup**: Journal files are automatically removed after successful saves
- **User notification**: Recovery operations are clearly communicated to users

#### Journal File Format
```json
[
  {
    "timestamp": 1234567890.0,
    "operation": "tag_update", 
    "old_path": "original_file.jpg",
    "new_path": "renamed_file.jpg"
  }
]
```

### Progress Reporting
Enhanced progress feedback for better user experience:

- **Real-time progress bar** showing completion percentage
- **File-by-file updates** displaying current file being processed
- **Batch save notifications** showing unsaved changes count
- **Works for both dry runs and actual operations**
- **Completion confirmation** before clearing progress indicators

These features ensure that large media organization tasks are both efficient and safe, with protection against interruptions and clear feedback on progress.

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
