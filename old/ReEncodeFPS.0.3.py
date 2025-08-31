import sys
import os
import re
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QLineEdit, QListWidget, QFileDialog, 
                             QGroupBox, QGridLayout, QMessageBox, QTextEdit, QProgressBar)
from PyQt5.QtCore import Qt, QProcess, QTimer

class FFmpegConverter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FFmpeg Batch Converter")
        self.setGeometry(100, 100, 900, 700)
        
        # Initialize process
        self.process = QProcess()
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.process_finished)
        
        # Initialize probe process (for getting video duration)
        self.probe_process = QProcess()
        self.probe_process.finished.connect(self.probe_finished)
        
        # Store conversion data
        self.current_file_index = -1
        self.total_files = 0
        self.files_to_process = []
        self.file_durations = {}  # Store duration for each file
        
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
        
        # Progress section
        progress_group = QGroupBox("Conversion Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        # Overall progress bar
        self.overall_progress = QProgressBar()
        self.overall_progress.setVisible(False)
        progress_layout.addWidget(QLabel("Overall Progress:"))
        progress_layout.addWidget(self.overall_progress)
        
        # Current file progress
        self.current_file_label = QLabel("Current File: None")
        progress_layout.addWidget(self.current_file_label)
        
        self.current_progress = QProgressBar()
        self.current_progress.setVisible(False)
        progress_layout.addWidget(self.current_progress)
        
        # Progress percentage and time
        progress_info_layout = QHBoxLayout()
        self.progress_percentage = QLabel("0%")
        self.elapsed_time = QLabel("Elapsed: 00:00:00")
        self.remaining_time = QLabel("Remaining: --:--:--")
        progress_info_layout.addWidget(self.progress_percentage)
        progress_info_layout.addWidget(self.elapsed_time)
        progress_info_layout.addWidget(self.remaining_time)
        progress_layout.addLayout(progress_info_layout)
        
        layout.addWidget(progress_group)
        
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
        
        # Timer for progress updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.start_time = None
        
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
    
    def get_video_duration(self, file_path):
        # Use ffprobe to get the duration of the video file
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            file_path
        ]
        
        self.probe_process.start(cmd[0], cmd[1:])
    
    def probe_finished(self):
        if self.probe_process.exitStatus() == QProcess.NormalExit and self.probe_process.exitCode() == 0:
            output = self.probe_process.readAllStandardOutput().data().decode()
            try:
                data = json.loads(output)
                duration = float(data['format']['duration'])
                current_file = self.files_to_process[self.current_file_index]
                self.file_durations[current_file] = duration
                self.update_status(f"Video duration: {self.format_time(duration)}")
                
                # Now that we have the duration, start the conversion
                self.start_conversion_process()
            except (KeyError, ValueError) as e:
                self.update_status(f"Error parsing video duration: {e}")
                # Continue with conversion but without accurate progress
                self.file_durations[self.files_to_process[self.current_file_index]] = 0
                self.start_conversion_process()
        else:
            self.update_status("Error getting video duration")
            # Continue with conversion but without accurate progress
            self.file_durations[self.files_to_process[self.current_file_index]] = 0
            self.start_conversion_process()
    
    def format_time(self, seconds):
        # Convert seconds to HH:MM:SS format
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def handle_stdout(self):
        data = self.process.readAllStandardOutput()
        stdout = bytes(data).decode("utf8")
        self.parse_ffmpeg_output(stdout)
    
    def handle_stderr(self):
        data = self.process.readAllStandardError()
        stderr = bytes(data).decode("utf8")
        self.parse_ffmpeg_output(stderr)
    
    def parse_ffmpeg_output(self, output):
        # Parse FFmpeg output to extract progress information
        lines = output.split('\n')
        for line in lines:
            if 'time=' in line:
                # Extract time information
                time_match = re.search(r'time=(\d+):(\d+):(\d+\.\d+)', line)
                if time_match:
                    hours = int(time_match.group(1))
                    minutes = int(time_match.group(2))
                    seconds = float(time_match.group(3))
                    current_time = hours * 3600 + minutes * 60 + seconds
                    
                    # Get the total duration for this file
                    current_file = self.files_to_process[self.current_file_index]
                    total_duration = self.file_durations.get(current_file, 0)
                    
                    if total_duration > 0:
                        # Calculate accurate progress percentage
                        progress = min(100, int((current_time / total_duration) * 100))
                        self.current_progress.setValue(progress)
                        self.progress_percentage.setText(f"{progress}%")
                        
                        # Calculate remaining time
                        if self.start_time and progress > 0:
                            elapsed_seconds = self.start_time.secsTo(QTime.currentTime())
                            total_estimated = elapsed_seconds * 100 / progress
                            remaining_seconds = total_estimated - elapsed_seconds
                            self.remaining_time.setText(f"Remaining: {self.format_time(remaining_seconds)}")
            
            # Display the output in the status area
            if line.strip():
                self.update_status(line.strip())
    
    def update_timer(self):
        if self.start_time:
            elapsed_seconds = self.start_time.secsTo(QTime.currentTime())
            self.elapsed_time.setText(f"Elapsed: {self.format_time(elapsed_seconds)}")
    
    def process_finished(self):
        # Stop the timer
        self.timer.stop()
        
        if self.process.exitStatus() == QProcess.NormalExit and self.process.exitCode() == 0:
            self.update_status(f"✓ Successfully converted {os.path.basename(self.files_to_process[self.current_file_index])}")
            
            # Move to next file
            self.current_file_index += 1
            if self.current_file_index < self.total_files:
                self.process_next_file()
            else:
                self.conversion_complete()
        else:
            error = self.process.readAllStandardError().data().decode()
            self.update_status(f"✗ Error converting file: {error}")
            self.conversion_complete()
    
    def start_conversion_process(self):
        file_path = self.files_to_process[self.current_file_index]
        filename = os.path.basename(file_path)
        
        # Update progress UI
        self.overall_progress.setValue(int((self.current_file_index / self.total_files) * 100))
        self.current_file_label.setText(f"Current File: {filename}")
        self.current_progress.setValue(0)
        self.progress_percentage.setText("0%")
        
        # Get settings
        bitrate = self.bitrate_input.text() or "3000k"
        fps = self.fps_input.text()
        preset = self.preset_input.text() or "p1"
        bframes = self.bframes_input.text() or "4"
        lookahead = self.lookahead_input.text() or "32"
        encoder = self.encoder_input.text() or "nvenc"
        decoder = self.decoder_input.text() or "cuda"
        threads = self.threads_input.text() or "1"
        output_folder = self.output_input.text()
        
        # Prepare output filename
        name, ext = os.path.splitext(filename)
        output_filename = f"{name}.{bitrate}bps.{fps if fps else 'source'}fps.{decoder}.{encoder}{ext}"
        output_path = os.path.join(output_folder, output_filename)
        
        # Skip if output file already exists
        if os.path.exists(output_path):
            self.update_status(f"Skipping {filename} - already exists in output folder")
            self.current_file_index += 1
            self.process_next_file()
            return
        
        # Build FFmpeg command
        cmd = [
            'ffmpeg',
            '-hide_banner',
            '-loglevel', 'info',
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
            '-y',  # Overwrite output files without asking
            output_path
        ])
        
        # Start the process
        self.update_status(f"Converting {filename}...")
        self.process.start(cmd[0], cmd[1:])
        
        # Start the timer for elapsed time
        self.start_time = QTime.currentTime()
        self.timer.start(1000)  # Update every second
    
    def process_next_file(self):
        if self.current_file_index >= self.total_files:
            self.conversion_complete()
            return
        
        # Get the duration of the current file first
        current_file = self.files_to_process[self.current_file_index]
        if current_file not in self.file_durations:
            self.get_video_duration(current_file)
        else:
            self.start_conversion_process()
    
    def conversion_complete(self):
        self.update_status(f"Conversion complete. {self.current_file_index}/{self.total_files} files processed successfully.")
        self.convert_btn.setEnabled(True)
        self.overall_progress.setVisible(False)
        self.current_progress.setVisible(False)
        QMessageBox.information(self, "Complete", f"Conversion complete. {self.current_file_index}/{self.total_files} files processed successfully.")
    
    def start_conversion(self):
        if not self.files:
            QMessageBox.warning(self, "No Files", "Please add files to convert first.")
            return
        
        output_folder = self.output_input.text()
        if not output_folder:
            QMessageBox.warning(self, "No Output Folder", "Please select an output folder first.")
            return
        
        # Create output folder if it doesn't exist
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
            self.update_status(f"Created output folder: {output_folder}")
        
        # Initialize conversion
        self.files_to_process = self.files
        self.total_files = len(self.files_to_process)
        self.current_file_index = 0
        self.file_durations = {}
        
        # Setup UI for conversion
        self.convert_btn.setEnabled(False)
        self.overall_progress.setVisible(True)
        self.overall_progress.setRange(0, 100)
        self.current_progress.setVisible(True)
        self.current_progress.setRange(0, 100)
        self.elapsed_time.setText("Elapsed: 00:00:00")
        self.remaining_time.setText("Remaining: --:--:--")
        
        # Start processing
        self.process_next_file()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FFmpegConverter()
    window.show()
    sys.exit(app.exec_())