from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import os
import time
import subprocess
import threading
import queue
import requests
from mainnoconversion import process_video  



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
                print("Processing video:", video_path)
                process_video(video_path, self.model_path, output_directory=self.output_directory)
            else:
                time.sleep(5)  # Sleep for 5 seconds if no tasks are available





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
            video_path = download_stream(streamer_name)
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
