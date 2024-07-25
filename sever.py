import socket
import json
import os
import struct
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO)

# Server Configuration
HOST = '192.168.1.135'
PORT = 65432
BUFFER_SIZE = 4096

# Directory where the files are stored, updated to the correct path
FILE_DIR = r'C:\Users\MSI\OneDrive - VNU-HCMUS\Đồ án mạng máy tính'

# List of downloadable files, ensure these are correct and exist in FILE_DIR
FILES = [
    "File1.zip",
    "File2.zip",
    "File3.zip",
    "File4.zip",
    "File5.zip"
]

def secure_filename(filename):
    """Ensure the filename does not contain path traversal attempts."""
    return os.path.basename(filename)

def get_file_size(file_path):
    """Get file size in bytes."""
    return os.path.getsize(file_path)

def update_files_dict():
    """Update the FILES dictionary with actual file sizes in MB."""
    files_dict = {}
    for filename in FILES:
        file_path = os.path.join(FILE_DIR, filename)
        if os.path.exists(file_path):
            file_size_bytes = get_file_size(file_path)
            file_size_mb = file_size_bytes / (1024 * 1024)  # Convert bytes to MB
            files_dict[filename] = round(file_size_mb, 2)  # Round to 2 decimal places
        else:
            logging.warning(f"File {filename} not found in {FILE_DIR}.")
    return files_dict

def send_file(conn, file_path):
    """Send the file size and then the file in chunks to the client."""
    try:
        file_size = get_file_size(file_path)
        conn.sendall(struct.pack('!Q', file_size))
        with open(file_path, 'rb') as file:
            while True:
                chunk = file.read(BUFFER_SIZE)
                if not chunk:
                    break
                conn.sendall(chunk)
    except IOError as e:
        logging.error(f"Failed to read file: {e}")
        conn.sendall(b"Failed to send file")

def handle_client(conn, addr):
    logging.info(f"Connected by {addr}")

    while True:
        data = conn.recv(BUFFER_SIZE).decode('utf-8')
        if not data:
            break

        if data.strip() == "LIST":
            # Update and send the list of files with their sizes to the client
            files_with_sizes = update_files_dict()
            data_to_send = json.dumps(files_with_sizes, ensure_ascii=False).encode('utf-8')
            logging.info(f"Sending file list: {data_to_send}")
            conn.sendall(data_to_send)
        else:
            filename = secure_filename(data.strip())
            if filename in update_files_dict():
                file_path = os.path.join(FILE_DIR, filename)
                if os.path.exists(file_path):
                    try:
                        send_file(conn, file_path)
                        logging.info(f"Sent {filename}")
                    except IOError as e:
                        logging.error(f"Failed to read file: {e}")
                        conn.sendall(b"Failed to send file")
                else:
                    conn.sendall(b"File not found")
            else:
                conn.sendall(b"File not found")

    conn.close()
    logging.info(f"Connection closed for {addr}")

def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((HOST, PORT))
            s.listen(1)  # Listen for only one connection at a time
            logging.info(f"Server listening on {HOST}:{PORT}")
            while True:
                conn, addr = s.accept()
                handle_client(conn, addr)
        except socket.error as e:
            logging.error(f"Socket error: {e}")

if __name__ == "__main__":
    start_server()
