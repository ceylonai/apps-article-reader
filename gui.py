import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
from typing import Dict, List
import threading
from queue import Queue
from content_extractor import ContentExtractor, save_to_file
import os
import json
from datetime import datetime
from enum import Enum
import uuid


class ProcessStatus(Enum):
    QUEUED = "Queued"
    PROCESSING = "Processing"
    COMPLETED = "Completed"
    ERROR = "Error"


class URLTask:
    def __init__(self, url: str):
        self.id = str(uuid.uuid4())
        self.url = url
        self.status = ProcessStatus.QUEUED
        self.progress = 0
        self.error = None
        self.result = None
        self.start_time = None
        self.end_time = None
        self.saved_path = None

    @property
    def duration(self):
        if self.start_time is None:
            return "Not started"
        if self.end_time is None:
            return "In progress"
        duration = self.end_time - self.start_time
        return f"{duration.seconds} seconds"


class TaskPanel(ttk.Frame):
    def __init__(self, parent, task: URLTask, on_select=None, on_restart=None):
        super().__init__(parent)
        self.task = task
        self.on_select = on_select
        self.on_restart = on_restart

        self.selected = False
        self.configure(relief="raised", borderwidth=1)

        # Grid configuration
        self.grid_columnconfigure(1, weight=1)

        # Status indicator
        self.status_label = ttk.Label(self, width=10)
        self.status_label.grid(row=0, column=0, padx=(5, 0), pady=5)

        # URL display
        url_display = ttk.Label(self, text=task.url, wraplength=300)
        url_display.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # Restart button
        self.restart_button = ttk.Button(
            self,
            text="↻",
            width=3,
            command=self._handle_restart
        )
        self.restart_button.grid(row=0, column=2, padx=5, pady=5)

        # Progress bar
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            self, length=200, mode='determinate',
            variable=self.progress_var
        )
        self.progress_bar.grid(row=1, column=0, columnspan=3, padx=5, sticky="ew")

        # Status info (Duration and Save Path)
        self.info_frame = ttk.Frame(self)
        self.info_frame.grid(row=2, column=0, columnspan=3, padx=5, pady=(0, 5), sticky="ew")

        self.duration_label = ttk.Label(self.info_frame, text="Duration: Not started")
        self.duration_label.pack(side="left", padx=5)

        self.save_path_label = ttk.Label(self.info_frame, text="")
        self.save_path_label.pack(side="right", padx=5)

        # Bind click event
        self.bind('<Button-1>', self.on_click)
        for child in self.winfo_children():
            if child != self.restart_button:  # Don't bind click event to restart button
                child.bind('<Button-1>', self.on_click)

        self.update_display()

    def _handle_restart(self):
        """Handle restart button click"""
        if self.on_restart:
            self.on_restart(self.task)

    def update_display(self):
        # Update status
        self.status_label.configure(
            text=self.task.status.value,
            foreground=self.get_status_color()
        )

        # Update progress
        self.progress_var.set(self.task.progress)

        # Update duration
        self.duration_label.configure(text=f"Duration: {self.task.duration}")

        # Update save path if available
        if self.task.saved_path:
            self.save_path_label.configure(
                text=f"Saved: {os.path.basename(self.task.saved_path)}"
            )
        else:
            self.save_path_label.configure(text="")

        # Update restart button state
        if self.task.status in [ProcessStatus.COMPLETED, ProcessStatus.ERROR]:
            self.restart_button.state(['!disabled'])
        else:
            self.restart_button.state(['disabled'])

        # Update panel style based on selection
        if self.selected:
            self.configure(style='Selected.TFrame')
        else:
            self.configure(style='TFrame')

    def get_status_color(self):
        status_colors = {
            ProcessStatus.QUEUED: "gray",
            ProcessStatus.PROCESSING: "blue",
            ProcessStatus.COMPLETED: "green",
            ProcessStatus.ERROR: "red"
        }
        return status_colors.get(self.task.status, "black")

    def on_click(self, event):
        if self.on_select:
            self.on_select(self.task)


class ContentExtractorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Content Extractor Dashboard")
        self.root.geometry("1200x800")

        # Initialize ContentExtractor
        self.extractor = ContentExtractor(model_name="llama3.2")

        # Task management
        self.tasks: Dict[str, URLTask] = {}
        self.selected_task = None

        # Thread management
        self.max_threads = 3
        self.active_threads = 0
        self.task_queue = Queue()
        self.process_queue_thread = threading.Thread(target=self.process_queue, daemon=True)
        self.process_queue_thread.start()

        # Load configuration
        self.config_file = "content_extractor_config.json"
        self.load_config()

        # Create main layout
        self.create_layout()

        # Create custom styles
        self.create_styles()

    def load_config(self):
        """Load configuration from file"""
        self.config = {
            'project_dir': os.getcwd(),
            'auto_save': True
        }

        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    saved_config = json.load(f)
                    self.config.update(saved_config)
        except Exception as e:
            print(f"Error loading config: {e}")

    def save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f)
        except Exception as e:
            print(f"Error saving config: {e}")

    def create_styles(self):
        style = ttk.Style()
        style.configure('Selected.TFrame', background='lightblue')

    def create_layout(self):
        # Main container
        main_container = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left panel (Task Management)
        left_panel = ttk.Frame(main_container)
        main_container.add(left_panel, weight=40)

        # Right panel (Results View)
        right_panel = ttk.Frame(main_container)
        main_container.add(right_panel, weight=60)

        self.create_left_panel(left_panel)
        self.create_right_panel(right_panel)

    def create_left_panel(self, parent):
        # Settings Frame
        settings_frame = ttk.LabelFrame(parent, text="Settings", padding="5")
        settings_frame.pack(fill=tk.X, padx=5, pady=5)

        # Project Directory Selection
        dir_frame = ttk.Frame(settings_frame)
        dir_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(dir_frame, text="Project Directory:").pack(side=tk.LEFT, padx=(0, 5))

        self.dir_var = tk.StringVar(value=self.config['project_dir'])
        dir_entry = ttk.Entry(dir_frame, textvariable=self.dir_var, state='readonly')
        dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        dir_button = ttk.Button(dir_frame, text="Browse", command=self.select_project_dir)
        dir_button.pack(side=tk.RIGHT)

        # Auto-save Option
        auto_save_frame = ttk.Frame(settings_frame)
        auto_save_frame.pack(fill=tk.X, padx=5, pady=5)

        self.auto_save_var = tk.BooleanVar(value=self.config['auto_save'])
        auto_save_cb = ttk.Checkbutton(
            auto_save_frame,
            text="Auto-save articles after processing",
            variable=self.auto_save_var,
            command=self.update_auto_save
        )
        auto_save_cb.pack(side=tk.LEFT)

        # URL Input
        input_frame = ttk.LabelFrame(parent, text="Add New Task", padding="5")
        input_frame.pack(fill=tk.X, padx=5, pady=5)

        self.url_entry = ttk.Entry(input_frame)
        self.url_entry.pack(fill=tk.X, padx=5, pady=5)

        add_button = ttk.Button(input_frame, text="Add URL", command=self.add_url)
        add_button.pack(pady=5)

        # Tasks List
        tasks_frame = ttk.LabelFrame(parent, text="Tasks", padding="5")
        tasks_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Scrollable container for tasks
        self.tasks_canvas = tk.Canvas(tasks_frame)
        scrollbar = ttk.Scrollbar(tasks_frame, orient="vertical", command=self.tasks_canvas.yview)
        self.tasks_container = ttk.Frame(self.tasks_canvas)

        self.tasks_container.bind(
            "<Configure>",
            lambda e: self.tasks_canvas.configure(scrollregion=self.tasks_canvas.bbox("all"))
        )

        self.tasks_canvas.create_window((0, 0), window=self.tasks_container, anchor="nw")
        self.tasks_canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.tasks_canvas.pack(side="left", fill="both", expand=True)

    def select_project_dir(self):
        """Open directory selection dialog"""
        dir_path = filedialog.askdirectory(
            initialdir=self.config['project_dir'],
            title="Select Project Directory"
        )
        if dir_path:
            self.config['project_dir'] = dir_path
            self.dir_var.set(dir_path)
            self.save_config()

    def update_auto_save(self):
        """Update auto-save configuration"""
        self.config['auto_save'] = self.auto_save_var.get()
        self.save_config()

    def process_task(self, task: URLTask):
        try:
            # Update status to processing
            task.status = ProcessStatus.PROCESSING
            task.start_time = datetime.now()
            self.update_task_display(task)

            # Process URL
            result = self.extractor.process_url(task.url)

            if result:
                task.result = result
                task.status = ProcessStatus.COMPLETED

                # Auto-save if enabled
                if self.config['auto_save']:
                    try:
                        # Ensure project directory exists
                        os.makedirs(self.config['project_dir'], exist_ok=True)

                        # Save the file
                        filename = save_to_file(result, task.url)
                        task.saved_path = os.path.join(self.config['project_dir'], filename)
                    except Exception as e:
                        print(f"Error auto-saving: {e}")
            else:
                task.status = ProcessStatus.ERROR
                task.error = "Failed to extract content"

        except Exception as e:
            task.status = ProcessStatus.ERROR
            task.error = str(e)

        finally:
            task.end_time = datetime.now()
            self.update_task_display(task)

    def save_selected(self):
        if not self.selected_task or not self.selected_task.result:
            return

        try:
            # Create project directory if it doesn't exist
            os.makedirs(self.config['project_dir'], exist_ok=True)

            # Save the file
            filename = save_to_file(self.selected_task.result, self.selected_task.url)
            full_path = os.path.join(self.config['project_dir'], filename)

            self.selected_task.saved_path = full_path
            self.update_task_display(self.selected_task)

            messagebox.showinfo("Success", f"Content saved to: {full_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file: {str(e)}")

    def update_display(self):
        # Update status
        self.status_label.configure(
            text=self.task.status.value,
            foreground=self.get_status_color()
        )

        # Update progress
        self.progress_var.set(self.task.progress)

        # Update duration
        self.duration_label.configure(text=f"Duration: {self.task.duration}")

        # Update panel style based on selection
        if self.selected:
            self.configure(style='Selected.TFrame')
        else:
            self.configure(style='TFrame')

    def get_status_color(self):
        status_colors = {
            ProcessStatus.QUEUED: "gray",
            ProcessStatus.PROCESSING: "blue",
            ProcessStatus.COMPLETED: "green",
            ProcessStatus.ERROR: "red"
        }
        return status_colors.get(self.task.status, "black")

    def on_click(self, event):
        if self.on_select:
            self.on_select(self.task)

    def create_right_panel(self, parent):
        # Result view
        self.result_frame = ttk.LabelFrame(parent, text="Results", padding="10")
        self.result_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.result_frame.grid_columnconfigure(0, weight=1)

        # Title
        ttk.Label(self.result_frame, text="Title:").grid(row=0, column=0, sticky="w", pady=2)
        self.title_text = scrolledtext.ScrolledText(self.result_frame, height=2, wrap=tk.WORD)
        self.title_text.grid(row=1, column=0, sticky="ew", pady=2)

        # Keywords
        ttk.Label(self.result_frame, text="Keywords:").grid(row=2, column=0, sticky="w", pady=2)
        self.keywords_text = scrolledtext.ScrolledText(self.result_frame, height=2, wrap=tk.WORD)
        self.keywords_text.grid(row=3, column=0, sticky="ew", pady=2)

        # Summary
        ttk.Label(self.result_frame, text="Summary:").grid(row=4, column=0, sticky="w", pady=2)
        self.summary_text = scrolledtext.ScrolledText(self.result_frame, height=4, wrap=tk.WORD)
        self.summary_text.grid(row=5, column=0, sticky="ew", pady=2)

        # Hashtags
        ttk.Label(self.result_frame, text="Hashtags:").grid(row=6, column=0, sticky="w", pady=2)
        self.hashtags_text = scrolledtext.ScrolledText(self.result_frame, height=2, wrap=tk.WORD)
        self.hashtags_text.grid(row=7, column=0, sticky="ew", pady=2)

        # Full Article
        ttk.Label(self.result_frame, text="Full Article:").grid(row=8, column=0, sticky="w", pady=2)
        self.article_text = scrolledtext.ScrolledText(self.result_frame, height=15, wrap=tk.WORD)
        self.article_text.grid(row=9, column=0, sticky="ew", pady=2)

        # Save button
        self.save_button = ttk.Button(self.result_frame, text="Save Result", command=self.save_selected)
        self.save_button.grid(row=10, column=0, pady=10)
        self.save_button.state(['disabled'])

        # Make all text widgets read-only
        for widget in (self.title_text, self.keywords_text, self.summary_text,
                       self.hashtags_text, self.article_text):
            widget.configure(state='disabled')

    def restart_task(self, task: URLTask):
        """Restart a completed or failed task"""
        # Reset task status
        task.status = ProcessStatus.QUEUED
        task.progress = 0
        task.error = None
        task.result = None
        task.start_time = None
        task.end_time = None
        task.saved_path = None

        # Update display
        self.update_task_display(task)

        # Add back to processing queue
        self.task_queue.put(task)

    def add_url(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a URL")
            return

        # Create new task
        task = URLTask(url)
        self.tasks[task.id] = task

        # Create and add task panel
        panel = TaskPanel(
            self.tasks_container,
            task,
            on_select=self.select_task,
            on_restart=self.restart_task  # Add restart callback
        )
        panel.pack(fill=tk.X, padx=5, pady=2)

        # Add to processing queue
        self.task_queue.put(task)

        # Clear entry
        self.url_entry.delete(0, tk.END)

    def process_queue(self):
        while True:
            # Wait for task from queue
            task = self.task_queue.get()

            # Start processing thread
            thread = threading.Thread(
                target=self.process_task,
                args=(task,),
                daemon=True
            )
            thread.start()

            # Wait for next task
            self.task_queue.task_done()

    def update_task_display(self, task: URLTask = None):
        """Update all task panels or a specific task panel if task is provided"""
        self.root.after(0, self._do_update_task_display, task)

    def _do_update_task_display(self, task: URLTask = None):
        """Actually perform the update on the main thread"""
        for child in self.tasks_container.winfo_children():
            if isinstance(child, TaskPanel):
                if task is None or child.task.id == task.id:
                    child.update_display()

    def select_task(self, task: URLTask):
        # Deselect previous selection
        for child in self.tasks_container.winfo_children():
            if isinstance(child, TaskPanel):
                child.selected = (child.task.id == task.id)
                child.update_display()

        self.selected_task = task
        self.update_result_view()

    def update_result_view(self):
        # Enable text widgets for updating
        for widget in (self.title_text, self.keywords_text, self.summary_text,
                       self.hashtags_text, self.article_text):
            widget.configure(state='normal')
            widget.delete(1.0, tk.END)

        if self.selected_task and self.selected_task.result:
            result = self.selected_task.result

            self.title_text.insert(tk.END, result['title'])
            self.keywords_text.insert(tk.END, ', '.join(result['keywords']))
            self.summary_text.insert(tk.END, result['content_summary'])
            self.hashtags_text.insert(tk.END, ' '.join(result['hashtags']))
            self.article_text.insert(tk.END, result['full_article'])

            self.save_button.state(['!disabled'])
        else:
            self.save_button.state(['disabled'])

        # Make text widgets read-only again
        for widget in (self.title_text, self.keywords_text, self.summary_text,
                       self.hashtags_text, self.article_text):
            widget.configure(state='disabled')

    def load_last_directory(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    return config.get('last_directory', os.getcwd())
        except Exception:
            pass
        return os.getcwd()


def main():
    root = tk.Tk()
    app = ContentExtractorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
