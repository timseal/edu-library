#!/usr/bin/env python3
"""
Educational Video Library Scanner - GUI
A cross-platform GUI for scanning and managing educational video libraries.
"""

import PySimpleGUI as sg
import threading
from pathlib import Path
from datetime import datetime
import sys
import os

from edu_scanner import scan_directory
from database import LibraryDatabase

# Set theme
sg.theme('DarkBlue3')

class ScannerGUI:
    def __init__(self):
        self.db = None
        self.scanning = False
        self.scan_thread = None
        self.scan_results = []
        
    def create_window(self):
        """Create the main GUI window"""
        layout = [
            [sg.Text('Educational Video Library Scanner', font=('Arial', 16, 'bold'))],
            [sg.Text('_' * 80)],
            
            # Library Path Selection
            [sg.Text('Library Root Path:', size=(15, 1)),
             sg.Input(key='-LIBRARY-PATH-', default_text='/Volumes/learning', size=(40, 1)),
             sg.FolderBrowse(button_text='Browse')],
            
            # Database Path Selection
            [sg.Text('Database Path:', size=(15, 1)),
             sg.Input(key='-DB-PATH-', default_text='library.db', size=(40, 1)),
             sg.FileBrowse(button_text='Browse', file_types=(('Database', '*.db'),))],
            
            # Options
            [sg.Checkbox('Clear database before scanning', key='-CLEAR-DB-', default=False)],
            
            [sg.Text('_' * 80)],
            
            # Scan Button
            [sg.Button('Start Scan', size=(15, 1), key='-SCAN-'),
             sg.Button('Stop Scan', size=(15, 1), key='-STOP-', disabled=True),
             sg.Button('Export Results', size=(15, 1), key='-EXPORT-', disabled=True),
             sg.Button('Exit', size=(15, 1))],
            
            # Progress
            [sg.ProgressBar(100, orientation='h', size=(60, 20), key='-PROGRESS-')],
            [sg.Text('Ready', key='-STATUS-', size=(80, 1))],
            
            [sg.Text('_' * 80)],
            
            # Results Display
            [sg.Multiline(size=(100, 30), key='-OUTPUT-', disabled=True, 
                         autoscroll=True, vertical_scroll_only=True)],
        ]
        
        window = sg.Window('Educational Video Library Scanner', layout, finalize=True)
        return window
    
    def scan_with_progress(self, library_path, db_path, clear_db):
        """Run scan in background and update progress"""
        try:
            lib_path = Path(library_path).expanduser().resolve()
            db = LibraryDatabase(Path(db_path))
            
            if clear_db:
                db.clear_all()
            
            # Update status
            self.window['-STATUS-'].update(f'Scanning {lib_path}...')
            
            # Perform scan
            courses = scan_directory(lib_path)
            
            # Store in database
            if courses:
                db_start = datetime.now()
                for course in courses:
                    course_dict = {
                        'name': course.name,
                        'dirpath': course.dirpath,
                        'description': course.description,
                        'instructor': course.instructor,
                        'year': course.year,
                        'source': {
                            'nfo': course.source.nfo,
                            'file_tags': course.source.file_tags,
                            'filename': course.source.filename,
                            'directory_name': course.source.directory_name,
                        }
                    }
                    course_id = db.add_course(course_dict)
                    
                    for lesson in course.lessons:
                        lesson_dict = {
                            'filepath': lesson.filepath,
                            'filename': lesson.filename,
                            'title': lesson.title,
                            'duration': lesson.duration,
                            'description': lesson.description,
                            'source': {
                                'nfo': lesson.source.nfo,
                                'file_tags': lesson.source.file_tags,
                                'filename': lesson.source.filename,
                            }
                        }
                        db.add_lesson(course_id, lesson_dict)
                
                db_elapsed = (datetime.now() - db_start).total_seconds()
                
                # Build results
                results = f"\n{'=' * 80}\n"
                results += f"SCAN COMPLETE\n"
                results += f"{'=' * 80}\n"
                results += f"Found {len(courses)} courses\n"
                results += f"Database stored in {db_elapsed:.2f}s\n\n"
                
                for course in courses:
                    results += f"COURSE: {course.name}\n"
                    results += f"-" * 80 + "\n"
                    if course.description:
                        results += f"Description: {course.description}\n"
                    if course.instructor:
                        results += f"Instructor: {course.instructor}\n"
                    if course.year:
                        results += f"Year: {course.year}\n"
                    
                    results += f"\nLessons ({len(course.lessons)} total):\n"
                    for i, lesson in enumerate(course.lessons, 1):
                        title = lesson.title or "[NO TITLE]"
                        results += f"  {i}. {title}\n"
                        results += f"     File: {lesson.filepath.name}\n"
                        results += f"     Duration: {lesson.duration_str}\n"
                    results += "\n"
                
                # Database stats
                stats = db.get_statistics()
                results += f"{'=' * 80}\n"
                results += f"DATABASE STATISTICS\n"
                results += f"{'=' * 80}\n"
                results += f"Total Courses: {stats['total_courses']}\n"
                results += f"Total Lessons: {stats['total_lessons']}\n"
                results += f"Lessons with Titles: {stats['lessons_with_title']}\n"
                
                self.window['-OUTPUT-'].update(results)
                self.window['-STATUS-'].update(f'✓ Scan complete: {len(courses)} courses, {sum(len(c.lessons) for c in courses)} lessons')
                self.window['-EXPORT-'].update(disabled=False)
            else:
                self.window['-OUTPUT-'].update("No courses found in the specified directory.")
                self.window['-STATUS-'].update('No courses found')
            
            db.close()
            
        except Exception as e:
            error_msg = f"ERROR: {str(e)}\n\n{type(e).__name__}"
            self.window['-OUTPUT-'].update(error_msg)
            self.window['-STATUS-'].update(f'Error: {str(e)}')
        
        finally:
            self.window['-SCAN-'].update(disabled=False)
            self.window['-STOP-'].update(disabled=True)
            self.scanning = False
    
    def run(self):
        """Run the GUI application"""
        self.window = self.create_window()
        
        while True:
            event, values = self.window.read(timeout=100)
            
            if event == sg.WINDOW_CLOSED or event == 'Exit':
                break
            
            elif event == '-SCAN-':
                if not self.scanning:
                    library_path = values['-LIBRARY-PATH-']
                    db_path = values['-DB-PATH-']
                    clear_db = values['-CLEAR-DB-']
                    
                    if not library_path or not db_path:
                        sg.popup_error('Please specify both library path and database path')
                        continue
                    
                    self.scanning = True
                    self.window['-SCAN-'].update(disabled=True)
                    self.window['-STOP-'].update(disabled=False)
                    self.window['-EXPORT-'].update(disabled=True)
                    self.window['-OUTPUT-'].update('')
                    
                    # Start scan in background thread
                    self.scan_thread = threading.Thread(
                        target=self.scan_with_progress,
                        args=(library_path, db_path, clear_db),
                        daemon=True
                    )
                    self.scan_thread.start()
            
            elif event == '-STOP-':
                # Note: We can't truly stop the thread, but we can disable it from updating
                self.scanning = False
                self.window['-SCAN-'].update(disabled=False)
                self.window['-STOP-'].update(disabled=True)
                self.window['-STATUS-'].update('Scan cancelled by user')
            
            elif event == '-EXPORT-':
                output = self.window['-OUTPUT-'].get()
                if output:
                    filename = sg.popup_get_file(
                        'Save results as...',
                        save_as=True,
                        file_types=(('Text Files', '*.txt'), ('All Files', '*.*'))
                    )
                    if filename:
                        try:
                            with open(filename, 'w') as f:
                                f.write(output)
                            sg.popup_ok(f'Results saved to {filename}')
                        except Exception as e:
                            sg.popup_error(f'Error saving file: {str(e)}')
        
        self.window.close()


def main():
    """Entry point for GUI"""
    app = ScannerGUI()
    app.run()


if __name__ == '__main__':
    main()
