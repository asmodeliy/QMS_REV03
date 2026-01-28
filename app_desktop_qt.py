import warnings
warnings.filterwarnings('ignore', category=UserWarning)

import sys
from PySide6.QtSvgWidgets import QSvgWidget
import json
import time
import threading
import platform
import logging
from pathlib import Path
from urllib.request import urlopen, Request, build_opener, HTTPCookieProcessor
from urllib.error import URLError, HTTPError
from urllib.parse import urljoin
from http.cookiejar import LWPCookieJar

logger = logging.getLogger('app_desktop')

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTabWidget, QScrollArea,
    QFrame, QSystemTrayIcon, QMenu, QMessageBox, QGridLayout, QSpacerItem, QSizePolicy,
    QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject, QThread, QSize
from PySide6.QtGui import QIcon, QFont, QGuiApplication, QColor, QPalette, QAction, QPixmap
import os
import requests
import math
import hashlib


class ToastNotification(QWidget):
    def __init__(self, title, message, duration=3000):
        super().__init__()
        self.os_type = platform.system()
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border-left: 4px solid #3b82f6;
                border-radius: 8px;
            }
        """)
        try:
            effect = QGraphicsDropShadowEffect(self)
            effect.setBlurRadius(18)
            effect.setColor(QColor(0, 0, 0, 80))
            effect.setOffset(0, 4)
            self.setGraphicsEffect(effect)
        except Exception:
            logger.debug("Drop shadow not available for toast", exc_info=True)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)
        
        title_label = QLabel(title)
        title_font = QFont("Segoe UI" if self.os_type == "Windows" else "San Francisco" if self.os_type == "Darwin" else "Ubuntu", 12, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #1e293b;")
        layout.addWidget(title_label)
        
        message_label = QLabel(message)
        message_font = QFont("Segoe UI" if self.os_type == "Windows" else "San Francisco" if self.os_type == "Darwin" else "Ubuntu", 11)
        message_label.setFont(message_font)
        message_label.setStyleSheet("color: #64748b;")
        message_label.setWordWrap(True)
        message_label.setMaximumWidth(250)
        layout.addWidget(message_label)
        
        self.setFixedWidth(400)
        self.adjustSize()
        self.move_to_bottom_right()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.close)
        self.timer.start(duration)
    
    def move_to_bottom_right(self):
        screen = QGuiApplication.primaryScreen().geometry()
        if self.os_type == "Darwin":
            x = screen.right() - self.width() - 30
            y = screen.bottom() - self.height() - 80
        else:
            x = screen.right() - self.width() - 20
            y = screen.bottom() - self.height() - 20
        self.move(x, y)
    
    def closeEvent(self, event):
        self.timer.stop()


class NotificationSummaryWindow(QWidget):
    def __init__(self, notifications, duration=8000):
        super().__init__()
        self.os_type = platform.system()
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        container = QFrame(self)
        container.setObjectName("mainContainer")
        container.setStyleSheet("""
            QFrame#mainContainer {
                background-color: #ffffff;
                border-radius: 12px;
                border: 1px solid #e2e8f0;
            }
        """)
        
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #3b82f6, stop:1 #2563eb);
                border-radius: 10px 10px 0 0;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(6, 2, 6, 2)
        header_layout.setSpacing(2)
        
        icon_label = QLabel("🔔")
        icon_label.setStyleSheet("font-size: 16px; background: transparent;")
        header_layout.addWidget(icon_label)
        
        title = QLabel(f"New Issues · {len(notifications)}건")
        font_family = "Segoe UI" if self.os_type == "Windows" else "San Francisco" if self.os_type == "Darwin" else "Ubuntu"
        title.setFont(QFont(font_family, 11, QFont.Weight.DemiBold))
        title.setStyleSheet("color: white; background: transparent;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.15);
                color: white;
                border: none;
                font-size: 14px;
                font-weight: normal;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.22);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.32);
            }
        """)
        close_btn.clicked.connect(self.close)
        header_layout.addWidget(close_btn)
        header.setFixedHeight(46)
        header_layout.setContentsMargins(8, 4, 8, 4)
        
        container_layout.addWidget(header)
        
        from PySide6.QtSvgWidgets import QSvgWidget
        import os
        total_frame = QFrame()
        total_frame.setStyleSheet("background: transparent;")
        total_frame.setFixedHeight(72)
        total_layout = QHBoxLayout(total_frame)
        total_layout.setContentsMargins(14, 10, 14, 10)
        total_layout.setSpacing(8)
        total_label = QLabel(f"Total notifications: {len(notifications)}")
        total_label.setFont(QFont(font_family, 16, QFont.Weight.Bold))
        total_label.setStyleSheet("color: #111827;")
        total_layout.addWidget(total_label, alignment=Qt.AlignmentFlag.AlignLeft)
        badge = QLabel(str(len(notifications)))
        badge.setFont(QFont(font_family, 14, QFont.Weight.Bold))
        badge.setStyleSheet("background: #eef2ff; color: #3730a3; padding: 8px 12px; border-radius: 14px;")
        total_layout.addStretch()
        total_layout.addWidget(badge, alignment=Qt.AlignmentFlag.AlignRight)

        summary_widget = QWidget()
        summary_layout = QVBoxLayout(summary_widget)
        summary_layout.setContentsMargins(6, 2, 6, 2)
        summary_layout.setSpacing(2)
        summary_widget.setStyleSheet("background: transparent;")

        module_info = {
            'rpmt': {'color': '#3b82f6', 'name': 'RPMT', 'icon': 'rpmt.svg'},
            'svit': {'color': '#8b5cf6', 'name': 'SVIT', 'icon': 'svit.svg'},
            'cits': {'color': '#ec4899', 'name': 'CITS', 'icon': 'cits.svg'},
            'spec': {'color': '#10b981', 'name': 'SPEC', 'icon': 'spec.svg'}
        }
        module_counts = {}
        for notif in notifications:
            mod = notif.get('module', 'Other')
            module_counts[mod] = module_counts.get(mod, 0) + 1
        self.module_row_widgets = {}
        for mod, count in module_counts.items():
            info = module_info.get(mod, {'color': '#d1d5db', 'name': mod, 'icon': None})
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(6, 4, 6, 4)
            row_layout.setSpacing(8)

            svg_size = 18
            name_font_size = 11
            count_font_size = 11
            row_height = 36

            icon_path = None
            if info.get('icon'):
                icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static', 'img', 'modules', info['icon']))

            if icon_path and os.path.exists(icon_path):
                try:
                    svg = QSvgWidget(icon_path)
                    svg.setFixedSize(svg_size, svg_size)
                    row_layout.addWidget(svg, alignment=Qt.AlignmentFlag.AlignVCenter)
                except Exception:
                    logger.exception("Failed to render module SVG; falling back to avatar")
                    avatar = QLabel(info.get('name', '?')[0])
                    avatar.setFixedSize(svg_size, svg_size)
                    avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    avatar.setStyleSheet(f"background: {info.get('color', '#ececec')}; color: white; border-radius: {svg_size//2}px; font-weight: bold;")
                    row_layout.addWidget(avatar, alignment=Qt.AlignmentFlag.AlignVCenter)
            else:
                initial = (info.get('name', mod)[:2]).upper()
                avatar = QLabel(initial)
                avatar.setFixedSize(svg_size, svg_size)
                avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
                avatar.setStyleSheet(f"background: {info.get('color', '#d1d5db')}; color: white; border-radius: {svg_size//2}px; font-weight: bold; font-size: 10px;")
                row_layout.addWidget(avatar, alignment=Qt.AlignmentFlag.AlignVCenter)

            name_label = QLabel(f"{info.get('name', mod)}")
            name_label.setFont(QFont(font_family, name_font_size, QFont.Weight.Medium))
            name_label.setStyleSheet("color: #22223b; padding-left: 8px;")
            row_layout.addWidget(name_label)

            count_label = QLabel(f"{count}")
            count_label.setFont(QFont(font_family, count_font_size, QFont.Weight.Bold))
            count_label.setStyleSheet(f"color: {info.get('color', '#6b7280')}; margin-left: 10px;")
            row_layout.addWidget(count_label)

            row_layout.addStretch()
            row_widget.setFixedHeight(row_height)
            row_widget.setCursor(Qt.CursorShape.PointingHandCursor)

            def make_click_handler(module_key, module_name, cnt):
                def handler(event):
                    try:
                        if event.button() == Qt.MouseButton.LeftButton:
                            self.filter_tasks_by_module(module_key)
                        elif event.button() == Qt.MouseButton.RightButton:
                            from PySide6.QtWidgets import QApplication
                            for w in QApplication.topLevelWidgets():
                                if w is self:
                                    continue
                                if getattr(w, '__class__', None) and getattr(w, '__class__').__name__ == 'QMSDesktopClient':
                                    w.show_notification(f"{module_name}", f"{cnt} new notification(s)")
                                    break
                    except Exception:
                        logger.exception("Error in module row click handler")
                return handler

            row_widget.mousePressEvent = make_click_handler(mod, info.get('name', mod), count)
            self.module_row_widgets[mod] = row_widget
            summary_layout.addWidget(row_widget)

        container_layout.addWidget(total_frame)
        container_layout.addWidget(summary_widget)
        
        footer = QFrame()
        footer.setStyleSheet("""
            QFrame {
                background-color: #f1f5f9;
                border-radius: 0 0 10px 10px;
            }
        """)
        footer.setFixedHeight(28)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(10, 4, 10, 4)
        
        footer_text = QLabel("QMS Desktop • Real-time updates")
        footer_text.setFont(QFont(font_family, 8))
        footer_text.setStyleSheet("color: #64748b; background: transparent; padding-left: 4px;")
        footer_layout.addWidget(footer_text)
        footer_layout.addStretch()
        
        container_layout.addWidget(footer)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 8, 10, 8)
        main_layout.addWidget(container)
        self.setFixedSize(560, min(300, 110 + len(notifications[:10]) * 34))
        self.move_to_bottom_right()

    def filter_tasks_by_module(self, module_key):
        parent = self.parent()
        while parent is not None:
            if getattr(parent, '__class__', None) and getattr(parent, '__class__').__name__ == 'QMSDesktopClient' and hasattr(parent, 'filter_tasks_by_module'):
                parent.filter_tasks_by_module(module_key)
                self.close()
                return
            parent = parent.parent() if hasattr(parent, 'parent') else None

        from PySide6.QtWidgets import QApplication
        for widget in QApplication.topLevelWidgets():
            if widget is self:
                continue
            if getattr(widget, '__class__', None) and getattr(widget, '__class__').__name__ == 'QMSDesktopClient' and hasattr(widget, 'filter_tasks_by_module'):
                widget.filter_tasks_by_module(module_key)
                break
        self.close()

    def create_notification_item(self, notif):
        item = QFrame()
        item.setObjectName("notifCard")
        item.setStyleSheet("""
            QFrame#notifCard {
                background-color: #ffffff;
                border-radius: 10px;
                border: 1px solid #e2e8f0;
                margin: 6px 8px;
            }
            QFrame#notifCard:hover {
                background-color: #f8fafc;
                border: 1px solid #cbd5e1;
            }
        """)
        
        layout = QVBoxLayout(item)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        module = notif.get('module', '')
        module_info = {
            'rpmt': {'color': '#3b82f6', 'name': 'RPMT', 'icon': '📊'},
            'svit': {'color': '#8b5cf6', 'name': 'SVIT', 'icon': '🔬'},
            'cits': {'color': '#ec4899', 'name': 'CITS', 'icon': '🎫'},
            'spec': {'color': '#10b981', 'name': 'SPEC', 'icon': '📝'}
        }
        info = module_info.get(module, {'color': '#64748b', 'name': 'QMS', 'icon': '📌'})
        
        badge = QLabel(f"{info['icon']} {info['name']}")
        font_family = "Segoe UI" if self.os_type == "Windows" else "San Francisco" if self.os_type == "Darwin" else "Ubuntu"
        badge.setFont(QFont(font_family, 9, QFont.Weight.Bold))
        badge.setStyleSheet(f"""
            background-color: {info['color']};
            color: white;
            padding: 4px 10px;
            border-radius: 6px;
        """)
        badge.setFixedHeight(24)
        header_layout.addWidget(badge)
        
        if notif.get('time'):
            time_badge = QLabel(notif.get('time', ''))
            time_badge.setFont(QFont(font_family, 9))
            time_badge.setStyleSheet("""
                background-color: #f1f5f9;
                color: #64748b;
                padding: 4px 10px;
                border-radius: 6px;
            """)
            time_badge.setFixedHeight(24)
            header_layout.addWidget(time_badge)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        title = QLabel(notif.get('title', 'Notification'))
        title.setFont(QFont(font_family, 12, QFont.Weight.DemiBold))
        title.setStyleSheet("color: #0f172a; background: transparent;")
        title.setWordWrap(True)
        layout.addWidget(title)
        
        if notif.get('description'):
            desc = QLabel(notif.get('description', ''))
            desc.setFont(QFont(font_family, 10))
            desc.setStyleSheet("color: #64748b; background: transparent;")
            desc.setWordWrap(True)
            layout.addWidget(desc)
        
        return item
    
    def move_to_bottom_right(self):
        screen = QGuiApplication.primaryScreen().geometry()
        if self.os_type == "Darwin":
            x = screen.right() - self.width() - 30
            y = screen.bottom() - self.height() - 80
        else:
            x = screen.right() - self.width() - 20
            y = screen.bottom() - self.height() - 20
        self.move(x, y)
    
    def closeEvent(self, event):
        super().closeEvent(event)
        event.accept()


