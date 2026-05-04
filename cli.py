#!/usr/bin/env python3
"""
Video Editor CLI - Command-line interface for video editing operations.

Usage:
    python cli.py <command> [options]

Run 'python cli.py --help' for full usage information.
"""
import argparse
import os
import sys
import time

import cv2
import matplotlib.pyplot as plt
import numpy as np
from moviepy import vfx
from moviepy.video.io.VideoFileClip import VideoFileClip


# ---------------------------------------------------------------------------
# Video processing functions
# ---------------------------------------------------------------------------

def mp4_to_webm(input_video_path, crf=32, use_opus=True):
    """
    MP4 -> WEBM (VP9 + Opus/Vorbis)
    - Output path: same folder, same basename, .webm extension
    """
    base, _ = os.path.splitext(input_video_path)
    output_path = base + ".webm"
    clip = VideoFileClip(input_video_path)

    common_ffmpeg = ["-b:v", "0", "-crf", str(crf)]

    if use_opus:
        try:
            clip.write_videofile(
                output_path,
                codec="libvpx-vp9",
                audio=True,
                audio_codec="libopus",
                audio_fps=48000,  # Opus requires 48k
                temp_audiofile=base + "_temp.opus",
                remove_temp=True,
                ffmpeg_params=common_ffmpeg,
            )
            return output_path
        except Exception:
            pass

    clip.write_videofile(
        output_path,
        codec="libvpx-vp9",
        audio=True,
        audio_codec="libvorbis",
        temp_audiofile=base + "_temp.ogg",
        remove_temp=True,
        ffmpeg_params=common_ffmpeg,
    )
    return output_path


def webm_to_mp4(input_video_path, crf=20, preset="medium"):
    """
    WEBM -> MP4 (H.264 + AAC)
    - Output path: same folder, same basename, .mp4 extension
    """
    base, _ = os.path.splitext(input_video_path)
    output_path = base + ".mp4"
    clip = VideoFileClip(input_video_path)
    clip.write_videofile(
        output_path,
        codec="libx264",
        audio=True,
        audio_codec="aac",
        ffmpeg_params=["-crf", str(crf), "-preset", preset],
    )
    return output_path


def mkv_to_mp4(input_video_path, crf=20, preset="medium"):
    """
    MKV -> MP4 (H.264 + AAC)
    - Output path: same folder, same basename, .mp4 extension
    """
    base, _ = os.path.splitext(input_video_path)
    output_path = base + ".mp4"
    clip = VideoFileClip(input_video_path)
    clip.write_videofile(
        output_path,
        codec="libx264",
        audio=True,
        audio_codec="aac",
        ffmpeg_params=["-crf", str(crf), "-preset", preset],
    )
    return output_path


def select_roi_from_video(video_path):
    cap = cv2.VideoCapture(video_path)

    ret, frame = cap.read()
    cap.release()

    if not ret:
        raise ValueError("Could not read the first frame from video")

    # Get original frame dimensions
    original_height, original_width = frame.shape[:2]

    # Get screen dimensions (approximate max display size)
    max_display_width = 1200
    max_display_height = 800

    # Calculate scaling factor to fit on screen
    width_scale = max_display_width / original_width
    height_scale = max_display_height / original_height
    scale_factor = min(width_scale, height_scale, 1.0)  # Don't scale up

    # Resize frame for display if needed
    if scale_factor < 1.0:
        display_width = int(original_width * scale_factor)
        display_height = int(original_height * scale_factor)
        display_frame = cv2.resize(frame, (display_width, display_height))
        print(
            f"Video scaled down by {scale_factor:.2f}x for display ({original_width}x{original_height} -> {display_width}x{display_height})"
        )
    else:
        display_frame = frame
        scale_factor = 1.0

    roi = cv2.selectROI(
        "Select ROI", display_frame, fromCenter=False, showCrosshair=True
    )
    cv2.destroyAllWindows()

    left, top, width, height = roi

    # Scale ROI coordinates back to original video dimensions
    if scale_factor < 1.0:
        left = int(left / scale_factor)
        top = int(top / scale_factor)
        width = int(width / scale_factor)
        height = int(height / scale_factor)

    right, bottom = left + width, top + height
    print(f"Selected ROI (original coordinates): ({left}, {top}, {right}, {bottom})")
    return left, top, right, bottom


def show_frame_from_vid(video_path):
    first_frame = cv2.VideoCapture(video_path).read()[1]
    plt.imshow(cv2.cvtColor(first_frame, cv2.COLOR_BGR2RGB))
    plt.show()


def crop_image(image, box):
    left, top, right, bottom = box
    return image[top:bottom, left:right]


