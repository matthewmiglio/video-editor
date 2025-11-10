import os
import time
import cv2
import matplotlib.pyplot as plt
import numpy as np
from moviepy import vfx
from moviepy.video.io.VideoFileClip import VideoFileClip

from moviepy.video.io.VideoFileClip import VideoFileClip


import os
from moviepy.video.io.VideoFileClip import VideoFileClip


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
        print(f"Cropping this video {os.path.basename(input_video_path)} to {box}")
        start_time = time.time()
        temp_output_path = input_video_path.replace(
            ".mp4", f"_cropped_temp_{box[0]}_{box[1]}_{box[2]}_{box[3]}.mp4"
        )

        left, top, right, bottom = box

        cap = cv2.VideoCapture(input_video_path)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        fps = int(cap.get(cv2.CAP_PROP_FPS))

        out = cv2.VideoWriter(
            temp_output_path, fourcc, fps, (right - left, bottom - top)
        )

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            cropped_frame = frame[top:bottom, left:right]
            out.write(cropped_frame)

        cap.release()
        out.release()

        if os.path.exists(input_video_path):
            os.remove(input_video_path)

        os.rename(temp_output_path, input_video_path)

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
    clip = VideoFileClip(input_video_path).fx(vfx.speedx, speed_factor)
    clip.write_videofile(temp_output_path, codec="libx264")
    clip.close()

    if os.path.exists(input_video_path):
        os.remove(input_video_path)

    os.rename(temp_output_path, input_video_path)

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


if __name__ == "__main__":
    file_path = r"C:\Users\matmi\Downloads\Untitled video - Made with Clipchamp (4).mp4"
    print(f'    Processing file: {file_path}')
    new_res = (589,330)
    stretch_video_dims(file_path, new_res[0], new_res[1])

        
    
