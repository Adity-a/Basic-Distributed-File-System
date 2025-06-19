# Distributed File System (DFS) with GUI

This is a basic distributed file system prototype with:
- File upload/download support
- File replication across multiple nodes
- Version-based consistency
- A user-friendly GUI

## Setup

### Install dependencies
```bash
pip install -r requirements.txt
```

### Start the 4 Node Servers (in 4 terminals)
```bash
python node_server.py node1 5001
python node_server.py node2 5002
python node_server.py node3 5003
python node_server.py node4 5004
```

### Run GUI Client
```bash
python client_gui.py
```

Use GUI to upload/download files and see logs.
