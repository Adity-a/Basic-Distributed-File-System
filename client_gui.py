import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from tkinter import ttk
import requests
import json
import os
import subprocess
import math

BLOCK_SIZE = 128 * 1024 * 1024

# Load config
with open("config.json") as f:
    config = json.load(f)

NODES = config["nodes"]
REPLICATION_FACTOR = config["replication_factor"]
SERVER_PROCESSES = []

def get_replicas(filename):
    return NODES[:REPLICATION_FACTOR]

class DFSClientGUI:
    def __init__(self, root):
       self.root = root
       self.root.geometry("700x750")
       self.root.configure(bg="#f0f0f0")
       style = ttk.Style()
       style.theme_use('clam')  # Looks modern
       style.configure("TButton", padding=1, font=("Arial", 10))
       style.configure("TLabel", font=("Arial", 10))
       style.configure("TEntry", font=("Arial", 10))

       # === SERVER CONTROLS ===
       server_frame = ttk.LabelFrame(root, text="Server Control", padding=10)
       server_frame.pack(padx=10, pady=10, fill='x')

       self.start_servers_btn = ttk.Button(server_frame, text="Start All Node Servers", command=self.start_all_servers)
       self.start_servers_btn.pack(side="left", padx=10)

       self.stop_servers_btn = ttk.Button(server_frame, text="Stop All Node Servers", command=self.stop_all_servers, state=tk.DISABLED)
       self.stop_servers_btn.pack(side="left", padx=10)

       # === FILE UPLOAD ===
       upload_frame = ttk.LabelFrame(root, text="Upload File", padding=10)
       upload_frame.pack(padx=10, pady=10, fill='x')

       self.upload_btn = ttk.Button(upload_frame, text="Select File to Upload", command=self.select_file)
       self.upload_btn.pack(pady=5)

       self.upload_file_lbl = ttk.Label(upload_frame, text="No file selected")
       self.upload_file_lbl.pack(pady=5)

       self.confirm_upload_btn = ttk.Button(upload_frame, text="Upload Selected File", command=self.upload_file)
       self.confirm_upload_btn.pack(pady=5)

       # === FILE DOWNLOAD ===
       download_frame = ttk.LabelFrame(root, text="Download or Delete Entire File", padding=10)
       download_frame.pack(padx=10, pady=10, fill='x')

       self.download_entry = ttk.Entry(download_frame, width=50)
       self.download_entry.pack(pady=5)
       self.download_entry.insert(0, "Enter filename to download or delete")

       self.download_btn = ttk.Button(download_frame, text="Download File", command=self.download_file)
       self.download_btn.pack(pady=5)

       self.delete_file_btn = ttk.Button(download_frame, text="Delete Entire File from All Nodes", command=self.delete_entire_file)
       self.delete_file_btn.pack(pady=5)

        # === NODE FILE VIEW ===
       view_frame = ttk.LabelFrame(root, text="Node Files Viewer", padding=10)
       view_frame.pack(padx=10, pady=10, fill='x')

       top_row = ttk.Frame(view_frame)
       top_row.pack()

       self.node_var = tk.StringVar()
       self.node_var.set(NODES[0]['id'])
       node_names = [n["id"] for n in NODES]
       self.node_menu = ttk.OptionMenu(top_row, self.node_var, NODES[0]['id'], *node_names, command=lambda _: self.refresh_node_files())
       self.node_menu.pack(side="left", padx=5)

       self.refresh_btn = ttk.Button(top_row, text="Refresh", command=self.refresh_node_files)
       self.refresh_btn.pack(side="left", padx=5)

       self.files_listbox = tk.Listbox(view_frame, width=60, height=6, font=("Courier", 10))
       self.files_listbox.pack(pady=5)

       self.delete_btn = ttk.Button(view_frame, text="Delete Selected File from Node", command=self.delete_selected_file)
       self.delete_btn.pack(pady=5)

       # === LOG OUTPUT ===
       log_frame = ttk.LabelFrame(root, text="Log Output", padding=10)
       log_frame.pack(padx=10, pady=10, fill='both', expand=True)

       self.log = scrolledtext.ScrolledText(log_frame, width=80, height=30, font=("Courier New", 10))
       self.log.pack(pady=5, fill='both', expand=True)

       # Handle window close
       self.root.protocol("WM_DELETE_WINDOW", self.on_close)


    def log_message(self, message):
        self.log.insert(tk.END, message + "\n")
        self.log.see(tk.END)

    def select_file(self):
        self.filename = filedialog.askopenfilename()
        if self.filename:
            self.upload_file_lbl.config(text=self.filename)
        else:
            self.upload_file_lbl.config(text="No file selected")

    def upload_file(self):
        if not self.filename:
            messagebox.showerror("Error", "No file selected!")
            return

        file_basename = os.path.basename(self.filename)

        # Load metadata
        try:
            with open("dfs_metadata.json") as f:
                metadata = json.load(f)
        except:
            metadata = {}

        version = metadata.get(file_basename, {}).get("version", 0) + 1

        with open(self.filename, 'rb') as f:
            block_id = 0
            while True:
                block_data = f.read(BLOCK_SIZE)
                if not block_data:
                    break

                block_filename = f"{file_basename}_block{block_id}"

                for node in NODES:
                    try:
                        r = requests.post(
                            f"http://{node['host']}:{node['port']}/upload",
                            files={'file': (block_filename, block_data)},
                            data={"version": version}
                        )
                        self.log_message(f"Uploaded block {block_id} to {node['id']}")
                    except Exception as e:
                        self.log_message(f"Failed to upload block {block_id} to {node['id']}: {e}")
                block_id += 1

        metadata[file_basename] = {
            "blocks": block_id,
            "replicas": [n["id"] for n in NODES],
            "version": version
        }

        with open("dfs_metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        self.refresh_node_files()

    def download_file(self):
        filename = self.download_entry.get().strip()
        if not filename:
            messagebox.showerror("Error", "Please enter a filename.")
            return

        try:
            with open("dfs_metadata.json") as f:
                metadata = json.load(f)
            file_info = metadata.get(filename)
            if not file_info:
                self.log_message("File metadata not found.")
                return
        except:
            self.log_message("Failed to read metadata.")
            return

        blocks = file_info["blocks"]
        output_path = f"downloaded_{filename}"

        with open(output_path, "wb") as outfile:
            for i in range(blocks):
                block_filename = f"{filename}_block{i}"
                block_found = False

                for node in NODES:
                    try:
                        r = requests.get(f"http://{node['host']}:{node['port']}/download/{block_filename}")
                        if r.status_code == 200:
                            outfile.write(r.content)
                            self.log_message(f"Downloaded block {i} from {node['id']}")
                            block_found = True
                            break
                    except:
                        continue

                if not block_found:
                    self.log_message(f"Failed to find block {i} on any node.")
                    return

        self.log_message(f"Successfully reassembled and saved as {output_path}")


    def start_all_servers(self):
        global SERVER_PROCESSES
        self.log_message("Starting all node servers...")
        SERVER_PROCESSES.clear()
        for node in NODES:
            try:
                cmd = ["python", "node_server.py", node["id"], str(node["port"])]
                proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                SERVER_PROCESSES.append(proc)
                self.log_message(f"Started server {node['id']} on port {node['port']}")
            except Exception as e:
                self.log_message(f"Failed to start {node['id']}: {e}")
        self.stop_servers_btn.config(state=tk.NORMAL)

    def stop_all_servers(self):
        global SERVER_PROCESSES
        self.log_message("Stopping all node servers...")
        for proc in SERVER_PROCESSES:
            try:
                proc.terminate()
            except:
                pass
        SERVER_PROCESSES.clear()
        self.stop_servers_btn.config(state=tk.DISABLED)
        self.log_message("All servers stopped.")
        
    def get_node_by_id(self, node_id):
     return next((n for n in NODES if n["id"] == node_id), None)

    def refresh_node_files(self):
        node_id = self.node_var.get()
        node = self.get_node_by_id(node_id)
        if not node:
            self.log_message("Invalid node selected.")
            return

        try:
            r = requests.get(f"http://{node['host']}:{node['port']}/list")
            files = r.json().get("files", [])
            self.files_listbox.delete(0, tk.END)
            for f in files:
                self.files_listbox.insert(tk.END, f)
            self.log_message(f"Updated file list from {node_id}")
        except Exception as e:
            self.log_message(f"Failed to fetch files from {node_id}: {e}")

    def delete_selected_file(self):
        node_id = self.node_var.get()
        node = self.get_node_by_id(node_id)
        selected = self.files_listbox.curselection()
        if not selected:
            messagebox.showerror("Error", "Select a file to delete.")
            return

        filename = self.files_listbox.get(selected[0])
        try:
            r = requests.delete(f"http://{node['host']}:{node['port']}/delete/{filename}")
            if r.status_code == 200:
                self.log_message(f"Deleted '{filename}' from {node_id}")
                self.refresh_node_files()
            else:
                self.log_message(f"Failed to delete '{filename}' from {node_id}")
        except Exception as e:
            self.log_message(f"Error deleting from {node_id}: {e}")
            
    def delete_entire_file(self):
        filename = self.download_entry.get().strip()
        if not filename:
            messagebox.showerror("Error", "Enter filename to delete.")
            return

        confirm = messagebox.askyesno("Confirm Deletion", f"Delete all blocks of '{filename}' from all nodes?")
        if not confirm:
            return

        try:
            with open("dfs_metadata.json") as f:
                metadata = json.load(f)
            file_info = metadata.get(filename)
            if not file_info:
                self.log_message("File metadata not found.")
                return
        except:
            self.log_message("Failed to read metadata.")
            return

        blocks = file_info["blocks"]
        deleted_blocks = 0

        for block_id in range(blocks):
            block_filename = f"{filename}_block{block_id}"
            for node in NODES:
                try:
                    r = requests.delete(f"http://{node['host']}:{node['port']}/delete/{block_filename}")
                    if r.status_code == 200:
                        self.log_message(f"Deleted block {block_id} from {node['id']}")
                        deleted_blocks += 1
                except Exception as e:
                    self.log_message(f"Error deleting block {block_id} from {node['id']}: {e}")

        # Clean up metadata
        if filename in metadata:
            del metadata[filename]
            with open("dfs_metadata.json", "w") as f:
                json.dump(metadata, f, indent=2)

        self.refresh_node_files()
        self.log_message(f"Deleted all blocks of '{filename}' from all nodes.")

    def on_close(self):
        self.stop_all_servers()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = DFSClientGUI(root)
    root.mainloop()
