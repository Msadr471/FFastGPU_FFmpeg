import sys
import os
import re
import json
import logging
import winreg
import traceback
import subprocess
from logging.handlers import RotatingFileHandler
from datetime import datetime
import qdarkstyle
import psutil
import GPUtil
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QLineEdit, QListWidget, QFileDialog, 
                             QGroupBox, QGridLayout, QMessageBox, QTextEdit, QProgressBar,
                             QMenuBar, QMenu, QAction, QComboBox)
from PyQt5.QtCore import Qt, QProcess, QTimer, QTime, pyqtSignal
from PyQt5.QtGui import QDragEnterEvent, QDropEvent

class FFmpegConverter(QMainWindow):
    # Add these signals
    gpu_stats_updated = pyqtSignal(float, float, float, float)
    
    # Version information
    NAME = "FFmpeg Batch Converter"
    VERSION = "1.1"
    FILE_DESCRIPTION = "Batch video conversion tool with GPU acceleration"
    PRODUCT_NAME = "FFmpeg Batch Converter"
    PRODUCT_VERSION = "1.1"
    COPYRIGHT = "Copyright © 2023"
    LANGUAGE = "English"
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{self.NAME} v{self.VERSION}")
        self.setGeometry(100, 100, 900, 800)  # Increased height for system monitoring
        
        # ENABLE DRAG AND DROP ON THE MAIN WINDOW
        self.setAcceptDrops(True)
        
        # Store app reference for theme toggling
        self.app = QApplication.instance()
        
        # Check dependencies before proceeding
        if not self.check_dependencies():
            QMessageBox.critical(self, "Missing Dependencies", 
                               "Required tools not found. Please install FFmpeg, FFprobe and NVIDIA drivers.")
            sys.exit(1)
        
        # Setup logging
        self.setup_logging()
        
        # Initialize process
        self.process = None
        self.probe_process = None
        
        # Connect the signal
        self.gpu_stats_updated.connect(self.update_gpu_labels)
        
        # Add these attributes for GPU monitoring
        self.gpu_enc_util = 0
        self.gpu_dec_util = 0
        self.gpu_monitor_process = None
        
        # Start GPU monitoring process
        self.start_gpu_monitoring()
        
        # Add this line to initialize conversion_stopped
        self.conversion_stopped = False
        
        # Add this line to initialize is_stopping
        self.is_stopping = False
        
        # Store conversion data
        self.current_file_index = -1
        self.total_files = 0
        self.files_to_process = []
        self.file_durations = {}  # Store duration for each file
        
        # Create menu bar
        self.create_menu()
        
        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # System monitoring section
        system_group = QGroupBox("System Monitoring")
        system_layout = QGridLayout(system_group)
        
        # CPU usage
        system_layout.addWidget(QLabel("CPU Usage:"), 0, 0)
        self.cpu_label = QLabel("0%")
        system_layout.addWidget(self.cpu_label, 0, 1)
        
        # RAM usage
        system_layout.addWidget(QLabel("RAM Usage:"), 1, 0)
        self.ram_label = QLabel("0%")
        system_layout.addWidget(self.ram_label, 1, 1)
        
        # GPU usage
        system_layout.addWidget(QLabel("GPU Usage:"), 0, 2)
        self.gpu_label = QLabel("0%")
        system_layout.addWidget(self.gpu_label, 0, 3)
        
        # GPU temperature
        system_layout.addWidget(QLabel("GPU Temp:"), 1, 2)
        self.gpu_temp_label = QLabel("0°C")
        system_layout.addWidget(self.gpu_temp_label, 1, 3)
        
        layout.addWidget(system_group)
        
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
        
        # File list with drag and drop support
        self.file_list = QListWidget()
        self.file_list.setAcceptDrops(True)
        self.file_list.setDragDropMode(QListWidget.DropOnly)
        file_layout.addWidget(self.file_list)
        
        layout.addWidget(file_group)
        
        # Settings section - 4 COLUMN VERSION
        settings_group = QGroupBox("Conversion Settings")
        settings_layout = QGridLayout(settings_group)

        # Row 0
        settings_layout.addWidget(QLabel("Bitrate:"), 0, 0)
        self.bitrate_input = QLineEdit("3000k")
        settings_layout.addWidget(self.bitrate_input, 0, 1)

        settings_layout.addWidget(QLabel("FPS:"), 0, 2)
        self.fps_input = QLineEdit("")
        self.fps_input.setPlaceholderText("source")
        settings_layout.addWidget(self.fps_input, 0, 3)

        # Row 1
        settings_layout.addWidget(QLabel("Preset:"), 1, 0)
        self.preset_input = QLineEdit("p1")
        settings_layout.addWidget(self.preset_input, 1, 1)

        settings_layout.addWidget(QLabel("B-frames:"), 1, 2)
        self.bframes_input = QLineEdit("4")
        settings_layout.addWidget(self.bframes_input, 1, 3)

        # Row 2
        settings_layout.addWidget(QLabel("Lookahead:"), 2, 0)
        self.lookahead_input = QLineEdit("32")
        settings_layout.addWidget(self.lookahead_input, 2, 1)

        settings_layout.addWidget(QLabel("Threads:"), 2, 2)
        self.threads_input = QLineEdit("1")
        settings_layout.addWidget(self.threads_input, 2, 3)

        # Row 3
        settings_layout.addWidget(QLabel("Encoder:"), 3, 0)
        self.encoder_input = QLineEdit("nvenc")
        settings_layout.addWidget(self.encoder_input, 3, 1)

        settings_layout.addWidget(QLabel("Decoder:"), 3, 2)
        self.decoder_input = QLineEdit("cuda")
        settings_layout.addWidget(self.decoder_input, 3, 3)

        # Row 4 - Output Folder and Format on the same row
        settings_layout.addWidget(QLabel("Output Folder:"), 4, 0)

        # Create a horizontal layout for folder browser and format
        output_row_layout = QHBoxLayout()

        # Output folder input and browse button
        folder_layout = QHBoxLayout()
        self.output_input = QLineEdit("")
        folder_layout.addWidget(self.output_input)
        self.browse_output_btn = QPushButton("Browse")
        self.browse_output_btn.clicked.connect(self.browse_output_folder)
        folder_layout.addWidget(self.browse_output_btn)
        folder_layout.setStretch(0, 3)  # Input field takes 3 parts
        folder_layout.setStretch(1, 1)  # Button takes 1 part

        output_row_layout.addLayout(folder_layout, 3)  # Folder section takes 3 parts

        # Output format combo box
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["mp4", "mkv"])
        self.format_combo.setMaximumWidth(80)  # Compact width
        format_layout.addWidget(self.format_combo)
        output_row_layout.addLayout(format_layout, 1)  # Format section takes 1 part

        # Add the combined layout to the grid
        settings_layout.addLayout(output_row_layout, 4, 1, 1, 3)  # Span all 3 columns

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
        
        # Stop button
        self.stop_btn = QPushButton("Stop Conversion")
        self.stop_btn.clicked.connect(self.stop_conversion)
        self.stop_btn.setEnabled(False)
        layout.addWidget(self.stop_btn)
        
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
        
        # Timer for system monitoring
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self.update_system_stats)
        self.monitor_timer.start(1000)  # Update every 3 seconds instead of 2
        
        # Store selected files
        self.files = []
        
        # Theme settings
        self.is_dark_mode = True  # Default to dark mode
        
        # Log startup
        logging.info(f"{self.NAME} v{self.VERSION} application started")
        self.update_status(f"{self.NAME} v{self.VERSION} - {self.COPYRIGHT}")
    
    def check_dependencies(self):
        """Check if required tools are available in the system PATH"""
        missing_tools = []
        
        # Check ffmpeg
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, 
                         timeout=2, creationflags=subprocess.CREATE_NO_WINDOW)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            missing_tools.append("FFmpeg")
        
        # Check ffprobe
        try:
            subprocess.run(['ffprobe', '-version'], capture_output=True, 
                         timeout=2, creationflags=subprocess.CREATE_NO_WINDOW)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            missing_tools.append("FFprobe")
        
        # Check nvidia-smi (for GPU monitoring)
        try:
            subprocess.run(['nvidia-smi', '--help'], capture_output=True, 
                         timeout=2, creationflags=subprocess.CREATE_NO_WINDOW)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            missing_tools.append("NVIDIA drivers (nvidia-smi)")
        
        if missing_tools:
            error_msg = f"Missing required tools: {', '.join(missing_tools)}"
            print(error_msg)
            return False
        
        return True

    def create_menu(self):
        """Create menu bar with theme toggle and about options"""
        menu_bar = QMenuBar(self)
        
        # File menu
        file_menu = menu_bar.addMenu("File")
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menu_bar.addMenu("View")
        
        # Theme toggle action
        self.theme_action = QAction("Toggle Dark/Light Theme", self)
        self.theme_action.triggered.connect(self.toggle_theme)
        view_menu.addAction(self.theme_action)
        
        # Help menu
        help_menu = menu_bar.addMenu("Help")
        
        # About action
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        self.setMenuBar(menu_bar)
    
    def show_about(self):
        """Show about dialog with version information"""
        about_text = f"""
        {self.NAME} v{self.VERSION}
        
        {self.FILE_DESCRIPTION}
        
        Product: {self.PRODUCT_NAME}
        Version: {self.PRODUCT_VERSION}
        {self.COPYRIGHT}
        Language: {self.LANGUAGE}
        
        This application requires:
        - FFmpeg and FFprobe
        - NVIDIA GPU with drivers
        """
        
        QMessageBox.about(self, f"About {self.NAME}", about_text)

    # Enhanced logging setup
    def setup_logging(self):
        # Create logs directory if it doesn't exist
        if not os.path.exists("logs"):
            os.makedirs("logs")
        
        # Setup GUI logger with rotation (10MB max, 5 backup files)
        self.gui_logger = logging.getLogger('gui')
        self.gui_logger.setLevel(logging.INFO)
        gui_handler = RotatingFileHandler(
            'logs/gui.log', maxBytes=10*1024*1024, backupCount=5
        )
        gui_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        self.gui_logger.addHandler(gui_handler)
        
        # Setup FFmpeg logger with rotation
        self.ffmpeg_logger = logging.getLogger('ffmpeg')
        self.ffmpeg_logger.setLevel(logging.DEBUG)
        ffmpeg_handler = RotatingFileHandler(
            'logs/ffmpeg.log', maxBytes=10*1024*1024, backupCount=5
        )
        ffmpeg_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        self.ffmpeg_logger.addHandler(ffmpeg_handler)
        
        # Also log to console for debugging
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        self.gui_logger.addHandler(console_handler)

    def update_gpu_labels(self, gpu_percent, gpu_temp, enc_util, dec_util):
        """Thread-safe update of GPU labels"""
        self.gpu_label.setText(f"GPU: {gpu_percent:.1f}% | ENC: {enc_util:.1f}% | DEC: {dec_util:.1f}%")
        self.gpu_temp_label.setText(f"GPU Temp: {gpu_temp:.1f}°C")

    def start_gpu_monitoring(self):
        """Start a background process to monitor GPU ENC/DEC utilization"""
        try:
            # Kill any existing monitoring process
            if self.gpu_monitor_process and self.gpu_monitor_process.poll() is None:
                self.gpu_monitor_process.terminate()
            
            # Start a new monitoring process
            self.gpu_monitor_process = subprocess.Popen([
                'nvidia-smi', 
                '-q', '-d', 'UTILIZATION', '-l', '1'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
               text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            
            # Start a thread to read the output
            import threading
            monitor_thread = threading.Thread(target=self.read_gpu_monitor_output)
            monitor_thread.daemon = True
            monitor_thread.start()
            
        except Exception as e:
            self.update_status(f"Error starting GPU monitoring: {e}")
            self.log_error_with_traceback(f"Error starting GPU monitoring: {e}")

    def read_gpu_monitor_output(self):
        """Read output from the GPU monitoring process"""
        try:
            while self.gpu_monitor_process and self.gpu_monitor_process.poll() is None:
                line = self.gpu_monitor_process.stdout.readline()
                if not line:
                    break
                    
                # Parse ENC utilization
                enc_match = re.search(r'Encoder\s+:\s+(\d+) %', line)
                if enc_match:
                    self.gpu_enc_util = float(enc_match.group(1))
                
                # Parse DEC utilization
                dec_match = re.search(r'Decoder\s+:\s+(\d+) %', line)
                if dec_match:
                    self.gpu_dec_util = float(dec_match.group(1))
                    
        except Exception as e:
            self.update_status(f"Error reading GPU monitor output: {e}")
            self.log_error_with_traceback(f"Error reading GPU monitor output: {e}")

    def update_system_stats(self):
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent()
            
            # RAM usage
            ram = psutil.virtual_memory()
            ram_percent = ram.percent
            
            # Update CPU and RAM
            self.cpu_label.setText(f"CPU: {cpu_percent:.1f}%")
            self.ram_label.setText(f"RAM: {ram_percent:.1f}%")
            
            # Only update GPU stats occasionally (every 10 seconds)
            current_time = QTime.currentTime()
            if not hasattr(self, 'last_gpu_update'):
                self.last_gpu_update = current_time.addSecs(-15)
                
            if self.last_gpu_update.secsTo(current_time) >= 10:
                self.last_gpu_update = current_time
                
                gpu_percent = 0
                gpu_temp = 0
                
                try:
                    # Get GPU usage and temperature
                    result = subprocess.run([
                        'nvidia-smi', 
                        '--query-gpu=utilization.gpu,temperature.gpu',
                        '--format=csv,noheader,nounits'
                    ], capture_output=True, text=True, timeout=3, creationflags=subprocess.CREATE_NO_WINDOW)
                    
                    if result.returncode == 0:
                        gpu_data = result.stdout.strip().split(', ')
                        if len(gpu_data) >= 2:
                            gpu_percent = float(gpu_data[0])
                            gpu_temp = float(gpu_data[1])
                except:
                    # Fallback to GPUtil if nvidia-smi fails
                    try:
                        gpus = GPUtil.getGPUs()
                        if gpus:
                            gpu = gpus[0]
                            gpu_percent = gpu.load * 100
                            gpu_temp = gpu.temperature
                    except:
                        gpu_percent = 0
                        gpu_temp = 0
                
                # Emit signal for thread-safe GUI update
                self.gpu_stats_updated.emit(gpu_percent, gpu_temp, self.gpu_enc_util, self.gpu_dec_util)
            
        except Exception as e:
            self.update_status(f"Error getting system stats: {e}")
            self.log_error_with_traceback(f"Error getting system stats: {e}")
    
    def dragEnterEvent(self, event):
        """Accept drag events containing URLs"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        """Handle file drops on the main window"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            video_files = []
            
            for url in urls:
                file_path = url.toLocalFile()
                if os.path.isfile(file_path) and file_path.lower().endswith(('.mp4', '.mkv')):
                    video_files.append(file_path)
            
            if video_files:
                self.files.extend(video_files)
                self.file_list.clear()
                self.file_list.addItems([os.path.basename(f) for f in self.files])
                self.update_status(f"Added {len(video_files)} files via drag & drop")
                self.gui_logger.info(f"Added {len(video_files)} files via drag & drop")
                
                # UPDATE OUTPUT FOLDER BASED ON NEW FILES
                self.update_output_folder_based_on_input()
            
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def add_files(self):
        try:
            files, _ = QFileDialog.getOpenFileNames(
                self, "Select Video Files", "", 
                "Video Files (*.mp4 *.mkv);;All Files (*)"
            )
            if files:
                self.files.extend(files)
                self.file_list.clear()
                self.file_list.addItems(self.files)
                self.update_status(f"Added {len(files)} files")
                self.gui_logger.info(f"Added {len(files)} files: {files}")
                
                # UPDATE OUTPUT FOLDER BASED ON NEW FILES
                self.update_output_folder_based_on_input()
        except Exception as e:
            error_msg = f"Error adding files: {str(e)}"
            self.update_status(error_msg)
            self.log_error_with_traceback(error_msg)
    
    def clear_file_list(self):
        try:
            self.files = []
            self.file_list.clear()
            self.update_status("File list cleared")
            self.gui_logger.info("File list cleared")
            
            # CLEAR OUTPUT FOLDER WHEN LIST IS CLEARED
            self.output_input.setText("")
        except Exception as e:
            error_msg = f"Error clearing file list: {str(e)}"
            self.update_status(error_msg)
            self.log_error_with_traceback(error_msg)
    
    def browse_output_folder(self):
        try:
            folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
            if folder:
                self.output_input.setText(folder)
                self.update_status(f"Output folder set to: {folder}")
                self.gui_logger.info(f"Output folder set to: {folder}")
        except Exception as e:
            error_msg = f"Error browsing output folder: {str(e)}"
            self.update_status(error_msg)
            self.log_error_with_traceback(error_msg)
    
    def update_status(self, message):
        try:
            self.status_text.append(message)
            self.gui_logger.info(message)
        except Exception as e:
            print(f"Error updating status: {str(e)}")  # Fallback to console
    
    def get_video_duration(self, file_path):
        try:
            # Use ffprobe to get the duration of the video file
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                file_path
            ]
            
            self.probe_process = QProcess()
            self.probe_process.finished.connect(self.probe_finished)
            self.probe_process.start(cmd[0], cmd[1:])
            self.gui_logger.info(f"Getting video duration for: {file_path}")
        except Exception as e:
            error_msg = f"Error getting video duration: {str(e)}"
            self.update_status(error_msg)
            self.log_error_with_traceback(error_msg)  # Use enhanced logging
            # Continue with conversion but without accurate progress
            self.file_durations[self.files_to_process[self.current_file_index]] = 0
            self.start_conversion_process()
    
    def probe_finished(self):
        try:
            if self.probe_process.exitStatus() == QProcess.NormalExit and self.probe_process.exitCode() == 0:
                output = self.probe_process.readAllStandardOutput().data().decode()
                self.ffmpeg_logger.debug(f"FFprobe output: {output}")
                try:
                    data = json.loads(output)
                    duration = float(data['format']['duration'])
                    current_file = self.files_to_process[self.current_file_index]
                    self.file_durations[current_file] = duration
                    self.update_status(f"Video duration: {self.format_time(duration)}")
                    
                    # Now that we have the duration, start the conversion
                    self.start_conversion_process()
                except (KeyError, ValueError) as e:
                    error_msg = f"Error parsing video duration: {e}"
                    self.update_status(error_msg)
                    self.log_error_with_traceback(error_msg)
                    # Continue with conversion but without accurate progress
                    self.file_durations[self.files_to_process[self.current_file_index]] = 0
                    self.start_conversion_process()
            else:
                error_msg = "Error getting video duration from ffprobe"
                self.update_status(error_msg)
                self.log_error_with_traceback(error_msg)
                # Continue with conversion but without accurate progress
                self.file_durations[self.files_to_process[self.current_file_index]] = 0
                self.start_conversion_process()
        except Exception as e:
            error_msg = f"Error in probe_finished: {str(e)}"
            self.update_status(error_msg)
            self.log_error_with_traceback(error_msg)
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
        try:
            data = self.process.readAllStandardOutput()
            stdout = bytes(data).decode("utf8", errors='ignore')
            self.ffmpeg_logger.info(f"FFmpeg stdout: {stdout}")
            self.parse_ffmpeg_output(stdout)
        except Exception as e:
            self.update_status(f"Error handling stdout: {str(e)}")
            self.log_error_with_traceback(f"Error handling stdout: {str(e)}")
    
    def handle_stderr(self):
        try:
            data = self.process.readAllStandardError()
            stderr = bytes(data).decode("utf8", errors='ignore')
            self.ffmpeg_logger.info(f"FFmpeg stderr: {stderr}")
            self.parse_ffmpeg_output(stderr)
        except Exception as e:
            self.update_status(f"Error handling stderr: {str(e)}")
            self.log_error_with_traceback(f"Error handling stderr: {str(e)}")
    
    def parse_ffmpeg_output(self, output):
        try:
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
        except Exception as e:
            error_msg = f"Error parsing FFmpeg output: {str(e)}"
            self.update_status(error_msg)
            self.log_error_with_traceback(error_msg)
    
    def update_timer(self):
        try:
            if self.start_time:
                elapsed_seconds = self.start_time.secsTo(QTime.currentTime())
                self.elapsed_time.setText(f"Elapsed: {self.format_time(elapsed_seconds)}")
        except Exception as e:
            self.update_status(f"Error updating timer: {str(e)}")
            self.log_error_with_traceback(f"Error updating timer: {str(e)}")
    
    def process_finished(self):
        try:
            # Stop the timer
            self.timer.stop()
            
            if self.process.exitStatus() == QProcess.NormalExit and self.process.exitCode() == 0:
                success_msg = f"✓ Successfully converted {os.path.basename(self.files_to_process[self.current_file_index])}"
                self.update_status(success_msg)
                self.gui_logger.info(success_msg)
                
                # Move to next file
                self.current_file_index += 1
                if self.current_file_index < self.total_files:
                    self.process_next_file()
                else:
                    self.conversion_complete()
            else:
                error = self.process.readAllStandardError().data().decode(errors='ignore')
                error_msg = f"✗ Error converting file: {error}"
                self.update_status(error_msg)
                self.log_error_with_traceback(error_msg)
                self.conversion_complete()
        except Exception as e:
            error_msg = f"Error in process_finished: {str(e)}"
            self.update_status(error_msg)
            self.log_error_with_traceback(error_msg)
            self.conversion_complete()
    
    def start_conversion_process(self):
        try:
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
            output_format = self.format_combo.currentText()
            
            # Prepare output filename
            name, ext = os.path.splitext(filename)
            output_filename = f"{name}.{bitrate}bps.{fps if fps else 'source'}fps.{decoder}.{encoder}.{output_format}"
            output_path = os.path.join(output_folder, output_filename)
            
            if not self.is_safe_path(output_path):
                error_msg = f"Output path contains invalid characters: {output_path}"
                self.update_status(error_msg)
                self.log_error_with_traceback(error_msg)
                self.current_file_index += 1
                self.process_next_file()
                return
            
            # Skip if output file already exists
            if os.path.exists(output_path):
                skip_msg = f"Skipping {filename} - already exists in output folder"
                self.update_status(skip_msg)
                self.gui_logger.info(skip_msg)
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
            
            # Log the command
            self.ffmpeg_logger.info(f"FFmpeg command: {' '.join(cmd)}")
            
            # Start the process
            self.update_status(f"Converting {filename}...")
            
            self.process = QProcess()
            self.process.readyReadStandardOutput.connect(self.handle_stdout)
            self.process.readyReadStandardError.connect(self.handle_stderr)
            self.process.finished.connect(self.process_finished)
            self.process.start(cmd[0], cmd[1:])
            
            # Start the timer for elapsed time
            self.start_time = QTime.currentTime()
            self.timer.start(1000)  # Update every second
        except Exception as e:
            error_msg = f"Error starting conversion process: {str(e)}"
            self.update_status(error_msg)
            self.log_error_with_traceback(error_msg)
            self.conversion_complete()
    
    def process_next_file(self):
        try:
            if self.current_file_index >= self.total_files:
                self.conversion_complete()
                return
            
            # Get the duration of the current file first
            current_file = self.files_to_process[self.current_file_index]
            if current_file not in self.file_durations:
                self.get_video_duration(current_file)
            else:
                self.start_conversion_process()
        except Exception as e:
            error_msg = f"Error in process_next_file: {str(e)}"
            self.update_status(error_msg)
            self.log_error_with_traceback(error_msg)
            self.conversion_complete()
    
    # In the stop_conversion method, set the flag:
    # In the stop_conversion method, add a check to prevent multiple calls:
    def stop_conversion(self):
        try:
            # Check if we're already in the process of stopping
            if hasattr(self, 'is_stopping') and self.is_stopping:
                return
                
            self.is_stopping = True
            self.conversion_stopped = True
            
            self.safe_terminate_process(self.process, "FFmpeg process")
            self.safe_terminate_process(self.probe_process, "probe process")
            
            stop_msg = "Conversion stopped by user"
            self.update_status(stop_msg)
            self.gui_logger.info(stop_msg)
            
            # Reset UI without showing completion message
            self.reset_after_conversion()
            
        except Exception as e:
            error_msg = f"Error stopping conversion: {str(e)}"
            self.update_status(error_msg)
            self.log_error_with_traceback(error_msg)
        finally:
            # Reset the stopping flag
            self.is_stopping = False

    # Add a new method to reset UI after conversion or stop
    # In the reset_after_conversion method, fix the condition check:
    def reset_after_conversion(self):
        try:
            # Stop timers
            if hasattr(self, 'timer') and self.timer.isActive():
                self.timer.stop()
            
            # Reset progress bars
            if hasattr(self, 'overall_progress'):
                self.overall_progress.setVisible(False)
            if hasattr(self, 'current_progress'):
                self.current_progress.setVisible(False)
            
            # Reset buttons
            if hasattr(self, 'convert_btn'):
                self.convert_btn.setEnabled(True)
            if hasattr(self, 'stop_btn'):
                self.stop_btn.setEnabled(False)
            
            # Reset file processing state
            if hasattr(self, 'files_to_process'):
                self.files_to_process = []
            if hasattr(self, 'current_file_index'):
                self.current_file_index = -1
            if hasattr(self, 'total_files'):
                self.total_files = 0
            if hasattr(self, 'file_durations'):
                self.file_durations = {}
            
            # Only show completion message if conversion wasn't stopped
            if not hasattr(self, 'conversion_stopped') or not self.conversion_stopped:
                self.update_status("Conversion completed successfully")
            
            # Reset the flag
            self.conversion_stopped = False
            
        except Exception as e:
            error_msg = f"Error resetting after conversion: {str(e)}"
            self.update_status(error_msg)
            self.log_error_with_traceback(error_msg)

    def safe_terminate_process(self, process, process_name=""):
        """Safely terminate a QProcess with error handling"""
        try:
            if process and process.state() == QProcess.Running:
                self.update_status(f"Stopping {process_name}...")
                process.terminate()
                if not process.waitForFinished(3000):  # Wait up to 3 seconds
                    process.kill()
                    process.waitForFinished(1000)
        except Exception as e:
            error_msg = f"Error terminating {process_name}: {str(e)}"
            self.update_status(error_msg)
            self.log_error_with_traceback(error_msg)
    
    def conversion_complete(self):
        try:
            # Stop the timer
            if hasattr(self, 'timer') and self.timer.isActive():
                self.timer.stop()
            
            # Reset progress bars
            if hasattr(self, 'overall_progress'):
                self.overall_progress.setVisible(False)
            if hasattr(self, 'current_progress'):
                self.current_progress.setVisible(False)
            
            # Reset buttons
            if hasattr(self, 'convert_btn'):
                self.convert_btn.setEnabled(True)
            if hasattr(self, 'stop_btn'):
                self.stop_btn.setEnabled(False)
            
            # Show completion message only if not stopped
            if not hasattr(self, 'conversion_stopped') or not self.conversion_stopped:
                self.update_status("Conversion completed successfully")
            
            # Reset file processing state
            if hasattr(self, 'files_to_process'):
                self.files_to_process = []
            if hasattr(self, 'current_file_index'):
                self.current_file_index = -1
            if hasattr(self, 'total_files'):
                self.total_files = 0
            if hasattr(self, 'file_durations'):
                self.file_durations = {}
            
        except Exception as e:
            error_msg = f"Error in conversion_complete: {str(e)}"
            self.update_status(error_msg)
            self.log_error_with_traceback(error_msg)
    
    def start_conversion(self):
        try:
            if not self.files:
                self.update_status("No files selected for conversion")
                return
            
            # Get output folder
            output_folder = self.output_input.text()
            if not output_folder:
                self.update_status("Please select an output folder")
                return
            
            if not os.path.exists(output_folder):
                try:
                    os.makedirs(output_folder)
                    self.update_status(f"Created output folder: {output_folder}")
                except Exception as e:
                    error_msg = f"Error creating output folder: {str(e)}"
                    self.update_status(error_msg)
                    self.log_error_with_traceback(error_msg)
                    return
            
            # Reset conversion state
            self.files_to_process = self.files.copy()
            self.total_files = len(self.files_to_process)
            self.current_file_index = 0
            self.conversion_stopped = False
            
            # Show progress bars
            self.overall_progress.setVisible(True)
            self.current_progress.setVisible(True)
            self.overall_progress.setValue(0)
            self.current_progress.setValue(0)
            
            # Update buttons
            self.convert_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            
            # Start processing
            self.update_status(f"Starting conversion of {self.total_files} files...")
            self.process_next_file()
        except Exception as e:
            error_msg = f"Error starting conversion: {str(e)}"
            self.update_status(error_msg)
            self.log_error_with_traceback(error_msg)
    
    def is_safe_path(self, path):
        """Check if the path contains any potentially dangerous characters"""
        try:
            # Normalize the path first to handle mixed slashes
            normalized_path = os.path.normpath(path)
            
            # Only check the filename part, not the entire path
            filename = os.path.basename(normalized_path)
            
            # Check for dangerous characters in filename only
            dangerous_chars = ['<', '>', ':', '"', '|', '?', '*']
            for char in dangerous_chars:
                if char in filename:
                    return False
            
            # Additional checks for problematic filename endings
            if filename.endswith(('.', ' ')):
                return False
                
            # Check if filename is empty or too long
            if not filename or len(filename) > 255:  # Windows filename limit
                return False
                
            return True
            
        except Exception as e:
            error_msg = f"Path validation error: {str(e)}"
            self.update_status(error_msg)
            self.log_error_with_traceback(error_msg)
            return False
    
    def log_error_with_traceback(self, message):
        """Enhanced error logging with traceback"""
        try:
            self.gui_logger.error(f"{message}\n{traceback.format_exc()}")
        except:
            print(f"ERROR: {message}")  # Fallback to console
    
    def toggle_theme(self):
        """Toggle between dark and light themes"""
        try:
            if self.is_dark_mode:
                # Switch to light mode
                self.app.setStyleSheet("")
                self.is_dark_mode = False
                self.update_status("Switched to light theme")
                self.gui_logger.info("Switched to light theme")
            else:
                # Switch to dark mode
                self.app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
                self.is_dark_mode = True
                self.update_status("Switched to dark theme")
                self.gui_logger.info("Switched to dark theme")
        except Exception as e:
            error_msg = f"Error toggling theme: {str(e)}"
            self.update_status(error_msg)
            self.log_error_with_traceback(error_msg)
    
    def update_output_folder_based_on_input(self):
        """Set output folder to the first file's directory if all files are from the same folder"""
        if not self.files:
            return
        
        # Get all unique directories
        directories = {os.path.dirname(file_path) for file_path in self.files}
        
        # If all files are from the same directory, set that as output folder
        if len(directories) == 1:
            common_directory = next(iter(directories))
            self.output_input.setText(common_directory)
            self.update_status(f"Output folder set to: {common_directory}")
        else:
            # Files from different directories - clear output folder
            self.output_input.setText("")
            self.update_status("Files from different directories - please select output folder manually")

    def closeEvent(self, event):
        """Handle application close event"""
        try:
            # Stop any running processes
            if hasattr(self, 'process') and self.process and self.process.state() == QProcess.Running:
                self.safe_terminate_process(self.process, "FFmpeg process")
            
            if hasattr(self, 'probe_process') and self.probe_process and self.probe_process.state() == QProcess.Running:
                self.safe_terminate_process(self.probe_process, "probe process")
            
            if hasattr(self, 'gpu_monitor_process') and self.gpu_monitor_process and self.gpu_monitor_process.poll() is None:
                self.gpu_monitor_process.terminate()
            
            # Stop timers
            if hasattr(self, 'timer') and self.timer.isActive():
                self.timer.stop()
            
            if hasattr(self, 'monitor_timer') and self.monitor_timer.isActive():
                self.monitor_timer.stop()
            
            self.gui_logger.info(f"{self.NAME} v{self.VERSION} application closed")
            event.accept()
        except Exception as e:
            error_msg = f"Error during application close: {str(e)}"
            print(error_msg)  # Fallback to console
            event.accept()

def main():
    # Create application
    app = QApplication(sys.argv)
    
    # Set application metadata
    app.setApplicationName(FFmpegConverter.NAME)
    app.setApplicationVersion(FFmpegConverter.VERSION)
    app.setOrganizationName("FFmpeg Converter")
    
    # Apply dark theme by default
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    
    # Create and show main window
    converter = FFmpegConverter()
    converter.show()
    
    # Run the application
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()