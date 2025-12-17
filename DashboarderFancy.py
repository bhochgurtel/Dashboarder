import sys
import os
import json
import sqlite3
import keyring
from urllib.parse import urlparse

from PyQt5.QtCore import QTimer, QUrl, Qt
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget,
    QPushButton, QFileDialog, QSplitter, QDialog,
    QFormLayout, QLineEdit, QDialogButtonBox, QLabel,
    QListWidget, QHBoxLayout, QMessageBox
)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings


# ===============================
# SQLite-backed app configuration
# ===============================

class AppConfig:
    """
    Stores non-sensitive metadata in SQLite:
    - websites list (if you want to persist)
    - per-site notes / options later if needed.
    """
    def __init__(self, db_path="config.db"):
        self.db_path = db_path
        self._ensure_schema()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _ensure_schema(self):
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS websites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def save_websites(self, websites):
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("DELETE FROM websites")
        for url in websites:
            cur.execute("INSERT OR IGNORE INTO websites (url) VALUES (?)", (url,))
        conn.commit()
        conn.close()

    def load_websites(self):
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT url FROM websites ORDER BY id ASC")
        rows = cur.fetchall()
        conn.close()
        return [r[0] for r in rows]


# ===============================
# Secure credential store (keyring)
# ===============================

class CredentialStore:
    SERVICE_NAME = "WebsiteRotatorApp"

    @staticmethod
    def _key(url, kind):
        # kind: "username" or "password"
        return f"{url}_{kind}"

    @staticmethod
    def save_credentials(url, username, password):
        keyring.set_password(CredentialStore.SERVICE_NAME,
                             CredentialStore._key(url, "username"),
                             username or "")
        keyring.set_password(CredentialStore.SERVICE_NAME,
                             CredentialStore._key(url, "password"),
                             password or "")

    @staticmethod
    def get_credentials(url):
        username = keyring.get_password(CredentialStore.SERVICE_NAME,
                                        CredentialStore._key(url, "username"))
        password = keyring.get_password(CredentialStore.SERVICE_NAME,
                                        CredentialStore._key(url, "password"))
        # keyring returns None if not set
        if not username or not password:
            return None, None
        return username, password

    @staticmethod
    def delete_credentials(url):
        for kind in ("username", "password"):
            try:
                keyring.delete_password(CredentialStore.SERVICE_NAME,
                                        CredentialStore._key(url, kind))
            except keyring.errors.PasswordDeleteError:
                pass  # Ignore if not present


# ===============================
# Website manager
# ===============================

class WebsiteManager:
    def __init__(self, json_path="websites.json", config: AppConfig = None):
        self.json_path = json_path
        self.config = config
        self.websites = self._load_initial_websites()
        self.index = 0

    def _load_initial_websites(self):
        websites_from_db = self.config.load_websites() if self.config else []
        if websites_from_db:
            return websites_from_db

        if os.path.exists(self.json_path):
            with open(self.json_path, "r") as f:
                data = json.load(f)
            urls = data.get("websites", [])
        else:
            urls = []

        if self.config:
            self.config.save_websites(urls)
        return urls

    def _persist(self):
        if self.config:
            self.config.save_websites(self.websites)

    def all(self):
        return list(self.websites)

    def current_url(self):
        if not self.websites:
            return None
        return self.websites[self.index]

    def next(self):
        if not self.websites:
            return None
        url = self.websites[self.index]
        self.index = (self.index + 1) % len(self.websites)
        self._persist()
        return url

    def previous(self):
        if not self.websites:
            return None
        self.index = (self.index - 1) % len(self.websites)
        self._persist()
        return self.websites[self.index]

    def peek_next(self):
        if not self.websites:
            return None
        return self.websites[(self.index + 1) % len(self.websites)]

    def add_images_from_directory(self, directory):
        added = False
        for file in os.listdir(directory):
            if file.lower().endswith((".jpg", ".jpeg")):
                full_path = os.path.join(directory, file)
                url = QUrl.fromLocalFile(full_path).toString()
                self.websites.append(url)
                added = True
        if added:
            self._persist()


