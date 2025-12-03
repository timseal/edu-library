# Educational Video Library Scanner

A Python tool to scan, organize, and catalog your personal collection of educational videos and courses for use with Jellyfin media server.

## Overview

This tool helps you organize scattered educational videos across multiple directories into a well-structured library that Jellyfin can recognize and display properly. It extracts metadata from multiple sources (NFO files, video file tags, filenames) and presents a comprehensive catalog of your courses and lessons.

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
- **Intelligent filename parsing** - Extracts lesson titles from common formats:
  - "Lesson 5 - Introduction to Python" → "Introduction to Python"
  - "05 - Title" → "Title"
  - "Title Only" → "Title Only"
- **Duration extraction** - Reads video duration from file metadata
- **Source attribution** - Shows where each piece of metadata came from (NFO, file-tags, filename, dir-name)
- **Completion tracking** - Reports which courses/lessons have complete metadata
- **Performance timing** - Shows how long each scan takes
- **Terminal output** - Clean, organized display grouped by course

## Requirements

- Python 3.7+
- `pymediainfo` - for extracting video file metadata
- `lxml` - for parsing NFO XML files

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Basic Scan

```bash
python edu_scanner.py
```

This scans `/Volumes/learning` (the configured library directory) and displays:
1. All courses found with their metadata
2. All lessons in each course with titles, durations, and metadata sources
3. Summary statistics on metadata completeness

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
└── test_data/               # Test course structure for development
    ├── Advanced_JavaScript_2023/
    ├── Python_Basics_2024/
    └── ... (other test courses)
```

## How It Works

### Scanning Process

1. **Directory Traversal** - Recursively walks through library directories
2. **Course Detection** - Identifies directories containing video files as courses
3. **Lesson Discovery** - Finds all video files within each course
4. **Metadata Extraction** (in priority order):
   - Checks for `tvshow.nfo` (course) and `[filename].nfo` (lesson) files
   - Extracts embedded metadata using MediaInfo
   - Parses filename to extract lesson title
   - Uses directory name as fallback course name
5. **Display** - Groups results by course and shows source attribution

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

## Configuration

Edit the `lib_paths` list in `main()` function to scan additional directories:

```python
lib_paths = [
    Path('/Volumes/learning').expanduser(),
    Path('/path/to/another/library').expanduser(),
]
```

## Future Features

- Interactive metadata editor UI
- Automatic NFO file generation for missing metadata
- Directory reorganization and file renaming
- Jellyfin integration for direct import
- Web-based dashboard
- Configurable filename parsing patterns

## Troubleshooting

**"Warning: Failed to parse [filename].nfo"**
- The NFO file is malformed XML. Check the file format.

**Duration shows "Unknown"**
- The video file has no embedded duration metadata. MediaInfo cannot extract it.
- Add a `<runtime>` tag to the `.nfo` file (in minutes).

**Course name shows "[dirname]-fromdir"**
- No `tvshow.nfo` file found in the course directory.
- Create a `tvshow.nfo` file with proper course metadata.

**Lessons not found**
- Check that files use supported video extensions (.mp4, .mkv, .avi, etc.)
- Verify files are in the library directory.

## License

Personal use - educational content organization

## Author

Created for organizing personal educational video collections for Jellyfin media server.