def crop_video(input_video_path, box, asyncly=False):
    def func():
        import subprocess

        print(f"Cropping this video {os.path.basename(input_video_path)} to {box}")
        start_time = time.time()

        left, top, right, bottom = box
        width = right - left
        height = bottom - top

        # Ensure dimensions are even (required for h264)
        width = width - (width % 2)
        height = height - (height % 2)

        temp_video_path = input_video_path.replace(
            ".mp4", f"_cropped_temp_{box[0]}_{box[1]}_{box[2]}_{box[3]}.mp4"
        )

        # Use ffmpeg to crop video with audio preserved
        cmd = [
            "ffmpeg", "-y",
            "-i", input_video_path,
            "-vf", f"crop={width}:{height}:{left}:{top}",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-c:a", "copy",
            temp_video_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"ffmpeg error: {result.stderr}")

        if os.path.exists(input_video_path):
            os.remove(input_video_path)

        os.rename(temp_video_path, input_video_path)

        time_taken = round((time.time() - start_time), 2)
        print(
            f"Saved cropped video as {os.path.basename(input_video_path)} in {time_taken}s (overwritten)"
        )
        return input_video_path

    if not asyncly:
        return func()
    else:
        import threading

        thread = threading.Thread(target=func)
        thread.start()
        return thread


def get_subclip(input_video_path, start_time, end_time):
    subclip_start_time = time.time()

    print(f"Clipping video from {start_time}s to {end_time}s")

    temp_output_path = input_video_path.replace(
        ".mp4", f"_subclip_temp_{start_time}_{end_time}.mp4"
    )

    clip = VideoFileClip(input_video_path)
    subclip = clip.subclipped(start_time, end_time)
    subclip.write_videofile(temp_output_path, codec="libx264")

    # Close both clips to release file handles
    subclip.close()
    clip.close()

    # Force garbage collection and wait for file handles to be released
    import gc
    import time as time_module
    gc.collect()
    time_module.sleep(1.5)

    # Retry logic for file operations
    max_retries = 5
    for attempt in range(max_retries):
        try:
            if os.path.exists(input_video_path):
                os.remove(input_video_path)
            os.rename(temp_output_path, input_video_path)
            break
        except PermissionError as e:
            if attempt < max_retries - 1:
                print(f"File locked, retrying in 1 second... (attempt {attempt + 1}/{max_retries})")
                time_module.sleep(1)
            else:
                raise Exception(f"Could not access file after {max_retries} attempts. Please close any programs using the video file.") from e

    time_taken = round((time.time() - subclip_start_time), 2)
    print(f"Saved subclip as {os.path.basename(input_video_path)} in {time_taken}s (overwritten)")

    return input_video_path


def convert_mp4_to_gif(input_video_path):
    # Generate the output GIF file path by replacing the .mp4 extension with .gif
    output_gif_path = input_video_path.replace(".mp4", ".gif")

    # Load the video file into a VideoFileClip object
    clip = VideoFileClip(input_video_path)

    # Write the video clip to a GIF file
    clip.write_gif(output_gif_path)

    return output_gif_path


def speed_up_mp4_video(input_video_path, speed_factor: float):
    start_time = time.time()

    temp_output_path = input_video_path.replace(".mp4", f"_sped_temp_{speed_factor}.mp4")
    clip = VideoFileClip(input_video_path).with_effects([vfx.MultiplySpeed(speed_factor)])
    clip.write_videofile(temp_output_path, codec="libx264")
    clip.close()

    import gc
    import time as time_module
    gc.collect()
    time_module.sleep(1.5)

    max_retries = 5
    for attempt in range(max_retries):
        try:
            if os.path.exists(input_video_path):
                os.remove(input_video_path)
            os.rename(temp_output_path, input_video_path)
            break
        except PermissionError as e:
            if attempt < max_retries - 1:
                print(f"File locked, retrying in 1 second... (attempt {attempt + 1}/{max_retries})")
                time_module.sleep(1)
            else:
                raise Exception(f"Could not access file after {max_retries} attempts.") from e

    time_taken = round((time.time() - start_time), 2)
    print(f"Saved sped video as {os.path.basename(input_video_path)} in {time_taken}s (overwritten)")

    return input_video_path


def blur_video(video_path, region):
    # expects a region of XYXY
    print(f"blurring this video: {os.path.basename(video_path)}")
    cap = cv2.VideoCapture(video_path)

    # Define the region (left, top, right, bottom)
    left, top, right, bottom = region

    # Define the kernel size for the blur
    kernel_size = (15, 15)  # Adjust for desired blur effect

    # Get the video properties
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Create the temp output video path
    base, ext = os.path.splitext(video_path)
    temp_output_path = f"{base}_blurred_temp{ext}"

    # Create the VideoWriter object
    out = cv2.VideoWriter(temp_output_path, fourcc, fps, (width, height))

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Extract the region to be blurred
        region = frame[top:bottom, left:right]

        # Apply Gaussian blur to the region
        blurred_region = cv2.GaussianBlur(region, kernel_size, 0)

        # Replace the original region with the blurred region
        frame[top:bottom, left:right] = blurred_region

        # Write the frame to the output video
        out.write(frame)

    cap.release()
    out.release()
    cv2.destroyAllWindows()

    if os.path.exists(video_path):
        os.remove(video_path)

    os.rename(temp_output_path, video_path)

    print(f"blurred this video: {os.path.basename(video_path)}! (overwritten)")
    return video_path


