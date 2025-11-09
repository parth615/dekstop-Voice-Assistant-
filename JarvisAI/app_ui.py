import sys
import datetime
import config
import commands
import voice
import os
import shlex
import time
from queue import Empty

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget,
    QPushButton, QTextEdit, QLabel, QStatusBar,
    QHBoxLayout
)
from PyQt6.QtCore import QThread, pyqtSignal, QObject, Qt, QByteArray, QTimer, QBuffer, QIODevice
from PyQt6.QtGui import QMovie, QFont
import requests


class ListenerWorker(QObject):
    finished = pyqtSignal()
    query_signal = pyqtSignal(str)

    def run(self):
        query = voice.listen()
        self.query_signal.emit(query)
        self.finished.emit()


# --- 2. ASSISTANT WORKER ---
class AssistantWorker(QObject):
    finished = pyqtSignal()

    def __init__(self, query_text, app_instance):
        super().__init__()
        self.query_text = query_text
        self.app_instance = app_instance

    def run(self):
        query = self.query_text

        try:
            if "exit" in query or "bye" in query or "stop listening" in query:
                voice.say("Goodbye Parth, closing the assistant.")
                time.sleep(1.0)
                self.app_instance.quit()
                return

            elif query.startswith(("open ", "launch ")):
                content = query.replace("open ", "", 1).replace("launch ", "", 1).strip()
                is_website_command = any(term in query for term in ["website", "site", "go to", "url"]) or any(
                    suffix in content for suffix in [".com", ".org", ".net", ".edu", ".gov"])

                if is_website_command:
                    site = content
                    if "go to" in query:
                        site = query.split("go to")[-1].strip()

                    site = site.replace("website", "").replace("site", "").replace("go to", "").strip()

                    if site.lower().strip() in ("any kind of site", ""):
                        site = "google.com"
                        voice.say("I'll open Google for you.")

                    if site:
                        commands.open_website(site)
                    else:
                        voice.say("Which website should I open?")
                else:
                    commands.open_app(content)

            elif "shutdown" in query:
                commands.shutdown()
            elif "restart" in query:
                commands.restart()

            elif any(phrase in query for phrase in
                     ["run diagnostics", "check system", "check memory", "check battery", "system status"]):
                commands.run_diagnostics()
            elif any(phrase in query for phrase in
                     ["remember that", "save this fact", "my name is", "i am called", "i live in"]):
                commands.remember_fact(query)

            elif any(phrase in query for phrase in
                     ["what is my", "what is your favorite", "where is my", "tell me about my"]):
                commands.recall_fact(query)

            elif "convert" in query or "conversion" in query:
                commands.convert_units(query)

            elif any(phrase in query for phrase in
                     ["what's copied", "read clipboard", "process clipboard", "what did i copy"]):
                commands.process_clipboard()

            elif query.startswith(("search file for", "find file for", "search local for")):
                keyword = query.split("for")[-1].strip()
                if keyword:
                    commands.search_local_files(keyword)
                else:
                    voice.say("Please provide a keyword to search for.")

            elif any(phrase in query for phrase in
                     ["plan a trip", "book a flight", "find a hotel", "trip to", "commute"]):
                commands.plan_trip_search(query)

            elif any(phrase in query for phrase in ["directions to", "map of", "show me on map", "where is"]):
                commands.search_maps(query)

            elif any(phrase in query for phrase in ["search youtube", "find on youtube", "play on youtube"]):
                commands.search_youtube(query)

            elif "time" in query:
                commands.get_time()
            elif "date" in query or "today's date" in query:
                commands.get_date()
            elif "weather" in query or "temperature" in query:
                parts = query.split("in")
                city = parts[-1].strip() if len(parts) > 1 else ""
                if city:
                    commands.get_weather(city)
                else:
                    voice.say("Which city would you like the weather for?")
            elif "news" in query or "headlines" in query:
                commands.get_news()
            elif "wikipedia" in query or "tell me about" in query:
                term = query.split("wikipedia")[-1].split("tell me about")[-1].strip()
                if term:
                    commands.search_wikipedia(term)
                else:
                    voice.say("What would you like me to search on Wikipedia?")
            elif "tell me a joke" in query or "joke" in query:
                commands.tell_a_joke()
            elif any(word in query for word in
                     ["plus", "minus", "times", "divide", "+", "-", "*", "/", "^", "square", "root", "sin", "cos",
                      "tan",
                      "calculate"]):
                expr = query.replace("what is", "").replace("calculate", "").replace("?", "").strip()
                commands.perform_calculation(expr)

            elif "add to do" in query or "add task" in query:
                task = query.split("add to do")[-1].split("add task")[-1].strip()
                if task:
                    commands.add_todo(task)
                else:
                    voice.say("What task would you like to add?")
            elif "view to do" in query or "what are my tasks" in query:
                commands.view_todo()
            elif "clear to do" in query:
                commands.clear_todo()
            elif "music" in query or "spotify" in query or "play" in query:
                commands.play_music()

            else:
                commands.search_web_general(query)

        except Exception as e:
            if voice.log_to_ui_callback:
                voice.log_to_ui_callback(f"<b><font color='red'>An unexpected error occurred: {e}</font></b>", "red")
            voice.say("I encountered an internal error while processing that command.")
            print(f"Error during command processing: {e}")

        finally:
            self.finished.emit()


