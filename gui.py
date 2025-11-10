import os
import time
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import cv2
import numpy as np
from main import (
    mp4_to_webm, webm_to_mp4, mkv_to_mp4, convert_mp4_to_gif, mp4_to_mp3,
    crop_video, get_subclip, speed_up_mp4_video, blur_video,
    stretch_video_dims, get_vid_dims, mute_video, get_video_duration
)


class VideoEditorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Editor")
        self.root.state('zoomed')

        # Define pastel colors for tabs
        self.pastel_colors = [
            '#FFE5E5',  # Pastel pink
            '#E5F5FF',  # Pastel blue
            '#E5FFE5',  # Pastel green
            '#FFF5E5',  # Pastel orange
            '#F5E5FF',  # Pastel purple
            '#FFFFE5',  # Pastel yellow
            '#FFE5F5'   # Pastel magenta
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
            font=('Arial', 14, 'bold'),
            bg=color,
            activebackground=darker_color,
            relief='flat',
            padx=20,
            pady=10,
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

        ttk.Label(tab, text="Input Video:").grid(row=0, column=0, padx=10, pady=10, sticky='w')
        self.format_input_path = tk.StringVar()
        ttk.Entry(tab, textvariable=self.format_input_path, width=50).grid(row=0, column=1, padx=10, pady=10)
        ttk.Button(tab, text="Browse", command=self.browse_format_input).grid(row=0, column=2, padx=10, pady=10)

        ttk.Label(tab, text="Output Format:").grid(row=1, column=0, padx=10, pady=10, sticky='w')
        self.format_output_type = tk.StringVar(value="WEBM")
        format_combo = ttk.Combobox(tab, textvariable=self.format_output_type,
                                    values=["WEBM", "MP4", "GIF", "MP3"], state='readonly')
        format_combo.grid(row=1, column=1, padx=10, pady=10, sticky='w')
        format_combo.bind('<<ComboboxSelected>>', self.on_format_change)

        self.format_options_frame = ttk.LabelFrame(tab, text="Conversion Options")
        self.format_options_frame.grid(row=2, column=0, columnspan=3, padx=10, pady=10, sticky='ew')

        self.webm_crf_var = tk.IntVar(value=32)
        ttk.Label(self.format_options_frame, text="CRF Quality (lower = better):").grid(row=0, column=0, padx=10, pady=5, sticky='w')
        ttk.Scale(self.format_options_frame, from_=0, to=51, variable=self.webm_crf_var, orient='horizontal').grid(row=0, column=1, padx=10, pady=5, sticky='ew')
        ttk.Label(self.format_options_frame, textvariable=self.webm_crf_var).grid(row=0, column=2, padx=10, pady=5)

        self.use_opus_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.format_options_frame, text="Use Opus codec (better quality)",
                       variable=self.use_opus_var).grid(row=1, column=0, columnspan=3, padx=10, pady=5, sticky='w')

        self.mp4_crf_var = tk.IntVar(value=20)
        self.mp4_preset_var = tk.StringVar(value="medium")

        ttk.Button(tab, text="Convert", command=self.convert_format).grid(row=3, column=0, columnspan=3, pady=20)

        self.format_progress = ttk.Progressbar(tab, mode='indeterminate')
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
        filename = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[("Video files", "*.mp4 *.webm *.mkv *.avi *.mov"), ("All files", "*.*")]
        )
        if filename:
            self.format_input_path.set(filename)

    def convert_format(self):
        input_path = self.format_input_path.get()
        if not input_path or not os.path.exists(input_path):
            messagebox.showerror("Error", "Please select a valid input video")
            return

        def convert_thread():
            try:
                self.format_progress.start()
                self.format_status.set("Converting...")

                format_type = self.format_output_type.get()

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

                self.format_progress.stop()
                self.format_status.set(f"Done! Saved to: {os.path.basename(output)}")
                messagebox.showinfo("Success", f"Conversion complete!\n{output}")
            except Exception as e:
                self.format_progress.stop()
                self.format_status.set("Error occurred")
                messagebox.showerror("Error", f"Conversion failed: {str(e)}")

        threading.Thread(target=convert_thread, daemon=True).start()

    def create_crop_tab(self):
        tab = tk.Frame(self.content_frame, bg='white')
        self.add_tab(tab, "Crop Video")

        ttk.Label(tab, text="Input Video:").grid(row=0, column=0, padx=10, pady=10, sticky='w')
        self.crop_input_path = tk.StringVar()
        ttk.Entry(tab, textvariable=self.crop_input_path, width=50).grid(row=0, column=1, padx=10, pady=10)
        ttk.Button(tab, text="Browse", command=self.browse_crop_input).grid(row=0, column=2, padx=10, pady=10)

        ttk.Button(tab, text="Load Preview", command=self.load_crop_preview).grid(row=1, column=0, columnspan=3, pady=10)

        self.crop_canvas_frame = ttk.Frame(tab)
        self.crop_canvas_frame.grid(row=2, column=0, columnspan=3, padx=10, pady=10)

        self.crop_canvas = tk.Canvas(self.crop_canvas_frame, width=640, height=360, bg='gray')
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

        coords_frame = ttk.Frame(tab)
        coords_frame.grid(row=3, column=0, columnspan=3, pady=10)

        ttk.Label(coords_frame, text="Crop Region:").pack(side='left', padx=5)
        self.crop_coords = tk.StringVar(value="Not selected")
        ttk.Label(coords_frame, textvariable=self.crop_coords).pack(side='left', padx=5)

        ttk.Button(tab, text="Crop Video", command=self.crop_video_action).grid(row=4, column=0, columnspan=3, pady=10)

        self.crop_progress = ttk.Progressbar(tab, mode='indeterminate')
        self.crop_progress.grid(row=5, column=0, columnspan=3, padx=10, pady=10, sticky='ew')

        self.crop_status = tk.StringVar(value="Ready")
        ttk.Label(tab, textvariable=self.crop_status).grid(row=6, column=0, columnspan=3, pady=5)

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
        ret, frame = cap.read()
        cap.release()

        if not ret:
            messagebox.showerror("Error", "Could not read video frame")
            return

        self.crop_original_frame = frame
        original_height, original_width = frame.shape[:2]

        max_width = 640
        max_height = 360

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

        self.crop_status.set("Preview loaded. Click and drag to select crop region.")

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

    def crop_video_action(self):
        if not hasattr(self, 'crop_box'):
            messagebox.showerror("Error", "Please select a crop region first")
            return

        input_path = self.crop_input_path.get()

        def crop_thread():
            try:
                self.crop_progress.start()
                self.crop_status.set("Cropping video...")

                output = crop_video(input_path, self.crop_box)

                self.crop_progress.stop()
                self.crop_status.set(f"Done! Saved to: {os.path.basename(output)}")
                messagebox.showinfo("Success", f"Crop complete!\n{output}")
            except Exception as e:
                self.crop_progress.stop()
                self.crop_status.set("Error occurred")
                messagebox.showerror("Error", f"Crop failed: {str(e)}")

        threading.Thread(target=crop_thread, daemon=True).start()

    def create_trim_tab(self):
        tab = tk.Frame(self.content_frame, bg='white')
        self.add_tab(tab, "Trim/Subclip")

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

        # Main content - split into left and right
        content_frame = ttk.Frame(tab)
        content_frame.pack(fill='both', expand=True, padx=10, pady=5)

        # Left side - controls
        left_frame = ttk.Frame(content_frame)
        left_frame.pack(side='left', fill='both', expand=False, padx=(0, 10))

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

        ttk.Button(left_frame, text="Trim Video", command=self.trim_video_action).pack(fill='x', pady=10)

        self.trim_progress = ttk.Progressbar(left_frame, mode='indeterminate')
        self.trim_progress.pack(fill='x', pady=5)

        self.trim_status = tk.StringVar(value="Ready")
        ttk.Label(left_frame, textvariable=self.trim_status).pack(pady=5)

        # Right side - preview
        preview_frame = ttk.LabelFrame(content_frame, text="Video Scrubber Preview")
        preview_frame.pack(side='right', fill='both', expand=True)

        self.trim_preview_label = tk.Label(preview_frame, bg='black', width=60, height=25)
        self.trim_preview_label.pack(padx=10, pady=10)

        scrubber_frame = ttk.Frame(preview_frame)
        scrubber_frame.pack(fill='x', padx=10, pady=(0, 10))

        self.scrubber_var = tk.DoubleVar(value=0)
        self.scrubber_time_label = tk.StringVar(value="00:00")

        ttk.Label(scrubber_frame, textvariable=self.scrubber_time_label, font=('Arial', 10)).pack(pady=2)
        self.scrubber_scale = ttk.Scale(scrubber_frame, from_=0, to=100, variable=self.scrubber_var,
                                        orient='horizontal', command=self.on_scrubber_change)
        self.scrubber_scale.pack(fill='x', pady=5)

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

    def trim_video_action(self):
        input_path = self.trim_input_path.get()
        if not input_path or not os.path.exists(input_path):
            messagebox.showerror("Error", "Please select a valid input video")
            return

        start_time = self.trim_start_var.get()
        end_time = self.trim_end_var.get()

        if start_time >= end_time:
            messagebox.showerror("Error", "Start time must be less than end time")
            return

        # Release the video capture before processing
        if hasattr(self, 'trim_video_cap') and self.trim_video_cap is not None:
            self.trim_video_cap.release()
            self.trim_video_cap = None

        def trim_thread():
            try:
                # Force garbage collection and wait to ensure file handles are released
                import gc
                gc.collect()
                time.sleep(1.0)

                self.trim_progress.start()
                self.trim_status.set("Trimming video...")

                output = get_subclip(input_path, start_time, end_time)

                self.trim_progress.stop()
                self.trim_status.set(f"Done! Saved to: {os.path.basename(output)}")
                messagebox.showinfo("Success", f"Trim complete!\n{output}")
            except Exception as e:
                self.trim_progress.stop()
                self.trim_status.set("Error occurred")
                messagebox.showerror("Error", f"Trim failed: {str(e)}")

        threading.Thread(target=trim_thread, daemon=True).start()

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
        self.speed_factor_var = tk.DoubleVar(value=1.0)

        speed_scale = ttk.Scale(speed_frame, from_=0.25, to=4.0, variable=self.speed_factor_var, orient='horizontal', length=300)
        speed_scale.grid(row=0, column=1, padx=10, pady=10, sticky='ew')

        speed_label = ttk.Label(speed_frame, text="1.0x")
        speed_label.grid(row=0, column=2, padx=10, pady=10)

        def update_speed_label(*args):
            speed_label.config(text=f"{self.speed_factor_var.get():.2f}x")

        self.speed_factor_var.trace_add('write', update_speed_label)

        presets_frame = ttk.Frame(speed_frame)
        presets_frame.grid(row=1, column=0, columnspan=3, pady=10)

        ttk.Label(presets_frame, text="Presets:").pack(side='left', padx=5)
        for preset in [0.25, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0]:
            ttk.Button(presets_frame, text=f"{preset}x",
                      command=lambda p=preset: self.speed_factor_var.set(p)).pack(side='left', padx=2)

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

        speed_factor = self.speed_factor_var.get()

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

        ttk.Label(tab, text="Input Video:").grid(row=0, column=0, padx=10, pady=10, sticky='w')
        self.resize_input_path = tk.StringVar()
        ttk.Entry(tab, textvariable=self.resize_input_path, width=50).grid(row=0, column=1, padx=10, pady=10)
        ttk.Button(tab, text="Browse", command=self.browse_resize_input).grid(row=0, column=2, padx=10, pady=10)

        ttk.Button(tab, text="Get Video Dimensions", command=self.get_resize_dims).grid(row=1, column=0, columnspan=3, pady=10)

        self.current_dims = tk.StringVar(value="Current: Unknown")
        ttk.Label(tab, textvariable=self.current_dims, font=('Arial', 12, 'bold')).grid(row=2, column=0, columnspan=3, pady=10)

        dims_frame = ttk.LabelFrame(tab, text="New Dimensions")
        dims_frame.grid(row=3, column=0, columnspan=3, padx=10, pady=10, sticky='ew')

        ttk.Label(dims_frame, text="Width:").grid(row=0, column=0, padx=10, pady=5, sticky='w')
        self.new_width_var = tk.IntVar(value=1920)
        ttk.Entry(dims_frame, textvariable=self.new_width_var, width=15).grid(row=0, column=1, padx=10, pady=5)

        ttk.Label(dims_frame, text="Height:").grid(row=1, column=0, padx=10, pady=5, sticky='w')
        self.new_height_var = tk.IntVar(value=1080)
        ttk.Entry(dims_frame, textvariable=self.new_height_var, width=15).grid(row=1, column=1, padx=10, pady=5)

        self.maintain_aspect = tk.BooleanVar(value=False)
        ttk.Checkbutton(dims_frame, text="Maintain Aspect Ratio", variable=self.maintain_aspect,
                       command=self.toggle_aspect_ratio).grid(row=2, column=0, columnspan=2, pady=5)

        presets_frame = ttk.LabelFrame(tab, text="Common Presets")
        presets_frame.grid(row=4, column=0, columnspan=3, padx=10, pady=10, sticky='ew')

        presets = [
            ("480p", 854, 480),
            ("720p", 1280, 720),
            ("1080p", 1920, 1080),
            ("1440p", 2560, 1440),
            ("4K", 3840, 2160)
        ]

        for i, (name, width, height) in enumerate(presets):
            ttk.Button(presets_frame, text=name,
                      command=lambda w=width, h=height: self.set_dimensions(w, h)).grid(row=0, column=i, padx=5, pady=5)

        ttk.Button(tab, text="Resize Video", command=self.resize_video_action).grid(row=5, column=0, columnspan=3, pady=20)

        self.resize_progress = ttk.Progressbar(tab, mode='indeterminate')
        self.resize_progress.grid(row=6, column=0, columnspan=3, padx=10, pady=10, sticky='ew')

        self.resize_status = tk.StringVar(value="Ready")
        ttk.Label(tab, textvariable=self.resize_status).grid(row=7, column=0, columnspan=3, pady=5)

    def browse_resize_input(self):
        filename = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[("Video files", "*.mp4 *.webm *.avi *.mov"), ("All files", "*.*")]
        )
        if filename:
            self.resize_input_path.set(filename)

    def get_resize_dims(self):
        input_path = self.resize_input_path.get()
        if not input_path or not os.path.exists(input_path):
            messagebox.showerror("Error", "Please select a valid input video")
            return

        try:
            width, height = get_vid_dims(input_path)
            self.original_width = width
            self.original_height = height
            self.current_dims.set(f"Current: {width} x {height}")
            self.new_width_var.set(width)
            self.new_height_var.set(height)
        except Exception as e:
            messagebox.showerror("Error", f"Could not get video dimensions: {str(e)}")

    def set_dimensions(self, width, height):
        self.new_width_var.set(width)
        self.new_height_var.set(height)

    def toggle_aspect_ratio(self):
        if self.maintain_aspect.get() and hasattr(self, 'original_width'):
            self.aspect_ratio = self.original_width / self.original_height
            self.new_width_var.trace_add('write', self.update_height_from_width)
            self.new_height_var.trace_add('write', self.update_width_from_height)

    def update_height_from_width(self, *args):
        if self.maintain_aspect.get() and hasattr(self, 'aspect_ratio'):
            try:
                new_width = self.new_width_var.get()
                new_height = int(new_width / self.aspect_ratio)
                self.new_height_var.set(new_height)
            except:
                pass

    def update_width_from_height(self, *args):
        if self.maintain_aspect.get() and hasattr(self, 'aspect_ratio'):
            try:
                new_height = self.new_height_var.get()
                new_width = int(new_height * self.aspect_ratio)
                self.new_width_var.set(new_width)
            except:
                pass

    def resize_video_action(self):
        input_path = self.resize_input_path.get()
        if not input_path or not os.path.exists(input_path):
            messagebox.showerror("Error", "Please select a valid input video")
            return

        new_width = self.new_width_var.get()
        new_height = self.new_height_var.get()

        def resize_thread():
            try:
                self.resize_progress.start()
                self.resize_status.set(f"Resizing to {new_width}x{new_height}...")

                output = stretch_video_dims(input_path, new_width, new_height)

                self.resize_progress.stop()
                self.resize_status.set(f"Done! Saved to: {os.path.basename(output)}")
                messagebox.showinfo("Success", f"Resize complete!\n{output}")
            except Exception as e:
                self.resize_progress.stop()
                self.resize_status.set("Error occurred")
                messagebox.showerror("Error", f"Resize failed: {str(e)}")

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


if __name__ == "__main__":
    root = tk.Tk()
    app = VideoEditorGUI(root)
    root.mainloop()
