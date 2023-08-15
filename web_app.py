from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Configuration for SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///streamers.db'
db = SQLAlchemy(app)

# Define the Streamer model
class Streamer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)

@app.route('/')
def index():
    streamers = Streamer.query.all()
    return render_template('index.html', streamers=streamers)

@app.route('/add_streamer', methods=['POST'])
def add_streamer():
    streamer_name = request.form.get('streamer_name')
    if not Streamer.query.filter_by(name=streamer_name).first():
        new_streamer = Streamer(name=streamer_name)
        db.session.add(new_streamer)
        db.session.commit()
        return jsonify(status="success", message=f"Added {streamer_name}")
    return jsonify(status="error", message=f"{streamer_name} already exists")

@app.route('/remove_streamer', methods=['POST'])
def remove_streamer():
    streamer_name = request.form.get('streamer_name')
    streamer = Streamer.query.filter_by(name=streamer_name).first()
    if streamer:
        db.session.delete(streamer)
        db.session.commit()
        return jsonify(status="success", message=f"Removed {streamer_name}")
    return jsonify(status="error", message=f"{streamer_name} not found")

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
