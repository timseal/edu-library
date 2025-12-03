#!/usr/bin/env python3
"""
Educational Video Library Scanner
Scans directories for courses and lessons, extracts metadata from multiple sources.
"""

import os
import re
import sys
import time
import argparse
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET
from collections import defaultdict

try:
    from pymediainfo import MediaInfo
except ImportError:
    MediaInfo = None

from database import LibraryDatabase


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class MetadataSource:
    """Indicates where metadata came from"""
    nfo: bool = False
    file_tags: bool = False
    filename: bool = False
    directory_name: bool = False


@dataclass
class Lesson:
    """Represents a single lesson/video file"""
    filepath: Path
    filename: str
    title: Optional[str] = None
    duration: Optional[int] = None  # seconds
    description: Optional[str] = None
    source: MetadataSource = field(default_factory=MetadataSource)

    @property
    def duration_str(self) -> str:
        """Format duration as HH:MM:SS"""
        if self.duration is None:
            return "Unknown"
        hours = self.duration // 3600
        minutes = (self.duration % 3600) // 60
        seconds = self.duration % 60
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"

    def is_complete(self) -> bool:
        """Check if lesson has essential metadata"""
        return self.title is not None


@dataclass
class Course:
    """Represents a course (directory containing lessons)"""
    dirpath: Path
    name: str
    description: Optional[str] = None
    instructor: Optional[str] = None
    year: Optional[str] = None
    lessons: List[Lesson] = field(default_factory=list)
    source: MetadataSource = field(default_factory=MetadataSource)

    def is_complete(self) -> bool:
        """Check if course has essential metadata"""
        return self.name is not None

    def lessons_complete(self) -> int:
        """Count how many lessons have complete metadata"""
        return sum(1 for lesson in self.lessons if lesson.is_complete())


# ============================================================================
# NFO File Parser
# ============================================================================

def parse_tvshow_nfo(nfo_path: Path) -> Optional[Dict]:
    """Parse tvshow.nfo file and extract course metadata"""
    try:
        tree = ET.parse(nfo_path)
        root = tree.getroot()

        metadata = {
            'name': None,
            'description': None,
            'instructor': None,
            'year': None,
        }

        for elem in root:
            if elem.tag == 'title':
                metadata['name'] = elem.text
            elif elem.tag == 'plot':
                metadata['description'] = elem.text
            elif elem.tag == 'director':
                metadata['instructor'] = elem.text
            elif elem.tag == 'year':
                metadata['year'] = elem.text

        return metadata
    except Exception as e:
        print(f"Warning: Failed to parse {nfo_path}: {e}", file=sys.stderr)
        return None


def parse_episode_nfo(nfo_path: Path) -> Optional[Dict]:
    """Parse episode.nfo file and extract lesson metadata"""
    try:
        tree = ET.parse(nfo_path)
        root = tree.getroot()

        metadata = {
            'title': None,
            'description': None,
            'duration': None,
        }

        for elem in root:
            if elem.tag == 'title':
                metadata['title'] = elem.text
            elif elem.tag == 'plot':
                metadata['description'] = elem.text
            elif elem.tag == 'runtime':
                # NFO stores runtime in minutes
                try:
                    metadata['duration'] = int(elem.text) * 60
                except (ValueError, TypeError):
                    pass

        return metadata
    except Exception as e:
        print(f"Warning: Failed to parse {nfo_path}: {e}", file=sys.stderr)
        return None


# ============================================================================
# MediaInfo Extractor
# ============================================================================

def extract_media_metadata(video_path: Path) -> Optional[Dict]:
    """Extract metadata from video file using MediaInfo"""
    if MediaInfo is None:
        return None

    try:
        media_info = MediaInfo.parse(str(video_path))
        metadata = {
            'duration': None,
            'title': None,
        }

        # Extract duration from General track
        for track in media_info.tracks:
            if track.track_type == 'General':
                if track.duration:
                    metadata['duration'] = int(track.duration / 1000)  # Convert ms to seconds
                if track.title:
                    metadata['title'] = track.title
                break

        return metadata
    except Exception as e:
        print(f"Warning: Failed to extract metadata from {video_path}: {e}", file=sys.stderr)
        return None


# ============================================================================
# Filename Parser
# ============================================================================

