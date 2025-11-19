import sys
import os
import json
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebEngineWidgets import QWebEngineSettings
from PyQt5.QtCore import QUrl

class BrowserWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Website Rotator")
        self.setGeometry(100, 100, 800, 600)
        
        # Set the window to be resizable
        self.setMinimumSize(400, 300)
        self.setMaximumSize(1600, 1200)

        self.browser = QWebEngineView()
        
        # Create layout and buttons
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.browser)

        self.button_prev = QPushButton("Previous")
        self.button_prev.clicked.connect(self.load_previous_website)
        self.layout.addWidget(self.button_prev)

        self.button_next = QPushButton("Next")
        self.button_next.clicked.connect(self.load_next_website)
        self.layout.addWidget(self.button_next)

        # Set the layout
        container = QWidget()
        container.setLayout(self.layout)
        self.setCentralWidget(container)

        # Load URLs from the JSON file
        self.websites = self.load_urls_from_json("websites.json")
        
        # Debug: Print loaded websites
        print("Websites loaded from JSON:", self.websites)

        # Load directory and update websites list
        self.load_directory("/Volumes/PhotoDrive/DiscoveredEagles")
        
        # Debug: Print loaded websites after adding files from directory
        print("Websites after loading directory:", self.websites)

        self.current_index = 0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.load_next_website)
        self.timer.start(300*1000)  # Change website every 5 seconds

        # Enable required settings
        self.browser.settings().setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        self.browser.settings().setAttribute(QWebEngineSettings.JavascriptEnabled, True)

        self.load_next_website()  # Load the first website initially

    def load_urls_from_json(self, file_path):
        with open(file_path, 'r') as file:
            data = json.load(file)
            return [QUrl.fromLocalFile(url).toString() if url.startswith('/') else url for url in data['websites']]

    def load_next_website(self):
        self.browser.setUrl(QUrl(self.websites[self.current_index]))
        self.current_index = (self.current_index + 1) % len(self.websites)

    def load_previous_website(self):
        self.current_index = (self.current_index - 1) % len(self.websites)
        self.browser.setUrl(QUrl(self.websites[self.current_index]))

    def load_directory(self, directory_path):
        files = [QUrl.fromLocalFile(os.path.join(directory_path, file)).toString()
                 for file in os.listdir(directory_path)
                 if file.endswith('.jpeg') or file.endswith('.jpg') or file.endswith('.JPG')]
        
        # Debug: Print files found in directory
        print("Files found in directory:", files)

        self.websites.extend(files)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BrowserWindow()
    window.show()
    sys.exit(app.exec_())
