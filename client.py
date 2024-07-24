import socket
import json
import os
import signal
import struct
import logging
import time

# Setup basic logging
logging.basicConfig(level=logging.INFO)

# Configuration
HOST = '127.0.0.1'
PORT = 65432
BUFFER_SIZE = 4096
is_running = True

def signal_handler(sig, frame):
    global is_running
    print("\nCtrl+C pressed. Exiting...")
    is_running = False

signal.signal(signal.SIGINT, signal_handler)

def get_last_position():
    if os.path.exists('last_position.txt'):
        with open('last_position.txt', 'r') as f:
            position = f.read()
            return int(position) if position else 0
    return 0

def set_last_position(position):
    with open('last_position.txt', 'w') as f:
        f.write(str(position))

def append_filenames_to_input():
    print("Enter filenames to download, separated by commas (,): ")
    filenames = input().split(',')
    with open('input.txt', 'a') as f:
        for filename in filenames:
            filename = filename.strip()
            f.write(filename + '\n')

def read_filenames_from_input():
    input_file_names = []
    if os.path.exists('input.txt'):
        with open('input.txt', 'r') as f:
            input_file_names = [line.strip() for line in f.readlines()]
    return input_file_names

def create_output_directory():
    if not os.path.exists('output'):
        os.makedirs('output')
    print("Output directory is located at:", os.path.abspath('output'))

def request_file_list(s):
    print("Requesting file list...")
    s.sendall("LIST".encode('utf-8'))
    try:
        data = s.recv(BUFFER_SIZE)
        logging.info(f"Received data: {data}")
        data = data.decode('utf-8')
        files = json.loads(data)
        return files
    except (ValueError, json.JSONDecodeError) as e:
        print(f"Failed to decode the file list: {e}")
        return {}
    except Exception as e:
        print(f"Error while requesting file list: {e}")

def format_file_size(size_bytes):
    """Format the file size in a human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} bytes"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / (1024 ** 2):.2f} MB"
    else:
        return f"{size_bytes / (1024 ** 3):.2f} GB"

def download_file(s, filename):
    global is_running
    print(f"Requesting {filename}...")
    s.sendall(filename.encode('utf-8'))

    file_path = os.path.join('output', filename)

    try:
        # Receive the total file size in bytes
        file_size_bytes = s.recv(8)
        if not file_size_bytes:
            print("Failed to receive file size.")
            return
        file_size = struct.unpack('!Q', file_size_bytes)[0]
        received_bytes = 0

        with open(file_path, 'wb') as f:
            print(f"Downloading {filename} ({format_file_size(file_size)})...")
            while is_running and received_bytes < file_size:
                data = s.recv(BUFFER_SIZE)
                if not data:
                    break
                f.write(data)
                received_bytes += len(data)
                # Calculate progress based on bytes
                progress = (received_bytes / file_size) * 100
                print(f"\rProgress: {progress:.2f}%", end="", flush=True)

            print()  # Xuống dòng mới sau khi tải xong
            if received_bytes != file_size:
                print(f"\nError: File size mismatch. Expected: {format_file_size(file_size)}, Received: {format_file_size(received_bytes)}")
                os.remove(file_path)
            else:
                print(f"Finished downloading {filename}.")
    except socket.error as e:
        print(f"Error while downloading {filename}: {e}")
        if os.path.exists(file_path):
            os.remove(file_path)
    except struct.error:
        print("Failed to unpack file size.")
        if os.path.exists(file_path):
            os.remove(file_path)
    except IOError as e:
        print(f"Error while downloading {filename}: {e}")
        if os.path.exists(file_path):
            os.remove(file_path)
    if not is_running:
        print("\nDownload interrupted. Cleaning up...")
        if os.path.exists(file_path):
            os.remove(file_path)

def main():
    create_output_directory()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((HOST, PORT))
        except socket.error as e:
            print(f"Failed to connect to server: {e}")
            return
        start_time = time.time()
        last_processed_index = get_last_position()
        downloaded_files = set()  # Tạo bộ để lưu các file đã tải
        while is_running:
            files = request_file_list(s)
            if not files:
                continue
            print("Available files (approximate sizes):")
            for file, size in files.items():
                print(f"{file} - {size} bytes")
            append_filenames_to_input()
            current_time = time.time()
            elapsed_time = current_time - start_time
            if elapsed_time >= 20:
                input_file_names = read_filenames_from_input()
                files_to_download = input_file_names[last_processed_index:]  # Chỉ xử lý các file mới
                for file_name in files_to_download:
                    if file_name in files and file_name not in downloaded_files:
                        download_file(s, file_name)
                        downloaded_files.add(file_name)  # Thêm file vào bộ (set) file đã tải
                        last_processed_index += 1
                        set_last_position(last_processed_index)
                    else:
                        print(f"File {file_name} does not exist on the server or already downloaded. Skipping.")
                start_time = time.time()  # Reset thời gian bắt đầu
            print("Waiting for new files to be added...")

if __name__ == "__main__":
    main()
