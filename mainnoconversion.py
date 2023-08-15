import subprocess
import os
import re
import glob
import shutil
import time
from trim_video import process_video as trim_video
from downloadvideo import download_video

def run_sound_reader(video_file, model_file):
    # Run sound_reader.py command
    command = ['python', 'sound_reader.py', '--model', model_file, video_file]
    output = subprocess.check_output(command)
    output_lines = output.decode().split('\n')
    timestamps = []
    timestamp_pattern = re.compile(r'\d{2}:\d{2}:\d{2}')
    for line in output_lines:
        match = timestamp_pattern.search(line)
        if match:
            timestamps.append(match.group())
    return timestamps

def extract_timestamps(video_file, model_file):
    # Run sound_reader.py command with video file
    timestamps = run_sound_reader(video_file, model_file)
    return timestamps



def compress_videos_in_directory(input_directory, output_directory=None):
    print(f"Scanning directory: {input_directory}")
    for file in os.listdir(input_directory):
        if os.path.isfile(os.path.join(input_directory, file)):
            if file.endswith(('.mp4', '.ts', '.mkv', '.avi', '.flv', '.mov', '.webm')):  # Add or remove extensions as needed
                input_file_path = os.path.join(input_directory, file)
                print(f"Found video: {input_file_path}")
                compress_video(input_file_path, output_directory)

def compress_video(input_file_path, output_directory=None):
    file_name = os.path.basename(input_file_path)
    file_name_without_extension, _ = os.path.splitext(file_name)
    output_file_name = f"{file_name_without_extension}_compressed.mp4"

    if output_directory:
        output_file_path = os.path.join(output_directory, output_file_name)
    else:
        output_file_path = os.path.join(os.path.dirname(input_file_path), output_file_name)

    command = f'ffmpeg -i "{input_file_path}" -c:v libx265 -crf 28 -preset medium -c:a aac -b:a 128k "{output_file_path}"'
    subprocess.call(command, shell=True)
    print(f"Compressed video saved as: {output_file_path}")




def merge_overlapping_segments(segments):
    if not segments:
        return []

    # Sort segments by start time
    segments.sort(key=lambda x: x[0])

    merged_segments = [segments[0]]

    for current_start, current_end in segments[1:]:
        last_start, last_end = merged_segments[-1]

        # If the current segment overlaps with the last merged segment, merge them
        if current_start <= last_end:
            merged_segments[-1] = (last_start, max(last_end, current_end))
        else:
            merged_segments.append((current_start, current_end))

    return merged_segments






def process_video(video_file, model_file, output_directory=None, buffer_before=0, buffer_after=0):
    # Start timing the process
    elapse_start_time = time.time()
    print(video_file)
    # Extract timestamps from video
    timestamps = extract_timestamps(video_file, model_file)
    sorted_timestamps = sorted(timestamps)

    print("time taken to get timestamps: ", time.time() - elapse_start_time)

    # Create list of segments with buffer padding
    segments = []
    start_time = None
    end_time = None

    for timestamp in sorted_timestamps:
        if start_time is None:
            start_time = timestamp
            end_time = timestamp
        elif timestamp == end_time or timestamp == increment_timestamp(end_time):
            end_time = timestamp
        else:
            # Modify the start and end times based on the buffer
            segments.append((decrement_timestamp_by_seconds(start_time, buffer_before), increment_timestamp_by_seconds(end_time, buffer_after)))
            start_time = timestamp
            end_time = timestamp

            

    if len(segments) == 0:
        print("No segments detected for video:", video_file)
        return
    

    # Merge overlapping segments
    segments = merge_overlapping_segments(segments)

    
    # Print the segments
    for segment in segments:
        print(segment)

    # Trim the video
    trim_video(video_file, segments, output_directory)

    # Calculate and print the time taken
    elapse_end_time = time.time()
    elapsed_time = elapse_end_time - elapse_start_time
    print(f"Processing time for {video_file}: {elapsed_time} seconds")


def increment_timestamp_by_seconds(timestamp, seconds):
    h, m, s = timestamp.split(':')
    total_seconds = int(h) * 3600 + int(m) * 60 + int(s) + seconds
    incremented_h = total_seconds // 3600
    incremented_m = (total_seconds % 3600) // 60
    incremented_s = total_seconds % 60
    return f"{incremented_h:02d}:{incremented_m:02d}:{incremented_s:02d}"

def decrement_timestamp_by_seconds(timestamp, seconds):
    h, m, s = timestamp.split(':')
    total_seconds = int(h) * 3600 + int(m) * 60 + int(s) - seconds
    total_seconds = max(0, total_seconds)  # Ensure it doesn't go below 0
    decremented_h = total_seconds // 3600
    decremented_m = (total_seconds % 3600) // 60
    decremented_s = total_seconds % 60
    return f"{decremented_h:02d}:{decremented_m:02d}:{decremented_s:02d}"

    

def process_folder(folder_path, model_file, output_directory=None):
    # Get all video files in the folder with supported extensions
    video_files = glob.glob(os.path.join(folder_path, '*.mp4'))
    video_files += glob.glob(os.path.join(folder_path, '*.ts'))
    video_files += glob.glob(os.path.join(folder_path, '*.mkv'))

    for video_file in video_files:
        process_video(video_file, model_file, output_directory)

def increment_timestamp(timestamp):
    h, m, s = timestamp.split(':')
    seconds = int(h) * 3600 + int(m) * 60 + int(s)
    incremented_seconds = seconds + 1
    incremented_h = incremented_seconds // 3600
    incremented_m = (incremented_seconds % 3600) // 60
    incremented_s = incremented_seconds % 60
    return f"{incremented_h:02d}:{incremented_m:02d}:{incremented_s:02d}"

def decrement_timestamp(timestamp):
    h, m, s = timestamp.split(':')
    seconds = int(h) * 3600 + int(m) * 60 + int(s)
    decremented_seconds = seconds - 1
    decremented_h = decremented_seconds // 3600
    decremented_m = (decremented_seconds % 3600) // 60
    decremented_s = decremented_seconds % 60
    return f"{decremented_h:02d}:{decremented_m:02d}:{decremented_s:02d}"



def download_and_process(url, model_file, output_folder, temp_folder, buffer_before_seconds, buffer_after_seconds, output_file=None):
    # Download video
    download_video(url, temp_folder)

    # Get the last downloaded file
    list_of_files = glob.glob(f'{temp_folder}/*')
    video_file = max(list_of_files, key=os.path.getctime)

    # Process video
    process_video(video_file, model_file, output_folder, buffer_before_seconds, buffer_after_seconds)





if __name__ == "__main__":

    # Paths to folder and model file
    folder_path = 'input'
    model_file = 'bdetectionmodel_05_01_23.onnx'
    output_directory = 'output'

    print("go")

    # Process videos in the folder
    process_folder(folder_path, model_file, output_directory)

    # url = "https://www.twitch.tv/videos/1865995406"
    # download_and_process(url, model_file, output_directory)



    # compress_videos_in_directory(folder_path, output_directory)


    # url = "https://www.youtube.com/watch?v=0fRoRymjoc0"
    # download_and_process(url, model_file, output_directory)





