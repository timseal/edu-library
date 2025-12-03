"""
Database operations for educational video library metadata.
Stores courses, lessons, and metadata in SQLite database.
"""

import sqlite3
from pathlib import Path
from typing import List, Optional
from dataclasses import asdict


class LibraryDatabase:
    """SQLite database for storing educational library metadata"""

    def __init__(self, db_path: Path = Path('library.db')):
        """Initialize database connection"""
        self.db_path = db_path
        self.connection = None
        self.init_db()

    def init_db(self):
        """Initialize database tables if they don't exist"""
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        cursor = self.connection.cursor()

        # Create courses table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                directory_path TEXT UNIQUE NOT NULL,
                description TEXT,
                instructor TEXT,
                year TEXT,
                metadata_source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create lessons table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                title TEXT,
                file_path TEXT UNIQUE NOT NULL,
                file_name TEXT NOT NULL,
                duration_seconds INTEGER,
                description TEXT,
                metadata_source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE
            )
        ''')

        # Create metadata_sources table to track where data came from
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metadata_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lesson_id INTEGER,
                course_id INTEGER,
                title_source TEXT,
                description_source TEXT,
                duration_source TEXT,
                FOREIGN KEY (lesson_id) REFERENCES lessons (id) ON DELETE CASCADE,
                FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE
            )
        ''')

        self.connection.commit()

    def add_course(self, course_data: dict) -> int:
        """
        Add or update a course in the database.
        Returns course ID.
        """
        cursor = self.connection.cursor()

        # Extract metadata source info
        sources = course_data.pop('source', {})
        source_text = self._format_source(sources)

        try:
            cursor.execute('''
                INSERT INTO courses 
                (name, directory_path, description, instructor, year, metadata_source)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                course_data['name'],
                str(course_data['dirpath']),
                course_data.get('description'),
                course_data.get('instructor'),
                course_data.get('year'),
                source_text
            ))
            self.connection.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            # Course exists, update it
            cursor.execute('''
                UPDATE courses 
                SET name = ?, description = ?, instructor = ?, year = ?, 
                    metadata_source = ?, updated_at = CURRENT_TIMESTAMP
                WHERE directory_path = ?
            ''', (
                course_data['name'],
                course_data.get('description'),
                course_data.get('instructor'),
                course_data.get('year'),
                source_text,
                str(course_data['dirpath'])
            ))
            self.connection.commit()
            cursor.execute('SELECT id FROM courses WHERE directory_path = ?',
                          (str(course_data['dirpath']),))
            return cursor.fetchone()[0]

    def add_lesson(self, course_id: int, lesson_data: dict) -> int:
        """
        Add or update a lesson in the database.
        Returns lesson ID.
        """
        cursor = self.connection.cursor()

        # Extract metadata source info
        sources = lesson_data.pop('source', {})
        source_text = self._format_source(sources)

        try:
            cursor.execute('''
                INSERT INTO lessons 
                (course_id, title, file_path, file_name, duration_seconds, 
                 description, metadata_source)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                course_id,
                lesson_data.get('title'),
                str(lesson_data['filepath']),
                lesson_data['filename'],
                lesson_data.get('duration'),
                lesson_data.get('description'),
                source_text
            ))
            self.connection.commit()
            lesson_id = cursor.lastrowid

            # Store detailed metadata sources
            cursor.execute('''
                INSERT INTO metadata_sources 
                (lesson_id, title_source, description_source, duration_source)
                VALUES (?, ?, ?, ?)
            ''', (
                lesson_id,
                'nfo' if sources.get('nfo') else ('file-tags' if sources.get('file_tags') else 
                       ('filename' if sources.get('filename') else 'unknown')),
                'nfo' if sources.get('nfo') else 'unknown',
                'file-tags' if sources.get('file_tags') else 'unknown'
            ))
            self.connection.commit()
            return lesson_id
        except sqlite3.IntegrityError:
            # Lesson exists, update it
            cursor.execute('''
                UPDATE lessons 
                SET title = ?, duration_seconds = ?, description = ?, 
                    metadata_source = ?, updated_at = CURRENT_TIMESTAMP
                WHERE file_path = ?
            ''', (
                lesson_data.get('title'),
                lesson_data.get('duration'),
                lesson_data.get('description'),
                source_text,
                str(lesson_data['filepath'])
            ))
            self.connection.commit()
            cursor.execute('SELECT id FROM lessons WHERE file_path = ?',
                          (str(lesson_data['filepath']),))
            return cursor.fetchone()[0]

    def get_all_courses(self) -> List[dict]:
        """Get all courses from database"""
        cursor = self.connection.cursor()
        cursor.execute('SELECT * FROM courses ORDER BY name')
        return [dict(row) for row in cursor.fetchall()]

    def get_course_lessons(self, course_id: int) -> List[dict]:
        """Get all lessons for a course"""
        cursor = self.connection.cursor()
        cursor.execute(
            'SELECT * FROM lessons WHERE course_id = ? ORDER BY id',
            (course_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_course_by_path(self, directory_path: str) -> Optional[dict]:
        """Get course by directory path"""
        cursor = self.connection.cursor()
        cursor.execute('SELECT * FROM courses WHERE directory_path = ?', (directory_path,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_lesson_by_path(self, file_path: str) -> Optional[dict]:
        """Get lesson by file path"""
        cursor = self.connection.cursor()
        cursor.execute('SELECT * FROM lessons WHERE file_path = ?', (file_path,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def clear_all(self):
        """Clear all data from database"""
        cursor = self.connection.cursor()
        cursor.execute('DELETE FROM lessons')
        cursor.execute('DELETE FROM courses')
        cursor.execute('DELETE FROM metadata_sources')
        self.connection.commit()

    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()

    @staticmethod
    def _format_source(source_dict: dict) -> str:
        """Format source dictionary as comma-separated string"""
        sources = []
        if source_dict.get('nfo'):
            sources.append('nfo')
        if source_dict.get('file_tags'):
            sources.append('file-tags')
        if source_dict.get('filename'):
            sources.append('filename')
        if source_dict.get('directory_name'):
            sources.append('dir-name')
        return ', '.join(sources) if sources else 'unknown'

    def get_statistics(self) -> dict:
        """Get library statistics"""
        cursor = self.connection.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM courses')
        total_courses = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM lessons')
        total_lessons = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM lessons WHERE title IS NOT NULL')
        lessons_with_title = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT course_id) FROM lessons WHERE duration_seconds IS NOT NULL')
        courses_with_duration = cursor.fetchone()[0]

        return {
            'total_courses': total_courses,
            'total_lessons': total_lessons,
            'lessons_with_title': lessons_with_title,
            'courses_with_duration': courses_with_duration,
        }