def get_vid_dims(video_path):
    cap = cv2.VideoCapture(video_path)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    return width, height


def stretch_video_dims(video_path, new_x, new_y):
    print(f"Stretching {os.path.basename(video_path)} to {new_x}x{new_y}")
    temp_video_path = video_path.replace(".mp4", f"_stretched_temp_{new_x}_{new_y}.mp4")
    cap = cv2.VideoCapture(video_path)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    out = cv2.VideoWriter(temp_video_path, fourcc, fps, (new_x, new_y))
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.resize(frame, (new_x, new_y), interpolation=cv2.INTER_LINEAR)
        out.write(frame)
    cap.release()
    out.release()

    if os.path.exists(video_path):
        os.remove(video_path)

    os.rename(temp_video_path, video_path)

    print(f"Stretched video saved as {os.path.basename(video_path)} (overwritten)")
    return video_path


def get_video_duration(video_path):
    clip = VideoFileClip(video_path)
    return clip.duration


def mp4_to_mp3(video_path):
    audio_path = video_path.replace(".mp4", ".mp3")
    clip = VideoFileClip(video_path)
    clip.audio.write_audiofile(audio_path)
    return audio_path


def mute_video(video_path):
    print(f"Muting video: {video_path}")
    clip = VideoFileClip(video_path)
    audio = clip.audio
    if audio:
        audio = audio.volumex(0)
        temp_output_path = video_path.replace(".mp4", "_muted_temp.mp4")
        clip.set_audio(audio).write_videofile(temp_output_path, codec="libx264")
        clip.close()

        if os.path.exists(video_path):
            os.remove(video_path)

        os.rename(temp_output_path, video_path)
        print(f"Muted video saved (overwritten)")
        return video_path
    else:
        print("No audio track found in the video.")
        return video_path


def adjust_brightness_video(video_path, brightness_factor):
    """
    Adjust brightness of a video in place.
    brightness_factor: float, 1.0 = no change, >1.0 = brighter, <1.0 = darker
    """
    print(f"Adjusting brightness of {os.path.basename(video_path)} by factor {brightness_factor}")
    start_time = time.time()

    base, ext = os.path.splitext(video_path)
    temp_output_path = f"{base}_brightness_temp{ext}"

    cap = cv2.VideoCapture(video_path)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    out = cv2.VideoWriter(temp_output_path, fourcc, fps, (width, height))

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Convert to float, apply brightness, clip to valid range, convert back
        adjusted = frame.astype(np.float32) * brightness_factor
        adjusted = np.clip(adjusted, 0, 255).astype(np.uint8)

        out.write(adjusted)

    cap.release()
    out.release()

    if os.path.exists(video_path):
        os.remove(video_path)

    os.rename(temp_output_path, video_path)

    time_taken = round((time.time() - start_time), 2)
    print(f"Brightness adjusted video saved as {os.path.basename(video_path)} in {time_taken}s (overwritten)")
    return video_path