def parse_lesson_filename(filename: str) -> Optional[str]:
    """
    Extract lesson title from filename.
    Handles formats like:
    - "Lesson 5 - Introduction to Python.mp4" -> "Introduction to Python"
    - "05 - Title.mp4" -> "Title"
    - "Title Only.mp4" -> "Title Only"
    """
    # Remove extension
    name_without_ext = Path(filename).stem

    # Try to match patterns with lesson numbers and separators
    # Pattern: "Lesson N -" or "N -" or "N. " or just use the whole name
    patterns = [
        r'^(?:Lesson\s+\d+\s*[-:]?\s*)(.+)$',  # "Lesson 5 - Title"
        r'^\d+\s*[-:\.]\s*(.+)$',  # "05 - Title" or "05: Title"
    ]

    for pattern in patterns:
        match = re.match(pattern, name_without_ext, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    # If no pattern matches, use the whole filename (without number prefix if present)
    # Remove leading numbers if they're followed by space/dash
    cleaned = re.sub(r'^\d+\s*[-:\.]?\s*', '', name_without_ext).strip()
    return cleaned if cleaned else None


# ============================================================================
# Directory Scanner
# ============================================================================

def is_video_file(path: Path) -> bool:
    """Check if file is a video file"""
    video_extensions = {'.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm', '.m4v'}
    return path.suffix.lower() in video_extensions


def find_nfo_file(directory: Path, pattern: str = '*.nfo') -> Optional[Path]:
    """Find first NFO file matching pattern in directory"""
    nfo_files = list(directory.glob(pattern))
    return nfo_files[0] if nfo_files else None


def scan_directory(library_path: Path) -> List[Course]:
    """
    Scan a library directory for courses and lessons.
    A course is a directory containing video files.
    """
    courses = []

    if not library_path.exists():
        print(f"Warning: Library path does not exist: {library_path}", file=sys.stderr)
        return courses

    # Iterate through top-level directories
    for course_dir in sorted(library_path.iterdir()):
        if not course_dir.is_dir():
            continue

        # Find all video files in this course directory (recursively, but only video files)
        video_files = []
        for root, dirs, files in os.walk(course_dir):
            for file in files:
                filepath = Path(root) / file
                if is_video_file(filepath):
                    video_files.append(filepath)

        if not video_files:
            continue  # Skip directories with no video files

        # Create course object
        course_name = course_dir.name
        course = Course(dirpath=course_dir, name=f"{course_name}-fromdir")
        course.source.directory_name = True

        # Try to load any tvshow.nfo or course-level NFO file
        tvshow_nfo = find_nfo_file(course_dir)
        if tvshow_nfo:
            nfo_data = parse_tvshow_nfo(tvshow_nfo)
            if nfo_data and nfo_data.get('name'):
                course.name = nfo_data['name']
                course.source.directory_name = False
                course.source.nfo = True
            if nfo_data:
                if nfo_data.get('description'):
                    course.description = nfo_data['description']
                if nfo_data.get('instructor'):
                    course.instructor = nfo_data['instructor']
                if nfo_data.get('year'):
                    course.year = nfo_data['year']

        # Process each video file
        for video_path in sorted(video_files):
            lesson = Lesson(filepath=video_path, filename=video_path.name)

            # Try to get metadata from any NFO file in same directory matching video name
            video_dir = video_path.parent
            
            # First try exact match with video filename stem
            nfo_candidates = [video_dir / f"{video_path.stem}.nfo"]
            
            # If no exact match, look for any NFO file in the directory
            if not nfo_candidates[0].exists():
                nfo_candidates = list(video_dir.glob('*.nfo'))
            
            for nfo_path in nfo_candidates:
                if nfo_path.exists():
                    nfo_data = parse_episode_nfo(nfo_path)
                    if nfo_data:
                        if nfo_data.get('title'):
                            lesson.title = nfo_data['title']
                            lesson.source.nfo = True
                        if nfo_data.get('duration') and not lesson.duration:
                            lesson.duration = nfo_data['duration']
                        if nfo_data.get('description'):
                            lesson.description = nfo_data['description']
                    break  # Use first found NFO file

            # Try to extract metadata from video file
            if MediaInfo:
                media_data = extract_media_metadata(video_path)
                if media_data:
                    if not lesson.duration and media_data.get('duration'):
                        lesson.duration = media_data['duration']
                    if not lesson.title and media_data.get('title'):
                        lesson.title = media_data['title']
                        lesson.source.file_tags = True

            # Parse filename for lesson title
            if not lesson.title:
                parsed_title = parse_lesson_filename(video_path.name)
                if parsed_title:
                    lesson.title = parsed_title
                    lesson.source.filename = True

            course.lessons.append(lesson)

        courses.append(course)

    return courses


# ============================================================================
# Terminal Output Formatter
# ============================================================================

def source_annotation(source: MetadataSource) -> str:
    """Generate a source annotation string"""
    sources = []
    if source.nfo:
        sources.append("NFO")
    if source.file_tags:
        sources.append("file-tags")
    if source.filename:
        sources.append("filename")
    if source.directory_name:
        sources.append("dir-name")
    return f" [{', '.join(sources)}]" if sources else ""


def format_course_output(course: Course) -> str:
    """Format a course and its lessons for terminal output"""
    lines = []
    
    # Course header
    course_note = source_annotation(course.source)
    lines.append(f"\n{'=' * 80}")
    lines.append(f"COURSE: {course.name}{course_note}")
    lines.append(f"{'=' * 80}")
    
    # Course metadata
    if course.description:
        lines.append(f"Description: {course.description}")
    if course.instructor:
        lines.append(f"Instructor: {course.instructor}")
    if course.year:
        lines.append(f"Year: {course.year}")
    
    # Lessons
    lines.append(f"\nLessons ({len(course.lessons)} total, {course.lessons_complete()} with metadata):")
    lines.append("-" * 80)
    
    for i, lesson in enumerate(course.lessons, 1):
        lesson_note = source_annotation(lesson.source)
        
        # Lesson title
        title = lesson.title or "[NO TITLE]"
        lines.append(f"{i:3d}. {title}{lesson_note}")
        
        # File info
        lines.append(f"      File: {lesson.filepath.relative_to(course.dirpath)}")
        lines.append(f"      Duration: {lesson.duration_str}")
        
        if lesson.description:
            lines.append(f"      Description: {lesson.description}")
        
        lines.append("")
    
    return "\n".join(lines)


def print_summary(courses: List[Course]):
    """Print summary statistics"""
    total_lessons = sum(len(c.lessons) for c in courses)
    complete_lessons = sum(c.lessons_complete() for c in courses)
    complete_courses = sum(1 for c in courses if c.is_complete())
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total Courses Found: {len(courses)}")
    print(f"Total Lessons Found: {total_lessons}")
    print(f"Lessons with Complete Metadata: {complete_lessons}/{total_lessons} ({100*complete_lessons//total_lessons if total_lessons else 0}%)")
    print(f"Courses with Complete Metadata: {complete_courses}/{len(courses)} ({100*complete_courses//len(courses) if courses else 0}%)")
    print("=" * 80 + "\n")


# ============================================================================
# Main
# ============================================================================

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Scan educational video library and extract metadata'
    )
    parser.add_argument(
        '--library-root',
        type=Path,
        default=Path('/Volumes/learning'),
        help='Root path to library directory (default: /Volumes/learning)'
    )
    parser.add_argument(
        '--db',
        type=Path,
        default=Path('library.db'),
        help='Path to SQLite database file (default: library.db)'
    )
    parser.add_argument(
        '--clear-db',
        action='store_true',
        help='Clear database before scanning'
    )
    args = parser.parse_args()

    lib_path = args.library_root.expanduser().resolve()
    
    # Initialize database
    db = LibraryDatabase(args.db)
    
    if args.clear_db:
        print("Clearing database...")
        db.clear_all()
    
    all_courses = []

    print(f"\nScanning: {lib_path}")
    print("-" * 80)
    
    start_time = time.time()
    courses = scan_directory(lib_path)
    elapsed = time.time() - start_time
    
    all_courses.extend(courses)
    
    if courses:
        print(f"Found {len(courses)} courses in {elapsed:.2f}s")
    else:
        print(f"No courses found (scanned in {elapsed:.2f}s)")

    # Store in database
    if all_courses:
        print("\nStoring in database...")
        db_start = time.time()
        for course in all_courses:
            course_dict = asdict(course)
            course_id = db.add_course(course_dict)
            
            for lesson in course.lessons:
                lesson_dict = asdict(lesson)
                db.add_lesson(course_id, lesson_dict)
        
        db_elapsed = time.time() - db_start
        print(f"Stored {len(all_courses)} courses in {db_elapsed:.2f}s")
        
        # Display results grouped by course
        for course in all_courses:
            print(format_course_output(course))
        
        # Print summary
        print_summary(all_courses)
        
        # Print database statistics
        stats = db.get_statistics()
        print(f"\nDatabase Statistics:")
        print(f"  Courses in database: {stats['total_courses']}")
        print(f"  Lessons in database: {stats['total_lessons']}")
        print(f"  Lessons with titles: {stats['lessons_with_title']}")
        
    else:
        print("\nNo courses found in library directory.")
    
    db.close()


if __name__ == '__main__':
    main()
