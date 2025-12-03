#!/usr/bin/env python3
"""
Educational Video Library Scanner - Tkinter GUI
A cross-platform GUI for scanning and managing educational video libraries.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
from pathlib import Path
from datetime import datetime
import sys
import json

from edu_scanner import scan_directory
from database import LibraryDatabase


class ScannerGUI:
    CONFIG_FILE = Path.home() / '.eduscan-gui.config'
    
    def __init__(self, root):
        self.root = root
        self.root.title('Educational Video Library Scanner')
        self.root.geometry('1000x800')
        
        self.db = None
        self.scanning = False
        self.scan_thread = None
        
        # Load config
        self.config = self.load_config()
        
        self.setup_ui()
        
        # Save config on close
        self.root.protocol('WM_DELETE_WINDOW', self.on_close)
    
    def setup_ui(self):
        """Setup the user interface"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding='10')
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights for resizing
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(12, weight=1)
        
        # Create notebook (tabbed interface) for log and results
        self.notebook = ttk.Notebook(main_frame)
        
        # Title
        title_label = ttk.Label(main_frame, text='Educational Video Library Scanner', 
                                font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 10))
        
        # Separator
        separator1 = ttk.Separator(main_frame, orient='horizontal')
        separator1.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Library Path
        ttk.Label(main_frame, text='Library Root Path:').grid(row=2, column=0, sticky=tk.W, padx=(0, 5))
        self.library_path_var = tk.StringVar(value=self.config.get('library_path', '/Volumes/learning'))
        library_entry = ttk.Entry(main_frame, textvariable=self.library_path_var, width=50)
        library_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        ttk.Button(main_frame, text='Browse', command=self.browse_library).grid(row=2, column=2)
        
        # Database Path
        ttk.Label(main_frame, text='Database Path:').grid(row=3, column=0, sticky=tk.W, padx=(0, 5), pady=(10, 0))
        self.db_path_var = tk.StringVar(value=self.config.get('db_path', 'library.db'))
        db_entry = ttk.Entry(main_frame, textvariable=self.db_path_var, width=50)
        db_entry.grid(row=3, column=1, sticky=(tk.W, tk.E), padx=(0, 5), pady=(10, 0))
        ttk.Button(main_frame, text='Browse', command=self.browse_database).grid(row=3, column=2, pady=(10, 0))
        
        # Options
        self.clear_db_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(main_frame, text='Clear database before scanning', 
                       variable=self.clear_db_var).grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))
        
        self.skip_media_info_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(main_frame, text='Skip MediaInfo (faster on network drives)', 
                       variable=self.skip_media_info_var).grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))
        
        # Separator
        separator2 = ttk.Separator(main_frame, orient='horizontal')
        separator2.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 10))
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.scan_button = ttk.Button(button_frame, text='Start Scan', command=self.start_scan)
        self.scan_button.pack(side=tk.LEFT, padx=2)
        
        self.stop_button = ttk.Button(button_frame, text='Stop Scan', command=self.stop_scan, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=2)
        
        self.export_button = ttk.Button(button_frame, text='Export Results', command=self.export_results, state=tk.DISABLED)
        self.export_button.pack(side=tk.LEFT, padx=2)
        
        ttk.Button(button_frame, text='Exit', command=self.root.quit).pack(side=tk.LEFT, padx=2)
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=8, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # Status label
        self.status_var = tk.StringVar(value='Ready')
        status_label = ttk.Label(main_frame, textvariable=self.status_var)
        status_label.grid(row=9, column=0, columnspan=3, sticky=tk.W, pady=(0, 10))
        
        # Separator
        separator3 = ttk.Separator(main_frame, orient='horizontal')
        separator3.grid(row=10, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Output text area with tabs
        self.notebook.grid(row=11, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Log tab
        log_frame = ttk.Frame(self.notebook)
        self.notebook.add(log_frame, text='Log')
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=25, width=120, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.log_text.config(state=tk.DISABLED)
        
        # Results tab
        results_frame = ttk.Frame(self.notebook)
        self.notebook.add(results_frame, text='Results')
        
        self.output_text = scrolledtext.ScrolledText(results_frame, height=25, width=120, wrap=tk.WORD)
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.output_text.config(state=tk.DISABLED)
    
    def browse_library(self):
        """Browse for library directory"""
        initial_dir = self.library_path_var.get() or str(Path.home())
        directory = filedialog.askdirectory(title='Select Library Directory', initialdir=initial_dir)
        if directory:
            self.library_path_var.set(directory)
    
    def load_config(self):
        """Load configuration from file"""
        if self.CONFIG_FILE.exists():
            try:
                with open(self.CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}
    
    def save_config(self):
        """Save configuration to file"""
        config = {
            'library_path': self.library_path_var.get(),
            'db_path': self.db_path_var.get(),
        }
        try:
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save config: {e}", file=sys.stderr)
    
    def on_close(self):
        """Handle window close"""
        self.save_config()
        self.root.destroy()
    
    def browse_database(self):
        """Browse for database file"""
        filename = filedialog.asksaveasfilename(
            title='Select Database File',
            defaultextension='.db',
            filetypes=[('Database files', '*.db'), ('All files', '*.*')]
        )
        if filename:
            self.db_path_var.set(filename)
    
    def start_scan(self):
        """Start the scan in a background thread"""
        library_path = self.library_path_var.get().strip()
        db_path = self.db_path_var.get().strip()
        
        if not library_path or not db_path:
            messagebox.showerror('Input Error', 'Please specify both library path and database path')
            return
        
        # Clear log and results
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete('1.0', tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete('1.0', tk.END)
        self.output_text.config(state=tk.DISABLED)
        
        self.log('Starting scan...')
        self.log(f'Library: {library_path}')
        self.log(f'Database: {db_path}')
        if self.clear_db_var.get():
            self.log('Database will be cleared')
        if self.skip_media_info_var.get():
            self.log('MediaInfo will be skipped (faster mode)')
        self.log('-' * 80)
        
        self.scanning = True
        self.scan_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.export_button.config(state=tk.DISABLED)
        self.progress.start()
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete('1.0', tk.END)
        self.output_text.config(state=tk.DISABLED)
        
        # Start scan in background thread
        self.scan_thread = threading.Thread(
            target=self.run_scan,
            args=(library_path, db_path, self.clear_db_var.get(), self.skip_media_info_var.get()),
            daemon=True
        )
        self.scan_thread.start()
    
    def stop_scan(self):
        """Stop the scan"""
        self.scanning = False
        self.scan_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.progress.stop()
        self.log('Scan cancelled by user')
        self.update_status('Scan cancelled by user')
    
    def run_scan(self, library_path, db_path, clear_db, skip_media_info):
        """Run scan in background"""
        try:
            lib_path = Path(library_path).expanduser().resolve()
            db = LibraryDatabase(Path(db_path))
            
            if clear_db:
                self.log('Clearing database...')
                db.clear_all()
                self.log('Database cleared')
            
            self.log(f'Scanning {lib_path}...')
            self.update_status(f'Scanning {lib_path}...')
            
            # Perform scan
            courses = scan_directory(lib_path, skip_media_info=skip_media_info)
            self.log(f'Found {len(courses)} courses')
            
            if courses:
                self.log(f'Storing in database...')
                db_start = datetime.now()
                for i, course in enumerate(courses, 1):
                    if not self.scanning:
                        self.log('Scan stopped by user')
                        break
                    
                    self.log(f'Processing course {i}/{len(courses)}: {course.name} ({len(course.lessons)} lessons)')
                    
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
                    results += f"{'-' * 80}\n"
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
                
                self.update_output(results)
                self.log('-' * 80)
                self.log(f'Scan complete: {len(courses)} courses, {sum(len(c.lessons) for c in courses)} lessons')
                self.update_status(f'✓ Scan complete: {len(courses)} courses, {sum(len(c.lessons) for c in courses)} lessons')
                self.export_button.config(state=tk.NORMAL)
            else:
                self.update_output("No courses found in the specified directory.")
                self.log('No courses found')
                self.update_status('No courses found')
            
            db.close()
        
        except Exception as e:
            error_msg = f"ERROR: {str(e)}\n\n{type(e).__name__}"
            self.update_output(error_msg)
            self.log(f'ERROR: {str(e)}')
            self.update_status(f'Error: {str(e)}')
        
        finally:
            self.scan_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.progress.stop()
            self.scanning = False
    
    def update_output(self, text):
        """Update output text area safely from thread"""
        self.root.after(0, self._do_update_output, text)
    
    def _do_update_output(self, text):
        """Actually update the output text"""
        self.output_text.config(state=tk.NORMAL)
        self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END)
        self.output_text.config(state=tk.DISABLED)
    
    def update_status(self, text):
        """Update status label safely from thread"""
        self.root.after(0, self.status_var.set, text)
    
    def log(self, message):
        """Add a log message with timestamp"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.root.after(0, self._do_log, f"[{timestamp}] {message}")
    
    def _do_log(self, message):
        """Actually write to log"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + '\n')
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def export_results(self):
        """Export results to file"""
        output = self.output_text.get('1.0', tk.END)
        if not output.strip():
            messagebox.showwarning('No Results', 'No results to export')
            return
        
        filename = filedialog.asksaveasfilename(
            title='Save Results As',
            defaultextension='.txt',
            filetypes=[('Text files', '*.txt'), ('All files', '*.*')]
        )
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(output)
                messagebox.showinfo('Success', f'Results saved to {filename}')
            except Exception as e:
                messagebox.showerror('Error', f'Error saving file: {str(e)}')


def main():
    """Entry point for GUI"""
    root = tk.Tk()
    app = ScannerGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
