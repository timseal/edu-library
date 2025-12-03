#!/usr/bin/env python3
"""
Educational Video Library Scanner - PyQt6 GUI
A modern cross-platform GUI for scanning and managing educational video libraries.
"""

import sys
import threading
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QCheckBox, QTabWidget, QTextEdit,
    QProgressBar, QFileDialog, QMessageBox, QSplitter, QGroupBox, QFormLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QThread
from PyQt6.QtGui import QFont, QIcon

from edu_scanner import scan_directory
from database import LibraryDatabase


class ScanWorker(QObject):
    """Worker thread for scanning"""
    finished = pyqtSignal()
    error = pyqtSignal(str)
    log_message = pyqtSignal(str)
    progress_update = pyqtSignal(str)
    results_ready = pyqtSignal(str)
    
    def __init__(self, library_path, db_path, clear_db, skip_media_info):
        super().__init__()
        self.library_path = library_path
        self.db_path = db_path
        self.clear_db = clear_db
        self.skip_media_info = skip_media_info
        self.is_running = True
    
    def stop(self):
        """Signal to stop scanning"""
        self.is_running = False
    
    def run(self):
        """Execute the scan in background"""
        try:
            lib_path = Path(self.library_path).expanduser().resolve()
            db = LibraryDatabase(Path(self.db_path))
            
            if self.clear_db:
                self.log_message.emit('Clearing database...')
                db.clear_all()
                self.log_message.emit('Database cleared')
            
            self.log_message.emit(f'Scanning {lib_path}...')
            self.progress_update.emit(f'Scanning {lib_path}...')
            
            # Perform scan
            courses = scan_directory(lib_path, skip_media_info=self.skip_media_info)
            self.log_message.emit(f'Found {len(courses)} courses')
            
            if courses:
                self.log_message.emit('Storing in database...')
                for i, course in enumerate(courses, 1):
                    if not self.is_running:
                        self.log_message.emit('Scan stopped by user')
                        break
                    
                    self.log_message.emit(f'Processing course {i}/{len(courses)}: {course.name} ({len(course.lessons)} lessons)')
                    
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
                
                # Build results
                results = "=" * 80 + "\n"
                results += "SCAN RESULTS\n"
                results += "=" * 80 + "\n\n"
                
                for course in courses:
                    results += f"COURSE: {course.name}\n"
                    results += "-" * 80 + "\n"
                    if course.description:
                        results += f"Description: {course.description}\n"
                    if course.instructor:
                        results += f"Instructor: {course.instructor}\n"
                    if course.year:
                        results += f"Year: {course.year}\n"
                    
                    results += f"\nLessons ({len(course.lessons)} total):\n"
                    for j, lesson in enumerate(course.lessons, 1):
                        title = lesson.title or "[NO TITLE]"
                        results += f"  {j}. {title}\n"
                        results += f"     File: {lesson.filepath.name}\n"
                        results += f"     Duration: {lesson.duration_str}\n"
                    results += "\n"
                
                # Database stats
                stats = db.get_statistics()
                results += "=" * 80 + "\n"
                results += "DATABASE STATISTICS\n"
                results += "=" * 80 + "\n"
                results += f"Total Courses: {stats['total_courses']}\n"
                results += f"Total Lessons: {stats['total_lessons']}\n"
                results += f"Lessons with Titles: {stats['lessons_with_title']}\n"
                
                self.results_ready.emit(results)
                self.log_message.emit('-' * 80)
                self.log_message.emit(f'Scan complete: {len(courses)} courses, {sum(len(c.lessons) for c in courses)} lessons')
                self.progress_update.emit(f'✓ Scan complete: {len(courses)} courses, {sum(len(c.lessons) for c in courses)} lessons')
            else:
                self.log_message.emit('No courses found')
                self.progress_update.emit('No courses found')
            
            db.close()
        
        except Exception as e:
            self.error.emit(f"ERROR: {str(e)}")
            self.log_message.emit(f'ERROR: {str(e)}')
        
        finally:
            self.finished.emit()


