from yt_dlp import YoutubeDL
import os
import time

def download_video(url, temp_folder):
    output_folder = temp_folder
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    ydl_opts = {
        'format': 'best[height<=720]',
        'nocheckcertificate': True,
        'outtmpl': f'{output_folder}/%(title)s-{timestamp}.%(ext)s',  # added timestamp suffix
        'cookies': 'cookies.txt',
        'quiet': True  # This will suppress all console output
    }


    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


if __name__ == "__main__":
    # Example usage
    url = 'https://www.twitch.tv/videos/1809427389?filter=archives&sort=time'  # Replace with the desired URL

    download_video(url)
