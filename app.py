
from flask import Flask, request, Response, jsonify, stream_with_context, send_from_directory
from flask_cors import CORS
import time

# Flask app, serving static files from ./static
app = Flask(__name__, static_folder="static")
CORS(app)  # allow browser fetches from same origin or other origins

# Suggested sizes for the UI (MB)
DOWNLOAD_SIZES_MB = [0.5, 1, 2, 5, 10]
CHUNK_SIZE = 64 * 1024  # 64 KiB


@app.after_request
def add_no_store_headers(resp):

    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@app.route("/ping")
def ping():

    server_time = int(time.time() * 1000)
    return jsonify({"status": "ok", "server_time_ms": server_time})


@app.route("/download-sizes")
def download_sizes():

    return jsonify({"sizes_mb": DOWNLOAD_SIZES_MB})


def generate_data(total_bytes: int):

    remaining = total_bytes
    chunk = b"\x00" * CHUNK_SIZE
    while remaining > 0:
        to_send = min(CHUNK_SIZE, remaining)
        yield chunk[:to_send]
        remaining -= to_send


@app.route("/download")
def download():

    try:
        size_mb = float(request.args.get("size_mb", "5"))
    except ValueError:
        size_mb = 5.0

    # clamp to a safe range
    size_mb = min(max(size_mb, 0.5), 100.0)  # 0.5-100 MB


    total_bytes = int(size_mb * 1024 * 1024)  # use MiB for actual bytes
    headers = {
        "Content-Type": "application/octet-stream",
        "Content-Length": str(total_bytes),
    }
    return Response(stream_with_context(generate_data(total_bytes)), headers=headers)


@app.route("/upload", methods=["POST"])
def upload():

    start = time.monotonic()
    total = 0
    while True:
        chunk = request.stream.read(CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
    duration = time.monotonic() - start
    duration = max(duration, 1e-6)
    mbps = (total * 8) / duration / 1_000_000  # bits/s -> Mbps

    return jsonify(
        {
            "status": "ok",
            "bytes_received": total,
            "duration_seconds": duration,
            "upload_mbps": mbps,
        }
    )


@app.route("/")
def index():

    return send_from_directory(app.static_folder, "index.html")


if __name__ == "__main__":
    # For local dev. In the cloud, you'll run via gunicorn or similar.
    app.run(host="0.0.0.0", port=5000, debug=True)
