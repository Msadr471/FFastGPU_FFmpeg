import sys
import os
import subprocess
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QLineEdit, QListWidget, QFileDialog, 
                             QGroupBox, QGridLayout, QMessageBox, QCheckBox, QTextEdit)
from PyQt5.QtCore import Qt

class FFmpegConverter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FFmpeg Batch Converter")
        self.setGeometry(100, 100, 900, 700)
        
        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # File selection section
        file_group = QGroupBox("File Selection")
        file_layout = QVBoxLayout(file_group)
        
        # Buttons for file selection
        button_layout = QHBoxLayout()
        self.add_files_btn = QPushButton("Add Files")
        self.add_files_btn.clicked.connect(self.add_files)
        self.clear_list_btn = QPushButton("Clear List")
        self.clear_list_btn.clicked.connect(self.clear_file_list)
        button_layout.addWidget(self.add_files_btn)
        button_layout.addWidget(self.clear_list_btn)
        file_layout.addLayout(button_layout)
        
        # File list
        self.file_list = QListWidget()
        file_layout.addWidget(self.file_list)
        
        layout.addWidget(file_group)
        
        # Settings section
        settings_group = QGroupBox("Conversion Settings")
        settings_layout = QGridLayout(settings_group)
        
        # Bitrate
        settings_layout.addWidget(QLabel("Video Bitrate:"), 0, 0)
        self.bitrate_input = QLineEdit("3000k")
        settings_layout.addWidget(self.bitrate_input, 0, 1)
        
        # FPS
        settings_layout.addWidget(QLabel("Target FPS (empty for source):"), 1, 0)
        self.fps_input = QLineEdit("")
        settings_layout.addWidget(self.fps_input, 1, 1)
        
        # Preset
        settings_layout.addWidget(QLabel("Preset:"), 2, 0)
        self.preset_input = QLineEdit("p1")
        settings_layout.addWidget(self.preset_input, 2, 1)
        
        # B-frames
        settings_layout.addWidget(QLabel("B-frames:"), 3, 0)
        self.bframes_input = QLineEdit("4")
        settings_layout.addWidget(self.bframes_input, 3, 1)
        
        # Lookahead
        settings_layout.addWidget(QLabel("Lookahead:"), 4, 0)
        self.lookahead_input = QLineEdit("32")
        settings_layout.addWidget(self.lookahead_input, 4, 1)
        
        # Encoder
        settings_layout.addWidget(QLabel("Encoder:"), 5, 0)
        self.encoder_input = QLineEdit("nvenc")
        settings_layout.addWidget(self.encoder_input, 5, 1)
        
        # Decoder
        settings_layout.addWidget(QLabel("Decoder:"), 6, 0)
        self.decoder_input = QLineEdit("cuda")
        settings_layout.addWidget(self.decoder_input, 6, 1)
        
        # Threads
        settings_layout.addWidget(QLabel("Threads:"), 7, 0)
        self.threads_input = QLineEdit("1")
        settings_layout.addWidget(self.threads_input, 7, 1)
        
        # Output folder
        settings_layout.addWidget(QLabel("Output Folder:"), 8, 0)
        output_layout = QHBoxLayout()
        self.output_input = QLineEdit("")
        output_layout.addWidget(self.output_input)
        self.browse_output_btn = QPushButton("Browse")
        self.browse_output_btn.clicked.connect(self.browse_output_folder)
        output_layout.addWidget(self.browse_output_btn)
        settings_layout.addLayout(output_layout, 8, 1)
        
        layout.addWidget(settings_group)
        
        # Conversion button
        self.convert_btn = QPushButton("Start Conversion")
        self.convert_btn.clicked.connect(self.start_conversion)
        layout.addWidget(self.convert_btn)
        
        # Status area
        status_group = QGroupBox("Conversion Status")
        status_layout = QVBoxLayout(status_group)
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        status_layout.addWidget(self.status_text)
        layout.addWidget(status_group)
        
        # Store selected files
        self.files = []
    
    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Video Files", "", 
            "Video Files (*.mp4 *.mkv);;All Files (*)"
        )
        if files:
            self.files.extend(files)
            self.file_list.clear()
            self.file_list.addItems(self.files)
            self.update_status(f"Added {len(files)} files")
    
    def clear_file_list(self):
        self.files = []
        self.file_list.clear()
        self.update_status("File list cleared")
    
    def browse_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_input.setText(folder)
            self.update_status(f"Output folder set to: {folder}")
    
    def update_status(self, message):
        self.status_text.append(message)
    
    def start_conversion(self):
        if not self.files:
            QMessageBox.warning(self, "No Files", "Please add files to convert first.")
            return
        
        output_folder = self.output_input.text()
        if not output_folder:
            QMessageBox.warning(self, "No Output Folder", "Please select an output folder first.")
            return
        
        # Get settings
        bitrate = self.bitrate_input.text() or "3000k"
        fps = self.fps_input.text()
        preset = self.preset_input.text() or "p1"
        bframes = self.bframes_input.text() or "4"
        lookahead = self.lookahead_input.text() or "32"
        encoder = self.encoder_input.text() or "nvenc"
        decoder = self.decoder_input.text() or "cuda"
        threads = self.threads_input.text() or "1"
        
        # Create output folder if it doesn't exist
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
            self.update_status(f"Created output folder: {output_folder}")
        
        # Process each file
        success_count = 0
        for file_path in self.files:
            try:
                # Prepare output filename
                filename = os.path.basename(file_path)
                name, ext = os.path.splitext(filename)
                
                # Build output path
                output_filename = f"{name}.{bitrate}bps.{fps if fps else 'source'}fps.{decoder}.{encoder}{ext}"
                output_path = os.path.join(output_folder, output_filename)
                
                # Skip if output file already exists
                if os.path.exists(output_path):
                    self.update_status(f"Skipping {filename} - already exists in output folder")
                    continue
                
                # Build FFmpeg command
                cmd = [
                    'ffmpeg',
                    '-hide_banner',
                    '-loglevel', 'warning',
                    '-stats',
                    '-hwaccel', decoder,
                    '-hwaccel_output_format', decoder,
                    '-threads', threads,
                    '-i', file_path
                ]
                
                # Add FPS filter if specified
                if fps:
                    cmd.extend(['-vf', f'fps={fps}'])
                
                # Add encoding parameters
                cmd.extend([
                    '-c:v', f'hevc_{encoder}',
                    '-preset', preset,
                    '-b:v', bitrate,
                    '-bf', bframes,
                    '-rc-lookahead', lookahead,
                    '-c:a', 'copy',
                    output_path
                ])
                
                # Run FFmpeg
                self.update_status(f"Converting {filename}...")
                QApplication.processEvents()  # Update UI
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    success_count += 1
                    self.update_status(f"✓ Successfully converted {filename}")
                else:
                    self.update_status(f"✗ Error converting {filename}: {result.stderr}")
                
            except Exception as e:
                self.update_status(f"✗ Error processing {filename}: {str(e)}")
        
        self.update_status(f"Conversion complete. {success_count}/{len(self.files)} files processed successfully.")
        QMessageBox.information(self, "Complete", f"Conversion complete. {success_count}/{len(self.files)} files processed successfully.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FFmpegConverter()
    window.show()
    sys.exit(app.exec_())