class ScannerGUI(QMainWindow):
    """Main GUI window for the scanner"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Educational Video Library Scanner')
        self.setGeometry(100, 100, 1200, 900)
        
        self.scan_worker = None
        self.scan_thread = None
        self.is_scanning = False
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Title
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label = QLabel('Educational Video Library Scanner')
        title_label.setFont(title_font)
        main_layout.addWidget(title_label)
        
        # Configuration section
        config_group = QGroupBox("Scan Configuration")
        config_layout = QFormLayout()
        
        # Library path
        path_layout = QHBoxLayout()
        self.library_path_input = QLineEdit()
        self.library_path_input.setText('/Volumes/learning')
        path_layout.addWidget(self.library_path_input)
        browse_lib_btn = QPushButton('Browse')
        browse_lib_btn.clicked.connect(self.browse_library)
        path_layout.addWidget(browse_lib_btn)
        config_layout.addRow('Library Root Path:', path_layout)
        
        # Database path
        db_layout = QHBoxLayout()
        self.db_path_input = QLineEdit()
        self.db_path_input.setText('library.db')
        db_layout.addWidget(self.db_path_input)
        browse_db_btn = QPushButton('Browse')
        browse_db_btn.clicked.connect(self.browse_database)
        db_layout.addWidget(browse_db_btn)
        config_layout.addRow('Database Path:', db_layout)
        
        # Options
        self.clear_db_checkbox = QCheckBox('Clear database before scanning')
        config_layout.addRow('', self.clear_db_checkbox)
        
        self.skip_media_checkbox = QCheckBox('Skip MediaInfo (faster on network drives)')
        config_layout.addRow('', self.skip_media_checkbox)
        
        config_group.setLayout(config_layout)
        main_layout.addWidget(config_group)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(0)  # Indeterminate mode
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel('Ready')
        main_layout.addWidget(self.status_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.scan_button = QPushButton('Start Scan')
        self.scan_button.clicked.connect(self.start_scan)
        button_layout.addWidget(self.scan_button)
        
        self.stop_button = QPushButton('Stop Scan')
        self.stop_button.clicked.connect(self.stop_scan)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)
        
        self.export_button = QPushButton('Export Results')
        self.export_button.clicked.connect(self.export_results)
        self.export_button.setEnabled(False)
        button_layout.addWidget(self.export_button)
        
        button_layout.addStretch()
        button_layout.addWidget(QPushButton('Exit', clicked=self.close))
        
        main_layout.addLayout(button_layout)
        
        # Tabs for log and results
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Log tab
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont('Courier', 9))
        self.tabs.addTab(self.log_text, 'Log')
        
        # Results tab
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setFont(QFont('Courier', 9))
        self.tabs.addTab(self.results_text, 'Results')
    
    def browse_library(self):
        """Browse for library directory"""
        directory = QFileDialog.getExistingDirectory(
            self,
            'Select Library Directory',
            self.library_path_input.text()
        )
        if directory:
            self.library_path_input.setText(directory)
    
    def browse_database(self):
        """Browse for database file"""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            'Select Database File',
            self.db_path_input.text(),
            'Database Files (*.db);;All Files (*)'
        )
        if filename:
            self.db_path_input.setText(filename)
    
    def start_scan(self):
        """Start the scan"""
        library_path = self.library_path_input.text().strip()
        db_path = self.db_path_input.text().strip()
        
        if not library_path or not db_path:
            QMessageBox.warning(self, 'Input Error', 'Please specify both library path and database path')
            return
        
        # Clear previous results
        self.log_text.clear()
        self.results_text.clear()
        
        # Log initial messages
        self.add_log('Starting scan...')
        self.add_log(f'Library: {library_path}')
        self.add_log(f'Database: {db_path}')
        if self.clear_db_checkbox.isChecked():
            self.add_log('Database will be cleared')
        if self.skip_media_checkbox.isChecked():
            self.add_log('MediaInfo will be skipped (faster mode)')
        self.add_log('-' * 80)
        
        # Disable controls
        self.scan_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.export_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        
        # Create worker and thread
        self.scan_worker = ScanWorker(
            library_path,
            db_path,
            self.clear_db_checkbox.isChecked(),
            self.skip_media_checkbox.isChecked()
        )
        
        self.scan_thread = QThread()
        self.scan_worker.moveToThread(self.scan_thread)
        
        # Connect signals
        self.scan_thread.started.connect(self.scan_worker.run)
        self.scan_worker.finished.connect(self.on_scan_finished)
        self.scan_worker.log_message.connect(self.add_log)
        self.scan_worker.progress_update.connect(self.update_status)
        self.scan_worker.results_ready.connect(self.show_results)
        self.scan_worker.error.connect(self.show_error)
        
        self.is_scanning = True
        self.scan_thread.start()
    
    def stop_scan(self):
        """Stop the scan"""
        if self.scan_worker:
            self.scan_worker.stop()
            self.add_log('Scan cancelled by user')
        self.is_scanning = False
    
    def on_scan_finished(self):
        """Handle scan completion"""
        if self.scan_thread:
            self.scan_thread.quit()
            self.scan_thread.wait()
        
        self.scan_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.export_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.is_scanning = False
    
    def add_log(self, message):
        """Add a log message with timestamp"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_text.append(f"[{timestamp}] {message}")
    
    def update_status(self, message):
        """Update status label"""
        self.status_label.setText(message)
    
    def show_results(self, results):
        """Display scan results"""
        self.results_text.setText(results)
    
    def show_error(self, error_message):
        """Show error message"""
        QMessageBox.critical(self, 'Scan Error', error_message)
        self.add_log(error_message)
    
    def export_results(self):
        """Export results to file"""
        results = self.results_text.toPlainText()
        if not results.strip():
            QMessageBox.warning(self, 'No Results', 'No results to export')
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            'Save Results As',
            '',
            'Text Files (*.txt);;All Files (*)'
        )
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(results)
                QMessageBox.information(self, 'Success', f'Results saved to {filename}')
            except Exception as e:
                QMessageBox.critical(self, 'Error', f'Error saving file: {str(e)}')


def main():
    """Entry point for GUI"""
    app = QApplication(sys.argv)
    window = ScannerGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
