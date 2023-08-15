from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import os
import time
import subprocess
import threading
import queue
from mainnoconversion import process_video  # Import the process_video function

MODEL = "/model/bdetectionmodel_05_01_23.onnx"

video_queue = queue.Queue()

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

def is_streamer_live(streamer_name):
    # Use yt-dlp to check if streamer is live
    result = subprocess.run(['yt-dlp', f'https://www.twitch.tv/{streamer_name}', '--skip-download', '--get-title'], capture_output=True, text=True)
    if "is offline" not in result.stdout:
        return True
    return False

def download_stream(streamer_name):
    # Use yt-dlp to download the live stream to the /downloads directory in the container
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    video_path = f"/downloads/{streamer_name}_{timestamp}.ext"
    os.system(f'yt-dlp -o "{video_path}" https://www.twitch.tv/{streamer_name}')
    return video_path



def get_most_recent_file(directory):
    files = [os.path.join(directory, f) for f in os.listdir(directory)]
    return max(files, key=os.path.getctime)


@app.route('/test_processing', methods=['GET'])
def test_processing():
    # Get the most recent file in the /downloads directory
    video_path = get_most_recent_file("/downloads")
    
    # Add the video to the processing queue
    video_queue.put(video_path)
    
    return "Started processing the most recent video!", 200



def monitor_and_download(streamer_name):
    check_interval = 60  # Check every 60 seconds
    while True:
        if is_streamer_live(streamer_name):
            print(f"{streamer_name} is live! Starting download...")
            video_path = download_stream(streamer_name)
            print("Download completed!")
            
            # Add the downloaded video to the processing queue
            video_queue.put(video_path)
        else:
            print(f"{streamer_name} is not live. Checking again in {check_interval} seconds...")
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


@app.before_first_request
def initialize_monitoring():
    with app.app_context():
        # Get all streamers from the database
        streamers = Streamer.query.all()
        for streamer in streamers:
            # Start monitoring for each streamer
            monitor_streamer(streamer.name)



def video_processing_worker():
    while True:
        # Wait for a video to be available in the queue
        video_path = video_queue.get()
        
        # Process the video
        process_video(video_path, MODEL, output_directory = "/output")
        
        # Mark the task as done
        video_queue.task_done()

# Start the video processing worker in a separate thread
threading.Thread(target=video_processing_worker, daemon=True).start()

def monitor_and_download(streamer_name):
    # ... [existing code] ...
    download_stream(streamer_name)
    print("Download completed!")
    
    # Add the downloaded video to the processing queue
    video_queue.put(f"/downloads/{streamer_name}_{timestamp}.ext")  # Modify the path as needed




def create_database():
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    create_database()
    app.run(host='0.0.0.0', port=5000)