class NotificationWorker(QObject):
    notification = Signal(str, str)
    
    def __init__(self, server_url, interval=30, cookie_jar=None):
        super().__init__()
        self.server_url = server_url
        self.interval = interval
        self.notification_count = 0
        self.running = True
        self.last_popup_time = None
        self.popup_interval = 4 * 3600
        self.cookie_jar = cookie_jar
    
    def run(self):
        login_time = time.time()
        first_run = True
        
        while self.running:
            try:
                url = f"{self.server_url}/api/notifications/count"
                req = Request(url)
                self.cookie_jar.add_cookie_header(req)
                response = urlopen(req, timeout=2)
                self.cookie_jar.extract_cookies(response, req)
                
                data = json.loads(response.read().decode())
                count = data.get('count', 0)
                
                if count > self.notification_count:
                    new_count = count - self.notification_count
                    self.notification.emit("[MSG] New Tasks", f"{new_count} new notification(s)")
                    self.notification_count = count
                
                current_time = time.time()
                
                if first_run:
                    first_run = False
                    self.last_popup_time = current_time
                    time.sleep(0.5)
                    self.notification.emit("[OK] App Started", "QMS is running in background")
                    
                elif current_time - self.last_popup_time >= self.popup_interval:
                    self.notification.emit("[TASK] Reminder", "Check your QMS tasks")
                    self.last_popup_time = current_time
                    
            except Exception as e:
                if self.running:
                    logger.debug("NotificationWorker run loop exception", exc_info=True)
            
            for _ in range(self.interval * 10):
                if not self.running:
                    break
                time.sleep(0.1)
    
    def stop(self):
        self.running = False


