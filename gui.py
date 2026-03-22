import os
import time
import random
import threading
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageEnhance
import cv2
import numpy as np

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "config")
SLIDESHOW_CONFIG_FILE = os.path.join(CONFIG_DIR, "slideshow_config.json")
SLOW_PAN_CONFIG_FILE = os.path.join(CONFIG_DIR, "slow_pan_config.json")
COLLAGE_CONFIG_FILE = os.path.join(CONFIG_DIR, "collage_config.json")
from cli import (
    mp4_to_webm, webm_to_mp4, mkv_to_mp4, convert_mp4_to_gif, mp4_to_mp3,
    crop_video, get_subclip, speed_up_mp4_video, blur_video,
    stretch_video_dims, get_vid_dims, mute_video, get_video_duration,
    adjust_brightness_video, create_slideshow, slow_pan_video, create_collage_video
)


class VideoEditorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Editor")
        self.root.state('zoomed')

        # Define pastel colors for tabs
        self.pastel_colors = [
            '#FF9999',  # Pastel pink
            '#99CFFF',  # Pastel blue
            '#99FF99',  # Pastel green
            '#FFD699',  # Pastel orange
            '#D699FF',  # Pastel purple
            '#FFFF99',  # Pastel yellow
            '#FF99D6'   # Pastel magenta
        ]

        # Create custom notebook with colored tabs
        self.main_container = tk.Frame(root)
        self.main_container.pack(fill='both', expand=True, padx=10, pady=10)

        # Tab bar frame
        self.tab_bar = tk.Frame(self.main_container, bg='#f0f0f0', height=50)
        self.tab_bar.pack(fill='x', side='top')

        # Content frame
        self.content_frame = tk.Frame(self.main_container, bg='white')
        self.content_frame.pack(fill='both', expand=True, side='top')

        self.tabs = []
        self.tab_buttons = []
        self.current_tab_index = 0

        self.create_format_conversion_tab()
        self.create_crop_tab()
        self.create_trim_tab()
        self.create_speed_tab()
        self.create_blur_tab()
        self.create_resize_tab()
        self.create_audio_tab()
        self.create_brightness_tab()
        self.create_slideshow_tab()
        self.create_bulk_crop_images_tab()
        self.create_slow_pan_tab()
        self.create_collage_tab()

        # Show first tab by default
        self.show_tab(0)

    def darken_color(self, hex_color, factor=0.15):
        """Darken a hex color by a given factor (0-1)"""
        # Remove the '#' if present
        hex_color = hex_color.lstrip('#')

        # Convert to RGB
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)

        # Darken by reducing each component
        r = int(r * (1 - factor))
        g = int(g * (1 - factor))
        b = int(b * (1 - factor))

        # Convert back to hex
        return f'#{r:02x}{g:02x}{b:02x}'

    def add_tab(self, content_widget, title):
        """Add a new tab with custom color"""
        tab_index = len(self.tabs)
        color = self.pastel_colors[tab_index % len(self.pastel_colors)]
        darker_color = self.darken_color(color, 0.15)

        # Create tab button
        tab_btn = tk.Button(
            self.tab_bar,
            text=title,
            font=('Arial', 9),
            bg=color,
            activebackground=darker_color,
            relief='flat',
            padx=12,
            pady=6,
            command=lambda idx=tab_index: self.show_tab(idx)
        )
        tab_btn.pack(side='left', padx=2)

        self.tab_buttons.append(tab_btn)
        self.tabs.append(content_widget)

    def show_tab(self, index):
        """Show the selected tab"""
        # Hide all tabs
        for tab in self.tabs:
            tab.pack_forget()

        # Update button colors
        for i, btn in enumerate(self.tab_buttons):
            color = self.pastel_colors[i % len(self.pastel_colors)]
            if i == index:
                darker_color = self.darken_color(color, 0.15)
                btn.config(bg=darker_color, relief='sunken')
            else:
                btn.config(bg=color, relief='flat')

        # Show selected tab
        self.tabs[index].pack(fill='both', expand=True)
        self.current_tab_index = index

    def create_format_conversion_tab(self):
        tab = tk.Frame(self.content_frame, bg='white')
        self.add_tab(tab, "Format Conversion")

        # File selection frame
        file_frame = ttk.LabelFrame(tab, text="Input Videos (batch conversion)")
        file_frame.grid(row=0, column=0, columnspan=3, padx=10, pady=10, sticky='nsew')

        # Listbox for selected files
        list_frame = ttk.Frame(file_frame)
        list_frame.pack(fill='both', expand=True, padx=5, pady=5)

        self.format_file_listbox = tk.Listbox(list_frame, height=6, selectmode=tk.EXTENDED)
        self.format_file_listbox.pack(side='left', fill='both', expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.format_file_listbox.yview)
        scrollbar.pack(side='right', fill='y')
        self.format_file_listbox.config(yscrollcommand=scrollbar.set)

        # Buttons for file management
        btn_frame = ttk.Frame(file_frame)
        btn_frame.pack(fill='x', padx=5, pady=5)

        ttk.Button(btn_frame, text="Add Files", command=self.browse_format_input).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Remove Selected", command=self.remove_format_files).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Clear All", command=self.clear_format_files).pack(side='left', padx=5)

        self.format_file_count = tk.StringVar(value="0 files selected")
        ttk.Label(btn_frame, textvariable=self.format_file_count).pack(side='right', padx=10)

        # Store the list of file paths
        self.format_input_files = []

        ttk.Label(tab, text="Output Format:").grid(row=1, column=0, padx=10, pady=10, sticky='w')
        self.format_output_type = tk.StringVar(value="MP4")
        format_combo = ttk.Combobox(tab, textvariable=self.format_output_type,
                                    values=["WEBM", "MP4", "GIF", "MP3"], state='readonly')
        format_combo.grid(row=1, column=1, padx=10, pady=10, sticky='w')
        format_combo.bind('<<ComboboxSelected>>', self.on_format_change)

        self.format_options_frame = ttk.LabelFrame(tab, text="Conversion Options")
        self.format_options_frame.grid(row=2, column=0, columnspan=3, padx=10, pady=10, sticky='ew')

        # Initialize variables for all format options
        self.webm_crf_var = tk.IntVar(value=32)
        self.use_opus_var = tk.BooleanVar(value=True)
        self.mp4_crf_var = tk.IntVar(value=20)
        self.mp4_preset_var = tk.StringVar(value="medium")

        # Show MP4 options by default
        ttk.Label(self.format_options_frame, text="CRF Quality (lower = better):").grid(row=0, column=0, padx=10, pady=5, sticky='w')
        ttk.Scale(self.format_options_frame, from_=0, to=51, variable=self.mp4_crf_var, orient='horizontal').grid(row=0, column=1, padx=10, pady=5, sticky='ew')
        ttk.Label(self.format_options_frame, textvariable=self.mp4_crf_var).grid(row=0, column=2, padx=10, pady=5)

        ttk.Label(self.format_options_frame, text="Preset:").grid(row=1, column=0, padx=10, pady=5, sticky='w')
        ttk.Combobox(self.format_options_frame, textvariable=self.mp4_preset_var,
                    values=["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"],
                    state='readonly').grid(row=1, column=1, padx=10, pady=5, sticky='w')

        ttk.Button(tab, text="Convert All", command=self.convert_format).grid(row=3, column=0, columnspan=3, pady=20)

        self.format_progress = ttk.Progressbar(tab, mode='determinate')
        self.format_progress.grid(row=4, column=0, columnspan=3, padx=10, pady=10, sticky='ew')

        self.format_status = tk.StringVar(value="Ready")
        ttk.Label(tab, textvariable=self.format_status).grid(row=5, column=0, columnspan=3, pady=5)

    def on_format_change(self, event=None):
        for widget in self.format_options_frame.winfo_children():
            widget.destroy()

        format_type = self.format_output_type.get()

        if format_type == "WEBM":
            ttk.Label(self.format_options_frame, text="CRF Quality (lower = better):").grid(row=0, column=0, padx=10, pady=5, sticky='w')
            ttk.Scale(self.format_options_frame, from_=0, to=51, variable=self.webm_crf_var, orient='horizontal').grid(row=0, column=1, padx=10, pady=5, sticky='ew')
            ttk.Label(self.format_options_frame, textvariable=self.webm_crf_var).grid(row=0, column=2, padx=10, pady=5)
            ttk.Checkbutton(self.format_options_frame, text="Use Opus codec (better quality)",
                           variable=self.use_opus_var).grid(row=1, column=0, columnspan=3, padx=10, pady=5, sticky='w')

        elif format_type == "MP4":
            ttk.Label(self.format_options_frame, text="CRF Quality (lower = better):").grid(row=0, column=0, padx=10, pady=5, sticky='w')
            ttk.Scale(self.format_options_frame, from_=0, to=51, variable=self.mp4_crf_var, orient='horizontal').grid(row=0, column=1, padx=10, pady=5, sticky='ew')
            ttk.Label(self.format_options_frame, textvariable=self.mp4_crf_var).grid(row=0, column=2, padx=10, pady=5)

            ttk.Label(self.format_options_frame, text="Preset:").grid(row=1, column=0, padx=10, pady=5, sticky='w')
            ttk.Combobox(self.format_options_frame, textvariable=self.mp4_preset_var,
                        values=["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"],
                        state='readonly').grid(row=1, column=1, padx=10, pady=5, sticky='w')

        elif format_type == "GIF":
            ttk.Label(self.format_options_frame, text="No additional options for GIF conversion").grid(row=0, column=0, padx=10, pady=5)

        elif format_type == "MP3":
            ttk.Label(self.format_options_frame, text="Audio will be extracted to MP3 format").grid(row=0, column=0, padx=10, pady=5)

    def browse_format_input(self):
        filenames = filedialog.askopenfilenames(
            title="Select Video Files",
            filetypes=[("Video files", "*.mp4 *.webm *.mkv *.avi *.mov"), ("All files", "*.*")]
        )
        if filenames:
            # Check if all files have the same extension
            extensions = set(os.path.splitext(f)[1].lower() for f in filenames)

            if self.format_input_files:
                # Check against existing files
                existing_ext = os.path.splitext(self.format_input_files[0])[1].lower()
                if len(extensions) > 1 or (len(extensions) == 1 and list(extensions)[0] != existing_ext):
                    messagebox.showerror("Error", "All input files must have the same format/extension")
                    return
            elif len(extensions) > 1:
                messagebox.showerror("Error", "All input files must have the same format/extension")
                return

            # Add new files (avoid duplicates)
            for f in filenames:
                if f not in self.format_input_files:
                    self.format_input_files.append(f)
                    self.format_file_listbox.insert(tk.END, os.path.basename(f))

            self.format_file_count.set(f"{len(self.format_input_files)} file(s) selected")

    def remove_format_files(self):
        selected = list(self.format_file_listbox.curselection())
        for idx in reversed(selected):
            self.format_file_listbox.delete(idx)
            del self.format_input_files[idx]
        self.format_file_count.set(f"{len(self.format_input_files)} file(s) selected")

    def clear_format_files(self):
        self.format_file_listbox.delete(0, tk.END)
        self.format_input_files = []
        self.format_file_count.set("0 files selected")

    def convert_format(self):
        if not self.format_input_files:
            messagebox.showerror("Error", "Please select at least one input video")
            return

        # Validate all files exist
        for f in self.format_input_files:
            if not os.path.exists(f):
                messagebox.showerror("Error", f"File not found: {f}")
                return

        def convert_thread():
            try:
                total = len(self.format_input_files)
                format_type = self.format_output_type.get()
                successful = []
                failed = []

                self.format_progress['maximum'] = total
                self.format_progress['value'] = 0

                for i, input_path in enumerate(self.format_input_files):
                    self.format_status.set(f"Converting {i+1}/{total}: {os.path.basename(input_path)}")

                    try:
                        if format_type == "WEBM":
                            output = mp4_to_webm(input_path, crf=self.webm_crf_var.get(), use_opus=self.use_opus_var.get())
                        elif format_type == "MP4":
                            if input_path.lower().endswith('.mkv'):
                                output = mkv_to_mp4(input_path, crf=self.mp4_crf_var.get(), preset=self.mp4_preset_var.get())
                            else:
                                output = webm_to_mp4(input_path, crf=self.mp4_crf_var.get(), preset=self.mp4_preset_var.get())
                        elif format_type == "GIF":
                            output = convert_mp4_to_gif(input_path)
                        elif format_type == "MP3":
                            output = mp4_to_mp3(input_path)
                        successful.append(output)
                    except Exception as e:
                        failed.append((input_path, str(e)))

                    self.format_progress['value'] = i + 1

                self.format_progress['value'] = total

                if failed:
                    self.format_status.set(f"Done with errors: {len(successful)} succeeded, {len(failed)} failed")
                    error_details = "\n".join([f"{os.path.basename(f)}: {e}" for f, e in failed])
                    messagebox.showwarning("Partial Success",
                                          f"Converted {len(successful)}/{total} files.\n\nFailed:\n{error_details}")
                else:
                    self.format_status.set(f"Done! Converted {total} file(s)")
                    messagebox.showinfo("Success", f"Batch conversion complete!\n{total} file(s) converted.")

            except Exception as e:
                self.format_progress['value'] = 0
                self.format_status.set("Error occurred")
                messagebox.showerror("Error", f"Conversion failed: {str(e)}")

        threading.Thread(target=convert_thread, daemon=True).start()

    def create_crop_tab(self):
        tab = tk.Frame(self.content_frame, bg='white')
        self.add_tab(tab, "Crop Video")

        # Initialize crop job queue
        self.crop_jobs = []
        self.crop_job_id = 0

        # Top section - file selection
        top_frame = ttk.Frame(tab)
        top_frame.pack(fill='x', padx=10, pady=10)

        ttk.Label(top_frame, text="Input Video:").pack(side='left', padx=5)
        self.crop_input_path = tk.StringVar()
        ttk.Entry(top_frame, textvariable=self.crop_input_path, width=50).pack(side='left', padx=5)
        ttk.Button(top_frame, text="Browse", command=self.browse_crop_input).pack(side='left', padx=5)
        ttk.Button(top_frame, text="Load Preview", command=self.load_crop_preview).pack(side='left', padx=5)

        # Main content frame
        content_frame = ttk.Frame(tab)
        content_frame.pack(fill='both', expand=True, padx=10, pady=5)

        # Left side - preview and controls
        left_frame = ttk.Frame(content_frame)
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))

        self.crop_canvas_frame = ttk.Frame(left_frame)
        self.crop_canvas_frame.pack(pady=5)

        self.crop_canvas = tk.Canvas(self.crop_canvas_frame, width=1088, height=612, bg='gray')
        self.crop_canvas.pack()

        self.crop_rect = None
        self.crop_start_x = None
        self.crop_start_y = None
        self.crop_image = None
        self.crop_photo = None
        self.crop_scale_factor = 1.0

        self.crop_canvas.bind("<ButtonPress-1>", self.on_crop_press)
        self.crop_canvas.bind("<B1-Motion>", self.on_crop_drag)
        self.crop_canvas.bind("<ButtonRelease-1>", self.on_crop_release)

        controls_frame = ttk.Frame(left_frame)
        controls_frame.pack(fill='x', pady=10)

        ttk.Label(controls_frame, text="Crop Region:").pack(side='left', padx=5)
        self.crop_coords = tk.StringVar(value="Not selected")
        ttk.Label(controls_frame, textvariable=self.crop_coords).pack(side='left', padx=5)

        ttk.Button(controls_frame, text="Add to Queue", command=self.add_crop_to_queue).pack(side='left', padx=20)

        self.crop_status = tk.StringVar(value="Ready - Load a video and select crop region")
        ttk.Label(left_frame, textvariable=self.crop_status).pack(pady=5)

        # Right side - Job Queue
        queue_frame = ttk.LabelFrame(content_frame, text="Processing Queue")
        queue_frame.pack(side='right', fill='both', expand=False)

        self.crop_queue_listbox = tk.Listbox(queue_frame, width=40, height=12, font=('Consolas', 9))
        self.crop_queue_listbox.pack(fill='both', expand=True, padx=5, pady=5)

        queue_btn_frame = ttk.Frame(queue_frame)
        queue_btn_frame.pack(fill='x', padx=5, pady=5)

        ttk.Button(queue_btn_frame, text="Clear Completed", command=self.clear_completed_crop_jobs).pack(side='left', padx=2)

        self.crop_queue_status = tk.StringVar(value="Queue: 0 jobs")
        ttk.Label(queue_frame, textvariable=self.crop_queue_status).pack(pady=5)

    def browse_crop_input(self):
        filename = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[("Video files", "*.mp4 *.webm *.avi *.mov"), ("All files", "*.*")]
        )
        if filename:
            self.crop_input_path.set(filename)

    def load_crop_preview(self):
        input_path = self.crop_input_path.get()
        if not input_path or not os.path.exists(input_path):
            messagebox.showerror("Error", "Please select a valid input video")
            return

        cap = cv2.VideoCapture(input_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if total_frames <= 0:
            messagebox.showerror("Error", "Could not read video frames")
            cap.release()
            return

        # Pick a random frame
        random_frame_idx = random.randint(0, total_frames - 1)
        cap.set(cv2.CAP_PROP_POS_FRAMES, random_frame_idx)
        ret, frame = cap.read()
        cap.release()

        if not ret:
            messagebox.showerror("Error", "Could not read video frame")
            return

        self.crop_original_frame = frame
        original_height, original_width = frame.shape[:2]

        max_width = 1088
        max_height = 612

        width_scale = max_width / original_width
        height_scale = max_height / original_height
        self.crop_scale_factor = min(width_scale, height_scale, 1.0)

        if self.crop_scale_factor < 1.0:
            display_width = int(original_width * self.crop_scale_factor)
            display_height = int(original_height * self.crop_scale_factor)
            frame = cv2.resize(frame, (display_width, display_height))

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.crop_image = Image.fromarray(frame_rgb)
        self.crop_photo = ImageTk.PhotoImage(self.crop_image)

        self.crop_canvas.config(width=self.crop_image.width, height=self.crop_image.height)
        self.crop_canvas.create_image(0, 0, anchor='nw', image=self.crop_photo)

        self.crop_status.set(f"Frame {random_frame_idx + 1}/{total_frames} loaded. Click and drag to select crop region.")

    def on_crop_press(self, event):
        self.crop_start_x = event.x
        self.crop_start_y = event.y
        if self.crop_rect:
            self.crop_canvas.delete(self.crop_rect)
        self.crop_rect = self.crop_canvas.create_rectangle(
            self.crop_start_x, self.crop_start_y, self.crop_start_x, self.crop_start_y,
            outline='red', width=2
        )

    def on_crop_drag(self, event):
        if self.crop_rect:
            self.crop_canvas.coords(self.crop_rect, self.crop_start_x, self.crop_start_y, event.x, event.y)

    def on_crop_release(self, event):
        if self.crop_start_x is None or self.crop_start_y is None:
            return

        x1 = min(self.crop_start_x, event.x)
        y1 = min(self.crop_start_y, event.y)
        x2 = max(self.crop_start_x, event.x)
        y2 = max(self.crop_start_y, event.y)

        orig_x1 = int(x1 / self.crop_scale_factor)
        orig_y1 = int(y1 / self.crop_scale_factor)
        orig_x2 = int(x2 / self.crop_scale_factor)
        orig_y2 = int(y2 / self.crop_scale_factor)

        self.crop_box = (orig_x1, orig_y1, orig_x2, orig_y2)
        self.crop_coords.set(f"({orig_x1}, {orig_y1}, {orig_x2}, {orig_y2})")

    def add_crop_to_queue(self):
        if not hasattr(self, 'crop_box'):
            messagebox.showerror("Error", "Please select a crop region first")
            return

        input_path = self.crop_input_path.get()
        if not input_path or not os.path.exists(input_path):
            messagebox.showerror("Error", "Please select a valid input video")
            return

        # Create job entry
        self.crop_job_id += 1
        job = {
            'id': self.crop_job_id,
            'input_path': input_path,
            'crop_box': self.crop_box,
            'status': 'queued',
            'filename': os.path.basename(input_path)
        }
        self.crop_jobs.append(job)

        # Update display
        self.update_crop_queue_display()

        # Start processing this job
        self.process_crop_job(job)

        box = self.crop_box
        self.crop_status.set(f"Added to queue: {job['filename']} ({box[2]-box[0]}x{box[3]-box[1]})")

    def process_crop_job(self, job):
        def crop_thread():
            try:
                import gc
                gc.collect()
                time.sleep(0.5)

                job['status'] = 'processing'
                self.root.after(0, self.update_crop_queue_display)

                output = crop_video(job['input_path'], job['crop_box'])

                job['status'] = 'done'
                job['output'] = output
                self.root.after(0, self.update_crop_queue_display)

            except Exception as e:
                job['status'] = 'error'
                job['error'] = str(e)
                self.root.after(0, self.update_crop_queue_display)

        threading.Thread(target=crop_thread, daemon=True).start()

    def update_crop_queue_display(self):
        self.crop_queue_listbox.delete(0, tk.END)

        status_icons = {
            'queued': '[...]',
            'processing': '[>>>]',
            'done': '[OK]',
            'error': '[ERR]'
        }

        for job in self.crop_jobs:
            icon = status_icons.get(job['status'], '[?]')
            box = job['crop_box']
            size = f"{box[2]-box[0]}x{box[3]-box[1]}"
            display = f"{icon} {job['filename'][:20]} ({size})"
            self.crop_queue_listbox.insert(tk.END, display)

            # Color code based on status
            idx = self.crop_jobs.index(job)
            if job['status'] == 'done':
                self.crop_queue_listbox.itemconfig(idx, fg='green')
            elif job['status'] == 'error':
                self.crop_queue_listbox.itemconfig(idx, fg='red')
            elif job['status'] == 'processing':
                self.crop_queue_listbox.itemconfig(idx, fg='blue')

        # Update queue status
        total = len(self.crop_jobs)
        processing = sum(1 for j in self.crop_jobs if j['status'] == 'processing')
        done = sum(1 for j in self.crop_jobs if j['status'] == 'done')
        self.crop_queue_status.set(f"Queue: {total} jobs ({processing} running, {done} done)")

    def clear_completed_crop_jobs(self):
        self.crop_jobs = [j for j in self.crop_jobs if j['status'] not in ('done', 'error')]
        self.update_crop_queue_display()

    def create_trim_tab(self):
        tab = tk.Frame(self.content_frame, bg='white')
        self.add_tab(tab, "Trim/Subclip")

        # Initialize trim job queue
        self.trim_jobs = []  # List of job dicts with status info
        self.trim_job_id = 0

        # Top section - file selection
        top_frame = ttk.Frame(tab)
        top_frame.pack(fill='x', padx=10, pady=10)

        ttk.Label(top_frame, text="Input Video:").pack(side='left', padx=5)
        self.trim_input_path = tk.StringVar()
        ttk.Entry(top_frame, textvariable=self.trim_input_path, width=50).pack(side='left', padx=5)
        ttk.Button(top_frame, text="Browse", command=self.browse_trim_input).pack(side='left', padx=5)
        ttk.Button(top_frame, text="Load Video Info", command=self.load_trim_info).pack(side='left', padx=5)

        self.trim_duration_var = tk.StringVar(value="Duration: Unknown")
        ttk.Label(top_frame, textvariable=self.trim_duration_var, font=('Arial', 10, 'bold')).pack(side='left', padx=10)

        # Main content - split into left, center, and right
        content_frame = ttk.Frame(tab)
        content_frame.pack(fill='both', expand=True, padx=10, pady=5)

        # Left side - controls
        left_frame = ttk.Frame(content_frame)
        left_frame.pack(side='left', fill='y', padx=(0, 10))

        time_frame = ttk.LabelFrame(left_frame, text="Select Time Range")
        time_frame.pack(fill='x', pady=5)

        ttk.Label(time_frame, text="Start Time (seconds):").grid(row=0, column=0, padx=10, pady=5, sticky='w')
        self.trim_start_var = tk.DoubleVar(value=0)
        ttk.Entry(time_frame, textvariable=self.trim_start_var, width=15).grid(row=0, column=1, padx=10, pady=5)

        ttk.Label(time_frame, text="End Time (seconds):").grid(row=1, column=0, padx=10, pady=5, sticky='w')
        self.trim_end_var = tk.DoubleVar(value=0)
        ttk.Entry(time_frame, textvariable=self.trim_end_var, width=15).grid(row=1, column=1, padx=10, pady=5)

        self.trim_clip_duration = tk.StringVar(value="Clip Duration: 0s")
        ttk.Label(time_frame, textvariable=self.trim_clip_duration).grid(row=2, column=0, columnspan=2, pady=5)

        self.trim_start_var.trace_add('write', self.update_trim_duration)
        self.trim_end_var.trace_add('write', self.update_trim_duration)

        ttk.Button(left_frame, text="Add to Queue", command=self.add_trim_to_queue).pack(fill='x', pady=10)

        self.trim_status = tk.StringVar(value="Ready - Set up a trim and add to queue")
        ttk.Label(left_frame, textvariable=self.trim_status).pack(pady=5)

        # Center - preview
        preview_frame = ttk.LabelFrame(content_frame, text="Video Scrubber Preview")
        preview_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))

        self.trim_preview_label = tk.Label(preview_frame, bg='black', width=50, height=20)
        self.trim_preview_label.pack(padx=10, pady=10)

        scrubber_frame = ttk.Frame(preview_frame)
        scrubber_frame.pack(fill='x', padx=10, pady=(0, 10))

        self.scrubber_var = tk.DoubleVar(value=0)
        self.scrubber_time_label = tk.StringVar(value="00:00")

        ttk.Label(scrubber_frame, textvariable=self.scrubber_time_label, font=('Arial', 10)).pack(pady=2)
        self.scrubber_scale = ttk.Scale(scrubber_frame, from_=0, to=100, variable=self.scrubber_var,
                                        orient='horizontal', command=self.on_scrubber_change)
        self.scrubber_scale.pack(fill='x', pady=5)

        # Right side - Job Queue
        queue_frame = ttk.LabelFrame(content_frame, text="Processing Queue")
        queue_frame.pack(side='right', fill='both', expand=False, padx=(0, 0))

        # Queue listbox
        self.trim_queue_listbox = tk.Listbox(queue_frame, width=40, height=10, font=('Consolas', 9))
        self.trim_queue_listbox.pack(fill='both', expand=True, padx=5, pady=5)

        queue_btn_frame = ttk.Frame(queue_frame)
        queue_btn_frame.pack(fill='x', padx=5, pady=5)

        ttk.Button(queue_btn_frame, text="Clear Completed", command=self.clear_completed_trim_jobs).pack(side='left', padx=2)

        self.trim_queue_status = tk.StringVar(value="Queue: 0 jobs")
        ttk.Label(queue_frame, textvariable=self.trim_queue_status).pack(pady=5)

    def browse_trim_input(self):
        filename = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[("Video files", "*.mp4 *.webm *.avi *.mov"), ("All files", "*.*")]
        )
        if filename:
            self.trim_input_path.set(filename)

    def load_trim_info(self):
        input_path = self.trim_input_path.get()
        if not input_path or not os.path.exists(input_path):
            messagebox.showerror("Error", "Please select a valid input video")
            return

        try:
            duration = get_video_duration(input_path)
            self.video_duration = duration
            self.trim_duration_var.set(f"Duration: {duration:.2f} seconds ({self.format_time(duration)})")
            self.trim_end_var.set(duration)

            self.trim_video_cap = cv2.VideoCapture(input_path)
            self.scrubber_scale.config(to=duration)
            self.scrubber_var.set(0)
            self.on_scrubber_change(0)

        except Exception as e:
            messagebox.showerror("Error", f"Could not load video info: {str(e)}")

    def on_scrubber_change(self, value):
        if not hasattr(self, 'trim_video_cap') or self.trim_video_cap is None:
            return

        try:
            timestamp = float(value)
            self.scrubber_time_label.set(f"{timestamp:.2f}s")

            self.trim_video_cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
            ret, frame = self.trim_video_cap.read()

            if ret:
                max_width = 640
                max_height = 360

                h, w = frame.shape[:2]
                scale = min(max_width / w, max_height / h)
                new_w = int(w * scale)
                new_h = int(h * scale)

                frame = cv2.resize(frame, (new_w, new_h))
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                photo = ImageTk.PhotoImage(img)

                self.trim_preview_label.config(image=photo, width=new_w, height=new_h)
                self.trim_preview_label.image = photo
        except Exception as e:
            print(f"Error updating preview: {e}")

    def format_time(self, seconds):
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"

    def update_trim_duration(self, *args):
        try:
            start = self.trim_start_var.get()
            end = self.trim_end_var.get()
            duration = max(0, end - start)
            self.trim_clip_duration.set(f"Clip Duration: {duration:.2f}s ({self.format_time(duration)})")
        except:
            pass

    def add_trim_to_queue(self):
        input_path = self.trim_input_path.get()
        if not input_path or not os.path.exists(input_path):
            messagebox.showerror("Error", "Please select a valid input video")
            return

        start_time = self.trim_start_var.get()
        end_time = self.trim_end_var.get()

        if start_time >= end_time:
            messagebox.showerror("Error", "Start time must be less than end time")
            return

        # Create job entry
        self.trim_job_id += 1
        job = {
            'id': self.trim_job_id,
            'input_path': input_path,
            'start_time': start_time,
            'end_time': end_time,
            'status': 'queued',
            'filename': os.path.basename(input_path)
        }
        self.trim_jobs.append(job)

        # Add to listbox
        self.update_trim_queue_display()

        # Start processing this job
        self.process_trim_job(job)

        self.trim_status.set(f"Added to queue: {job['filename']} ({start_time:.1f}s - {end_time:.1f}s)")

    def process_trim_job(self, job):
        def trim_thread():
            try:
                import gc
                gc.collect()
                time.sleep(0.5)

                job['status'] = 'processing'
                self.root.after(0, self.update_trim_queue_display)

                output = get_subclip(job['input_path'], job['start_time'], job['end_time'])

                job['status'] = 'done'
                job['output'] = output
                self.root.after(0, self.update_trim_queue_display)

            except Exception as e:
                job['status'] = f'error'
                job['error'] = str(e)
                self.root.after(0, self.update_trim_queue_display)

        threading.Thread(target=trim_thread, daemon=True).start()

    def update_trim_queue_display(self):
        self.trim_queue_listbox.delete(0, tk.END)

        status_icons = {
            'queued': '[...]',
            'processing': '[>>>]',
            'done': '[OK]',
            'error': '[ERR]'
        }

        for job in self.trim_jobs:
            icon = status_icons.get(job['status'], '[?]')
            time_range = f"{job['start_time']:.1f}-{job['end_time']:.1f}s"
            display = f"{icon} {job['filename'][:20]} ({time_range})"
            self.trim_queue_listbox.insert(tk.END, display)

            # Color code based on status
            idx = self.trim_jobs.index(job)
            if job['status'] == 'done':
                self.trim_queue_listbox.itemconfig(idx, fg='green')
            elif job['status'] == 'error':
                self.trim_queue_listbox.itemconfig(idx, fg='red')
            elif job['status'] == 'processing':
                self.trim_queue_listbox.itemconfig(idx, fg='blue')

        # Update queue status
        total = len(self.trim_jobs)
        processing = sum(1 for j in self.trim_jobs if j['status'] == 'processing')
        done = sum(1 for j in self.trim_jobs if j['status'] == 'done')
        self.trim_queue_status.set(f"Queue: {total} jobs ({processing} running, {done} done)")

    def clear_completed_trim_jobs(self):
        self.trim_jobs = [j for j in self.trim_jobs if j['status'] not in ('done', 'error')]
        self.update_trim_queue_display()

    def create_speed_tab(self):
        tab = tk.Frame(self.content_frame, bg='white')
        self.add_tab(tab, "Speed Adjustment")

        ttk.Label(tab, text="Input Video:").grid(row=0, column=0, padx=10, pady=10, sticky='w')
        self.speed_input_path = tk.StringVar()
        ttk.Entry(tab, textvariable=self.speed_input_path, width=50).grid(row=0, column=1, padx=10, pady=10)
        ttk.Button(tab, text="Browse", command=self.browse_speed_input).grid(row=0, column=2, padx=10, pady=10)

        speed_frame = ttk.LabelFrame(tab, text="Speed Settings")
        speed_frame.grid(row=1, column=0, columnspan=3, padx=10, pady=10, sticky='ew')

        ttk.Label(speed_frame, text="Speed Factor:").grid(row=0, column=0, padx=10, pady=10, sticky='w')
        self.speed_factor_var = tk.StringVar(value="1.0")
        ttk.Entry(speed_frame, textvariable=self.speed_factor_var, width=10).grid(row=0, column=1, padx=10, pady=10, sticky='w')
        ttk.Label(speed_frame, text="(e.g. 7.3 = 7.3x faster)").grid(row=0, column=2, padx=10, pady=10, sticky='w')

        ttk.Button(tab, text="Apply Speed Change", command=self.speed_video_action).grid(row=2, column=0, columnspan=3, pady=20)

        self.speed_progress = ttk.Progressbar(tab, mode='indeterminate')
        self.speed_progress.grid(row=3, column=0, columnspan=3, padx=10, pady=10, sticky='ew')

        self.speed_status = tk.StringVar(value="Ready")
        ttk.Label(tab, textvariable=self.speed_status).grid(row=4, column=0, columnspan=3, pady=5)

    def browse_speed_input(self):
        filename = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[("Video files", "*.mp4 *.webm *.avi *.mov"), ("All files", "*.*")]
        )
        if filename:
            self.speed_input_path.set(filename)

    def speed_video_action(self):
        input_path = self.speed_input_path.get()
        if not input_path or not os.path.exists(input_path):
            messagebox.showerror("Error", "Please select a valid input video")
            return

        try:
            speed_factor = float(self.speed_factor_var.get())
            if speed_factor <= 0:
                raise ValueError("Speed must be positive")
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid positive number for speed factor")
            return

        def speed_thread():
            try:
                self.speed_progress.start()
                self.speed_status.set(f"Applying {speed_factor}x speed...")

                output = speed_up_mp4_video(input_path, speed_factor)

                self.speed_progress.stop()
                self.speed_status.set(f"Done! Saved to: {os.path.basename(output)}")
                messagebox.showinfo("Success", f"Speed adjustment complete!\n{output}")
            except Exception as e:
                self.speed_progress.stop()
                self.speed_status.set("Error occurred")
                messagebox.showerror("Error", f"Speed adjustment failed: {str(e)}")

        threading.Thread(target=speed_thread, daemon=True).start()

    def create_blur_tab(self):
        tab = tk.Frame(self.content_frame, bg='white')
        self.add_tab(tab, "Blur Region")

        ttk.Label(tab, text="Input Video:").grid(row=0, column=0, padx=10, pady=10, sticky='w')
        self.blur_input_path = tk.StringVar()
        ttk.Entry(tab, textvariable=self.blur_input_path, width=50).grid(row=0, column=1, padx=10, pady=10)
        ttk.Button(tab, text="Browse", command=self.browse_blur_input).grid(row=0, column=2, padx=10, pady=10)

        ttk.Button(tab, text="Load Preview", command=self.load_blur_preview).grid(row=1, column=0, columnspan=3, pady=10)

        self.blur_canvas_frame = ttk.Frame(tab)
        self.blur_canvas_frame.grid(row=2, column=0, columnspan=3, padx=10, pady=10)

        self.blur_canvas = tk.Canvas(self.blur_canvas_frame, width=640, height=360, bg='gray')
        self.blur_canvas.pack()

        self.blur_rect = None
        self.blur_start_x = None
        self.blur_start_y = None
        self.blur_scale_factor = 1.0

        self.blur_canvas.bind("<ButtonPress-1>", self.on_blur_press)
        self.blur_canvas.bind("<B1-Motion>", self.on_blur_drag)
        self.blur_canvas.bind("<ButtonRelease-1>", self.on_blur_release)

        coords_frame = ttk.Frame(tab)
        coords_frame.grid(row=3, column=0, columnspan=3, pady=10)

        ttk.Label(coords_frame, text="Blur Region:").pack(side='left', padx=5)
        self.blur_coords = tk.StringVar(value="Not selected")
        ttk.Label(coords_frame, textvariable=self.blur_coords).pack(side='left', padx=5)

        ttk.Button(tab, text="Apply Blur", command=self.blur_video_action).grid(row=4, column=0, columnspan=3, pady=10)

        self.blur_progress = ttk.Progressbar(tab, mode='indeterminate')
        self.blur_progress.grid(row=5, column=0, columnspan=3, padx=10, pady=10, sticky='ew')

        self.blur_status = tk.StringVar(value="Ready")
        ttk.Label(tab, textvariable=self.blur_status).grid(row=6, column=0, columnspan=3, pady=5)

    def browse_blur_input(self):
        filename = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[("Video files", "*.mp4 *.webm *.avi *.mov"), ("All files", "*.*")]
        )
        if filename:
            self.blur_input_path.set(filename)

    def load_blur_preview(self):
        input_path = self.blur_input_path.get()
        if not input_path or not os.path.exists(input_path):
            messagebox.showerror("Error", "Please select a valid input video")
            return

        cap = cv2.VideoCapture(input_path)
        ret, frame = cap.read()
        cap.release()

        if not ret:
            messagebox.showerror("Error", "Could not read video frame")
            return

        self.blur_original_frame = frame
        original_height, original_width = frame.shape[:2]

        max_width = 640
        max_height = 360

        width_scale = max_width / original_width
        height_scale = max_height / original_height
        self.blur_scale_factor = min(width_scale, height_scale, 1.0)

        if self.blur_scale_factor < 1.0:
            display_width = int(original_width * self.blur_scale_factor)
            display_height = int(original_height * self.blur_scale_factor)
            frame = cv2.resize(frame, (display_width, display_height))

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.blur_image = Image.fromarray(frame_rgb)
        self.blur_photo = ImageTk.PhotoImage(self.blur_image)

        self.blur_canvas.config(width=self.blur_image.width, height=self.blur_image.height)
        self.blur_canvas.create_image(0, 0, anchor='nw', image=self.blur_photo)

        self.blur_status.set("Preview loaded. Click and drag to select blur region.")

    def on_blur_press(self, event):
        self.blur_start_x = event.x
        self.blur_start_y = event.y
        if self.blur_rect:
            self.blur_canvas.delete(self.blur_rect)
        self.blur_rect = self.blur_canvas.create_rectangle(
            self.blur_start_x, self.blur_start_y, self.blur_start_x, self.blur_start_y,
            outline='yellow', width=2
        )

    def on_blur_drag(self, event):
        if self.blur_rect:
            self.blur_canvas.coords(self.blur_rect, self.blur_start_x, self.blur_start_y, event.x, event.y)

    def on_blur_release(self, event):
        if self.blur_start_x is None or self.blur_start_y is None:
            return

        x1 = min(self.blur_start_x, event.x)
        y1 = min(self.blur_start_y, event.y)
        x2 = max(self.blur_start_x, event.x)
        y2 = max(self.blur_start_y, event.y)

        orig_x1 = int(x1 / self.blur_scale_factor)
        orig_y1 = int(y1 / self.blur_scale_factor)
        orig_x2 = int(x2 / self.blur_scale_factor)
        orig_y2 = int(y2 / self.blur_scale_factor)

        self.blur_box = (orig_x1, orig_y1, orig_x2, orig_y2)
        self.blur_coords.set(f"({orig_x1}, {orig_y1}, {orig_x2}, {orig_y2})")

    def blur_video_action(self):
        if not hasattr(self, 'blur_box'):
            messagebox.showerror("Error", "Please select a blur region first")
            return

        input_path = self.blur_input_path.get()

        def blur_thread():
            try:
                self.blur_progress.start()
                self.blur_status.set("Blurring video...")

                output = blur_video(input_path, self.blur_box)

                self.blur_progress.stop()
                self.blur_status.set(f"Done! Saved to: {os.path.basename(output)}")
                messagebox.showinfo("Success", f"Blur complete!\n{output}")
            except Exception as e:
                self.blur_progress.stop()
                self.blur_status.set("Error occurred")
                messagebox.showerror("Error", f"Blur failed: {str(e)}")

        threading.Thread(target=blur_thread, daemon=True).start()

    def create_resize_tab(self):
        tab = tk.Frame(self.content_frame, bg='white')
        self.add_tab(tab, "Resize/Stretch")

        # Store resize file data: list of {path, width, height}
        self.resize_files = []

        # Top section - file management buttons
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill='x', padx=10, pady=10)

        ttk.Button(btn_frame, text="Add Videos", command=self.browse_resize_input).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Remove Selected", command=self.remove_resize_files).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Clear All", command=self.clear_resize_files).pack(side='left', padx=5)

        self.resize_file_count = tk.StringVar(value="0 files")
        ttk.Label(btn_frame, textvariable=self.resize_file_count).pack(side='right', padx=10)

        # Table showing videos with dimensions
        table_frame = ttk.LabelFrame(tab, text="Video Dimensions")
        table_frame.pack(fill='both', expand=True, padx=10, pady=5)

        # Create Treeview for table
        columns = ('filename', 'width', 'height')
        self.resize_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=8)

        self.resize_tree.heading('filename', text='Video Name')
        self.resize_tree.heading('width', text='Width')
        self.resize_tree.heading('height', text='Height')

        self.resize_tree.column('filename', width=300)
        self.resize_tree.column('width', width=100, anchor='center')
        self.resize_tree.column('height', width=100, anchor='center')

        scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=self.resize_tree.yview)
        self.resize_tree.configure(yscrollcommand=scrollbar.set)

        self.resize_tree.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        scrollbar.pack(side='right', fill='y', pady=5)

        # Output resolution section
        output_frame = ttk.LabelFrame(tab, text="Output Resolution")
        output_frame.pack(fill='x', padx=10, pady=10)

        dims_frame = ttk.Frame(output_frame)
        dims_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(dims_frame, text="Width:").pack(side='left', padx=5)
        self.new_width_var = tk.IntVar(value=1920)
        ttk.Entry(dims_frame, textvariable=self.new_width_var, width=10).pack(side='left', padx=5)

        ttk.Label(dims_frame, text="Height:").pack(side='left', padx=15)
        self.new_height_var = tk.IntVar(value=1080)
        ttk.Entry(dims_frame, textvariable=self.new_height_var, width=10).pack(side='left', padx=5)

        # Presets
        presets_frame = ttk.Frame(output_frame)
        presets_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(presets_frame, text="Presets:").pack(side='left', padx=5)
        ttk.Button(presets_frame, text="1080p Desktop (1920x1080)",
                  command=lambda: self.set_dimensions(1920, 1080)).pack(side='left', padx=5)
        ttk.Button(presets_frame, text="1080p Phone (1080x1920)",
                  command=lambda: self.set_dimensions(1080, 1920)).pack(side='left', padx=5)

        # Batch stretch button
        ttk.Button(tab, text="Batch Stretch All", command=self.batch_resize_action).pack(pady=10)

        # Progress
        self.resize_progress = ttk.Progressbar(tab, mode='determinate')
        self.resize_progress.pack(fill='x', padx=10, pady=5)

        self.resize_status = tk.StringVar(value="Ready - Add videos to resize")
        ttk.Label(tab, textvariable=self.resize_status).pack(pady=5)

    def browse_resize_input(self):
        filenames = filedialog.askopenfilenames(
            title="Select Video Files",
            filetypes=[("Video files", "*.mp4 *.webm *.avi *.mov"), ("All files", "*.*")]
        )
        if filenames:
            for f in filenames:
                if f not in [item['path'] for item in self.resize_files]:
                    try:
                        width, height = get_vid_dims(f)
                        self.resize_files.append({'path': f, 'width': width, 'height': height})
                        self.resize_tree.insert('', tk.END, values=(os.path.basename(f), width, height))
                    except Exception as e:
                        messagebox.showerror("Error", f"Could not read dimensions for {os.path.basename(f)}: {e}")

            self.resize_file_count.set(f"{len(self.resize_files)} file(s)")

    def remove_resize_files(self):
        selected = self.resize_tree.selection()
        for item in selected:
            idx = self.resize_tree.index(item)
            self.resize_tree.delete(item)
            del self.resize_files[idx]
        self.resize_file_count.set(f"{len(self.resize_files)} file(s)")

    def clear_resize_files(self):
        self.resize_tree.delete(*self.resize_tree.get_children())
        self.resize_files = []
        self.resize_file_count.set("0 files")

    def set_dimensions(self, width, height):
        self.new_width_var.set(width)
        self.new_height_var.set(height)

    def batch_resize_action(self):
        if not self.resize_files:
            messagebox.showerror("Error", "Please add at least one video")
            return

        new_width = self.new_width_var.get()
        new_height = self.new_height_var.get()

        def resize_thread():
            try:
                total = len(self.resize_files)
                self.resize_progress['maximum'] = total
                self.resize_progress['value'] = 0

                successful = []
                failed = []

                for i, file_info in enumerate(self.resize_files):
                    input_path = file_info['path']
                    self.resize_status.set(f"Resizing {i+1}/{total}: {os.path.basename(input_path)}")

                    try:
                        output = stretch_video_dims(input_path, new_width, new_height)
                        successful.append(output)
                    except Exception as e:
                        failed.append((input_path, str(e)))

                    self.resize_progress['value'] = i + 1

                self.resize_progress['value'] = total

                if failed:
                    self.resize_status.set(f"Done with errors: {len(successful)} succeeded, {len(failed)} failed")
                    error_details = "\n".join([f"{os.path.basename(f)}: {e}" for f, e in failed])
                    messagebox.showwarning("Partial Success",
                                          f"Resized {len(successful)}/{total} files.\n\nFailed:\n{error_details}")
                else:
                    self.resize_status.set(f"Done! Resized {total} file(s) to {new_width}x{new_height}")
                    messagebox.showinfo("Success", f"Batch resize complete!\n{total} file(s) resized.")

            except Exception as e:
                self.resize_progress['value'] = 0
                self.resize_status.set("Error occurred")
                messagebox.showerror("Error", f"Resize failed: {str(e)}")

        threading.Thread(target=resize_thread, daemon=True).start()

        threading.Thread(target=resize_thread, daemon=True).start()

    def create_audio_tab(self):
        tab = tk.Frame(self.content_frame, bg='white')
        self.add_tab(tab, "Audio Operations")

        ttk.Label(tab, text="Input Video:").grid(row=0, column=0, padx=10, pady=10, sticky='w')
        self.audio_input_path = tk.StringVar()
        ttk.Entry(tab, textvariable=self.audio_input_path, width=50).grid(row=0, column=1, padx=10, pady=10)
        ttk.Button(tab, text="Browse", command=self.browse_audio_input).grid(row=0, column=2, padx=10, pady=10)

        operations_frame = ttk.LabelFrame(tab, text="Audio Operations")
        operations_frame.grid(row=1, column=0, columnspan=3, padx=10, pady=20, sticky='ew')

        ttk.Button(operations_frame, text="Mute Video", command=self.mute_video_action, width=30).grid(row=0, column=0, padx=20, pady=10)
        ttk.Label(operations_frame, text="Remove all audio from video").grid(row=0, column=1, padx=10, pady=10, sticky='w')

        ttk.Button(operations_frame, text="Extract Audio (MP3)", command=self.extract_audio_action, width=30).grid(row=1, column=0, padx=20, pady=10)
        ttk.Label(operations_frame, text="Save audio track as MP3 file").grid(row=1, column=1, padx=10, pady=10, sticky='w')

        self.audio_progress = ttk.Progressbar(tab, mode='indeterminate')
        self.audio_progress.grid(row=2, column=0, columnspan=3, padx=10, pady=10, sticky='ew')

        self.audio_status = tk.StringVar(value="Ready")
        ttk.Label(tab, textvariable=self.audio_status).grid(row=3, column=0, columnspan=3, pady=5)

    def browse_audio_input(self):
        filename = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[("Video files", "*.mp4 *.webm *.avi *.mov"), ("All files", "*.*")]
        )
        if filename:
            self.audio_input_path.set(filename)

    def mute_video_action(self):
        input_path = self.audio_input_path.get()
        if not input_path or not os.path.exists(input_path):
            messagebox.showerror("Error", "Please select a valid input video")
            return

        def mute_thread():
            try:
                self.audio_progress.start()
                self.audio_status.set("Muting video...")

                output = mute_video(input_path)

                self.audio_progress.stop()
                self.audio_status.set(f"Done! Saved to: {os.path.basename(output)}")
                messagebox.showinfo("Success", f"Mute complete!\n{output}")
            except Exception as e:
                self.audio_progress.stop()
                self.audio_status.set("Error occurred")
                messagebox.showerror("Error", f"Mute failed: {str(e)}")

        threading.Thread(target=mute_thread, daemon=True).start()

    def extract_audio_action(self):
        input_path = self.audio_input_path.get()
        if not input_path or not os.path.exists(input_path):
            messagebox.showerror("Error", "Please select a valid input video")
            return

        def extract_thread():
            try:
                self.audio_progress.start()
                self.audio_status.set("Extracting audio...")

                output = mp4_to_mp3(input_path)

                self.audio_progress.stop()
                self.audio_status.set(f"Done! Saved to: {os.path.basename(output)}")
                messagebox.showinfo("Success", f"Audio extraction complete!\n{output}")
            except Exception as e:
                self.audio_progress.stop()
                self.audio_status.set("Error occurred")
                messagebox.showerror("Error", f"Audio extraction failed: {str(e)}")

        threading.Thread(target=extract_thread, daemon=True).start()

    def create_brightness_tab(self):
        tab = tk.Frame(self.content_frame, bg='white')
        self.add_tab(tab, "Brightness Editor")

        # Top section - file selection
        top_frame = ttk.Frame(tab)
        top_frame.pack(fill='x', padx=10, pady=10)

        ttk.Label(top_frame, text="Input Video:").pack(side='left', padx=5)
        self.brightness_input_path = tk.StringVar()
        ttk.Entry(top_frame, textvariable=self.brightness_input_path, width=50).pack(side='left', padx=5)
        ttk.Button(top_frame, text="Browse", command=self.browse_brightness_input).pack(side='left', padx=5)
        ttk.Button(top_frame, text="Load Random Frame", command=self.load_brightness_preview).pack(side='left', padx=5)

        # Main content - split into left (original) and right (preview)
        content_frame = ttk.Frame(tab)
        content_frame.pack(fill='both', expand=True, padx=10, pady=5)

        # Left side - Original frame
        left_frame = ttk.LabelFrame(content_frame, text="Original Frame")
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 5))

        self.brightness_original_label = tk.Label(left_frame, bg='black', width=50, height=20)
        self.brightness_original_label.pack(padx=10, pady=10, fill='both', expand=True)

        # Right side - Adjusted preview
        right_frame = ttk.LabelFrame(content_frame, text="Brightness Adjusted Preview")
        right_frame.pack(side='right', fill='both', expand=True, padx=(5, 0))

        self.brightness_preview_label = tk.Label(right_frame, bg='black', width=50, height=20)
        self.brightness_preview_label.pack(padx=10, pady=10, fill='both', expand=True)

        # Controls section
        controls_frame = ttk.Frame(tab)
        controls_frame.pack(fill='x', padx=10, pady=10)

        # Brightness slider
        slider_frame = ttk.LabelFrame(controls_frame, text="Brightness Adjustment")
        slider_frame.pack(fill='x', pady=5)

        ttk.Label(slider_frame, text="Darker").pack(side='left', padx=10)

        self.brightness_var = tk.DoubleVar(value=1.0)
        self.brightness_scale = ttk.Scale(
            slider_frame, from_=0.2, to=10.0, variable=self.brightness_var,
            orient='horizontal', length=400, command=self.on_brightness_change
        )
        self.brightness_scale.pack(side='left', fill='x', expand=True, padx=10)

        ttk.Label(slider_frame, text="Brighter").pack(side='left', padx=10)

        self.brightness_value_label = ttk.Label(slider_frame, text="1.00x", width=8)
        self.brightness_value_label.pack(side='left', padx=10)

        # Preset buttons
        presets_frame = ttk.Frame(slider_frame)
        presets_frame.pack(side='left', padx=10)

        for preset in [0.5, 1.0, 2.0, 4.0, 6.0, 8.0, 10.0]:
            text = f"{preset}x"
            ttk.Button(presets_frame, text=text, width=5,
                      command=lambda p=preset: self.set_brightness_preset(p)).pack(side='left', padx=2)

        # Save button and progress
        button_frame = ttk.Frame(tab)
        button_frame.pack(fill='x', padx=10, pady=10)

        ttk.Button(button_frame, text="SAVE", command=self.save_brightness_video,
                  style='Accent.TButton').pack(pady=10)

        self.brightness_progress = ttk.Progressbar(button_frame, mode='indeterminate')
        self.brightness_progress.pack(fill='x', pady=5)

        self.brightness_status = tk.StringVar(value="Ready - Load a video to begin")
        ttk.Label(button_frame, textvariable=self.brightness_status).pack(pady=5)

        # Store original frame for preview updates
        self.brightness_original_frame = None
        self.brightness_original_pil = None

    def browse_brightness_input(self):
        filename = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[("Video files", "*.mp4 *.webm *.avi *.mov"), ("All files", "*.*")]
        )
        if filename:
            self.brightness_input_path.set(filename)

    def load_brightness_preview(self):
        input_path = self.brightness_input_path.get()
        if not input_path or not os.path.exists(input_path):
            messagebox.showerror("Error", "Please select a valid input video")
            return

        cap = cv2.VideoCapture(input_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if total_frames <= 0:
            messagebox.showerror("Error", "Could not read video frames")
            cap.release()
            return

        # Get a random frame
        random_frame_idx = random.randint(0, total_frames - 1)
        cap.set(cv2.CAP_PROP_POS_FRAMES, random_frame_idx)
        ret, frame = cap.read()
        cap.release()

        if not ret:
            messagebox.showerror("Error", "Could not read video frame")
            return

        # Store original frame for brightness adjustments
        self.brightness_original_frame = frame
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.brightness_original_pil = Image.fromarray(frame_rgb)

        # Resize for display
        max_width = 400
        max_height = 300
        h, w = frame.shape[:2]
        scale = min(max_width / w, max_height / h, 1.0)
        new_w = int(w * scale)
        new_h = int(h * scale)

        # Display original frame
        display_pil = self.brightness_original_pil.resize((new_w, new_h), Image.LANCZOS)
        photo = ImageTk.PhotoImage(display_pil)
        self.brightness_original_label.config(image=photo, width=new_w, height=new_h)
        self.brightness_original_label.image = photo

        # Reset brightness slider
        self.brightness_var.set(1.0)
        self.brightness_value_label.config(text="1.00x")

        # Update preview
        self.update_brightness_preview()

        self.brightness_status.set(f"Loaded random frame #{random_frame_idx + 1} of {total_frames}")

    def on_brightness_change(self, value):
        self.brightness_value_label.config(text=f"{float(value):.2f}x")
        self.update_brightness_preview()

    def set_brightness_preset(self, preset):
        self.brightness_var.set(preset)
        self.brightness_value_label.config(text=f"{preset:.2f}x")
        self.update_brightness_preview()

    def update_brightness_preview(self):
        if self.brightness_original_pil is None:
            return

        brightness_factor = self.brightness_var.get()

        # Apply brightness using PIL ImageEnhance
        enhancer = ImageEnhance.Brightness(self.brightness_original_pil)
        adjusted_pil = enhancer.enhance(brightness_factor)

        # Resize for display
        max_width = 400
        max_height = 300
        w, h = adjusted_pil.size
        scale = min(max_width / w, max_height / h, 1.0)
        new_w = int(w * scale)
        new_h = int(h * scale)

        display_pil = adjusted_pil.resize((new_w, new_h), Image.LANCZOS)
        photo = ImageTk.PhotoImage(display_pil)
        self.brightness_preview_label.config(image=photo, width=new_w, height=new_h)
        self.brightness_preview_label.image = photo

    def save_brightness_video(self):
        input_path = self.brightness_input_path.get()
        if not input_path or not os.path.exists(input_path):
            messagebox.showerror("Error", "Please select a valid input video")
            return

        brightness_factor = self.brightness_var.get()

        if brightness_factor == 1.0:
            messagebox.showinfo("Info", "Brightness is at 1.0x (no change). Adjust the slider to modify brightness.")
            return

        def save_thread():
            try:
                self.brightness_progress.start()
                self.brightness_status.set(f"Applying {brightness_factor:.2f}x brightness...")

                output = adjust_brightness_video(input_path, brightness_factor)

                self.brightness_progress.stop()
                self.brightness_status.set(f"Done! Saved in place: {os.path.basename(output)}")
                messagebox.showinfo("Success", f"Brightness adjustment complete!\nVideo saved in place:\n{output}")
            except Exception as e:
                self.brightness_progress.stop()
                self.brightness_status.set("Error occurred")
                messagebox.showerror("Error", f"Brightness adjustment failed: {str(e)}")

        threading.Thread(target=save_thread, daemon=True).start()

    def create_slideshow_tab(self):
        tab = tk.Frame(self.content_frame, bg='white')
        self.add_tab(tab, "Slideshow Maker")

        # Main layout - two columns
        main_frame = ttk.Frame(tab)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Left column - inputs
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))

        # Image folder selection
        folder_frame = ttk.LabelFrame(left_frame, text="Image Folder")
        folder_frame.pack(fill='x', pady=5)

        folder_row = ttk.Frame(folder_frame)
        folder_row.pack(fill='x', padx=10, pady=5)

        self.slideshow_folder_path = tk.StringVar()
        ttk.Entry(folder_row, textvariable=self.slideshow_folder_path, width=50).pack(side='left', padx=(0, 5))
        ttk.Button(folder_row, text="Browse", command=self.browse_slideshow_folder).pack(side='left')

        self.slideshow_image_count = tk.StringVar(value="No folder selected")
        ttk.Label(folder_frame, textvariable=self.slideshow_image_count).pack(padx=10, pady=(0, 5))

        # Track number of images for duration calculation
        self.slideshow_num_images = 0

        # Duration settings
        duration_frame = ttk.LabelFrame(left_frame, text="Frame Duration (seconds)")
        duration_frame.pack(fill='x', pady=5)

        dur_row = ttk.Frame(duration_frame)
        dur_row.pack(fill='x', padx=10, pady=5)

        ttk.Label(dur_row, text="Start Rate:").pack(side='left', padx=(0, 5))
        self.slideshow_start_duration = tk.StringVar(value="1.0")
        ttk.Entry(dur_row, textvariable=self.slideshow_start_duration, width=8).pack(side='left', padx=(0, 15))

        ttk.Label(dur_row, text="End Rate:").pack(side='left', padx=(0, 5))
        self.slideshow_end_duration = tk.StringVar(value="1.0")
        ttk.Entry(dur_row, textvariable=self.slideshow_end_duration, width=8).pack(side='left')

        # Expected length display
        self.slideshow_expected_length = tk.StringVar(value="Expected length: --")
        ttk.Label(duration_frame, textvariable=self.slideshow_expected_length, font=('Arial', 10, 'bold')).pack(padx=10, pady=5)

        ttk.Label(duration_frame, text="Use different values to speed up/slow down over time").pack(padx=10, pady=(0, 5))

        # Add traces to update expected length when durations change
        self.slideshow_start_duration.trace_add('write', self.update_slideshow_expected_length)
        self.slideshow_end_duration.trace_add('write', self.update_slideshow_expected_length)

        # Options frame
        options_frame = ttk.LabelFrame(left_frame, text="Options")
        options_frame.pack(fill='x', pady=5)

        # Shuffle checkbox
        self.slideshow_shuffle = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Shuffle images", variable=self.slideshow_shuffle).pack(anchor='w', padx=10, pady=2)

        # Scale mode
        scale_row = ttk.Frame(options_frame)
        scale_row.pack(fill='x', padx=10, pady=5)

        ttk.Label(scale_row, text="Image Scaling:").pack(side='left', padx=(0, 5))
        self.slideshow_scale_mode = tk.StringVar(value="stretch")
        scale_combo = ttk.Combobox(scale_row, textvariable=self.slideshow_scale_mode,
                                   values=["stretch", "fit", "crop"], state='readonly', width=15)
        scale_combo.pack(side='left')

        # Random rotation section
        rotation_frame = ttk.LabelFrame(left_frame, text="Random Rotation")
        rotation_frame.pack(fill='x', pady=5)

        self.slideshow_random_rotation = tk.BooleanVar(value=False)
        ttk.Checkbutton(rotation_frame, text="Enable random rotation",
                       variable=self.slideshow_random_rotation).pack(anchor='w', padx=10, pady=2)

        rot_row = ttk.Frame(rotation_frame)
        rot_row.pack(fill='x', padx=10, pady=5)

        ttk.Label(rot_row, text="Left degrees:").pack(side='left', padx=(0, 5))
        self.slideshow_rotation_left = tk.StringVar(value="15")
        ttk.Entry(rot_row, textvariable=self.slideshow_rotation_left, width=6).pack(side='left', padx=(0, 15))

        ttk.Label(rot_row, text="Right degrees:").pack(side='left', padx=(0, 5))
        self.slideshow_rotation_right = tk.StringVar(value="15")
        ttk.Entry(rot_row, textvariable=self.slideshow_rotation_right, width=6).pack(side='left')

        # Sound effect section
        sound_frame = ttk.LabelFrame(left_frame, text="Sound Effect (optional)")
        sound_frame.pack(fill='x', pady=5)

        sound_row = ttk.Frame(sound_frame)
        sound_row.pack(fill='x', padx=10, pady=5)

        self.slideshow_sound_path = tk.StringVar()
        ttk.Entry(sound_row, textvariable=self.slideshow_sound_path, width=40).pack(side='left', padx=(0, 5))
        ttk.Button(sound_row, text="Browse", command=self.browse_slideshow_sound).pack(side='left', padx=(0, 5))
        ttk.Button(sound_row, text="Clear", command=lambda: self.slideshow_sound_path.set("")).pack(side='left')

        ttk.Label(sound_frame, text="Plays on each frame transition").pack(padx=10, pady=(0, 5))

        # Right column - output and action
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side='right', fill='both', expand=True)

        # Output folder selection
        output_frame = ttk.LabelFrame(right_frame, text="Output Folder")
        output_frame.pack(fill='x', pady=5)

        output_row = ttk.Frame(output_frame)
        output_row.pack(fill='x', padx=10, pady=5)

        self.slideshow_output_folder = tk.StringVar()
        ttk.Entry(output_row, textvariable=self.slideshow_output_folder, width=50).pack(side='left', padx=(0, 5))
        ttk.Button(output_row, text="Browse", command=self.browse_slideshow_output).pack(side='left')

        ttk.Label(output_frame, text="Output will be saved as slideshow.mp4").pack(padx=10, pady=(0, 5))

        # Create button
        ttk.Button(right_frame, text="Create Slideshow", command=self.create_slideshow_action).pack(pady=20)

        # Progress
        self.slideshow_progress = ttk.Progressbar(right_frame, mode='determinate')
        self.slideshow_progress.pack(fill='x', pady=5)

        self.slideshow_status = tk.StringVar(value="Ready - Select an image folder to begin")
        ttk.Label(right_frame, textvariable=self.slideshow_status).pack(pady=5)

        # Load saved config
        self.load_slideshow_config()

    def browse_slideshow_folder(self):
        folder = filedialog.askdirectory(title="Select Image Folder")
        if folder:
            self.slideshow_folder_path.set(folder)
            # Count valid images
            valid_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'}
            count = sum(1 for f in os.listdir(folder)
                       if os.path.splitext(f)[1].lower() in valid_extensions)
            self.slideshow_num_images = count
            self.slideshow_image_count.set(f"{count} images found")
            self.update_slideshow_expected_length()

    def browse_slideshow_sound(self):
        filename = filedialog.askopenfilename(
            title="Select Sound Effect",
            filetypes=[("Audio files", "*.mp3 *.wav *.ogg *.m4a"), ("All files", "*.*")]
        )
        if filename:
            self.slideshow_sound_path.set(filename)

    def browse_slideshow_output(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.slideshow_output_folder.set(folder)

    def save_slideshow_config(self):
        """Save slideshow settings to config file"""
        config = {
            'folder_path': self.slideshow_folder_path.get(),
            'start_duration': self.slideshow_start_duration.get(),
            'end_duration': self.slideshow_end_duration.get(),
            'shuffle': self.slideshow_shuffle.get(),
            'scale_mode': self.slideshow_scale_mode.get(),
            'random_rotation': self.slideshow_random_rotation.get(),
            'rotation_left': self.slideshow_rotation_left.get(),
            'rotation_right': self.slideshow_rotation_right.get(),
            'sound_path': self.slideshow_sound_path.get(),
            'output_folder': self.slideshow_output_folder.get(),
        }
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(SLIDESHOW_CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Failed to save slideshow config: {e}")

    def load_slideshow_config(self):
        """Load slideshow settings from config file"""
        if not os.path.exists(SLIDESHOW_CONFIG_FILE):
            return
        try:
            with open(SLIDESHOW_CONFIG_FILE, 'r') as f:
                config = json.load(f)

            if config.get('folder_path'):
                self.slideshow_folder_path.set(config['folder_path'])
                # Update image count if folder exists
                if os.path.isdir(config['folder_path']):
                    valid_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'}
                    count = sum(1 for f in os.listdir(config['folder_path'])
                               if os.path.splitext(f)[1].lower() in valid_extensions)
                    self.slideshow_num_images = count
                    self.slideshow_image_count.set(f"{count} images found")

            if config.get('start_duration'):
                self.slideshow_start_duration.set(config['start_duration'])
            if config.get('end_duration'):
                self.slideshow_end_duration.set(config['end_duration'])
            if 'shuffle' in config:
                self.slideshow_shuffle.set(config['shuffle'])
            if config.get('scale_mode'):
                self.slideshow_scale_mode.set(config['scale_mode'])
            if 'random_rotation' in config:
                self.slideshow_random_rotation.set(config['random_rotation'])
            if config.get('rotation_left'):
                self.slideshow_rotation_left.set(config['rotation_left'])
            if config.get('rotation_right'):
                self.slideshow_rotation_right.set(config['rotation_right'])
            if config.get('sound_path'):
                self.slideshow_sound_path.set(config['sound_path'])
            if config.get('output_folder'):
                self.slideshow_output_folder.set(config['output_folder'])

            # Update expected length display
            self.update_slideshow_expected_length()

        except Exception as e:
            print(f"Failed to load slideshow config: {e}")

    def update_slideshow_expected_length(self, *args):
        try:
            start = float(self.slideshow_start_duration.get())
            end = float(self.slideshow_end_duration.get())
            n = self.slideshow_num_images

            if n <= 0:
                self.slideshow_expected_length.set("Expected length: --")
                return

            # Total duration = sum of linearly interpolated durations
            # For n images: total = n * (start + end) / 2
            total_seconds = n * (start + end) / 2

            # Format as mm:ss or hh:mm:ss
            minutes = int(total_seconds // 60)
            seconds = total_seconds % 60
            if minutes >= 60:
                hours = minutes // 60
                minutes = minutes % 60
                time_str = f"{hours}h {minutes}m {seconds:.1f}s"
            elif minutes > 0:
                time_str = f"{minutes}m {seconds:.1f}s"
            else:
                time_str = f"{seconds:.1f}s"

            self.slideshow_expected_length.set(f"Expected length: {time_str}")
        except (ValueError, AttributeError):
            self.slideshow_expected_length.set("Expected length: --")

    def create_slideshow_action(self):
        # Validate inputs
        image_folder = self.slideshow_folder_path.get()
        if not image_folder or not os.path.isdir(image_folder):
            messagebox.showerror("Error", "Please select a valid image folder")
            return

        output_folder = self.slideshow_output_folder.get()
        if not output_folder or not os.path.isdir(output_folder):
            messagebox.showerror("Error", "Please select a valid output folder")
            return

        try:
            start_duration = float(self.slideshow_start_duration.get())
            end_duration = float(self.slideshow_end_duration.get())
            if start_duration <= 0 or end_duration <= 0:
                raise ValueError("Durations must be positive")
        except ValueError:
            messagebox.showerror("Error", "Please enter valid positive numbers for duration")
            return

        try:
            rotation_left = float(self.slideshow_rotation_left.get())
            rotation_right = float(self.slideshow_rotation_right.get())
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers for rotation degrees")
            return

        output_path = os.path.join(output_folder, "slideshow.mp4")
        sound_path = self.slideshow_sound_path.get() or None

        def progress_callback(current, total):
            self.slideshow_progress['maximum'] = total
            self.slideshow_progress['value'] = current
            self.slideshow_status.set(f"Processing image {current}/{total}...")

        def slideshow_thread():
            try:
                self.slideshow_status.set("Creating slideshow...")

                create_slideshow(
                    image_folder=image_folder,
                    output_path=output_path,
                    start_duration=start_duration,
                    end_duration=end_duration,
                    shuffle_images=self.slideshow_shuffle.get(),
                    random_rotation=self.slideshow_random_rotation.get(),
                    rotation_left=rotation_left,
                    rotation_right=rotation_right,
                    sound_effect_path=sound_path,
                    scale_mode=self.slideshow_scale_mode.get(),
                    progress_callback=lambda c, t: self.root.after(0, lambda: progress_callback(c, t))
                )

                # Save config after successful creation
                self.root.after(0, self.save_slideshow_config)

                self.root.after(0, lambda: self.slideshow_progress.configure(value=0))
                self.root.after(0, lambda: self.slideshow_status.set(f"Done! Saved to: {output_path}"))
                self.root.after(0, lambda: messagebox.showinfo("Success", f"Slideshow created!\n{output_path}"))

            except Exception as e:
                import traceback
                print("=" * 50)
                print("SLIDESHOW ERROR:")
                traceback.print_exc()
                print("=" * 50)
                error_msg = str(e) if str(e) else repr(e)
                self.root.after(0, lambda: self.slideshow_progress.configure(value=0))
                self.root.after(0, lambda: self.slideshow_status.set("Error occurred"))
                self.root.after(0, lambda msg=error_msg: messagebox.showerror("Error", f"Slideshow creation failed: {msg}"))

        threading.Thread(target=slideshow_thread, daemon=True).start()

    def create_bulk_crop_images_tab(self):
        tab = tk.Frame(self.content_frame, bg='white')
        self.add_tab(tab, "Bulk Crop Images")

        # Store image folder data
        self.bulk_crop_image_files = []
        self.bulk_crop_current_index = 0

        # Top section - folder selection
        top_frame = ttk.Frame(tab)
        top_frame.pack(fill='x', padx=10, pady=10)

        ttk.Label(top_frame, text="Image Folder:").pack(side='left', padx=5)
        self.bulk_crop_folder_path = tk.StringVar()
        ttk.Entry(top_frame, textvariable=self.bulk_crop_folder_path, width=50).pack(side='left', padx=5)
        ttk.Button(top_frame, text="Browse", command=self.browse_bulk_crop_folder).pack(side='left', padx=5)
        ttk.Button(top_frame, text="Load Preview", command=self.load_bulk_crop_preview).pack(side='left', padx=5)

        self.bulk_crop_image_count = tk.StringVar(value="No folder selected")
        ttk.Label(top_frame, textvariable=self.bulk_crop_image_count, font=('Arial', 10, 'bold')).pack(side='left', padx=10)

        # Main content frame
        content_frame = ttk.Frame(tab)
        content_frame.pack(fill='both', expand=True, padx=10, pady=5)

        # Left side - preview and controls
        left_frame = ttk.Frame(content_frame)
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))

        # Canvas for image preview
        self.bulk_crop_canvas_frame = ttk.Frame(left_frame)
        self.bulk_crop_canvas_frame.pack(pady=5)

        self.bulk_crop_canvas = tk.Canvas(self.bulk_crop_canvas_frame, width=640, height=480, bg='gray')
        self.bulk_crop_canvas.pack()

        # Initialize crop rectangle variables
        self.bulk_crop_rect = None
        self.bulk_crop_start_x = None
        self.bulk_crop_start_y = None
        self.bulk_crop_image = None
        self.bulk_crop_photo = None
        self.bulk_crop_scale_factor = 1.0
        self.bulk_crop_box = None

        # Bind mouse events for rectangle selection
        self.bulk_crop_canvas.bind("<ButtonPress-1>", self.on_bulk_crop_press)
        self.bulk_crop_canvas.bind("<B1-Motion>", self.on_bulk_crop_drag)
        self.bulk_crop_canvas.bind("<ButtonRelease-1>", self.on_bulk_crop_release)

        # Navigation controls
        nav_frame = ttk.Frame(left_frame)
        nav_frame.pack(fill='x', pady=5)

        ttk.Button(nav_frame, text="<< Prev", command=self.bulk_crop_prev_image).pack(side='left', padx=5)
        self.bulk_crop_nav_label = tk.StringVar(value="Image: 0 / 0")
        ttk.Label(nav_frame, textvariable=self.bulk_crop_nav_label, font=('Arial', 10)).pack(side='left', padx=20)
        ttk.Button(nav_frame, text="Next >>", command=self.bulk_crop_next_image).pack(side='left', padx=5)

        self.bulk_crop_filename_label = tk.StringVar(value="")
        ttk.Label(nav_frame, textvariable=self.bulk_crop_filename_label).pack(side='left', padx=20)

        # Crop region display
        coords_frame = ttk.Frame(left_frame)
        coords_frame.pack(fill='x', pady=10)

        ttk.Label(coords_frame, text="Crop Region:").pack(side='left', padx=5)
        self.bulk_crop_coords = tk.StringVar(value="Not selected")
        ttk.Label(coords_frame, textvariable=self.bulk_crop_coords, font=('Arial', 10, 'bold')).pack(side='left', padx=5)

        # Action buttons
        action_frame = ttk.Frame(left_frame)
        action_frame.pack(fill='x', pady=10)

        ttk.Button(action_frame, text="Crop All Images", command=self.bulk_crop_all_images).pack(side='left', padx=20)
        ttk.Button(action_frame, text="Clear Selection", command=self.clear_bulk_crop_selection).pack(side='left', padx=5)

        # 1-pixel crop buttons
        pixel_crop_frame = ttk.LabelFrame(left_frame, text="Crop 1 Pixel From Edge")
        pixel_crop_frame.pack(fill='x', pady=5)

        pixel_btn_frame = ttk.Frame(pixel_crop_frame)
        pixel_btn_frame.pack(pady=5)

        ttk.Button(pixel_btn_frame, text="Left", command=lambda: self.bulk_crop_1px('left')).pack(side='left', padx=5)
        ttk.Button(pixel_btn_frame, text="Right", command=lambda: self.bulk_crop_1px('right')).pack(side='left', padx=5)
        ttk.Button(pixel_btn_frame, text="Top", command=lambda: self.bulk_crop_1px('top')).pack(side='left', padx=5)
        ttk.Button(pixel_btn_frame, text="Bottom", command=lambda: self.bulk_crop_1px('bottom')).pack(side='left', padx=5)

        # Progress bar
        self.bulk_crop_progress = ttk.Progressbar(left_frame, mode='determinate')
        self.bulk_crop_progress.pack(fill='x', pady=5)

        self.bulk_crop_status = tk.StringVar(value="Ready - Select a folder and load preview")
        ttk.Label(left_frame, textvariable=self.bulk_crop_status).pack(pady=5)

    def browse_bulk_crop_folder(self):
        folder = filedialog.askdirectory(title="Select Image Folder")
        if folder:
            self.bulk_crop_folder_path.set(folder)

    def load_bulk_crop_preview(self):
        folder = self.bulk_crop_folder_path.get()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror("Error", "Please select a valid image folder")
            return

        # Find all image files
        valid_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'}
        self.bulk_crop_image_files = []
        for f in os.listdir(folder):
            ext = os.path.splitext(f)[1].lower()
            if ext in valid_extensions:
                self.bulk_crop_image_files.append(os.path.join(folder, f))

        self.bulk_crop_image_files.sort()

        if not self.bulk_crop_image_files:
            messagebox.showerror("Error", "No valid image files found in the folder")
            return

        self.bulk_crop_image_count.set(f"{len(self.bulk_crop_image_files)} images found")
        self.bulk_crop_current_index = 0
        self.display_bulk_crop_image()
        self.bulk_crop_status.set("Preview loaded. Click and drag to select crop region.")

    def display_bulk_crop_image(self):
        if not self.bulk_crop_image_files:
            return

        img_path = self.bulk_crop_image_files[self.bulk_crop_current_index]

        # Load image with OpenCV
        frame = cv2.imread(img_path)
        if frame is None:
            messagebox.showerror("Error", f"Could not read image: {os.path.basename(img_path)}")
            return

        self.bulk_crop_original_frame = frame
        original_height, original_width = frame.shape[:2]

        # Calculate scale factor to fit in canvas
        max_width = 640
        max_height = 480

        width_scale = max_width / original_width
        height_scale = max_height / original_height
        self.bulk_crop_scale_factor = min(width_scale, height_scale, 1.0)

        if self.bulk_crop_scale_factor < 1.0:
            display_width = int(original_width * self.bulk_crop_scale_factor)
            display_height = int(original_height * self.bulk_crop_scale_factor)
            frame = cv2.resize(frame, (display_width, display_height))

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.bulk_crop_image = Image.fromarray(frame_rgb)
        self.bulk_crop_photo = ImageTk.PhotoImage(self.bulk_crop_image)

        self.bulk_crop_canvas.config(width=self.bulk_crop_image.width, height=self.bulk_crop_image.height)
        self.bulk_crop_canvas.delete("all")
        self.bulk_crop_canvas.create_image(0, 0, anchor='nw', image=self.bulk_crop_photo)

        # Update navigation labels
        self.bulk_crop_nav_label.set(f"Image: {self.bulk_crop_current_index + 1} / {len(self.bulk_crop_image_files)}")
        self.bulk_crop_filename_label.set(os.path.basename(img_path))

        # Redraw crop rectangle if exists
        if self.bulk_crop_box:
            self.redraw_bulk_crop_rect()

    def redraw_bulk_crop_rect(self):
        if self.bulk_crop_box and self.bulk_crop_scale_factor:
            # Convert original coordinates to display coordinates
            x1 = int(self.bulk_crop_box[0] * self.bulk_crop_scale_factor)
            y1 = int(self.bulk_crop_box[1] * self.bulk_crop_scale_factor)
            x2 = int(self.bulk_crop_box[2] * self.bulk_crop_scale_factor)
            y2 = int(self.bulk_crop_box[3] * self.bulk_crop_scale_factor)

            if self.bulk_crop_rect:
                self.bulk_crop_canvas.delete(self.bulk_crop_rect)
            self.bulk_crop_rect = self.bulk_crop_canvas.create_rectangle(
                x1, y1, x2, y2, outline='red', width=2
            )

    def bulk_crop_prev_image(self):
        if self.bulk_crop_image_files and self.bulk_crop_current_index > 0:
            self.bulk_crop_current_index -= 1
            self.display_bulk_crop_image()

    def bulk_crop_next_image(self):
        if self.bulk_crop_image_files and self.bulk_crop_current_index < len(self.bulk_crop_image_files) - 1:
            self.bulk_crop_current_index += 1
            self.display_bulk_crop_image()

    def on_bulk_crop_press(self, event):
        self.bulk_crop_start_x = event.x
        self.bulk_crop_start_y = event.y
        if self.bulk_crop_rect:
            self.bulk_crop_canvas.delete(self.bulk_crop_rect)
        self.bulk_crop_rect = self.bulk_crop_canvas.create_rectangle(
            self.bulk_crop_start_x, self.bulk_crop_start_y,
            self.bulk_crop_start_x, self.bulk_crop_start_y,
            outline='red', width=2
        )

    def on_bulk_crop_drag(self, event):
        if self.bulk_crop_rect:
            self.bulk_crop_canvas.coords(
                self.bulk_crop_rect,
                self.bulk_crop_start_x, self.bulk_crop_start_y,
                event.x, event.y
            )

    def on_bulk_crop_release(self, event):
        if self.bulk_crop_start_x is None or self.bulk_crop_start_y is None:
            return

        x1 = min(self.bulk_crop_start_x, event.x)
        y1 = min(self.bulk_crop_start_y, event.y)
        x2 = max(self.bulk_crop_start_x, event.x)
        y2 = max(self.bulk_crop_start_y, event.y)

        # Convert to original image coordinates
        orig_x1 = int(x1 / self.bulk_crop_scale_factor)
        orig_y1 = int(y1 / self.bulk_crop_scale_factor)
        orig_x2 = int(x2 / self.bulk_crop_scale_factor)
        orig_y2 = int(y2 / self.bulk_crop_scale_factor)

        self.bulk_crop_box = (orig_x1, orig_y1, orig_x2, orig_y2)
        width = orig_x2 - orig_x1
        height = orig_y2 - orig_y1
        self.bulk_crop_coords.set(f"({orig_x1}, {orig_y1}, {orig_x2}, {orig_y2}) - {width}x{height}")

    def clear_bulk_crop_selection(self):
        if self.bulk_crop_rect:
            self.bulk_crop_canvas.delete(self.bulk_crop_rect)
            self.bulk_crop_rect = None
        self.bulk_crop_box = None
        self.bulk_crop_coords.set("Not selected")

    def bulk_crop_all_images(self):
        if not self.bulk_crop_box:
            messagebox.showerror("Error", "Please select a crop region first")
            return

        if not self.bulk_crop_image_files:
            messagebox.showerror("Error", "No images loaded")
            return

        # Confirm action
        result = messagebox.askyesno(
            "Confirm Bulk Crop",
            f"This will crop {len(self.bulk_crop_image_files)} images to the selected region.\n\n"
            f"Crop region: {self.bulk_crop_box}\n\n"
            "Files will be overwritten. Continue?"
        )
        if not result:
            return

        def crop_thread():
            try:
                total = len(self.bulk_crop_image_files)
                self.bulk_crop_progress['maximum'] = total
                self.bulk_crop_progress['value'] = 0

                left, top, right, bottom = self.bulk_crop_box
                successful = 0
                failed = []

                for i, img_path in enumerate(self.bulk_crop_image_files):
                    self.bulk_crop_status.set(f"Cropping {i+1}/{total}: {os.path.basename(img_path)}")

                    try:
                        # Read image
                        img = cv2.imread(img_path)
                        if img is None:
                            failed.append((img_path, "Could not read image"))
                            continue

                        # Crop image
                        cropped = img[top:bottom, left:right]

                        # Save back (overwrite)
                        cv2.imwrite(img_path, cropped)
                        successful += 1

                    except Exception as e:
                        failed.append((img_path, str(e)))

                    self.bulk_crop_progress['value'] = i + 1

                self.bulk_crop_progress['value'] = total

                if failed:
                    self.bulk_crop_status.set(f"Done with errors: {successful} succeeded, {len(failed)} failed")
                    error_details = "\n".join([f"{os.path.basename(f)}: {e}" for f, e in failed[:5]])
                    if len(failed) > 5:
                        error_details += f"\n... and {len(failed) - 5} more"
                    self.root.after(0, lambda: messagebox.showwarning(
                        "Partial Success",
                        f"Cropped {successful}/{total} images.\n\nFailed:\n{error_details}"
                    ))
                else:
                    self.bulk_crop_status.set(f"Done! Cropped {total} images")
                    self.root.after(0, lambda: messagebox.showinfo(
                        "Success",
                        f"Bulk crop complete!\n{total} images cropped and saved."
                    ))

                # Reload the current image to show cropped result
                self.root.after(0, self.display_bulk_crop_image)
                # Clear the selection since image dimensions changed
                self.root.after(0, self.clear_bulk_crop_selection)

            except Exception as e:
                self.bulk_crop_progress['value'] = 0
                self.bulk_crop_status.set("Error occurred")
                self.root.after(0, lambda: messagebox.showerror("Error", f"Bulk crop failed: {str(e)}"))

        threading.Thread(target=crop_thread, daemon=True).start()

    def bulk_crop_1px(self, side):
        """Crop 1 pixel from the specified side of all images"""
        if not self.bulk_crop_image_files:
            messagebox.showerror("Error", "No images loaded")
            return

        result = messagebox.askyesno(
            "Confirm 1-Pixel Crop",
            f"This will crop 1 pixel from the {side} of {len(self.bulk_crop_image_files)} images.\n\n"
            "Files will be overwritten. Continue?"
        )
        if not result:
            return

        def crop_thread():
            try:
                total = len(self.bulk_crop_image_files)
                self.bulk_crop_progress['maximum'] = total
                self.bulk_crop_progress['value'] = 0

                successful = 0
                failed = []

                for i, img_path in enumerate(self.bulk_crop_image_files):
                    self.bulk_crop_status.set(f"Cropping {side} 1px - {i+1}/{total}: {os.path.basename(img_path)}")

                    try:
                        img = cv2.imread(img_path)
                        if img is None:
                            failed.append((img_path, "Could not read image"))
                            continue

                        h, w = img.shape[:2]

                        if side == 'left':
                            cropped = img[:, 1:]
                        elif side == 'right':
                            cropped = img[:, :w-1]
                        elif side == 'top':
                            cropped = img[1:, :]
                        elif side == 'bottom':
                            cropped = img[:h-1, :]
                        else:
                            failed.append((img_path, f"Unknown side: {side}"))
                            continue

                        cv2.imwrite(img_path, cropped)
                        successful += 1

                    except Exception as e:
                        failed.append((img_path, str(e)))

                    self.bulk_crop_progress['value'] = i + 1

                self.bulk_crop_progress['value'] = total

                if failed:
                    self.bulk_crop_status.set(f"Done with errors: {successful} succeeded, {len(failed)} failed")
                    error_details = "\n".join([f"{os.path.basename(f)}: {e}" for f, e in failed[:5]])
                    self.root.after(0, lambda: messagebox.showwarning(
                        "Partial Success",
                        f"Cropped {successful}/{total} images.\n\nFailed:\n{error_details}"
                    ))
                else:
                    self.bulk_crop_status.set(f"Done! Cropped 1px from {side} of {total} images")
                    self.root.after(0, lambda: messagebox.showinfo(
                        "Success",
                        f"Cropped 1 pixel from {side} of {total} images."
                    ))

                # Reload to show result
                self.root.after(0, self.display_bulk_crop_image)

            except Exception as e:
                self.bulk_crop_progress['value'] = 0
                self.bulk_crop_status.set("Error occurred")
                self.root.after(0, lambda: messagebox.showerror("Error", f"1-pixel crop failed: {str(e)}"))

        threading.Thread(target=crop_thread, daemon=True).start()

    def create_slow_pan_tab(self):
        tab = tk.Frame(self.content_frame, bg='white')
        self.add_tab(tab, "Slow Pan")

        # Top section - file selection
        top_frame = ttk.Frame(tab)
        top_frame.pack(fill='x', padx=10, pady=10)

        ttk.Label(top_frame, text="Input Video:").pack(side='left', padx=5)
        self.slow_pan_input_path = tk.StringVar()
        ttk.Entry(top_frame, textvariable=self.slow_pan_input_path, width=50).pack(side='left', padx=5)
        ttk.Button(top_frame, text="Browse", command=self.browse_slow_pan_input).pack(side='left', padx=5)

        self.slow_pan_video_info = tk.StringVar(value="No video selected")
        ttk.Label(top_frame, textvariable=self.slow_pan_video_info, font=('Arial', 10)).pack(side='left', padx=10)

        # Settings frame
        settings_frame = ttk.LabelFrame(tab, text="Pan Settings")
        settings_frame.pack(fill='x', padx=10, pady=10)

        # Pan duration
        dur_frame = ttk.Frame(settings_frame)
        dur_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(dur_frame, text="Pan Duration (seconds):").pack(side='left', padx=5)
        self.slow_pan_duration = tk.StringVar(value="10")
        ttk.Entry(dur_frame, textvariable=self.slow_pan_duration, width=10).pack(side='left', padx=5)

        # Output dimensions
        dims_frame = ttk.Frame(settings_frame)
        dims_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(dims_frame, text="Output Width:").pack(side='left', padx=5)
        self.slow_pan_output_width = tk.StringVar(value="1080")
        ttk.Entry(dims_frame, textvariable=self.slow_pan_output_width, width=8).pack(side='left', padx=5)

        ttk.Label(dims_frame, text="Output Height:").pack(side='left', padx=15)
        self.slow_pan_output_height = tk.StringVar(value="1920")
        ttk.Entry(dims_frame, textvariable=self.slow_pan_output_height, width=8).pack(side='left', padx=5)

        # Presets
        presets_frame = ttk.Frame(settings_frame)
        presets_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(presets_frame, text="Presets:").pack(side='left', padx=5)
        ttk.Button(presets_frame, text="Mobile Portrait (1080x1920)",
                  command=lambda: self.set_slow_pan_dims(1080, 1920)).pack(side='left', padx=5)
        ttk.Button(presets_frame, text="Mobile Landscape (1920x1080)",
                  command=lambda: self.set_slow_pan_dims(1920, 1080)).pack(side='left', padx=5)

        # Info label
        info_frame = ttk.Frame(tab)
        info_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(info_frame, text="This will scale the video to fit the output height, then pan from left to right.",
                 font=('Arial', 9, 'italic')).pack(anchor='w')

        # Process button
        ttk.Button(tab, text="Create Slow Pan Video", command=self.create_slow_pan_action).pack(pady=20)

        # Progress
        self.slow_pan_progress = ttk.Progressbar(tab, mode='determinate')
        self.slow_pan_progress.pack(fill='x', padx=10, pady=5)

        self.slow_pan_status = tk.StringVar(value="Ready - Select a video to begin")
        ttk.Label(tab, textvariable=self.slow_pan_status).pack(pady=5)

        # Load config
        self.load_slow_pan_config()

    def set_slow_pan_dims(self, width, height):
        self.slow_pan_output_width.set(str(width))
        self.slow_pan_output_height.set(str(height))

    def browse_slow_pan_input(self):
        filename = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[("Video files", "*.mp4 *.webm *.avi *.mov"), ("All files", "*.*")]
        )
        if filename:
            self.slow_pan_input_path.set(filename)
            # Show video info
            try:
                width, height = get_vid_dims(filename)
                duration = get_video_duration(filename)
                self.slow_pan_video_info.set(f"{width}x{height}, {duration:.1f}s")
            except:
                self.slow_pan_video_info.set("Could not read video info")

    def save_slow_pan_config(self):
        config = {
            'pan_duration': self.slow_pan_duration.get(),
            'output_width': self.slow_pan_output_width.get(),
            'output_height': self.slow_pan_output_height.get(),
        }
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(SLOW_PAN_CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Failed to save slow pan config: {e}")

    def load_slow_pan_config(self):
        if not os.path.exists(SLOW_PAN_CONFIG_FILE):
            return
        try:
            with open(SLOW_PAN_CONFIG_FILE, 'r') as f:
                config = json.load(f)

            if config.get('pan_duration'):
                self.slow_pan_duration.set(config['pan_duration'])
            if config.get('output_width'):
                self.slow_pan_output_width.set(config['output_width'])
            if config.get('output_height'):
                self.slow_pan_output_height.set(config['output_height'])
        except Exception as e:
            print(f"Failed to load slow pan config: {e}")

    def create_slow_pan_action(self):
        input_path = self.slow_pan_input_path.get()
        if not input_path or not os.path.exists(input_path):
            messagebox.showerror("Error", "Please select a valid input video")
            return

        try:
            pan_duration = int(self.slow_pan_duration.get())
            output_width = int(self.slow_pan_output_width.get())
            output_height = int(self.slow_pan_output_height.get())

            if pan_duration <= 0:
                raise ValueError("Duration must be positive")
            if output_width <= 0 or output_height <= 0:
                raise ValueError("Dimensions must be positive")
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid settings: {e}")
            return

        # Save config
        self.save_slow_pan_config()

        def progress_callback(current, total):
            self.slow_pan_progress['maximum'] = total
            self.slow_pan_progress['value'] = current
            self.slow_pan_status.set(f"Processing frame {current}/{total}...")

        def pan_thread():
            try:
                self.slow_pan_status.set("Creating slow pan video...")

                output = slow_pan_video(
                    input_path,
                    pan_duration,
                    output_width=output_width,
                    output_height=output_height,
                    progress_callback=lambda c, t: self.root.after(0, lambda: progress_callback(c, t))
                )

                self.root.after(0, lambda: self.slow_pan_progress.configure(value=0))
                self.root.after(0, lambda: self.slow_pan_status.set(f"Done! Saved to: {os.path.basename(output)}"))
                self.root.after(0, lambda: messagebox.showinfo("Success", f"Slow pan video created!\n{output}"))

            except Exception as e:
                import traceback
                traceback.print_exc()
                error_msg = str(e)
                self.root.after(0, lambda: self.slow_pan_progress.configure(value=0))
                self.root.after(0, lambda: self.slow_pan_status.set("Error occurred"))
                self.root.after(0, lambda msg=error_msg: messagebox.showerror("Error", f"Slow pan failed: {msg}"))

        threading.Thread(target=pan_thread, daemon=True).start()

    def create_collage_tab(self):
        tab = tk.Frame(self.content_frame, bg='white')
        self.add_tab(tab, "Collage Generator")

        # Track number of images for duration calculation
        self.collage_num_images = 0

        # Main layout - two columns
        main_frame = ttk.Frame(tab)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Left column - inputs
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))

        # Image folder selection
        folder_frame = ttk.LabelFrame(left_frame, text="Image Folder")
        folder_frame.pack(fill='x', pady=5)

        folder_row = ttk.Frame(folder_frame)
        folder_row.pack(fill='x', padx=10, pady=5)

        self.collage_folder_path = tk.StringVar()
        ttk.Entry(folder_row, textvariable=self.collage_folder_path, width=40).pack(side='left', padx=(0, 5))
        ttk.Button(folder_row, text="Browse", command=self.browse_collage_folder).pack(side='left')

        self.collage_image_count = tk.StringVar(value="No folder selected")
        ttk.Label(folder_frame, textvariable=self.collage_image_count).pack(padx=10, pady=(0, 5))

        # Canvas dimensions
        dims_frame = ttk.LabelFrame(left_frame, text="Output Video Dimensions")
        dims_frame.pack(fill='x', pady=5)

        dims_row = ttk.Frame(dims_frame)
        dims_row.pack(fill='x', padx=10, pady=5)

        ttk.Label(dims_row, text="Width:").pack(side='left', padx=(0, 5))
        self.collage_canvas_width = tk.StringVar(value="1080")
        ttk.Entry(dims_row, textvariable=self.collage_canvas_width, width=8).pack(side='left', padx=(0, 15))

        ttk.Label(dims_row, text="Height:").pack(side='left', padx=(0, 5))
        self.collage_canvas_height = tk.StringVar(value="1920")
        ttk.Entry(dims_row, textvariable=self.collage_canvas_height, width=8).pack(side='left')

        presets_row = ttk.Frame(dims_frame)
        presets_row.pack(fill='x', padx=10, pady=5)

        ttk.Label(presets_row, text="Presets:").pack(side='left', padx=(0, 5))
        ttk.Button(presets_row, text="Mobile (1080x1920)",
                  command=lambda: self.set_collage_dims(1080, 1920)).pack(side='left', padx=2)
        ttk.Button(presets_row, text="Desktop (1920x1080)",
                  command=lambda: self.set_collage_dims(1920, 1080)).pack(side='left', padx=2)

        # Image height range
        height_frame = ttk.LabelFrame(left_frame, text="Overlay Image Height Range")
        height_frame.pack(fill='x', pady=5)

        height_row = ttk.Frame(height_frame)
        height_row.pack(fill='x', padx=10, pady=5)

        ttk.Label(height_row, text="Min Height:").pack(side='left', padx=(0, 5))
        self.collage_height_min = tk.StringVar(value="100")
        ttk.Entry(height_row, textvariable=self.collage_height_min, width=8).pack(side='left', padx=(0, 15))

        ttk.Label(height_row, text="Max Height:").pack(side='left', padx=(0, 5))
        self.collage_height_max = tk.StringVar(value="300")
        ttk.Entry(height_row, textvariable=self.collage_height_max, width=8).pack(side='left')

        # Collage rate
        rate_frame = ttk.LabelFrame(left_frame, text="Collage Rate (seconds between images)")
        rate_frame.pack(fill='x', pady=5)

        rate_row = ttk.Frame(rate_frame)
        rate_row.pack(fill='x', padx=10, pady=5)

        ttk.Label(rate_row, text="Start Rate:").pack(side='left', padx=(0, 5))
        self.collage_start_rate = tk.StringVar(value="0.5")
        ttk.Entry(rate_row, textvariable=self.collage_start_rate, width=8).pack(side='left', padx=(0, 15))

        ttk.Label(rate_row, text="End Rate:").pack(side='left', padx=(0, 5))
        self.collage_end_rate = tk.StringVar(value="0.1")
        ttk.Entry(rate_row, textvariable=self.collage_end_rate, width=8).pack(side='left')

        # Expected duration display
        self.collage_expected_duration = tk.StringVar(value="Expected duration: --")
        ttk.Label(rate_frame, textvariable=self.collage_expected_duration, font=('Arial', 10, 'bold')).pack(padx=10, pady=5)

        # Add traces to update expected duration
        self.collage_start_rate.trace_add('write', self.update_collage_expected_duration)
        self.collage_end_rate.trace_add('write', self.update_collage_expected_duration)

        # Right column
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side='right', fill='both', expand=True)

        # Rotation settings
        rotation_frame = ttk.LabelFrame(right_frame, text="Random Rotation (degrees)")
        rotation_frame.pack(fill='x', pady=5)

        rot_row = ttk.Frame(rotation_frame)
        rot_row.pack(fill='x', padx=10, pady=5)

        ttk.Label(rot_row, text="Left (CCW):").pack(side='left', padx=(0, 5))
        self.collage_rotation_left = tk.StringVar(value="15")
        ttk.Entry(rot_row, textvariable=self.collage_rotation_left, width=8).pack(side='left', padx=(0, 15))

        ttk.Label(rot_row, text="Right (CW):").pack(side='left', padx=(0, 5))
        self.collage_rotation_right = tk.StringVar(value="15")
        ttk.Entry(rot_row, textvariable=self.collage_rotation_right, width=8).pack(side='left')

        # Output folder selection
        output_frame = ttk.LabelFrame(right_frame, text="Output Folder")
        output_frame.pack(fill='x', pady=5)

        output_row = ttk.Frame(output_frame)
        output_row.pack(fill='x', padx=10, pady=5)

        self.collage_output_folder = tk.StringVar()
        ttk.Entry(output_row, textvariable=self.collage_output_folder, width=40).pack(side='left', padx=(0, 5))
        ttk.Button(output_row, text="Browse", command=self.browse_collage_output).pack(side='left')

        ttk.Label(output_frame, text="Output will be saved as collage.mp4").pack(padx=10, pady=(0, 5))

        # Create button
        ttk.Button(right_frame, text="Create Collage Video", command=self.create_collage_action).pack(pady=20)

        # Progress
        self.collage_progress = ttk.Progressbar(right_frame, mode='determinate')
        self.collage_progress.pack(fill='x', pady=5)

        self.collage_status = tk.StringVar(value="Ready - Select an image folder to begin")
        ttk.Label(right_frame, textvariable=self.collage_status).pack(pady=5)

        # Load config
        self.load_collage_config()

    def set_collage_dims(self, width, height):
        self.collage_canvas_width.set(str(width))
        self.collage_canvas_height.set(str(height))

    def browse_collage_folder(self):
        folder = filedialog.askdirectory(title="Select Image Folder")
        if folder:
            self.collage_folder_path.set(folder)
            # Count valid images
            valid_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'}
            count = sum(1 for f in os.listdir(folder)
                       if os.path.splitext(f)[1].lower() in valid_extensions)
            self.collage_num_images = count
            self.collage_image_count.set(f"{count} images found")
            self.update_collage_expected_duration()

    def browse_collage_output(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.collage_output_folder.set(folder)

    def update_collage_expected_duration(self, *args):
        try:
            start_rate = float(self.collage_start_rate.get())
            end_rate = float(self.collage_end_rate.get())
            n = self.collage_num_images

            if n <= 0:
                self.collage_expected_duration.set("Expected duration: --")
                return

            # Calculate total duration (sum of linearly interpolated rates)
            total_seconds = 0
            for i in range(n):
                t = i / (n - 1) if n > 1 else 0
                rate = start_rate + t * (end_rate - start_rate)
                total_seconds += rate

            # Format as mm:ss or hh:mm:ss
            minutes = int(total_seconds // 60)
            seconds = total_seconds % 60
            if minutes >= 60:
                hours = minutes // 60
                minutes = minutes % 60
                time_str = f"{hours}h {minutes}m {seconds:.1f}s"
            elif minutes > 0:
                time_str = f"{minutes}m {seconds:.1f}s"
            else:
                time_str = f"{seconds:.1f}s"

            self.collage_expected_duration.set(f"Expected duration: {time_str}")
        except (ValueError, AttributeError):
            self.collage_expected_duration.set("Expected duration: --")

    def save_collage_config(self):
        config = {
            'folder_path': self.collage_folder_path.get(),
            'canvas_width': self.collage_canvas_width.get(),
            'canvas_height': self.collage_canvas_height.get(),
            'height_min': self.collage_height_min.get(),
            'height_max': self.collage_height_max.get(),
            'start_rate': self.collage_start_rate.get(),
            'end_rate': self.collage_end_rate.get(),
            'rotation_left': self.collage_rotation_left.get(),
            'rotation_right': self.collage_rotation_right.get(),
            'output_folder': self.collage_output_folder.get(),
        }
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(COLLAGE_CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Failed to save collage config: {e}")

    def load_collage_config(self):
        if not os.path.exists(COLLAGE_CONFIG_FILE):
            return
        try:
            with open(COLLAGE_CONFIG_FILE, 'r') as f:
                config = json.load(f)

            if config.get('folder_path'):
                self.collage_folder_path.set(config['folder_path'])
                if os.path.isdir(config['folder_path']):
                    valid_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'}
                    count = sum(1 for f in os.listdir(config['folder_path'])
                               if os.path.splitext(f)[1].lower() in valid_extensions)
                    self.collage_num_images = count
                    self.collage_image_count.set(f"{count} images found")

            if config.get('canvas_width'):
                self.collage_canvas_width.set(config['canvas_width'])
            if config.get('canvas_height'):
                self.collage_canvas_height.set(config['canvas_height'])
            if config.get('height_min'):
                self.collage_height_min.set(config['height_min'])
            if config.get('height_max'):
                self.collage_height_max.set(config['height_max'])
            if config.get('start_rate'):
                self.collage_start_rate.set(config['start_rate'])
            if config.get('end_rate'):
                self.collage_end_rate.set(config['end_rate'])
            if config.get('rotation_left'):
                self.collage_rotation_left.set(config['rotation_left'])
            if config.get('rotation_right'):
                self.collage_rotation_right.set(config['rotation_right'])
            if config.get('output_folder'):
                self.collage_output_folder.set(config['output_folder'])

            self.update_collage_expected_duration()
        except Exception as e:
            print(f"Failed to load collage config: {e}")

    def create_collage_action(self):
        # Validate inputs
        image_folder = self.collage_folder_path.get()
        if not image_folder or not os.path.isdir(image_folder):
            messagebox.showerror("Error", "Please select a valid image folder")
            return

        output_folder = self.collage_output_folder.get()
        if not output_folder or not os.path.isdir(output_folder):
            messagebox.showerror("Error", "Please select a valid output folder")
            return

        try:
            canvas_width = int(self.collage_canvas_width.get())
            canvas_height = int(self.collage_canvas_height.get())
            height_min = int(self.collage_height_min.get())
            height_max = int(self.collage_height_max.get())
            start_rate = float(self.collage_start_rate.get())
            end_rate = float(self.collage_end_rate.get())
            rotation_left = int(self.collage_rotation_left.get())
            rotation_right = int(self.collage_rotation_right.get())

            if canvas_width <= 0 or canvas_height <= 0:
                raise ValueError("Canvas dimensions must be positive")
            if height_min <= 0 or height_max <= 0 or height_min > height_max:
                raise ValueError("Invalid height range")
            if start_rate <= 0 or end_rate <= 0:
                raise ValueError("Rates must be positive")
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid settings: {e}")
            return

        # Save config
        self.save_collage_config()

        output_path = os.path.join(output_folder, "collage.mp4")

        def progress_callback(current, total):
            self.collage_progress['maximum'] = total
            self.collage_progress['value'] = current

        def collage_thread():
            try:
                self.collage_status.set("Creating collage video...")

                output, duration = create_collage_video(
                    image_folder=image_folder,
                    output_path=output_path,
                    canvas_width=canvas_width,
                    canvas_height=canvas_height,
                    height_min=height_min,
                    height_max=height_max,
                    start_rate=start_rate,
                    end_rate=end_rate,
                    rotation_left=rotation_left,
                    rotation_right=rotation_right,
                    progress_callback=lambda c, t: self.root.after(0, lambda: progress_callback(c, t))
                )

                self.root.after(0, lambda: self.collage_progress.configure(value=0))
                self.root.after(0, lambda: self.collage_status.set(f"Done! Duration: {duration:.1f}s - Saved to: {output_path}"))
                self.root.after(0, lambda: messagebox.showinfo("Success", f"Collage video created!\nDuration: {duration:.1f}s\n{output_path}"))

            except Exception as e:
                import traceback
                traceback.print_exc()
                error_msg = str(e)
                self.root.after(0, lambda: self.collage_progress.configure(value=0))
                self.root.after(0, lambda: self.collage_status.set("Error occurred"))
                self.root.after(0, lambda msg=error_msg: messagebox.showerror("Error", f"Collage creation failed: {msg}"))

        threading.Thread(target=collage_thread, daemon=True).start()


if __name__ == "__main__":
    root = tk.Tk()
    app = VideoEditorGUI(root)
    root.mainloop()