# --- 3. ASSISTANT WINDOW (UI) ---
class AssistantWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Jarvis Voice Assistant UI")
        self.setGeometry(100, 100, 800, 600)

        self.setStyleSheet("QMainWindow { background-color: #121212; }")

        self.listener_thread = None
        self.listener_worker = None
        self.processor_thread = None
        self.processor_worker = None

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        try:
            self.log_text.setFont(QFont("Arial", 10))
        except:
            self.log_text.setFont(QFont("Arial", 10))

        self.log_text.setStyleSheet(
            "border: 1px solid #333333; padding: 15px; background-color: #1E1E1E; color: #CCCCCC; border-radius: 8px;"
        )
        self.log_text.setText(
            "<b><font color='#A0A0A0'>Welcome to Jarvis! Click Listen to Command to activate the assistant.</font></b>")

        self.gif_label = QLabel()
        self.gif_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.gif_label.setMinimumHeight(250)

        movie = QMovie()
        self.gif_label.setMovie(movie)

        self.load_gif_from_url(
            "https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExc3ZjcTBmZGR1cWptYWQ4YWw4OGgxamR3dXliZXlna21rbnQxMGR5NiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/XsNAXQl1E8ig8MHAhf/giphy.gif",
            self.gif_label.movie()
        )

        self.listen_button = QPushButton("🎤 Listen to Command")
        self.listen_button.setFixedHeight(50)
        self.listen_button.setStyleSheet(
            "QPushButton { background-color: #007ACC; color: white; border-radius: 8px; font-size: 16px; border: none; }"
            "QPushButton:hover { background-color: #005A99; }"
            "QPushButton:disabled { background-color: #333333; color: #999999; }"
            "QPushButton:pressed { background-color: #004080; }"
        )
        self.listen_button.clicked.connect(self.start_listening)

        control_layout = QHBoxLayout()
        control_layout.addWidget(self.listen_button)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.gif_label)
        main_layout.addWidget(self.log_text)
        main_layout.addLayout(control_layout)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet(
            "QStatusBar { background-color: #1E1E1E; color: #A0A0A0; border-top: 1px solid #333333; }")
        self.setStatusBar(self.status_bar)
        self.set_status("Ready. Click Listen to Command.")

        self.speech_timer = QTimer(self)
        self.speech_timer.timeout.connect(self.process_speech_queue)
        self.speech_timer.start(150)

    def process_speech_queue(self):
        """Checks the global speech queue and executes commands in the main thread."""
        try:
            text = voice.speech_queue.get_nowait()
            if text:
                voice.engine.say(text)
                voice.engine.runAndWait()
        except Empty:
            pass
        except Exception as e:
            print(f"Speech processing error in QTimer: {e}")

    def set_status(self, text, color='#A0A0A0'):
        """Updates the status bar message (Sets status bar color explicitly)."""
        self.status_bar.setStyleSheet(
            f"QStatusBar {{ background-color: #1E1E1E; color: {color}; border-top: 1px solid #333333; }}")
        self.status_bar.showMessage(text)

    def cleanup_listener(self):
        """Aggressively cleans up listener objects."""
        if self.listener_thread:
            self.listener_thread.quit()
            self.listener_thread.wait(500)
            self.listener_thread.deleteLater()
            self.listener_thread = None
        if self.listener_worker:
            self.listener_worker.deleteLater()
            self.listener_worker = None

    def cleanup_processor(self):
        """Aggressively cleans up processor objects."""
        if self.processor_thread:
            self.processor_thread.quit()
            self.processor_thread.wait(500)
            self.processor_thread.deleteLater()
            self.processor_thread = None
        if self.processor_worker:
            self.processor_worker.deleteLater()
            self.processor_worker = None

    def start_listening(self):
        """Initializes and starts the ListenerWorker thread."""
        self.listen_button.setEnabled(False)
        self.set_status("Listening for your command...", '#FFD700')

        self.cleanup_listener()

        self.listener_thread = QThread()
        self.listener_worker = ListenerWorker()
        self.listener_worker.moveToThread(self.listener_thread)

        self.listener_thread.started.connect(self.listener_worker.run)

        self.listener_worker.finished.connect(self.cleanup_listener)
        self.listener_worker.query_signal.connect(self.process_command)
        self.listener_worker.finished.connect(lambda: self.listen_button.setEnabled(True))

        self.listener_thread.start()

    def process_command(self, query):
        """Receives query from Listener and starts AssistantWorker."""
        self.set_status("Speech Recognized. Processing Command...", '#007ACC')

        if query:
            self.cleanup_processor()

            self.processor_thread = QThread()
            self.processor_worker = AssistantWorker(query, self.app)
            self.processor_worker.moveToThread(self.processor_thread)

            self.processor_thread.started.connect(self.processor_worker.run)

            self.processor_worker.finished.connect(self.cleanup_processor)
            self.processor_worker.finished.connect(lambda: self.listen_button.setEnabled(True))
            self.processor_worker.finished.connect(lambda: self.set_status("Ready", '#A0A0A0'))

            self.processor_thread.start()
        else:
            self.listen_button.setEnabled(True)
            self.set_status("Ready (No command detected)", '#A0A0A0')

    def append_log(self, text, color):
        """Appends formatted text to the main log area (The UI callback)."""
        if color == "darkorange":
            display_color = "#FFD700"
        elif color == "black":
            display_color = "#FFFFFF"
        elif color == "navy":
            display_color = "#90CAF9"
        elif color == "red":
            display_color = "#FF8A80"
        else:
            display_color = "#CCCCCC"

        self.log_text.append(f"<p style='color:{display_color}; margin: 0;'>{text}</p>")

    def load_gif_from_url(self, url, movie_player):
        """Fetches a GIF from a URL and loads it into a QMovie object (PyQt6 compatible)."""
        try:
            response = requests.get(url, stream=True, timeout=10)

            if response.status_code == 200:
                self.gif_byte_array = QByteArray(response.content)
                self.gif_buffer = QBuffer(self.gif_byte_array)
                self.gif_buffer.open(QIODevice.OpenModeFlag.ReadOnly)

                movie_player.setDevice(self.gif_buffer)
                movie_player.setCacheMode(QMovie.CacheMode.CacheAll)
                movie_player.start()
            else:
                self.log_text.append(
                    f"<b><font color='#FF8A80'>Error loading GIF: HTTP Status {response.status_code}</font></b>")

        except requests.exceptions.Timeout:
            self.log_text.append("<b><font color='#FF8A80'>Error loading GIF: Request timed out.</font></b>")
        except Exception as e:
            self.log_text.append(f"<b><font color='#FF8A80'>Error loading GIF: {type(e).__name__}: {e}</font></b>")


if __name__ == '__main__':
    app = QApplication(sys.argv)

    window = AssistantWindow()
    window.show()

    voice.set_ui_log_callback(window.append_log)
    app.aboutToQuit.connect(voice.engine.stop)
    window.app = app

    sys.exit(app.exec())