class QMSDesktopClient(QMainWindow):
    def filter_tasks_by_module(self, module_key):
        self.selected_module_filter = module_key
        self.show_main_ui()

    def __init__(self):
        super().__init__()
        
        self.root_dir = Path(__file__).parent
        self.server_url = "http://210.117.32.72:58080"
        self.current_user = None
        self.tray = None
        self.os_type = platform.system()
        self.active_toasts = [] 
        
        self.cookie_file = self.root_dir / ".qms_cookies"
        self.cookie_jar = LWPCookieJar(str(self.cookie_file))
        self.load_cookies()
        self.restore_session()
        
        self.setWindowTitle("RAMSCHIP QMS")
                                
        self.setMinimumSize(920, 680)
        self.resize(1000, 750)
        self.set_icon()

                                                  
        try:
            app_font = QFont(self.get_font_family(), 11)
            QApplication.setFont(app_font)
        except Exception:
            pass

        self.setStyleSheet("""
            QMainWindow, QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f6f7fb,
                    stop:0.5 #ffffff,
                    stop:1 #f8fafc);
                font-family: 'Segoe UI', 'DejaVu Sans', sans-serif;
            }
        """)

                                  
        try:
            menu_bar = self.menuBar()

                                                                               
            file_menu = menu_bar.addMenu('File')
            try:
                user_email = self.current_user.get('email') if self.current_user else None
                try:
                    from core.config import GARAGE_ADMIN_EMAILS
                    if user_email and user_email.lower() in GARAGE_ADMIN_EMAILS:
                        upload_action = QAction('Upload to Garage', self)
                        upload_action.triggered.connect(self.upload_to_garage)
                        file_menu.addAction(upload_action)
                except Exception:
                    logger.debug('Failed to check GARAGE_ADMIN_EMAILS', exc_info=True)
            except Exception:
                logger.debug('Failed to determine current user for menu', exc_info=True)

            help_menu = menu_bar.addMenu('Help')
            about_action = QAction('About QMS', self)
            about_action.triggered.connect(self.show_about)
            help_menu.addAction(about_action)
        except Exception:
            logger.debug('Menu bar not available', exc_info=True)
        
        if self.current_user:
            self.show_main_ui()
            QTimer.singleShot(1000, self.show_notification_popups)
        else:
            self.show_login_ui()
        
        self.start_notification_worker()
        self.setup_tray()

    def show_about(self):
        try:
            QMessageBox.about(self, "About RAMSCHIP QMS", "RAMSCHIP QMS Desktop\nVersion 1.0.0\n\nA lightweight desktop client for QMS.")
        except Exception:
            logger.exception('Failed to show About dialog')

    def upload_to_garage(self):
        try:
            from PySide6.QtWidgets import QFileDialog, QMessageBox
                                                                           
            user_email = self.current_user.get('email') if self.current_user else None
            try:
                from core.config import GARAGE_ADMIN_EMAILS
                if not (user_email and user_email.lower() in GARAGE_ADMIN_EMAILS):
                    QMessageBox.warning(self, 'Not allowed', 'Desktop upload is restricted to administrator accounts.')
                    logger.warning('Unauthorized upload attempt by %s', user_email)
                    return
            except Exception:
                QMessageBox.warning(self, 'Not allowed', 'Desktop upload is restricted to administrator accounts.')
                logger.warning('Unauthorized upload attempt by %s', user_email)
                return

            path, _ = QFileDialog.getOpenFileName(self, "Upload to Garage")
            if not path:
                return

                                         
            filename = os.path.basename(path)
            total_size = os.path.getsize(path)
                                         
            desired_chunk = 10 * 1024 * 1024

                                                              
            records_path = self.root_dir / '.garage_uploads.json'
            existing_records = {}
            try:
                if records_path.exists():
                    existing_records = json.loads(records_path.read_text())
            except Exception:
                existing_records = {}

                                                                  
            file_key = f"{os.path.abspath(path)}:{total_size}:{int(os.path.getmtime(path))}"
            resume = False
            resume_upload_id = None
            if file_key in existing_records:
                resume_upload_id = existing_records[file_key].get('upload_id')
                                            
                choice = QMessageBox.question(self, 'Resume upload', 'A previous upload for this file was detected. Resume?')
                if choice == QMessageBox.StandardButton.Yes:
                    resume = True

            if resume and resume_upload_id:
                upload_id = resume_upload_id
                                                                                                   
                chunk_size = desired_chunk
            else:
                                       
                init_resp = self.api_request('/api/garage/init', method='POST', data={
                    'filename': filename,
                    'chunk_size': desired_chunk,
                    'total_size': total_size
                }, silent=True)

                if not init_resp or 'upload_id' not in init_resp:
                    QMessageBox.critical(self, 'Upload Failed', 'Failed to start upload session')
                    return

                upload_id = init_resp['upload_id']
                chunk_size = init_resp.get('chunk_size', desired_chunk)
                                                                               
                try:
                    existing_records[file_key] = {'upload_id': upload_id, 'filename': filename, 'size': total_size}
                    records_path.write_text(json.dumps(existing_records))
                except Exception:
                    logger.debug('Failed to persist upload record', exc_info=True)

                                                                                    
            threading.Thread(target=self._perform_chunked_upload, args=(path, upload_id, chunk_size), daemon=True).start()
            QMessageBox.information(self, 'Upload Started', 'Upload started in background. You will be notified when it completes.')
        except Exception:
            logger.exception('Failed to start upload')

    def _perform_chunked_upload(self, path, upload_id, chunk_size):
                                                                                       
        try:
            s = requests.Session()
                                                
            cookies = {c.name: c.value for c in self.cookie_jar}
            s.cookies.update(cookies)

            total_size = os.path.getsize(path)
            total_chunks = math.ceil(total_size / chunk_size)

                                                      
            try:
                status = s.get(f"{self.server_url.rstrip('/')}/api/garage/status/{upload_id}", timeout=10)
                uploaded = status.json().get('uploaded_chunks', []) if status.status_code == 200 else []
            except Exception:
                uploaded = []

            with open(path, 'rb') as f:
                for idx in range(total_chunks):
                    if idx in uploaded:
                        continue
                    f.seek(idx * chunk_size)
                    to_send = f.read(chunk_size)
                    for attempt in range(4):
                        try:
                            files = {'file': ('chunk', to_send, 'application/octet-stream')}
                            put_url = f"{self.server_url.rstrip('/')}/api/garage/upload/{upload_id}/{idx}"
                            r = s.put(put_url, files=files, timeout=60)
                            if r.status_code == 200:
                                break
                            else:
                                logger.warning('Chunk upload failed %s %s', r.status_code, r.text)
                        except Exception as e:
                            logger.exception('Chunk upload exception')
                        time.sleep(2 ** attempt)
                    else:
                                            
                        self.show_notification('Upload failed', f'Chunk {idx} failed')
                        return

                      
            try:
                r = s.post(f"{self.server_url.rstrip('/')}/api/garage/complete/{upload_id}", timeout=30)
                records_path = self.root_dir / '.garage_uploads.json'
                file_key = f"{os.path.abspath(path)}:{total_size}:{int(os.path.getmtime(path))}"
                if r.status_code == 200:
                    data = r.json()
                                                        
                    try:
                        if records_path.exists():
                            recs = json.loads(records_path.read_text())
                            if file_key in recs:
                                del recs[file_key]
                                records_path.write_text(json.dumps(recs))
                    except Exception:
                        logger.debug('Failed to clean upload record', exc_info=True)
                    self.show_notification('Upload complete', f"Uploaded to {data.get('path')}")
                else:
                    logger.warning('Complete failed: %s %s', r.status_code, r.text)
                    self.show_notification('Upload incomplete', 'Server failed to assemble file')
            except Exception:
                logger.exception('Failed to complete upload')
                self.show_notification('Upload incomplete', 'Failed to complete upload')
        except Exception:
            logger.exception('Upload thread failed')
            self.show_notification('Upload failed', 'An error occurred during upload')
    
    def load_cookies(self):
        try:
            if self.cookie_file.exists():
                self.cookie_jar.load(ignore_discard=True, ignore_expires=True)
        except Exception:
            logger.debug("Failed to load cookies", exc_info=True)
    
    def save_cookies(self):
        try:
            self.cookie_jar.save(ignore_discard=True, ignore_expires=True)
        except Exception:
            logger.debug("Failed to save cookies", exc_info=True)
    
    def restore_session(self):
        try:
            has_session = any(c.name == 'session' for c in self.cookie_jar)
            if not has_session:
                return False
            
            result = self.api_request("/auth/api/me", silent=True)
            if result and result.get("authenticated"):
                self.current_user = result.get("user", {})
                return True
            return False
        except Exception as e:
            logger.debug("Failed to restore session", exc_info=True)
            return False
    
    def get_font_family(self):
        if self.os_type == "Windows":
            return "Segoe UI"
        elif self.os_type == "Darwin":
            return "San Francisco"
        else:
            return "Ubuntu"
    
    def api_request(self, endpoint, method="GET", data=None, silent=False):
        try:
                                                        
            if not endpoint.startswith('/'):
                endpoint = '/' + endpoint

                                                                                          
            if endpoint.startswith('/main/'):
                endpoint = endpoint[len('/main'):]

            opener = build_opener(HTTPCookieProcessor(self.cookie_jar))
                                                     
            base = self.server_url.rstrip('/')
            url = f"{base}{endpoint}"

            if method == "POST" and data:
                data = json.dumps(data).encode()
                req = Request(url, data=data, method="POST")
                req.add_header('Content-Type', 'application/json')
            else:
                req = Request(url, method=method)

                                                                                
            max_redirects = 3
            attempt = 0
            while True:
                try:
                    response = opener.open(req, timeout=3)
                    break
                except HTTPError as he:
                                                                          
                    if he.code in (301, 302, 307, 308) and attempt < max_redirects:
                        loc = he.headers.get('Location')
                        if not loc:
                            if not silent:
                                logger.error("Redirect response missing Location header for %s", url)
                            return None
                        new_url = urljoin(base + '/', loc)
                        logger.debug("Following redirect %s -> %s", url, new_url)
                                                                        
                        if method == "POST" and data:
                            req = Request(new_url, data=data, method="POST")
                            req.add_header('Content-Type', 'application/json')
                        else:
                            req = Request(new_url, method=method)
                        url = new_url
                        attempt += 1
                        continue
                    else:
                        if not silent:
                            logger.exception("API request HTTP error %s", he)
                        return None
                except URLError as ue:
                    if not silent:
                        logger.exception("API request URL error")
                    return None

            result = json.loads(response.read().decode())
            return result
        except Exception as e:
            if not silent:
                logger.exception("API request error")
            return None
    
    def set_icon(self):
        icon_paths = [
            self.root_dir / "static" / "favicon.ico",
            self.root_dir / "favicon.ico",
        ]
        for icon_path in icon_paths:
            if icon_path.exists():
                self.setWindowIcon(QIcon(str(icon_path)))
                return
    
    def setup_tray(self):
        icon_paths = [
            self.root_dir / "static" / "favicon.ico",
            self.root_dir / "favicon.ico",
        ]
        icon = None
        for icon_path in icon_paths:
            if icon_path.exists():
                icon = QIcon(str(icon_path))
                break
        
        if icon:
            self.tray = QSystemTrayIcon(self)
            self.tray.setIcon(icon)
            self.tray.setToolTip('RAMSCHIP QMS Desktop')
            tray_menu = QMenu()
            tray_menu.addAction("Open", self.show_window)
            tray_menu.addAction("Show Notifications", self.show_notification_popups)
            tray_menu.addSeparator()
            try:
                user_email = self.current_user.get('email') if self.current_user else None
                from core.config import GARAGE_ADMIN_EMAILS
                if user_email and user_email.lower() in GARAGE_ADMIN_EMAILS:
                    upload_action = QAction('Upload to Garage', self)
                    upload_action.triggered.connect(self.upload_to_garage)
                    tray_menu.addAction(upload_action)
                    tray_menu.addSeparator()
            except Exception:
                logger.debug('Failed to determine current user for tray menu', exc_info=True)
            about_action = QAction('About', self)
            about_action.triggered.connect(self.show_about)
            tray_menu.addAction(about_action)
            tray_menu.addSeparator()
            tray_menu.addAction("Exit", self.exit_app)
            self.tray.setContextMenu(tray_menu)
            self.tray.show()
                                          
            QTimer.singleShot(1500, lambda: self.show_notification('QMS', 'Desktop client running'))
    
    def show_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()
    
    def show_login_ui(self):
        central_widget = QWidget()
        central_widget.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fbf8ff, stop:1 #f6f4fb);")
        self.setCentralWidget(central_widget)
                                                                 
        self.setMinimumSize(1000, 760)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(0)
                                                                                 
        layout.setContentsMargins(120, 0, 120, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        header = QFrame()
        header.setStyleSheet("background: transparent;")
        header.setFixedHeight(140)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)
                                                                                                  
        header_layout.addStretch()
        group = QWidget()
        group_layout = QHBoxLayout(group)
        group_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.setSpacing(12)

        title = QLabel("RAMSCHIP QMS")
        font_family = "Segoe UI" if self.os_type == "Windows" else "San Francisco" if self.os_type == "Darwin" else "Ubuntu"
        title.setFont(QFont(font_family, 46, QFont.Weight.Bold))
        title.setStyleSheet("color: #6d28d9; background: transparent; letter-spacing: 1.5px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle = QLabel("Quality Management System")
        subtitle.setFont(QFont(font_family, 14))
        subtitle.setStyleSheet("color: #6b7280; background: transparent;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
                                                                          
        title_frame = QWidget()
        tf_layout = QVBoxLayout(title_frame)
        tf_layout.setContentsMargins(0, 0, 0, 0)
        tf_layout.setSpacing(6)
        tf_layout.addWidget(title)
        tf_layout.addWidget(subtitle)
        group_layout.addWidget(title_frame)
        header_layout.addWidget(group)
        header_layout.addStretch()
        layout.addWidget(header) 
        
        form_frame = QFrame()
        form_frame.setStyleSheet("background-color: #ffffff; border-radius: 12px; border: 1px solid #e6e9ef;")
                                                                                    
        form_frame.setMaximumWidth(820)
        try:
            shadow = QGraphicsDropShadowEffect(form_frame)
            shadow.setBlurRadius(32)
            shadow.setColor(QColor(0,0,0,45))
            shadow.setOffset(0,10)
            form_frame.setGraphicsEffect(shadow)
        except Exception:
            logger.debug('Shadow not available for login frame', exc_info=True)

        form_layout = QVBoxLayout(form_frame)
        form_layout.setSpacing(22)
                                                            
        form_layout.setContentsMargins(72, 56, 72, 56)
        
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #ef4444; font-size: 13px;")
        self.error_label.setVisible(False)
        form_layout.addWidget(self.error_label)
        
        email_label = QLabel("Email")
        email_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #1e293b;")
        form_layout.addWidget(email_label)
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter your email")
        self.email_input.setFixedHeight(64)
        self.email_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.email_input.setMinimumWidth(520)
        self.email_input.setStyleSheet("""
            QLineEdit {
                padding: 12px 14px;
                border: 2px solid #e6eef8;
                border-radius: 8px;
                font-size: 16px;
                font-family: Segoe UI;
                background-color: #f8fafc;
                color: #0f172a;
            }
            QLineEdit::placeholder {
                color: #94a3b8;
            }
            QLineEdit:focus {
                border: 2px solid #4f46e5;
                background-color: #ffffff;
            }
        """)
        form_layout.addWidget(self.email_input)
        
        pwd_label = QLabel("Password")
        pwd_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #1e293b;")
        form_layout.addWidget(pwd_label)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setFixedHeight(64)
        self.password_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.password_input.setMinimumWidth(520)
        self.password_input.setStyleSheet("""
            QLineEdit {
                padding: 12px 14px;
                border: 2px solid #e6eef8;
                border-radius: 8px;
                font-size: 16px;
                font-family: Segoe UI;
                background-color: #f8fafc;
                color: #0f172a;
            }
            QLineEdit::placeholder {
                color: #94a3b8;
            }
            QLineEdit:focus {
                border: 2px solid #4f46e5;
                background-color: #ffffff;
            }
        """)
        form_layout.addWidget(self.password_input)
        
        login_btn = QPushButton("Login")
        login_btn.setFixedHeight(64)
        login_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #6d28d9, stop:1 #4f46e5);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 17px;
                font-weight: 800;
                padding: 12px 18px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #7d3be0, stop:1 #3b6cf0);
            }
        """)
        login_btn.clicked.connect(self.handle_login)
        form_layout.addWidget(login_btn)
        
        form_layout.addStretch()
        
        footer = QLabel("Secure connection • Notifications enabled  • www.ramschip.com")
        footer.setStyleSheet("color: #6b7280; font-size: 12px;")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        form_layout.addWidget(footer)
        
        layout.addWidget(form_frame, alignment=Qt.AlignmentFlag.AlignCenter)
    
    def handle_login(self):
        email = self.email_input.text().strip()
        password = self.password_input.text().strip()
        
        if not email or not password:
            self.show_error("Please enter email and password")
            return
        
        try:
            result = self.api_request("/auth/api/login", method="POST", data={
                "email": email,
                "password": password
            })
            
            if result and result.get("success"):
                self.current_user = result.get("user", {})
                self.save_cookies()
                self.show_main_ui()
                self.show_notification_popups()
            else:
                message = result.get("message", "Login failed") if result else "Connection failed"
                self.show_error(message)
        except Exception as e:
            self.show_error(f"Login error: {str(e)}")
    
    def show_error(self, message):
        self.error_label.setText(message)
        self.error_label.setVisible(True)
    
    def show_main_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
                                            
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        navbar = self.create_navbar()
        layout.addWidget(navbar)
        
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabBar {
                background-color: transparent;
            }
            QTabBar::tab {
                background-color: transparent;
                padding: 12px 28px;
                border-bottom: 3px solid transparent;
                font-family: Segoe UI;
                font-size: 13px;
                font-weight: 500;
                color: #94a3b8;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                border-bottom: 3px solid #3b82f6;
                color: #1e293b;
                background-color: rgba(59, 130, 246, 0.08);
            }
            QTabBar::tab:hover {
                background-color: rgba(59, 130, 246, 0.08);
            }
            QTabWidget::pane {
                border: none;
                background-color: #f8fafc;
            }
        """)
        
        tabs.addTab(self.create_tasks_tab(), "My Tasks")
        tabs.addTab(self.create_notifications_tab(), "Notifications")
        tabs.addTab(self.create_modules_tab(), "Quick Access")
        
        layout.addWidget(tabs)
    
    def create_navbar(self):
        navbar = QFrame()
        navbar.setStyleSheet("background-color: #ffffff; border-bottom: 2px solid #e5e7eb;")
        navbar.setFixedHeight(64)
        layout = QHBoxLayout(navbar)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(16)
        
        title = QLabel("RAMSCHIP QMS")
        title_font = QFont("Segoe UI", 18, QFont.Weight.Bold)
        title_font.setLetterSpacing(QFont.AbsoluteSpacing, 0.3)
        title.setFont(title_font)
        title.setStyleSheet("color: #3b82f6;")
        layout.addWidget(title)
        layout.addStretch()
        
        if self.current_user:
            user_name = self.current_user.get('english_name', 'User')
            user_label = QLabel(user_name)
            user_font = QFont("Segoe UI", 11, QFont.Weight.Normal)
            user_label.setFont(user_font)
            user_label.setStyleSheet("font-size: 12px; color: #64748b; padding: 0px 8px;")
            layout.addWidget(user_label)
        
        browser_btn = QPushButton("Open in Browser")
        browser_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: 1px solid #1f3a8a;
                padding: 8px 20px;
                border-radius: 8px;
                font-size: 12px;
                font-weight: 600;
                letter-spacing: 0.3px;
            }
            QPushButton:hover {
                background-color: #2563eb;
                border: 1px solid #1e40af;
            }
            QPushButton:pressed {
                background-color: #1d4ed8;
            }
        """)
        browser_btn.clicked.connect(self.open_browser)
        layout.addWidget(browser_btn)
        
        logout_btn = QPushButton("Logout")
        logout_btn.setStyleSheet("""
            QPushButton {
                background-color: #64748b;
                color: white;
                border: 1px solid #334155;
                padding: 8px 20px;
                border-radius: 8px;
                font-size: 12px;
                font-weight: 600;
                letter-spacing: 0.3px;
            }
            QPushButton:hover {
                background-color: #475569;
                border: 1px solid #1e293b;
            }
            QPushButton:pressed {
                background-color: #334155;
            }
        """)
        logout_btn.clicked.connect(self.handle_logout)
        layout.addWidget(logout_btn)
        
        return navbar
    
    def create_tasks_tab(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

                                                      
        if hasattr(self, 'selected_module_filter') and self.selected_module_filter:
            filter_banner = QLabel(f"Filtering tasks by module: {self.selected_module_filter.upper()}")
            filter_banner.setStyleSheet("background: #e0e7ff; color: #3730a3; padding: 6px 12px; border-radius: 8px; font-weight: bold;")
            layout.addWidget(filter_banner)
        container.setStyleSheet("background-color: #f8fafc;")
        
        try:
            result = self.api_request("/rpmt/api/my-tasks")
            if result and result.get("tasks"):
                tasks = result.get("tasks", [])
                
                if tasks:
                    scroll = QScrollArea()
                    scroll.setWidgetResizable(True)
                    scroll.setStyleSheet("""
                        QScrollArea {
                            border: none;
                            background-color: transparent;
                        }
                        QScrollBar:vertical {
                            width: 8px;
                            background: transparent;
                            margin: 0px 0px 0px 0px;
                        }
                        QScrollBar::handle:vertical {
                            background: #3b82f6;
                            border-radius: 4px;
                            min-height: 40px;
                        }
                        QScrollBar::handle:vertical:hover {
                            background: #60a5fa;
                        }
                        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                            height: 0px;
                        }
                    """)
                    scroll_widget = QWidget()
                    scroll_widget.setStyleSheet("background-color: transparent;")
                    scroll_layout = QVBoxLayout(scroll_widget)
                    scroll_layout.setContentsMargins(0, 0, 0, 0)
                    
                    for task in tasks[:30]:
                        card = self.create_task_card(task)
                        scroll_layout.addWidget(card)
                    
                    scroll_layout.addStretch()
                    scroll.setWidget(scroll_widget)
                    layout.addWidget(scroll)
                else:
                    empty_label = QLabel("No tasks assigned")
                    empty_label.setStyleSheet("color: #94a3b8;")
                    layout.addWidget(empty_label)
                    layout.addStretch()
            else:
                fail_label = QLabel("Failed to load tasks")
                fail_label.setStyleSheet("color: #94a3b8;")
                layout.addWidget(fail_label)
                layout.addStretch()
        except Exception as e:
            layout.addWidget(QLabel(f"Error: {str(e)}"))
            layout.addStretch()
        
        return container
    
    def create_task_card(self, task):
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f9fafb);
                border: 1px solid #e5e7eb;
                border-radius: 14px;
                margin: 4px 16px;
                padding: 8px;
            }
            QFrame:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f9fafb, stop:1 #f3f4f6);
                border: 1px solid #3b82f6;
            }
        """)
        
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 40))
        card.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        title = QLabel(task.get('title', 'Unknown'))
        title_font = QFont("Segoe UI", 13, QFont.Weight.DemiBold)
        title_font.setLetterSpacing(QFont.AbsoluteSpacing, 0.2)
        title.setFont(title_font)
        title.setStyleSheet("color: #1e293b; line-height: 1.4;")
        title.setWordWrap(True)
        layout.addWidget(title)
        
        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(12)
        
        status = task.get('status', 'N/A')
        status_label = QLabel(f"● {status}")
        status_color = "#10b981" if status == "Completed" else "#f59e0b" if status == "In Progress" else "#6b7280"
        status_label.setStyleSheet(f"color: {status_color}; font-size: 12px; font-weight: 600;")
        meta_layout.addWidget(status_label)
        
        if task.get('due_date'):
            due_label = QLabel(f"📅 {task.get('due_date')}")
            due_label.setStyleSheet("color: #64748b; font-size: 11px;")
            meta_layout.addWidget(due_label)
        
        meta_layout.addStretch()
        layout.addLayout(meta_layout)
        
        return card
    
    def create_notifications_tab(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        container.setStyleSheet("background-color: #f8fafc;")
        
        try:
            result = self.api_request("/api/notifications")
            if result and result.get("notifications"):
                notifications = result.get("notifications", [])
                
                if notifications:
                    scroll = QScrollArea()
                    scroll.setWidgetResizable(True)
                    scroll.setStyleSheet("""
                        QScrollArea {
                            border: none;
                            background-color: transparent;
                        }
                        QScrollBar:vertical {
                            width: 8px;
                            background: transparent;
                            margin: 0px 0px 0px 0px;
                        }
                        QScrollBar::handle:vertical {
                            background: #3b82f6;
                            border-radius: 4px;
                            min-height: 40px;
                        }
                        QScrollBar::handle:vertical:hover {
                            background: #60a5fa;
                        }
                        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                            height: 0px;
                        }
                    """)
                    scroll_widget = QWidget()
                    scroll_widget.setStyleSheet("background-color: transparent;")
                    scroll_layout = QVBoxLayout(scroll_widget)
                    scroll_layout.setContentsMargins(0, 0, 0, 0)
                    
                    for notif in notifications[:30]:
                        card = self.create_notification_card(notif)
                        scroll_layout.addWidget(card)
                    
                    scroll_layout.addStretch()
                    scroll.setWidget(scroll_widget)
                    layout.addWidget(scroll)
                else:
                    layout.addWidget(QLabel("No notifications"))
                    layout.addStretch()
            else:
                layout.addWidget(QLabel("Failed to load notifications"))
                layout.addStretch()
        except Exception as e:
            layout.addWidget(QLabel(f"Error: {str(e)}"))
            layout.addStretch()
        
        return container
    
    def create_notification_card(self, notif):
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f9fafb);
                border-left: 4px solid #3b82f6;
                border: 1px solid #e5e7eb;
                margin: 4px 16px;
                padding: 8px 16px;
                border-radius: 12px;
            }
            QFrame:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f9fafb, stop:1 #f3f4f6);
                border: 1px solid #3b82f6;
            }
        """)
        
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 3)
        shadow.setColor(QColor(0, 0, 0, 30))
        card.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        title = QLabel(notif.get('title', 'Unknown'))
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: #1e293b;")
        layout.addWidget(title)
        
        if notif.get('description'):
            desc = QLabel(notif.get('description', ''))
            desc.setStyleSheet("color: #64748b; font-size: 11px;")
            desc.setWordWrap(True)
            layout.addWidget(desc)
        
        time_label = QLabel(notif.get('time', ''))
        time_label.setStyleSheet("color: #94a3b8; font-size: 10px;")
        layout.addWidget(time_label)
        
        return card
    
    def create_modules_tab(self):
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

                                                                 
        gradient_bg = QFrame(container)
        gradient_bg.setObjectName("gradientBg")
        gradient_bg.setStyleSheet("""
            QFrame#gradientBg {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(102,126,234,25),
                    stop:0.25 rgba(118,75,162,25),
                    stop:0.4 rgba(240,147,251,25),
                    stop:0.5 #f8f9fc,
                    stop:1 #f8f9fc);
            }
        """)
        gradient_bg.setGeometry(0, 0, 1, 1)                             
        main_layout.addWidget(gradient_bg)

                                           
        fg_widget = QWidget(container)
        fg_layout = QVBoxLayout(fg_widget)
        fg_layout.setContentsMargins(0, 0, 0, 0)
        fg_layout.setSpacing(0)

        title = QLabel("Quick Access to Modules")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #1e293b; margin: 20px 20px 20px 20px;")
        fg_layout.addWidget(title)

        modules = [
            {"name": "RPMT", "url": "/rpmt", "color": "#667eea", "svg": '''<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\"><path d=\"M12 2L2 7v10c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-10-5z\"/><path d=\"M10 17l-3-3 1.41-1.41L10 14.17l4.59-4.58L16 11l-6 6z\"/></svg>'''},
            {"name": "SVIT", "url": "/svit", "color": "#00d4ff", "svg": '''<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\"><path d=\"M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2\"/><line x1=\"16\" y1=\"13\" x2=\"8\" y2=\"13\"/></svg>'''},
            {"name": "CITS", "url": "/cits", "color": "#e63946", "svg": '''<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\"><path d=\"M12 2a7 7 0 100 14 7 7 0 000-14z\"/><path d=\"M4 20c1.5-3 5-5 8-5s6.5 2 8 5\"/></svg>'''},
            {"name": "APQP", "url": "/apqp", "color": "#f59e0b", "svg": '''<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\"><rect x=\"3\" y=\"3\" width=\"18\" height=\"18\" rx=\"4\"/><path d=\"M8 12h8\"/></svg>'''},
            {"name": "SPEC Center", "url": "/spec-center", "color": "#10b981", "svg": '''<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\"><circle cx=\"12\" cy=\"8\" r=\"3\"/><path d=\"M5 20c2-3 6-4 7-4s5 1 7 4\"/></svg>'''},
            {"name": "PRODUCT-INFO", "url": "/product-info", "color": "#2e5bff", "svg": '''<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\"><rect x=\"3\" y=\"4\" width=\"18\" height=\"16\" rx=\"3\"/><path d=\"M8 9h8\"/><path d=\"M8 13h5\"/></svg>'''}
        ]
        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(40)
        grid_layout.setContentsMargins(10, 10, 10, 10)
        col_count = 2
        for idx, module in enumerate(modules):
            card = self.create_module_card(module)
            row = idx // col_count
            col = idx % col_count
            grid_layout.addWidget(card, row, col, alignment=Qt.AlignmentFlag.AlignTop)
        fg_layout.addWidget(grid_widget)
        fg_layout.addStretch()
        main_layout.addWidget(fg_widget, 1)
        return container
    
    def create_module_card(self, module):
        module_color = module.get("color", "#667eea")
        module_svg = module.get("svg", None)
        card = QFrame()
        card.setFixedSize(300, 150)
        card.setStyleSheet(f"""
            QFrame {{
                background: #fff;
                border-radius: 16px;
                border: none;
            }}
            QFrame:hover {{
                background: #f8fafc;
            }}
        """)
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 24))
        card.setGraphicsEffect(shadow)
        vbox = QVBoxLayout(card)
        vbox.setContentsMargins(16, 16, 16, 16)
        vbox.setSpacing(4)
        top_bar = QFrame()
        top_bar.setFixedHeight(5)
        top_bar.setStyleSheet(f"background: {module_color}; border-radius: 3px 3px 0 0;")
        vbox.addWidget(top_bar)
                 
        if module_svg:
            svg_widget = QSvgWidget()
            svg_widget.load(bytearray(module_svg, encoding='utf-8'))
            svg_widget.setFixedSize(32, 32)
            vbox.addWidget(svg_widget, alignment=Qt.AlignmentFlag.AlignLeft)
        name = QLabel(module['name'])
        name.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        name.setStyleSheet("color: #1a1a2e; margin-bottom: 0px; background: transparent;")
        name.setAlignment(Qt.AlignmentFlag.AlignLeft)
        vbox.addWidget(name)
        vbox.addStretch()
        card.mousePressEvent = lambda e: self.open_module(module['url'])
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        return card
    
    def open_module(self, url):
        try:
            result = self.api_request("/auth/api/web-token")
            if result and result.get("success"):
                token = result.get("token")
                if token:
                    import webbrowser
                    module_url = f"{self.server_url}/auth/api/web-login?token={token}&next={url}"
                    webbrowser.open(module_url)
                    return
            QMessageBox.warning(self, "Error", "Failed to get web token: " + str(result))
        except Exception as e:
            logger.exception("Browser error during open_module")
            QMessageBox.warning(self, "Error", f"Browser error: {str(e)}")
    
    def open_browser(self):
        try:
            result = self.api_request("/auth/api/web-token")
            if result and result.get("success"):
                token = result.get("token")
                if token:
                    import webbrowser
                    url = f"{self.server_url}/auth/api/web-login?token={token}"
                    webbrowser.open(url)
                    return
            QMessageBox.warning(self, "Error", "Failed to get web token: " + str(result))
        except Exception as e:
            logger.exception("Browser error during open_browser")
            QMessageBox.warning(self, "Error", f"Browser error: {str(e)}")
    
    def handle_logout(self):
        try:
            self.cookie_jar.clear()
            if self.cookie_file.exists():
                self.cookie_file.unlink()
            self.current_user = None
            self.show_login_ui()
        except Exception:
            logger.debug("Error during logout", exc_info=True)
    
    def show_notification_popups(self):
        try:
            result = self.api_request("/api/notifications")
            if result and result.get("notifications"):
                notifications = result.get("notifications", [])
                if notifications:
                    summary = NotificationSummaryWindow(notifications)
                    self.active_toasts.append(summary)
                    summary.show()
                    logger.info(f"Showing {len(notifications)} notifications in summary window")
        except Exception:
            logger.exception("Failed to fetch or show notification popups")
    
    def show_notification(self, title, message):
        if platform.system() == "Darwin":
            import subprocess
            script = f'display notification "{message}" with title "{title}"'
            subprocess.run(["osascript", "-e", script])
        else:
            toast = ToastNotification(title, message)
            self.active_toasts.append(toast)
            toast.show()
            QTimer.singleShot(5000, lambda: self.active_toasts.remove(toast) if toast in self.active_toasts else None)
    
    def start_notification_worker(self):
        self.worker = NotificationWorker(self.server_url, cookie_jar=self.cookie_jar)
        self.worker_thread = QThread()
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.notification.connect(self.show_notification)
        self.worker_thread.start()
    
    def closeEvent(self, event):
        if self.tray:
            self.hide()
            event.ignore()
        else:
            event.accept()
    
    def exit_app(self):
        self.worker.stop()
        self.worker_thread.quit()
        self.worker_thread.wait()
        QApplication.quit()


def main():
    app = QApplication(sys.argv)
    window = QMSDesktopClient()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
