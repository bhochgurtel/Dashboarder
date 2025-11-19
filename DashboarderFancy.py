import sys
import os
import json
from PyQt5.QtCore import QTimer, QUrl
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QFileDialog, QSplitter
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebEngineWidgets import QWebEngineSettings


class BrowserWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Website Rotator")
        self.setGeometry(100, 100, 1000, 600)

        self.main_browser = QWebEngineView()
        self.preview_browser = QWebEngineView()

        # Splitter to separate main and preview browsers
        self.splitter = QSplitter()
        self.splitter.addWidget(self.main_browser)
        self.splitter.addWidget(self.preview_browser)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.splitter)

        # Previous and Next buttons
        self.button_prev = QPushButton("Previous")
        self.button_prev.clicked.connect(self.load_previous_website)
        self.layout.addWidget(self.button_prev)

        self.button_next = QPushButton("Next")
        self.button_next.clicked.connect(self.load_next_website)
        self.layout.addWidget(self.button_next)

        # Button to browse for a directory
        self.button_browse = QPushButton("Browse for Images")
        self.button_browse.clicked.connect(self.browse_directory)
        self.layout.addWidget(self.button_browse)

        container = QWidget()
        container.setLayout(self.layout)
        self.setCentralWidget(container)

        self.websites = self.load_urls_from_json("websites.json")
        self.current_index = 0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.load_next_website)
        self.timer.start(300 * 1000)  # Change website every 5 minutes

        self.main_browser.settings().setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        self.main_browser.settings().setAttribute(QWebEngineSettings.JavascriptEnabled, True)

        self.preview_browser.settings().setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        self.preview_browser.settings().setAttribute(QWebEngineSettings.JavascriptEnabled, True)

        self.load_next_website()  # Load the first website initially

    def load_urls_from_json(self, file_path):
        with open(file_path, 'r') as file:
            data = json.load(file)
            return [QUrl.fromLocalFile(url).toString() if url.startswith('/') else url for url in data['websites']]

    def load_next_website(self):
        self.main_browser.setUrl(QUrl(self.websites[self.current_index]))
        self.preview_browser.setUrl(QUrl(self.websites[(self.current_index + 1) % len(self.websites)]))
        self.current_index = (self.current_index + 1) % len(self.websites)

    def load_previous_website(self):
        self.current_index = (self.current_index - 1) % len(self.websites)
        self.main_browser.setUrl(QUrl(self.websites[self.current_index]))
        self.preview_browser.setUrl(QUrl(self.websites[(self.current_index + 1) % len(self.websites)]))

    def load_directory(self, directory_path):
        files = [QUrl.fromLocalFile(os.path.join(directory_path, file)).toString()
                 for file in os.listdir(directory_path)
                 if file.lower().endswith(('.jpeg', '.jpg'))]
        self.websites.extend(files)

    def browse_directory(self):
        directory_path = QFileDialog.getExistingDirectory(self, "Select Directory")
        if directory_path:
            self.load_directory(directory_path)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BrowserWindow()
    window.show()
    sys.exit(app.exec_())
