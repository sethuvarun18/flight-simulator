import sys
import os
import threading
import requests
import psutil
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel,
    QProgressBar, QTextEdit, QFileDialog, QHBoxLayout, QCheckBox, QComboBox
)
from PyQt6.QtCore import Qt

BASE_URL = "https://msfs.b-cdn.net/msfs/Official"
BLOCK_COUNT = 5120
BLOCK_PREFIX = "Official"
BLOCK_DIGITS = 4
DOWNLOAD_DIR = "downloads"

class InstallerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MSFS2020 Downloader")
        self.resize(700, 500)

        self.logs = []

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Info disclaimer
        self.info_label = QLabel("This installer is in development. Use at your own risk. Requires SSD (preferably NVMe) with at least 600 GB free space. Microsoft Flight Simulator 2020 must be installed.")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        # Folder selection
        self.folder_label = QLabel("No folder selected")
        layout.addWidget(self.folder_label)
        select_folder_btn = QPushButton("Select MSFS Folder")
        select_folder_btn.clicked.connect(self.select_folder)
        layout.addWidget(select_folder_btn)

        # Mode selection
        mode_layout = QHBoxLayout()
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Download & install immediately", "Download all first, then install"])
        mode_layout.addWidget(QLabel("Mode:"))
        mode_layout.addWidget(self.mode_combo)
        layout.addLayout(mode_layout)

        # RAM limit checkbox
        self.ram_checkbox = QCheckBox("Limit RAM usage to 8GB")
        layout.addWidget(self.ram_checkbox)

        # Progress bars
        self.download_progress = QProgressBar()
        self.download_progress.setFormat("Download progress: %p%")
        layout.addWidget(self.download_progress)

        self.install_progress = QProgressBar()
        self.install_progress.setFormat("Install progress: %p%")
        layout.addWidget(self.install_progress)

        # Logs
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

        # Start button
        start_button = QPushButton("Start")
        start_button.clicked.connect(self.start_installation)
        layout.addWidget(start_button)

        # Donation
        self.donation_label = QLabel("Support the project (hosting is expensive):\nMonero: 41mC3...ZNhQ")
        layout.addWidget(self.donation_label)

        self.setLayout(layout)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select MSFS Folder")
        if folder:
            self.folder_label.setText(folder)
            self.install_path = folder

    def log(self, message):
        self.logs.append(message)
        self.log_text.setPlainText("\n".join(self.logs))
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def start_installation(self):
        thread = threading.Thread(target=self.download_and_install)
        thread.start()

    def download_and_install(self):
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import shutil
        import zipfile
        import time

        base_url = BASE_URL
        download_dir = DOWNLOAD_DIR
        os.makedirs(download_dir, exist_ok=True)

        self.log("Checking disk space and RAM usage...")

        # Check free disk space
        total, used, free = shutil.disk_usage(download_dir)
        if free < 600 * 1024**3:
            self.log("Insufficient disk space. At least 600 GB is required.")
            return

        # RAM limit check
        if self.ram_checkbox.isChecked():
            ram = psutil.virtual_memory()
            if ram.total > 8 * 1024**3:
                self.log("RAM limit enabled. Monitoring memory usage...")
                def wait_for_memory():
                    while psutil.virtual_memory().used > 8 * 1024**3:
                        self.log("High memory usage, waiting...")
                        time.sleep(1)
                wait_for_memory()

        files = [f"{BLOCK_PREFIX}.zip.{str(i).zfill(4)}" for i in range(1, 2408)]

        def download_file(filename):
            url = f"{base_url}{filename}"
            local_path = os.path.join(download_dir, filename)
            if os.path.exists(local_path):
                return f"{filename} already exists."
            try:
                with requests.get(url, stream=True, timeout=30) as r:
                    r.raise_for_status()
                    with open(local_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                # Attempt extraction if ZIP
                if local_path.endswith(".zip"):
                    with zipfile.ZipFile(local_path, 'r') as zip_ref:
                        zip_ref.extractall(self.install_path or download_dir)
                    return f"Downloaded and extracted {filename}"
                return f"Downloaded {filename}"
            except Exception as e:
                return f"Failed to download {filename}: {e}"

        max_workers = 4
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {executor.submit(download_file, fname): fname for fname in files}
            for i, future in enumerate(as_completed(future_to_file)):
                result = future.result()
                self.log(result)
                self.download_progress.setValue(int((i + 1) / len(files) * 100))
                self.install_progress.setValue(int((i + 1) / len(files) * 100))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = InstallerApp()
    window.show()
    sys.exit(app.exec())