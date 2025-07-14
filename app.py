from flask import Flask, request, jsonify
from pymongo import MongoClient
from datetime import datetime
from flask import render_template
from bson.json_util import dumps

app = Flask(__name__)

# Connect to your MongoDB database
client = MongoClient("mongodb://localhost:27017/")  # Use MongoDB Atlas URI if using cloud DB
db = client["webhook_db"]
collection = db["github_events"]        


from dateutil import parser  # Install via: pip install python-dateutil

@app.route('/webhook', methods=['POST'])
def webhook():
    event_type = request.headers.get('X-GitHub-Event')
    payload = request.json

    author = payload.get("pusher", {}).get("name") or payload.get("sender", {}).get("login")

    # Extract timestamp from payload
    raw_timestamp = (
        payload.get("head_commit", {}).get("timestamp") or
        payload.get("pull_request", {}).get("created_at") or
        payload.get("pull_request", {}).get("merged_at") or
        payload.get("repository", {}).get("pushed_at")
    )

    if raw_timestamp:
        # Convert to datetime and format
        dt = parser.parse(raw_timestamp)
        timestamp = dt.strftime("%d %B %Y - %I:%M %p UTC")
    else:
        # fallback to current UTC if missing
        timestamp = datetime.utcnow().strftime("%d %B %Y - %I:%M %p UTC")

    data = {
        "request_id": payload.get("after") or payload.get("pull_request", {}).get("id"),
        "author": author,
        "action": event_type.upper(),
        "from_branch": payload.get("pull_request", {}).get("head", {}).get("ref", ""),
        "to_branch": payload.get("pull_request", {}).get("base", {}).get("ref", payload.get("ref", "").split("/")[-1]),
        "timestamp": timestamp
    }

    collection.insert_one(data)
    return jsonify({"message": "Webhook received!"}), 200

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/events')
def get_events():
    # Get last 10 entries, most recent first
    events = list(collection.find().sort('_id', -1).limit(10))
    return dumps(events)
if __name__ == '__main__':
    app.run(debug=True)
