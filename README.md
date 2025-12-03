# Educational Video Library Scanner

A Python tool to scan, organize, and catalog your personal collection of educational videos and courses for use with Jellyfin media server.

## Overview

This tool helps you organize scattered educational videos across multiple directories into a well-structured library that Jellyfin can recognize and display properly. It extracts metadata from multiple sources (NFO files, video file tags, filenames) and presents a comprehensive catalog of your courses and lessons.

### Quick Start

```bash
# 1. Clone and setup
git clone https://github.com/timseal/edu-library.git
cd edu-library

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies (including mediainfo system package)
pip install -r requirements.txt

# 4a. Run the GUI
python gui.py

# 4b. Or run the command-line scanner
python edu_scanner.py --library-root=/path/to/your/library
```

### Problem It Solves

- **Scattered content**: Educational videos stored in various directories
- **Forgotten content**: Can't remember what courses you have or where they are
- **Duplicate searches**: Finding content online you've already acquired
- **Missing metadata**: Videos lack proper titles, descriptions, and organization

### Solution

Scans your library directories, extracts metadata from:
- **NFO files** (tvshow.nfo for courses, episode.nfo for lessons)
- **Video file tags** (embedded metadata)
- **Filenames** (automatically extracts lesson titles)
- **Directory structure** (uses folder names as fallback)

Then displays everything organized by course with clear source attribution for each piece of metadata.

## Features

- **Recursive directory scanning** - Finds all courses and lessons in your library
- **Multi-source metadata extraction** - Prioritizes: NFO files → embedded tags → filenames → directory names
- **Flexible NFO naming** - Finds any `.nfo` file in course/lesson directories, not just specific names
- **Intelligent filename parsing** - Extracts lesson titles from common formats:
  - "Lesson 5 - Introduction to Python" → "Introduction to Python"
  - "05 - Title" → "Title"
  - "Title Only" → "Title Only"
- **Duration extraction** - Reads video duration from file metadata
- **Source attribution** - Shows where each piece of metadata came from (NFO, file-tags, filename, dir-name)
- **SQLite database storage** - Persists all metadata for querying and analysis
- **Completion tracking** - Reports which courses/lessons have complete metadata
- **Performance timing** - Shows how long each scan takes
- **Terminal output** - Clean, organized display grouped by course

## Requirements

- Python 3.7+
- `pymediainfo` - for extracting video file metadata
- `lxml` - for parsing NFO XML files
- `PySimpleGUI` - for the graphical user interface

### System Dependencies

#### macOS

```bash
# Install mediainfo (required for pymediainfo)
brew install mediainfo
```

#### Linux (Ubuntu/Debian)

```bash
# Install mediainfo
sudo apt-get install mediainfo

# Install Python development headers (may be needed)
sudo apt-get install python3-dev
```

#### Linux (Fedora/RHEL)

```bash
# Install mediainfo
sudo dnf install mediainfo
```

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/timseal/edu-library.git
cd edu-library
```

### 2. Create a Virtual Environment (Recommended)

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows (if you use it)
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Verify Installation

```bash
# Test command-line scanner
python edu_scanner.py --help

# Test GUI
python gui.py
```

## Dependencies Explained

| Package | Version | Purpose |
|---------|---------|---------|
| `pymediainfo` | ≥6.0.0 | Extracts metadata from video files (duration, codecs, etc.) |
| `lxml` | ≥4.9.0 | Parses NFO XML files for metadata |
| `PySimpleGUI` | ≥4.60.0 | Creates cross-platform graphical interface |

## Usage

### Command-Line Interface

The command-line scanner is ideal for automation, scripting, and server environments.

#### Basic Scan

```bash
python edu_scanner.py
```

This scans `/Volumes/learning` (the default library directory) and stores results in `library.db`.

#### Custom Library Path

```bash
python edu_scanner.py --library-root=/path/to/library
```

#### Using a Different Database

```bash
python edu_scanner.py --db=/path/to/custom.db
```

#### Clear Database Before Scanning

```bash
python edu_scanner.py --clear-db
```

#### Faster Scanning on Network Drives

If your library is on a network drive and scanning is slow, skip the MediaInfo extraction:

```bash
python edu_scanner.py --skip-media-info
```

This uses only NFO files and filename parsing for metadata, which is much faster on network drives. You'll still get titles and descriptions from NFO files, but duration data will only come from NFO files (not from video file inspection).

**Note:** Requires NFO files for best results. Without `--skip-media-info`, the scanner reads metadata directly from video files, which is slower on network drives but more comprehensive.

#### Get Help

```bash
python edu_scanner.py --help
```

### Graphical User Interface

The GUI provides an easy, visual way to interact with the scanner.

#### Launch the GUI

```bash
python gui.py
```

**GUI Features:**
1. **Browse Library Path** - Click "Browse" button to select your library directory
2. **Browse Database** - Choose where to save the database file
3. **Clear Database** - Checkbox to clear database before scanning
4. **Start Scan** - Begin scanning your library
5. **View Results** - Results appear in the text area
6. **Export Results** - Save results to a text file

### Output

The scanner displays:

1. Scan progress with timing information
2. All courses found with their metadata
3. All lessons in each course with titles, durations, and metadata sources
4. Summary statistics on metadata completeness
5. Database statistics (courses stored, lessons stored, etc.)

### Understanding the Output

Each lesson shows source attribution in brackets:
- `[NFO]` - Title/description came from an NFO file
- `[file-tags]` - Metadata was in the video file itself
- `[filename]` - Title was parsed from the filename
- `[dir-name]` - Course name came from the directory folder name

Example output:
```
COURSE: Python Fundamentals [NFO]
================================================================================
Description: Learn Python from basics to advanced
Instructor: John Smith
Year: 2024