# ===============================
# Credential dialog (add/edit)
# ===============================

class CredentialDialog(QDialog):
    def __init__(self, parent=None, url=None, username="", password=""):
        super().__init__(parent)
        self.setWindowTitle("Site Credentials")

        self.url = url

        layout = QFormLayout(self)

        self.url_label = QLabel(url or "(current site)")
        layout.addRow("URL:", self.url_label)

        self.username_edit = QLineEdit()
        self.username_edit.setText(username or "")
        layout.addRow("Username:", self.username_edit)

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setText(password or "")
        layout.addRow("Password:", self.password_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
                                   Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self):
        return self.username_edit.text(), self.password_edit.text()


# ===============================
# Settings window for sites/credentials
# ===============================

class SettingsWindow(QDialog):
    def __init__(self, parent, manager: WebsiteManager):
        super().__init__(parent)
        self.setWindowTitle("Settings – Sites & Credentials")
        self.manager = manager

        main_layout = QVBoxLayout(self)

        self.site_list = QListWidget()
        self.site_list.addItems(self.manager.all())
        main_layout.addWidget(QLabel("Sites:"))
        main_layout.addWidget(self.site_list)

        button_layout = QHBoxLayout()

        self.btn_edit_cred = QPushButton("Edit Credentials")
        self.btn_edit_cred.clicked.connect(self.edit_credentials)
        button_layout.addWidget(self.btn_edit_cred)

        self.btn_delete_cred = QPushButton("Delete Credentials")
        self.btn_delete_cred.clicked.connect(self.delete_credentials)
        button_layout.addWidget(self.btn_delete_cred)

        main_layout.addLayout(button_layout)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        main_layout.addWidget(close_btn)

    def _selected_url(self):
        item = self.site_list.currentItem()
        if not item:
            return None
        return item.text()

    def edit_credentials(self):
        url = self._selected_url()
        if not url:
            QMessageBox.warning(self, "No site selected", "Please select a site first.")
            return

        username, password = CredentialStore.get_credentials(url)
        dlg = CredentialDialog(self, url=url, username=username, password=password)
        if dlg.exec_() == QDialog.Accepted:
            new_user, new_pass = dlg.get_data()
            CredentialStore.save_credentials(url, new_user, new_pass)
            QMessageBox.information(self, "Saved", "Credentials saved.")

    def delete_credentials(self):
        url = self._selected_url()
        if not url:
            QMessageBox.warning(self, "No site selected", "Please select a site first.")
            return
        CredentialStore.delete_credentials(url)
        QMessageBox.information(self, "Deleted", "Credentials deleted for this site.")


# ===============================
# Main browser window
# ===============================

class BrowserWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Website Rotator")
        self.setGeometry(100, 100, 1200, 700)

        self.config = AppConfig()
        self.manager = WebsiteManager(config=self.config)

        self.main_browser = QWebEngineView()
        self.preview_browser = QWebEngineView()

        self.configure_browser(self.main_browser)
        self.configure_browser(self.preview_browser)

        self.build_ui()

        self.main_browser.loadFinished.connect(self.on_main_load_finished)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.load_next)
        self.timer.start(300 * 1000)

        self.load_next()

    def configure_browser(self, browser):
        settings = browser.settings()
        settings.setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        if browser is self.preview_browser:
            browser.setZoomFactor(0.3)  # thumbnail-style

    def build_ui(self):
        layout = QVBoxLayout()

        splitter = QSplitter()
        splitter.addWidget(self.main_browser)
        splitter.addWidget(self.preview_browser)
        layout.addWidget(splitter)

        nav_layout = QHBoxLayout()

        btn_prev = QPushButton("Previous")
        btn_prev.clicked.connect(self.load_previous)
        nav_layout.addWidget(btn_prev)

        btn_next = QPushButton("Next")
        btn_next.clicked.connect(self.load_next)
        nav_layout.addWidget(btn_next)

        btn_browse = QPushButton("Browse for Images")
        btn_browse.clicked.connect(self.browse_directory)
        nav_layout.addWidget(btn_browse)

        btn_credentials = QPushButton("Set Credentials for Current Site")
        btn_credentials.clicked.connect(self.set_credentials_for_current_site)
        nav_layout.addWidget(btn_credentials)

        btn_settings = QPushButton("Settings…")
        btn_settings.clicked.connect(self.open_settings)
        nav_layout.addWidget(btn_settings)

        layout.addLayout(nav_layout)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    # ------------- rotation -------------

    def load_next(self):
        url = self.manager.next()
        if not url:
            return
        self.main_browser.setUrl(QUrl(url))

        peek = self.manager.peek_next()
        if peek:
            self.preview_browser.setUrl(QUrl(peek))

    def load_previous(self):
        url = self.manager.previous()
        if not url:
            return
        self.main_browser.setUrl(QUrl(url))

        peek = self.manager.peek_next()
        if peek:
            self.preview_browser.setUrl(QUrl(peek))

    def browse_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        if directory:
            self.manager.add_images_from_directory(directory)
            self.refresh_preview_after_change()

    def refresh_preview_after_change(self):
        peek = self.manager.peek_next()
        if peek:
            self.preview_browser.setUrl(QUrl(peek))

    # ------------- credentials -------------

    def current_site_url(self):
        qurl = self.main_browser.url()
        if not qurl.isValid():
            return None
        return qurl.toString()

    def set_credentials_for_current_site(self):
        url = self.current_site_url()
        if not url:
            QMessageBox.warning(self, "No site loaded", "Load a site first.")
            return

        username, password = CredentialStore.get_credentials(url)
        dlg = CredentialDialog(self, url=url, username=username, password=password)
        if dlg.exec_() == QDialog.Accepted:
            new_user, new_pass = dlg.get_data()
            CredentialStore.save_credentials(url, new_user, new_pass)
            QMessageBox.information(self, "Saved", "Credentials saved for this site.")

    def open_settings(self):
        dlg = SettingsWindow(self, self.manager)
        dlg.exec_()

    # ------------- auto-login via JS -------------

    def on_main_load_finished(self, ok):
        if not ok:
            return

        url = self.current_site_url()
        if not url:
            return

        username, password = CredentialStore.get_credentials(url)
        if not username or not password:
            return

        js = self._build_auto_login_js(username, password)
        self.main_browser.page().runJavaScript(js)

    def _build_auto_login_js(self, username, password):
        username_js = json.dumps(username)
        password_js = json.dumps(password)

        js_code = f"""
            (function() {{
                var user = {username_js};
                var pass = {password_js};

                function findUsernameField() {{
                    var selectors = [
                        "input[name='username']",
                        "input[id='username']",
                        "input[name='email']",
                        "input[id='email']",
                        "input[type='email']",
                        "input[type='text']"
                    ];
                    for (var i = 0; i < selectors.length; i++) {{
                        var el = document.querySelector(selectors[i]);
                        if (el) return el;
                    }}
                    return null;
                }}

                function findPasswordField() {{
                    var el = document.querySelector("input[type='password']");
                    return el || null;
                }}

                function findSubmitButton() {{
                    var selectors = [
                        "button[type='submit']",
                        "input[type='submit']",
                        "button.login",
                        "button[id*='login']",
                        "button[name*='login']"
                    ];
                    for (var i = 0; i < selectors.length; i++) {{
                        var el = document.querySelector(selectors[i]);
                        if (el) return el;
                    }}
                    var buttons = document.querySelectorAll("button");
                    if (buttons.length === 1) return buttons[0];
                    return null;
                }}

                var u = findUsernameField();
                var p = findPasswordField();

                if (!u || !p) {{
                    console.log("Auto-login: Could not find username/password fields.");
                    return;
                }}

                u.focus();
                u.value = user;
                u.dispatchEvent(new Event('input', {{ bubbles: true }}));

                p.focus();
                p.value = pass;
                p.dispatchEvent(new Event('input', {{ bubbles: true }}));

                var btn = findSubmitButton();
                if (btn) {{
                    btn.click();
                }}
            }})();
        """
        return js_code


# ===============================
# Entry point
# ===============================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BrowserWindow()
    window.show()
    sys.exit(app.exec_())
