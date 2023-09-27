from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import os
import time
import subprocess
import threading
import queue
import requests
from mainnoconversion import process_video  


# if true, remove the originally downloaded stream after converting to new format
DELETE_ORIGINAL = False
DELETE_ALL = False


class VideoProcessingQueue:
    def __init__(self, model_path, output_directory="/output"):
        self.tasks = []
        self.model_path = model_path
        self.output_directory = output_directory
        self.worker_thread = threading.Thread(target=self._video_processing_worker, daemon=True)
        self.worker_thread.start()

    def add_task(self, video_path):
        self.tasks.append(video_path)

    def _video_processing_worker(self):
        while True:
            if self.tasks:
                video_path = self.tasks.pop(0)
                start_time = time.time()

                try:
                    #first round of processing. this extracts the audio
                    if "libx" in str(video_path):
                        # this means its already been converted to a proper file 
                        # convert in the processvideo function means that mp3 audio is extracted if true
                        print("found lib in file path, does not need converting to fresh video file")
                        outputfile1 = process_video(video_path, self.model_path, output_directory=self.output_directory, buffer_after=20, buffer_before=10)
                    else:
                        print("converting video to better format:", video_path)
                        #convert the video to not corrupt video stream
                        new_codec_video = convert_video(video_path)
                        outputfile1 = process_video(new_codec_video, self.model_path, output_directory=self.output_directory, buffer_after=20, buffer_before=10)

                    print("Processing video:", video_path)


                    #second round of processing
                    #if no timestamps have been detected, then exit.
                    if outputfile1 == False:
                        print(f"No segments detected for video: {video_path}")
                        # Delete the original video only if DELETE_ORIGINAL is True and the video is not needed anymore
                        if DELETE_ORIGINAL and os.path.exists(video_path):
                            os.remove(video_path)
                        #continuing to next item in queue
                        continue

                    # At this point, outputfile1 has been successfully created and is no longer needed after outputfile2 is created
                    outputfile2 = process_video(outputfile1, self.model_path, output_directory=self.output_directory, convert=False, buffer_before=2, buffer_after=2)


                    # delete the output of the first round of processing.
                    if os.path.exists(outputfile1) and DELETE_ALL:
                        os.remove(outputfile1)

                    # Delete the original video only if DELETE_ORIGINAL is True and the video is not needed anymore
                    if DELETE_ORIGINAL and os.path.exists(video_path):
                        os.remove(video_path)

                except Exception as e:
                    print(f"somewhere An error occurred: {e}")
                    continue

                print(f"total time taken to process {video_path}: {time.time() - start_time}, or {(time.time() - start_time) / 60} mins ")

            else:
                time.sleep(5)




def convert_video(input_file_path):
    # Get the directory and file name of the input file
    input_directory, input_file_name = os.path.split(input_file_path)
    
    # Generate the output file name by appending a prefix
    output_file_name = f"libx264_server_{input_file_name}"
    
    # Generate the output file path
    output_file_path = os.path.join(input_directory, output_file_name)
    
    # Define the FFmpeg command as a list of arguments
    ffmpeg_command = [
        "ffmpeg",
        "-i", input_file_path,
        "-c:v", "libx264",
        "-b:v", "400k",  # Lower video bitrate
        "-preset", "ultrafast",  # fastest preset
        "-crf", "28",  # higher CRF means faster encoding but lower quality
        # "-vf", "scale=-1:720",  # lower resolution
        "-r", "24",  # lower frame rate
        "-c:a", "aac",
     
        output_file_path
    ]
    
    # Run the FFmpeg command
    subprocess.run(ffmpeg_command)
    
    return output_file_path




MODEL = "/model/bdetectionmodel_05_01_23.onnx"

video_queue = VideoProcessingQueue(MODEL)



app = Flask(__name__)

# Configuration for SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////config/database.db'

db = SQLAlchemy(app)

# Define the Streamer model
class Streamer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)








@app.route('/')
def index():
    streamers = Streamer.query.all()
    return render_template('index.html', streamers=streamers)






# curl -X POST 'https://id.twitch.tv/oauth2/token?client_id=bhi8sez9xw58zn0yqnjiji6uzlewhd&client_secret=3a101si6uje2ii62t0h73vuu5qye7q&grant_type=client_credentials'