def create_slideshow(image_folder, output_path, start_duration, end_duration,
                     shuffle_images=False, random_rotation=False,
                     rotation_left=0, rotation_right=0, sound_effect_path=None,
                     scale_mode='stretch', progress_callback=None):
    """
    Create a slideshow video from images in a folder.

    Args:
        image_folder: Path to folder containing images
        output_path: Full path to output MP4 file
        start_duration: Duration in seconds for first image
        end_duration: Duration in seconds for last image (interpolates between)
        shuffle_images: Whether to randomize image order
        random_rotation: Whether to apply random rotation to each image
        rotation_left: Max degrees to rotate left (negative rotation)
        rotation_right: Max degrees to rotate right (positive rotation)
        sound_effect_path: Optional path to sound file to play on each transition
        scale_mode: 'stretch', 'fit', or 'crop'
        progress_callback: Optional callback(current, total) for progress updates
    """
    from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip
    from PIL import Image
    import random
    import tempfile

    # Get list of image files
    valid_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'}
    image_files = []
    for f in os.listdir(image_folder):
        ext = os.path.splitext(f)[1].lower()
        if ext in valid_extensions:
            image_files.append(os.path.join(image_folder, f))

    if not image_files:
        raise ValueError("No valid image files found in the folder")

    # Sort by name initially
    image_files.sort()

    # Shuffle if requested
    if shuffle_images:
        random.shuffle(image_files)

    print(f"Creating slideshow from {len(image_files)} images")

    # Determine output resolution from first image
    first_img = Image.open(image_files[0])
    output_width, output_height = first_img.size
    first_img.close()

    # Ensure dimensions are divisible by 2 (required for h264/yuv420p)
    output_width = output_width - (output_width % 2)
    output_height = output_height - (output_height % 2)

    # Calculate duration for each image (linear interpolation)
    num_images = len(image_files)
    if num_images == 1:
        durations = [start_duration]
    else:
        durations = []
        for i in range(num_images):
            t = i / (num_images - 1)
            duration = start_duration + t * (end_duration - start_duration)
            durations.append(duration)

    clips = []
    temp_files = []

    for i, img_path in enumerate(image_files):
        if progress_callback:
            progress_callback(i, num_images)

        # Load and process image
        img = Image.open(img_path)

        # Apply random rotation if enabled
        if random_rotation and (rotation_left > 0 or rotation_right > 0):
            angle = random.uniform(-rotation_left, rotation_right)
            img = img.rotate(angle, expand=True, fillcolor=(0, 0, 0))

        # Scale to match output resolution
        if scale_mode == 'stretch':
            img = img.resize((output_width, output_height), Image.LANCZOS)
        elif scale_mode == 'fit':
            # Fit with black bars
            img.thumbnail((output_width, output_height), Image.LANCZOS)
            background = Image.new('RGB', (output_width, output_height), (0, 0, 0))
            offset = ((output_width - img.width) // 2, (output_height - img.height) // 2)
            background.paste(img, offset)
            img = background
        elif scale_mode == 'crop':
            # Crop to fill
            img_ratio = img.width / img.height
            output_ratio = output_width / output_height
            if img_ratio > output_ratio:
                # Image is wider, crop width
                new_width = int(img.height * output_ratio)
                left = (img.width - new_width) // 2
                img = img.crop((left, 0, left + new_width, img.height))
            else:
                # Image is taller, crop height
                new_height = int(img.width / output_ratio)
                top = (img.height - new_height) // 2
                img = img.crop((0, top, img.width, top + new_height))
            img = img.resize((output_width, output_height), Image.LANCZOS)

        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')

        # Save temp file for moviepy (use system temp dir to avoid polluting input folder)
        temp_path = os.path.join(tempfile.gettempdir(), f"_slideshow_temp_{i}.png")
        img.save(temp_path)
        temp_files.append(temp_path)
        img.close()

        # Create clip
        clip = ImageClip(temp_path).with_duration(durations[i])
        clips.append(clip)

    if progress_callback:
        progress_callback(num_images, num_images)

    final_clip = None
    sound_clips = []

    try:
        # Concatenate all clips
        print("Concatenating clips...")
        final_clip = concatenate_videoclips(clips, method="compose")

        # Add sound effects if provided
        if sound_effect_path and os.path.exists(sound_effect_path):
            print("Adding sound effects...")
            # Load once to get the duration
            sample_sound = AudioFileClip(sound_effect_path)
            sound_duration = sample_sound.duration
            sample_sound.close()
            print(f"Sound effect duration: {sound_duration}s")

            current_time = 0
            for i in range(num_images):
                if i > 0:  # Sound on each transition (not on first frame)
                    sound = AudioFileClip(sound_effect_path)
                    # Set start time and explicitly set end time to prevent access beyond duration
                    sound = sound.with_start(current_time).with_end(current_time + sound_duration)
                    sound_clips.append(sound)
                current_time += durations[i]

            if sound_clips:
                # Set the composite audio duration to match the video
                composite_audio = CompositeAudioClip(sound_clips).with_duration(final_clip.duration)
                final_clip = final_clip.with_audio(composite_audio)

        # Write output
        print(f"Writing output to {output_path}...")
        final_clip.write_videofile(
            output_path,
            codec="libx264",
            fps=30,
            ffmpeg_params=["-pix_fmt", "yuv420p"]
        )

        print(f"Slideshow saved to {output_path}")
        return output_path

    finally:
        # Always cleanup, even on error
        print("Cleaning up temp files...")
        if final_clip:
            final_clip.close()
        for clip in clips:
            try:
                clip.close()
            except:
                pass
        for sound in sound_clips:
            try:
                sound.close()
            except:
                pass
        for temp_path in temp_files:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass


def slow_pan_video(input_video_path, pan_duration, output_width=1080, output_height=1920, progress_callback=None):
    """
    Create a slow pan effect from a landscape video to a mobile portrait format.

    Args:
        input_video_path: Path to input video
        pan_duration: Duration in seconds for the pan
        output_width: Output video width (default 1080 for mobile)
        output_height: Output video height (default 1920 for mobile)
        progress_callback: Optional callback(current_frame, total_frames) for progress

    Returns:
        Path to output video
    """
    import subprocess

    print(f"Creating slow pan for {os.path.basename(input_video_path)}")

    # Ensure output dimensions are even (required for h264)
    output_width = output_width - (output_width % 2)
    output_height = output_height - (output_height % 2)

    print(f"Pan duration: {pan_duration}s, Output: {output_width}x{output_height}")
    start_time = time.time()

    # Get input video dimensions
    cap = cv2.VideoCapture(input_video_path)
    orig_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    print(f"Input: {orig_width}x{orig_height}, {fps} fps, {total_frames} frames")

    # Calculate scaled dimensions (scale so height matches output height)
    scale_factor = output_height / orig_height
    scaled_width = int(orig_width * scale_factor)
    scaled_height = output_height

    # Ensure even dimensions
    scaled_width = scaled_width - (scaled_width % 2)
    scaled_height = scaled_height - (scaled_height % 2)

    print(f"Scaled: {scaled_width}x{scaled_height}")

    # Calculate pan distance
    pan_distance = scaled_width - output_width
    if pan_distance <= 0:
        raise ValueError(f"Video is not wide enough to pan. Scaled width ({scaled_width}) must be > output width ({output_width})")

    print(f"Pan distance: {pan_distance} pixels")

    # Output path
    base, ext = os.path.splitext(input_video_path)
    temp_output_path = f"{base}_slowpan_temp{ext}"

    # Calculate total output frames
    output_total_frames = int(pan_duration * fps)

    # Create video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(temp_output_path, fourcc, fps, (output_width, output_height))

    # Process frames
    cap = cv2.VideoCapture(input_video_path)

    for frame_idx in range(output_total_frames):
        # Calculate which source frame to use (loop if needed)
        source_frame_idx = frame_idx % total_frames
        cap.set(cv2.CAP_PROP_POS_FRAMES, source_frame_idx)
        ret, frame = cap.read()

        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = cap.read()
            if not ret:
                break

        # Scale the frame
        scaled_frame = cv2.resize(frame, (scaled_width, scaled_height))

        # Calculate pan position (linear from left to right)
        t = frame_idx / (output_total_frames - 1) if output_total_frames > 1 else 0
        x_offset = int(t * pan_distance)

        # Crop the viewport (use .copy() to ensure contiguous array for VideoWriter)
        cropped = scaled_frame[:, x_offset:x_offset + output_width].copy()

        out.write(cropped)

        if progress_callback and frame_idx % 30 == 0:
            progress_callback(frame_idx, output_total_frames)

    cap.release()
    out.release()

    if progress_callback:
        progress_callback(output_total_frames, output_total_frames)

    # Now mux audio from original video using ffmpeg
    final_output_path = f"{base}_slowpan{ext}"

    # Check if original has audio
    probe_cmd = ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_type", "-of", "csv=p=0", input_video_path]
    probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
    has_audio = "audio" in probe_result.stdout

    if has_audio:
        print("Muxing audio...")
        # Get audio from original and combine with new video
        mux_cmd = [
            "ffmpeg", "-y",
            "-i", temp_output_path,
            "-i", input_video_path,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-map", "0:v:0",
            "-map", "1:a:0?",
            "-c:a", "aac",
            "-shortest",
            final_output_path
        ]
        result = subprocess.run(mux_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Audio mux warning: {result.stderr}")
            # Fall back to video only
            os.rename(temp_output_path, final_output_path)
        else:
            os.remove(temp_output_path)
    else:
        # No audio, just re-encode for compatibility
        encode_cmd = [
            "ffmpeg", "-y",
            "-i", temp_output_path,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            final_output_path
        ]
        result = subprocess.run(encode_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"ffmpeg error: {result.stderr}")
        os.remove(temp_output_path)

    time_taken = round((time.time() - start_time), 2)
    print(f"Slow pan video saved as {os.path.basename(final_output_path)} in {time_taken}s")

    return final_output_path


def create_collage_video(
    image_folder,
    output_path,
    canvas_width=1080,
    canvas_height=1920,
    height_min=100,
    height_max=300,
    start_rate=0.5,
    end_rate=0.1,
    rotation_left=15,
    rotation_right=15,
    fps=30,
    progress_callback=None
):
    """
    Create a collage video where images appear and stack on a canvas.

    Args:
        image_folder: Path to folder containing images
        output_path: Full path to output MP4 file
        canvas_width: Output video width
        canvas_height: Output video height
        height_min: Minimum height for resized images
        height_max: Maximum height for resized images
        start_rate: Seconds between images at start
        end_rate: Seconds between images at end
        rotation_left: Max degrees to rotate left (negative)
        rotation_right: Max degrees to rotate right (positive)
        fps: Output video framerate
        progress_callback: Optional callback(current, total) for progress updates

    Returns:
        Path to output video, total duration in seconds
    """
    import subprocess
    from PIL import Image
    import random

    print(f"Creating collage video from {image_folder}")
    start_time = time.time()

    # Ensure even dimensions
    canvas_width = canvas_width - (canvas_width % 2)
    canvas_height = canvas_height - (canvas_height % 2)

    # Get list of image files
    valid_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'}
    image_files = []
    for f in os.listdir(image_folder):
        ext = os.path.splitext(f)[1].lower()
        if ext in valid_extensions:
            image_files.append(os.path.join(image_folder, f))

    if not image_files:
        raise ValueError("No valid image files found in the folder")

    image_files.sort()
    random.shuffle(image_files)
    num_images = len(image_files)

    print(f"Found {num_images} images")
    print(f"Canvas: {canvas_width}x{canvas_height}, Image height range: {height_min}-{height_max}")
    print(f"Rate: {start_rate}s -> {end_rate}s, Rotation: -{rotation_left} to +{rotation_right} degrees")

    # Calculate timing for each image (linear interpolation of rate)
    image_times = []
    current_time = 0
    for i in range(num_images):
        image_times.append(current_time)
        # Interpolate rate
        t = i / (num_images - 1) if num_images > 1 else 0
        rate = start_rate + t * (end_rate - start_rate)
        current_time += rate

    total_duration = current_time
    total_frames = int(total_duration * fps)

    print(f"Total duration: {total_duration:.2f}s, Total frames: {total_frames}")

    # Preload and process all images
    processed_images = []
    for i, img_path in enumerate(image_files):
        if progress_callback:
            progress_callback(i, num_images + total_frames)

        img = Image.open(img_path)

        # Convert to RGBA for rotation with transparency
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        # Resize to random height within range, maintaining aspect ratio
        target_height = random.randint(height_min, height_max)
        aspect = img.width / img.height
        target_width = int(target_height * aspect)
        img = img.resize((target_width, target_height), Image.LANCZOS)

        # Apply random rotation
        if rotation_left > 0 or rotation_right > 0:
            angle = random.uniform(-rotation_left, rotation_right)
            img = img.rotate(angle, expand=True, fillcolor=(0, 0, 0, 0))

        # Random position (ensure at least part of image is visible)
        x = random.randint(-img.width // 2, canvas_width - img.width // 2)
        y = random.randint(-img.height // 2, canvas_height - img.height // 2)

        processed_images.append({
            'img': img,
            'x': x,
            'y': y,
            'time': image_times[i]
        })

    # Create video
    temp_output_path = output_path.replace('.mp4', '_temp.mp4')
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(temp_output_path, fourcc, fps, (canvas_width, canvas_height))

    # Create base canvas (black)
    canvas = Image.new('RGB', (canvas_width, canvas_height), (0, 0, 0))

    current_image_idx = 0

    for frame_idx in range(total_frames):
        if progress_callback and frame_idx % 10 == 0:
            progress_callback(num_images + frame_idx, num_images + total_frames)

        frame_time = frame_idx / fps

        # Add any images that should appear by this time
        while current_image_idx < num_images and processed_images[current_image_idx]['time'] <= frame_time:
            img_data = processed_images[current_image_idx]
            # Paste image onto canvas (with alpha compositing)
            canvas.paste(img_data['img'], (img_data['x'], img_data['y']), img_data['img'])
            current_image_idx += 1

        # Convert to BGR for OpenCV
        frame_bgr = cv2.cvtColor(np.array(canvas), cv2.COLOR_RGB2BGR)
        out.write(frame_bgr)

    out.release()

    # Re-encode for compatibility
    print("Encoding final video...")
    encode_cmd = [
        "ffmpeg", "-y",
        "-i", temp_output_path,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        output_path
    ]
    result = subprocess.run(encode_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"ffmpeg error: {result.stderr}")
    os.remove(temp_output_path)

    if progress_callback:
        progress_callback(num_images + total_frames, num_images + total_frames)

    time_taken = round((time.time() - start_time), 2)
    print(f"Collage video saved as {os.path.basename(output_path)} in {time_taken}s")

    return output_path, total_duration


# ---------------------------------------------------------------------------
# CLI command handlers
# ---------------------------------------------------------------------------

def cmd_convert(args):
    input_path = args.input
    fmt = args.format.lower()

    if fmt == "webm":
        result = mp4_to_webm(input_path, crf=args.crf)
    elif fmt == "mp4":
        ext = os.path.splitext(input_path)[1].lower()
        if ext == ".webm":
            result = webm_to_mp4(input_path, crf=args.crf, preset=args.preset)
        elif ext == ".mkv":
            result = mkv_to_mp4(input_path, crf=args.crf, preset=args.preset)
        else:
            print(f"Error: Cannot convert {ext} to mp4. Supported sources: .webm, .mkv")
            sys.exit(1)
    elif fmt == "gif":
        result = convert_mp4_to_gif(input_path)
    elif fmt == "mp3":
        result = mp4_to_mp3(input_path)
    else:
        print(f"Error: Unsupported format '{fmt}'. Use: webm, mp4, gif, mp3")
        sys.exit(1)

    print(f"Output: {result}")


def cmd_crop(args):
    if args.box:
        box = tuple(map(int, args.box.split(",")))
        if len(box) != 4:
            print("Error: --box must be 4 comma-separated integers: left,top,right,bottom")
            sys.exit(1)
    else:
        print("Select crop region interactively...")
        box = select_roi_from_video(args.input)

    crop_video(args.input, box)


def cmd_trim(args):
    result = get_subclip(args.input, args.start, args.end)
    print(f"Output: {result}")


def cmd_speed(args):
    if args.duration:
        clip = VideoFileClip(args.input)
        factor = clip.duration / args.duration
        clip.close()
        print(f"Target duration: {args.duration}s -> speed factor: {factor:.2f}x")
    elif args.factor:
        factor = args.factor
    else:
        print("Error: provide either a speed factor or --duration")
        sys.exit(1)
    result = speed_up_mp4_video(args.input, factor)
    print(f"Output: {result}")


def cmd_blur(args):
    if args.region:
        region = tuple(map(int, args.region.split(",")))
        if len(region) != 4:
            print("Error: --region must be 4 comma-separated integers: left,top,right,bottom")
            sys.exit(1)
    else:
        print("Select blur region interactively...")
        region = select_roi_from_video(args.input)

    result = blur_video(args.input, region)
    print(f"Output: {result}")


def cmd_resize(args):
    if args.info:
        w, h = get_vid_dims(args.input)
        dur = get_video_duration(args.input)
        print(f"Dimensions: {w}x{h}")
        print(f"Duration: {dur:.2f}s")
        return

    if not args.width or not args.height:
        print("Error: --width and --height are required (or use --info to view dimensions)")
        sys.exit(1)

    result = stretch_video_dims(args.input, args.width, args.height)
    print(f"Output: {result}")


def cmd_audio(args):
    if args.mute:
        result = mute_video(args.input)
        print(f"Output: {result}")
    elif args.extract:
        result = mp4_to_mp3(args.input)
        print(f"Output: {result}")
    else:
        print("Error: Specify --mute or --extract")
        sys.exit(1)


def cmd_brightness(args):
    result = adjust_brightness_video(args.input, args.factor)
    print(f"Output: {result}")


def cmd_slideshow(args):
    result = create_slideshow(
        image_folder=args.folder,
        output_path=args.output,
        start_duration=args.start_duration,
        end_duration=args.end_duration,
        shuffle_images=args.shuffle,
        random_rotation=args.rotate,
        rotation_left=args.rotate_left,
        rotation_right=args.rotate_right,
        sound_effect_path=args.sound,
        scale_mode=args.scale_mode,
    )
    print(f"Output: {result}")


def cmd_slowpan(args):
    result = slow_pan_video(
        input_video_path=args.input,
        pan_duration=args.duration,
        output_width=args.width,
        output_height=args.height,
    )
    print(f"Output: {result}")


def cmd_collage(args):
    result, duration = create_collage_video(
        image_folder=args.folder,
        output_path=args.output,
        canvas_width=args.width,
        canvas_height=args.height,
        height_min=args.height_min,
        height_max=args.height_max,
        start_rate=args.start_rate,
        end_rate=args.end_rate,
        rotation_left=args.rotate_left,
        rotation_right=args.rotate_right,
        fps=args.fps,
    )
    print(f"Output: {result} ({duration:.2f}s)")


def cmd_info(args):
    w, h = get_vid_dims(args.input)
    dur = get_video_duration(args.input)
    print(f"File:       {os.path.basename(args.input)}")
    print(f"Dimensions: {w}x{h}")
    print(f"Duration:   {dur:.2f}s")


def main():
    parser = argparse.ArgumentParser(
        prog="video-editor",
        description="Video Editor CLI - All video editing operations from the command line.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # convert
    p = subparsers.add_parser("convert", help="Convert video between formats (webm, mp4, gif, mp3)")
    p.add_argument("input", help="Input video file path")
    p.add_argument("format", help="Target format: webm, mp4, gif, mp3")
    p.add_argument("--crf", type=int, default=20, help="Quality (CRF value, default: 20)")
    p.add_argument("--preset", default="medium", help="Encoding preset (default: medium)")
    p.set_defaults(func=cmd_convert)

    # crop
    p = subparsers.add_parser("crop", help="Crop video to a region")
    p.add_argument("input", help="Input video file path")
    p.add_argument("--box", help="Crop box as left,top,right,bottom (e.g. 100,50,500,400). Interactive if omitted.")
    p.set_defaults(func=cmd_crop)

    # trim
    p = subparsers.add_parser("trim", help="Trim/subclip video to a time range")
    p.add_argument("input", help="Input video file path")
    p.add_argument("start", type=float, help="Start time in seconds")
    p.add_argument("end", type=float, help="End time in seconds")
    p.set_defaults(func=cmd_trim)

    # speed
    p = subparsers.add_parser("speed", help="Change video playback speed")
    p.add_argument("input", help="Input video file path")
    p.add_argument("factor", type=float, nargs="?", default=None, help="Speed multiplier (e.g. 2.0 = 2x faster, 0.5 = half speed)")
    p.add_argument("--duration", type=float, help="Desired output duration in seconds (auto-calculates speed factor)")
    p.set_defaults(func=cmd_speed)

    # blur
    p = subparsers.add_parser("blur", help="Blur a region of the video")
    p.add_argument("input", help="Input video file path")
    p.add_argument("--region", help="Blur region as left,top,right,bottom (e.g. 100,50,500,400). Interactive if omitted.")
    p.set_defaults(func=cmd_blur)

    # resize
    p = subparsers.add_parser("resize", help="Resize/stretch video dimensions")
    p.add_argument("input", help="Input video file path")
    p.add_argument("--width", type=int, help="New width")
    p.add_argument("--height", type=int, help="New height")
    p.add_argument("--info", action="store_true", help="Just show current dimensions and duration")
    p.set_defaults(func=cmd_resize)

    # audio
    p = subparsers.add_parser("audio", help="Audio operations (mute or extract)")
    p.add_argument("input", help="Input video file path")
    p.add_argument("--mute", action="store_true", help="Mute the video audio")
    p.add_argument("--extract", action="store_true", help="Extract audio to MP3")
    p.set_defaults(func=cmd_audio)

    # brightness
    p = subparsers.add_parser("brightness", help="Adjust video brightness")
    p.add_argument("input", help="Input video file path")
    p.add_argument("factor", type=float, help="Brightness factor (1.0 = no change, >1.0 = brighter, <1.0 = darker)")
    p.set_defaults(func=cmd_brightness)

    # slideshow
    p = subparsers.add_parser("slideshow", help="Create slideshow video from images")
    p.add_argument("folder", help="Folder containing images")
    p.add_argument("output", help="Output video file path")
    p.add_argument("--start-duration", type=float, default=3.0, help="Duration for first image in seconds (default: 3.0)")
    p.add_argument("--end-duration", type=float, default=1.0, help="Duration for last image in seconds (default: 1.0)")
    p.add_argument("--shuffle", action="store_true", help="Shuffle image order")
    p.add_argument("--rotate", action="store_true", help="Apply random rotation to images")
    p.add_argument("--rotate-left", type=float, default=0, help="Max left rotation degrees (default: 0)")
    p.add_argument("--rotate-right", type=float, default=0, help="Max right rotation degrees (default: 0)")
    p.add_argument("--sound", help="Sound effect file to play on each transition")
    p.add_argument("--scale-mode", choices=["stretch", "fit", "crop"], default="stretch", help="Image scaling mode (default: stretch)")
    p.set_defaults(func=cmd_slideshow)

    # slowpan
    p = subparsers.add_parser("slowpan", help="Create slow pan effect (landscape to portrait)")
    p.add_argument("input", help="Input video file path")
    p.add_argument("duration", type=float, help="Pan duration in seconds")
    p.add_argument("--width", type=int, default=1080, help="Output width (default: 1080)")
    p.add_argument("--height", type=int, default=1920, help="Output height (default: 1920)")
    p.set_defaults(func=cmd_slowpan)

    # collage
    p = subparsers.add_parser("collage", help="Create collage video from images")
    p.add_argument("folder", help="Folder containing images")
    p.add_argument("output", help="Output video file path")
    p.add_argument("--width", type=int, default=1080, help="Canvas width (default: 1080)")
    p.add_argument("--height", type=int, default=1920, help="Canvas height (default: 1920)")
    p.add_argument("--height-min", type=int, default=100, help="Min image height (default: 100)")
    p.add_argument("--height-max", type=int, default=300, help="Max image height (default: 300)")
    p.add_argument("--start-rate", type=float, default=0.5, help="Seconds between images at start (default: 0.5)")
    p.add_argument("--end-rate", type=float, default=0.1, help="Seconds between images at end (default: 0.1)")
    p.add_argument("--rotate-left", type=float, default=15, help="Max left rotation degrees (default: 15)")
    p.add_argument("--rotate-right", type=float, default=15, help="Max right rotation degrees (default: 15)")
    p.add_argument("--fps", type=int, default=30, help="Output framerate (default: 30)")
    p.set_defaults(func=cmd_collage)

    # info
    p = subparsers.add_parser("info", help="Show video file information")
    p.add_argument("input", help="Input video file path")
    p.set_defaults(func=cmd_info)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
