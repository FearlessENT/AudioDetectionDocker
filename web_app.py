from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import os
import time
import subprocess
import threading

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
    os.system(f'yt-dlp -o "/downloads/{streamer_name}_%(timestamp)s.%(ext)s" https://www.twitch.tv/{streamer_name}')


def monitor_and_download(streamer_name):
    check_interval = 60  # Check every 60 seconds
    while True:
        if is_streamer_live(streamer_name):
            print(f"{streamer_name} is live! Starting download...")
            download_stream(streamer_name)
            print("Download completed!")
            break
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





def create_database():
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    create_database()
    app.run(host='0.0.0.0', port=5000)
