from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Base API URL
API_BASE_URL = "https://terabox.hnn.workers.dev"

# HTML template for dynamically generated streaming pages
STREAM_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="robots" content="noindex,nofollow">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/video.js/8.8.0/video-js.min.css">
    <link rel="stylesheet" href="/style.css">
    <title>{{ file_name }} - Streaming</title>
</head>
<body>
    <div class="container">
        <h1 id="name">{{ file_name }}</h1>
        <video id="player" class="video-js vjs-default-skin vjs-big-play-centered" controls></video>
        <div class="form-group">
            <button id="get-link-button">DOWNLOAD</button>
        </div>
    </div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/video.js/8.8.0/video.min.js"></script>
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const shortUrl = "{{ short_url }}";
            const TeraBoxData = JSON.parse(localStorage.getItem('TeraBoxData')) || [];
            const matchedItem = TeraBoxData.find(item => item.shortUrl === shortUrl);
            const downloadLink = matchedItem ? matchedItem.downloadLink : '';

            if (downloadLink) {
                const player = videojs(document.getElementById('player'));
                player.src({ src: downloadLink, type: 'video/mp4' });
            }

            document.getElementById("get-link-button").addEventListener("click", function() {
                if (downloadLink) window.open(downloadLink, '_blank');
            });
        });
    </script>
</body>
</html>
"""

@app.route('/proxy', methods=['GET', 'POST'])
def proxy():
    """Proxy API requests to bypass CORS"""
    target_url = request.args.get('url')  # Extract API path
    if not target_url:
        return jsonify({"error": "Missing 'url' parameter"}), 400

    query_params = request.query_string.decode('utf-8').replace(f"url={target_url}&", "")  # Remove 'url' param
    full_url = f"{API_BASE_URL}{target_url}"
    if query_params:
        full_url += f"?{query_params}"

    print(f"[DEBUG] Forwarding request to: {full_url}")

    try:
        headers = {"Content-Type": "application/json"}
        if request.method == 'GET':
            response = requests.get(full_url, headers=headers)
        else:
            response = requests.post(full_url, json=request.json, headers=headers)

        print(f"[DEBUG] Response Status: {response.status_code}")
        return (response.text, response.status_code, {"Content-Type": response.headers.get("Content-Type", "application/json")})

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Request Failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/w/<short_url>.html')
def serve_streaming_page(short_url):
    """Dynamically generate and serve the streaming page."""
    return render_template_string(STREAM_PAGE_TEMPLATE, short_url=short_url, file_name="TeraBox Video")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
