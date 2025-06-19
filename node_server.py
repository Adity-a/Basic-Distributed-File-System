from flask import Flask, request, jsonify, send_from_directory
import os
import sys

app = Flask(__name__)

# --- Configuration ---
NODE_ID = sys.argv[1]      
PORT = int(sys.argv[2])      

STORAGE_PATH = os.path.join("node_storage", NODE_ID)
os.makedirs(STORAGE_PATH, exist_ok=True)

# --- Upload File ---
@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    version = request.form.get('version', '1')
    filepath = os.path.join(STORAGE_PATH, file.filename)
    file.save(filepath)

    # Save version metadata
    with open(filepath + ".meta", 'w') as f:
        f.write(version)

    return "Uploaded", 200

# --- Download File ---
@app.route('/download/<filename>', methods=['GET'])
def download(filename):
    return send_from_directory(STORAGE_PATH, filename)

# --- Get File Version ---
@app.route('/version/<filename>', methods=['GET'])
def get_version(filename):
    try:
        with open(os.path.join(STORAGE_PATH, filename + ".meta")) as f:
            version = f.read()
        return jsonify({"version": version})
    except FileNotFoundError:
        return jsonify({"version": "0"})

# --- List Files ---
@app.route("/list", methods=["GET"])
def list_files():
    # Filter out .meta files
    files = [f for f in os.listdir(STORAGE_PATH) if not f.endswith('.meta')]
    return jsonify({"files": files})

# --- Delete File ---
@app.route("/delete/<filename>", methods=["DELETE"])
def delete_file(filename):
    filepath = os.path.join(STORAGE_PATH, filename)
    meta_path = filepath + ".meta"

    if os.path.exists(filepath):
        os.remove(filepath)
        if os.path.exists(meta_path):
            os.remove(meta_path)
        return jsonify({"status": "deleted"})
    return jsonify({"status": "not found"}), 404

# --- Run Server ---
if __name__ == '__main__':
    app.run(port=PORT)
