"""
Universal Share - P2P File Sharing Backend
Creator: Aniket Mujbaile
"""

from flask import Flask, request, jsonify, abort, send_from_directory
from flask_cors import CORS
import threading
import os
import tempfile
import uuid
from flask import send_file

app = Flask(__name__)
CORS(app)

# In-memory storage for signaling data
sessions = {}
lock = threading.Lock()

# Temporary file storage
UPLOAD_FOLDER = tempfile.mkdtemp()
file_map = {}  # Maps file_id to file path

def get_session(share_id):
    with lock:
        if share_id not in sessions:
            sessions[share_id] = {
                'offer': None,
                'answer': None,
                'candidates': []
            }
        return sessions[share_id]

def validate_json(required_keys):
    data = request.json
    if not data:
        abort(400, description="Missing JSON body.")
    for key in required_keys:
        if key not in data:
            abort(400, description=f"Missing required field: {key}")
    return data

@app.route('/offer', methods=['POST'])
def offer():
    data = validate_json(['id'])
    share_id = data['id']
    sdp = data.get('sdp')
    session = get_session(share_id)
    if sdp:
        session['offer'] = sdp
        return jsonify({'ok': True}), 200
    if session['offer']:
        return jsonify({'sdp': session['offer']}), 200
    return jsonify({'error': 'No offer found'}), 404

@app.route('/answer', methods=['POST'])
def answer():
    data = validate_json(['id'])
    share_id = data['id']
    sdp = data.get('sdp')
    session = get_session(share_id)
    if sdp:
        session['answer'] = sdp
        return jsonify({'ok': True}), 200
    if session['answer']:
        return jsonify({'sdp': session['answer']}), 200
    return jsonify({'error': 'No answer found'}), 404

@app.route('/candidate', methods=['POST'])
def candidate():
    data = validate_json(['id'])
    share_id = data['id']
    candidate = data.get('candidate')
    session = get_session(share_id)
    if candidate:
        session['candidates'].append(candidate)
        return jsonify({'ok': True}), 200
    # Return and clear all candidates as a list
    candidates = session['candidates'][:]
    session['candidates'].clear()
    return jsonify({'candidates': candidates}), 200

@app.route('/reset', methods=['POST'])
def reset():
    """Reset all sessions (for debugging or manual cleanup)."""
    global sessions
    with lock:
        sessions = {}
    return jsonify({'ok': True})

@app.route('/session/<share_id>', methods=['GET'])
def session_info(share_id):
    """Get the current state of a session (for debugging)."""
    session = get_session(share_id)
    return jsonify(session)

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        abort(400, description="No file part in the request.")
    file = request.files['file']
    if file.filename == '':
        abort(400, description="No selected file.")
    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_FOLDER, file_id + '_' + file.filename)
    file.save(file_path)
    file_map[file_id] = file_path
    download_url = request.host_url.rstrip('/') + f"/download/{file_id}"
    return jsonify({'download_url': download_url, 'file_id': file_id}), 200

@app.route('/download/<file_id>', methods=['GET'])
def download(file_id):
    file_path = file_map.get(file_id)
    if not file_path or not os.path.exists(file_path):
        abort(404, description="File not found or expired.")
    # Serve the file for download
    filename = os.path.basename(file_path).split('_', 1)[-1]
    response = send_file(file_path, as_attachment=True, download_name=filename)
    # Optionally, delete file after download (uncomment next two lines for one-time download)
    # os.remove(file_path)
    # file_map.pop(file_id, None)
    return response

@app.route('/url/<file_id>', methods=['GET'])
def get_download_url(file_id):
    """Return the direct download URL for a given file_id if it exists."""
    file_path = file_map.get(file_id)
    if not file_path or not os.path.exists(file_path):
        abort(404, description="File not found or expired.")
    download_url = request.host_url.rstrip('/') + f"/download/{file_id}"
    return jsonify({'download_url': download_url}), 200

@app.route('/')
def root():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def static_proxy(path):
    # Serve static files (js, css, etc.) from the root directory
    return send_from_directory('.', path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
