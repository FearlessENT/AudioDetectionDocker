from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.compositing.concatenate import concatenate_videoclips
import os
import subprocess
import re
from datetime import datetime

def get_video_bitrate(filename):
    command = ['ffprobe', '-v', 'error', '-show_entries', 'format=bit_rate', '-of',
               'default=noprint_wrappers=1:nokey=1', filename]
    output = subprocess.check_output(command).decode()
    bitrate = re.search(r'\d+', output)
    if bitrate:
        return bitrate.group()
    else:
        return None  # if the bitrate cannot be determined

def convert_timestamp_to_seconds(timestamp):
    # Converts the HH:MM:SS format timestamp to seconds
    hours, minutes, seconds = map(int, timestamp.split(":"))
    return hours * 60 * 60 + minutes * 60 + seconds


def reencode_video(filename):
    output_filename = f"{os.path.splitext(filename)[0]}_reencoded.mp4"
    command = ['ffmpeg', '-i', filename, '-c:v', 'libx264', '-preset', 'veryfast', '-c:a', 'aac', '-y', output_filename]
    subprocess.run(command)
    return output_filename


def remux_video(filename):
    output_filename = f"{os.path.splitext(filename)[0]}_remuxed.mp4"
    command = ['ffmpeg', '-i', filename, '-c', 'copy', '-y', output_filename]
    subprocess.run(command)
    return output_filename



def is_within_duration(start_seconds, end_seconds, duration):
    # Check if both start and end times are within the video duration
    return start_seconds <= duration and end_seconds <= duration




def process_video(filename, timestamps, output_directory=None, pass_number = 1):
    # filename = remux_video(filename)


    base_filename, _ = os.path.splitext(os.path.basename(filename))
    video_specific_folder = os.path.join(output_directory, base_filename) if output_directory else base_filename


    video_clip = VideoFileClip(filename)
    video_duration = video_clip.duration

    if pass_number == 2:  # Check if it's the second pass
        if not os.path.exists(video_specific_folder):
            os.makedirs(video_specific_folder)  # Create the directory if it does not exist

        clip_counter = 1

        for start, end in timestamps:

            # Convert timestamps to seconds
            start_seconds = convert_timestamp_to_seconds(start)
            end_seconds = convert_timestamp_to_seconds(end)

            if is_within_duration(start_seconds, end_seconds, video_duration):


                
                clip = video_clip.subclip(start_seconds, end_seconds)
                # Determine output filename for individual clip
                base_filename, _ = os.path.splitext(os.path.basename(filename))
                individual_clip_output_filename = f"{video_specific_folder}/{base_filename}_clip_{clip_counter}.mp4"

                # Write the individual clip to file
                clip.write_videofile(individual_clip_output_filename, codec="libx264", audio_codec="aac")

                clip_counter += 1



    clips = []
    

    

    for start, end in timestamps:
        # Convert timestamps to seconds
        start_seconds = convert_timestamp_to_seconds(start)
        end_seconds = convert_timestamp_to_seconds(end)

        if is_within_duration(start_seconds, end_seconds, video_duration):

            # Create subclip and add to clips list
            clips.append(video_clip.subclip(start_seconds, end_seconds))
        
        

    # Concatenate and save clips
    final_clip = concatenate_videoclips(clips, method="compose")
    
    # Determine output filename
    base_filename, _ = os.path.splitext(os.path.basename(filename))
    output_filename = f"{base_filename}_edited.mp4"
    if output_directory:
        output_filename = os.path.join(output_directory, output_filename)

    # If the output file already exists, append a unique identifier to avoid overwriting
    if os.path.exists(output_filename):
        unique_id = datetime.now().strftime('%Y%m%d%H%M%S')  # timestamp with year, month, day, hour, minute, second
        output_filename = f"{base_filename}_edited_{unique_id}.mp4"
        if output_directory:
            output_filename = os.path.join(output_directory, output_filename)

    # Set the output codec to 'libx264' for video and 'aac' for audio
    output_video_codec = 'libx264'
    output_audio_codec = 'aac'

    # Get the bitrate of the original video and pass it to write_videofile
    bitrate = get_video_bitrate(filename)
    if bitrate is not None:
        final_clip.write_videofile(output_filename, codec=output_video_codec, audio_codec=output_audio_codec, bitrate=bitrate)
    else:
        final_clip.write_videofile(output_filename, codec=output_video_codec, audio_codec=output_audio_codec)

    return output_filename