Lessons (12 total, 12 with metadata):
--------------------------------------------------------------------------------
  1. Introduction to Python [filename]
      File: Season 01/01 - Introduction to Python.mp4
      Duration: 45:32
```

## Project Structure

```
edu-library/
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── edu_scanner.py           # Main scanner script
├── database.py              # SQLite database module
├── .gitignore               # Git ignore rules
├── library.db               # Main database (created on first run)
└── test_data/               # Test course structure for development
    ├── Advanced_JavaScript_2023/
    ├── Python_Basics_2024/
    └── ... (other test courses)
```

## How It Works

### Scanning Process

1. **Directory Traversal** - Recursively walks through library directories using `os.walk()`
2. **Course Detection** - Identifies directories containing video files as courses
3. **Lesson Discovery** - Finds all video files within each course
4. **Metadata Extraction** (in priority order):
   - Checks for any `.nfo` file in the directory (flexible naming)
   - Extracts embedded metadata using MediaInfo
   - Parses filename to extract lesson title
   - Uses directory name as fallback course name
5. **Database Storage** - Stores all metadata with source attribution in SQLite
6. **Display** - Groups results by course and shows source attribution

### Supported Video Formats

- MP4, MKV, AVI, MOV, FLV, WMV, WebM, M4V

### Supported Metadata

**Course Metadata:**
- Title, Description, Instructor, Year

**Lesson Metadata:**
- Title, Description, Duration

## NFO File Format

The scanner recognizes standard Kodi/Jellyfin NFO files:

**tvshow.nfo** (in course directory):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<tvshow>
    <title>Course Name</title>
    <plot>Course description</plot>
    <director>Instructor Name</director>
    <year>2024</year>
</tvshow>
```

**episode.nfo** (same directory as video):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<episodedetails>
    <title>Lesson Title</title>
    <plot>Lesson description</plot>
    <runtime>45</runtime>
</episodedetails>
```

## Database Schema

The SQLite database includes three tables:

**courses** table:
- `id` - Unique identifier
- `name` - Course title
- `directory_path` - Full path to course directory
- `description` - Course description
- `instructor` - Primary instructor name
- `year` - Year published
- `metadata_source` - Where metadata came from (NFO, file-tags, dir-name)
- `created_at`, `updated_at` - Timestamps

**lessons** table:
- `id` - Unique identifier
- `course_id` - Foreign key to courses
- `title` - Lesson title
- `file_path` - Full path to video file
- `file_name` - Video filename
- `duration_seconds` - Video duration in seconds
- `description` - Lesson description
- `metadata_source` - Where metadata came from
- `created_at`, `updated_at` - Timestamps

**metadata_sources** table:
- Tracks granular source information for each metadata field
- Useful for understanding which fields need manual assignment

## Database Queries

You can query the database directly:

```bash
# List all courses
sqlite3 library.db "SELECT name, instructor, year FROM courses;"

# List lessons for a specific course
sqlite3 library.db "SELECT title, duration_seconds FROM lessons WHERE course_id = 1;"

# Find lessons without titles
sqlite3 library.db "SELECT file_name FROM lessons WHERE title IS NULL;"

# Get completion statistics
sqlite3 library.db "SELECT COUNT(*) FROM lessons WHERE title IS NOT NULL;"
```

## Future Features

- Interactive metadata editor UI for updating database
- Automatic NFO file generation from database
- Directory reorganization and file renaming
- Jellyfin API integration for direct import
- Web-based dashboard for browsing library
- Export to various metadata formats (YAML, JSON)
- Configurable filename parsing patterns

## Troubleshooting

**"Warning: Failed to parse [filename].nfo"**
- The NFO file is malformed XML. Check the file format.

**Duration shows "Unknown"**
- The video file has no embedded duration metadata. MediaInfo cannot extract it.
- Add a `<runtime>` tag to the `.nfo` file (in minutes).

**Course name shows "[dirname]-fromdir"**
- No `.nfo` file found in the course directory.
- Create any `.nfo` file (e.g., `tvshow.nfo`) with proper course metadata.

**Lessons not found**
- Check that files use supported video extensions (.mp4, .mkv, .avi, etc.)
- Verify files are in the library directory.
- Check filesystem permissions for the library path.

**Database file not found**
- The database is created automatically on first scan.
- Check that you have write permissions in the current directory.
- Use `--db=/path/to/database.db` to specify a custom location.

## License

Personal use - educational content organization

## Author

Created for organizing personal educational video collections for Jellyfin media server.
