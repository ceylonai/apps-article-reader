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

    @property
    def duration(self):
        if self.start_time is None:
            return "Not started"
        if self.end_time is None:
            return "In progress"
        duration = self.end_time - self.start_time
        return f"{duration.seconds} seconds"


class TaskPanel(ttk.Frame):
    def __init__(self, parent, task: URLTask, on_select=None):
        super().__init__(parent)
        self.task = task
        self.on_select = on_select

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

        # Progress bar
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            self, length=200, mode='determinate',
            variable=self.progress_var
        )
        self.progress_bar.grid(row=1, column=0, columnspan=2, padx=5, sticky="ew")

        # Duration label
        self.duration_label = ttk.Label(self, text="Duration: Not started")
        self.duration_label.grid(row=2, column=0, columnspan=2, padx=5, pady=(0, 5), sticky="w")

        # Bind click event
        self.bind('<Button-1>', self.on_click)
        for child in self.winfo_children():
            child.bind('<Button-1>', self.on_click)

        self.update_display()

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

        # Load last used directory
        self.config_file = "content_extractor_config.json"
        self.project_dir = self.load_last_directory()

        # Create main layout
        self.create_layout()

        # Create custom styles
        self.create_styles()

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

    def add_url(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a URL")
            return

        # Create new task
        task = URLTask(url)
        self.tasks[task.id] = task

        # Create and add task panel
        panel = TaskPanel(self.tasks_container, task, on_select=self.select_task)
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
            else:
                task.status = ProcessStatus.ERROR
                task.error = "Failed to extract content"

        except Exception as e:
            task.status = ProcessStatus.ERROR
            task.error = str(e)

        finally:
            task.end_time = datetime.now()
            self.update_task_display(task)

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

    def save_selected(self):
        if not self.selected_task or not self.selected_task.result:
            return

        try:
            # Create project directory if it doesn't exist
            if not os.path.exists(self.project_dir):
                os.makedirs(self.project_dir)

            # Change to project directory before saving
            current_dir = os.getcwd()
            os.chdir(self.project_dir)

            filename = save_to_file(self.selected_task.result, self.selected_task.url)
            messagebox.showinfo("Success", f"Content saved to: {os.path.join(self.project_dir, filename)}")

            # Change back to original directory
            os.chdir(current_dir)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file: {str(e)}")

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