def is_streamer_live(streamer_name):
    # Use the Twitch API to check if the streamer is live
    headers = {
        'Client-ID': 'bhi8sez9xw58zn0yqnjiji6uzlewhd',
        'Authorization': 'Bearer svpsvp9a4beqdgycuzhipafpsosatv'
    }
    response = requests.get(f'https://api.twitch.tv/helix/streams?user_login={streamer_name}', headers=headers)
    data = response.json()
    
    # Check if the streamer is live
    if data['data'] and data['data'][0]['type'] == 'live':
        return True
    return False




import subprocess

def download_stream_with_streamlink(streamer_name, download_directory="/downloads"):
    timestamp = time.strftime("%Y%m%d%H%M%S")
    video_path = f"{download_directory}/{streamer_name}_{timestamp}.mp4"
    
    print(f"Downloading stream from {streamer_name} using streamlink...")
    subprocess.call(['streamlink', f'https://www.twitch.tv/{streamer_name}', 'best', '-o', video_path])
    print(f"Downloaded stream from {streamer_name}")
    print(video_path)
    return video_path








def download_stream(streamer_name):
    # Use yt-dlp to download the live stream to the /downloads directory in the container
    timestamp = time.strftime("%Y%m%d%H%M%S")
    video_path = f"/downloads/{streamer_name}_{timestamp}.mp4"
    
    # Use subprocess to run the yt-dlp command and mute its output
    print(f"download_stream() downloading stream from {streamer_name}")
    with open(os.devnull, 'w') as fnull:
        subprocess.call(['yt-dlp', '-o', video_path, f'https://www.twitch.tv/{streamer_name}'], stdout=fnull, stderr=fnull)
    print(f"download_stream() downloaded stream from {streamer_name}")
    print(video_path)
    return video_path



def get_most_recent_file(directory):
    files = [os.path.join(directory, f) for f in os.listdir(directory) if not f.endswith('.part')]
    return max(files, key=os.path.getctime)



@app.route('/test_processing', methods=['GET'])
def test_processing():
    # Get the most recent file in the /downloads directory
    video_path = get_most_recent_file("/downloads")
    
    # Add the video to the processing queue
    video_queue.add_task(video_path)

    
    return "Started processing the most recent video!", 200



def monitor_and_download(streamer_name):
    check_interval = 300  # Check every 60 seconds
    while True:
        if is_streamer_live(streamer_name):
            print(f"{streamer_name} is live! Starting download...")
            
            
            
            # video_path = download_stream(streamer_name)

            video_path = download_stream_with_streamlink(streamer_name)



            print(f"Download completed for {streamer_name}")
            
            # Add the downloaded video to the processing queue
            time.sleep(2)
            video_queue.add_task(video_path)
            print(f"download from {streamer_name} added to processing queue")
        else:
            # print(f"{streamer_name} is not live. Checking again in {check_interval} seconds...")
            time.sleep(check_interval)




@app.route('/add_streamer', methods=['POST'])
def add_streamer():
    streamer_name = request.form.get('streamer_name')
    if not Streamer.query.filter_by(name=streamer_name).first():
        new_streamer = Streamer(name=streamer_name)
        db.session.add(new_streamer)
        db.session.commit()
        # Start a new thread to monitor and download the stream
        threading.Thread(target=monitor_and_download, args=(streamer_name,)).start()
    return redirect(url_for('index'))


@app.route('/remove_streamer', methods=['POST'])
def remove_streamer():
    streamer_name = request.form.get('streamer_name')
    streamer = Streamer.query.filter_by(name=streamer_name).first()
    if streamer:
        db.session.delete(streamer)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/view_streamers', methods=['GET'])
def view_streamers():
    streamers = [streamer.name for streamer in Streamer.query.all()]
    return jsonify(streamers=streamers)





def start_monitoring_all_streamers():
    with app.app_context():
        streamers = Streamer.query.all()
        for streamer in streamers:
            threading.Thread(target=monitor_and_download, args=(streamer.name,)).start()








def create_database():
    with app.app_context():
        db.create_all()


























































if __name__ == '__main__':
    create_database()
    start_monitoring_all_streamers()
    app.run(host='0.0.0.0', port=5000)
