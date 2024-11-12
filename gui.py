import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
from typing import Dict
import threading
from content_extractor import ContentExtractor, save_to_file
import os
import json


class ContentExtractorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Content Extractor")
        self.root.geometry("800x900")

        # Initialize ContentExtractor
        self.extractor = ContentExtractor(model_name="llama3.2")

        # Load last used directory
        self.config_file = "content_extractor_config.json"
        self.project_dir = self.load_last_directory()

        # Create and configure grid
        self.root.grid_columnconfigure(0, weight=1)
        self.create_widgets()

    def load_last_directory(self):
        """Load the last used directory from config file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    return config.get('last_directory', os.getcwd())
        except Exception:
            pass
        return os.getcwd()

    def save_last_directory(self):
        """Save the current directory to config file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump({'last_directory': self.project_dir}, f)
        except Exception:
            pass

    def create_widgets(self):
        # Project Location Frame
        location_frame = ttk.LabelFrame(self.root, text="Project Location", padding="10")
        location_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        location_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(location_frame, text="Save Location:").grid(row=0, column=0, padx=5)
        self.location_entry = ttk.Entry(location_frame)
        self.location_entry.grid(row=0, column=1, sticky="ew", padx=5)
        self.location_entry.insert(0, self.project_dir)

        self.browse_button = ttk.Button(location_frame, text="Browse", command=self.browse_location)
        self.browse_button.grid(row=0, column=2, padx=5)

        # URL Input Frame
        url_frame = ttk.LabelFrame(self.root, text="URL Input", padding="10")
        url_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        url_frame.grid_columnconfigure(0, weight=1)

        self.url_entry = ttk.Entry(url_frame)
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=5)

        self.process_button = ttk.Button(url_frame, text="Process URL", command=self.process_url)
        self.process_button.grid(row=0, column=1, padx=5)

        # Progress Frame
        progress_frame = ttk.Frame(self.root, padding="10")
        progress_frame.grid(row=2, column=0, sticky="ew", padx=10)
        progress_frame.grid_columnconfigure(0, weight=1)

        self.status_label = ttk.Label(progress_frame, text="Status: Ready")
        self.status_label.grid(row=0, column=0, sticky="w")

        self.progress_bar = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.progress_bar.grid(row=1, column=0, sticky="ew", pady=5)

        # Results Frame
        results_frame = ttk.LabelFrame(self.root, text="Results", padding="10")
        results_frame.grid(row=3, column=0, sticky="nsew", padx=10, pady=5)
        results_frame.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(3, weight=1)

        # Title
        ttk.Label(results_frame, text="Title:").grid(row=0, column=0, sticky="w", pady=2)
        self.title_text = scrolledtext.ScrolledText(results_frame, height=2, wrap=tk.WORD)
        self.title_text.grid(row=1, column=0, sticky="ew", pady=2)

        # Keywords
        ttk.Label(results_frame, text="Keywords:").grid(row=2, column=0, sticky="w", pady=2)
        self.keywords_text = scrolledtext.ScrolledText(results_frame, height=2, wrap=tk.WORD)
        self.keywords_text.grid(row=3, column=0, sticky="ew", pady=2)

        # Summary
        ttk.Label(results_frame, text="Summary:").grid(row=4, column=0, sticky="w", pady=2)
        self.summary_text = scrolledtext.ScrolledText(results_frame, height=4, wrap=tk.WORD)
        self.summary_text.grid(row=5, column=0, sticky="ew", pady=2)

        # Hashtags
        ttk.Label(results_frame, text="Hashtags:").grid(row=6, column=0, sticky="w", pady=2)
        self.hashtags_text = scrolledtext.ScrolledText(results_frame, height=2, wrap=tk.WORD)
        self.hashtags_text.grid(row=7, column=0, sticky="ew", pady=2)

        # Full Article
        ttk.Label(results_frame, text="Full Article:").grid(row=8, column=0, sticky="w", pady=2)
        self.article_text = scrolledtext.ScrolledText(results_frame, height=15, wrap=tk.WORD)
        self.article_text.grid(row=9, column=0, sticky="nsew", pady=2)

        # Save Button
        self.save_button = ttk.Button(results_frame, text="Save to File", command=self.save_results)
        self.save_button.grid(row=10, column=0, pady=10)
        self.save_button.state(['disabled'])

        # Make all text widgets read-only initially
        for widget in (self.title_text, self.keywords_text, self.summary_text,
                       self.hashtags_text, self.article_text):
            widget.configure(state='disabled')

    def browse_location(self):
        """Open directory browser and update project location"""
        directory = filedialog.askdirectory(initialdir=self.project_dir)
        if directory:
            self.project_dir = directory
            self.location_entry.delete(0, tk.END)
            self.location_entry.insert(0, directory)
            self.save_last_directory()

    def process_url(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a URL")
            return

        # Update project directory from entry
        self.project_dir = self.location_entry.get().strip()
        if not os.path.exists(self.project_dir):
            try:
                os.makedirs(self.project_dir)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create directory: {str(e)}")
                return

        # Clear previous results
        self.clear_results()

        # Disable process button and show progress
        self.process_button.state(['disabled'])
        self.progress_bar.start()
        self.status_label.configure(text="Status: Processing...")

        # Start processing in a separate thread
        thread = threading.Thread(target=self.process_url_thread, args=(url,))
        thread.daemon = True
        thread.start()

    def process_url_thread(self, url: str):
        try:
            result = self.extractor.process_url(url)
            if result:
                self.root.after(0, self.update_results, result)
            else:
                self.root.after(0, self.show_error, "Failed to extract information from the URL")
        except Exception as e:
            self.root.after(0, self.show_error, f"Error processing URL: {str(e)}")

    def update_results(self, result: Dict):
        # Enable text widgets for updating
        for widget in (self.title_text, self.keywords_text, self.summary_text,
                       self.hashtags_text, self.article_text):
            widget.configure(state='normal')

        # Update text widgets
        self.title_text.delete(1.0, tk.END)
        self.title_text.insert(tk.END, result['title'])

        self.keywords_text.delete(1.0, tk.END)
        self.keywords_text.insert(tk.END, ', '.join(result['keywords']))

        self.summary_text.delete(1.0, tk.END)
        self.summary_text.insert(tk.END, result['content_summary'])

        self.hashtags_text.delete(1.0, tk.END)
        self.hashtags_text.insert(tk.END, ' '.join(result['hashtags']))

        self.article_text.delete(1.0, tk.END)
        self.article_text.insert(tk.END, result['full_article'])

        # Make text widgets read-only again
        for widget in (self.title_text, self.keywords_text, self.summary_text,
                       self.hashtags_text, self.article_text):
            widget.configure(state='disabled')

        # Enable save button
        self.save_button.state(['!disabled'])

        # Reset progress
        self.progress_bar.stop()
        self.process_button.state(['!disabled'])
        self.status_label.configure(text="Status: Complete")

    def show_error(self, message: str):
        messagebox.showerror("Error", message)
        self.progress_bar.stop()
        self.process_button.state(['!disabled'])
        self.status_label.configure(text="Status: Error")

    def clear_results(self):
        for widget in (self.title_text, self.keywords_text, self.summary_text,
                       self.hashtags_text, self.article_text):
            widget.configure(state='normal')
            widget.delete(1.0, tk.END)
            widget.configure(state='disabled')

        self.save_button.state(['disabled'])

    def save_results(self):
        url = self.url_entry.get().strip()
        result = {
            'title': self.title_text.get(1.0, tk.END).strip(),
            'keywords': self.keywords_text.get(1.0, tk.END).strip().split(', '),
            'content_summary': self.summary_text.get(1.0, tk.END).strip(),
            'hashtags': self.hashtags_text.get(1.0, tk.END).strip().split(),
            'full_article': self.article_text.get(1.0, tk.END).strip()
        }

        try:
            # Change to project directory before saving
            current_dir = os.getcwd()
            os.chdir(self.project_dir)

            filename = save_to_file(result, url)
            messagebox.showinfo("Success", f"Content saved to: {os.path.join(self.project_dir, filename)}")

            # Change back to original directory
            os.chdir(current_dir)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file: {str(e)}")


def main():
    root = tk.Tk()
    app = ContentExtractorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()