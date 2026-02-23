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
    QGraphicsDropShadowEffect, QCheckBox
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject, QThread, QSize
from PySide6.QtGui import QIcon, QFont, QGuiApplication, QColor, QPalette, QAction, QPixmap, QKeySequence
import os
import requests
import math
import hashlib


class ToastNotification(QWidget):
    def __init__(self, title, message, duration=4200, variant="info", action_label=None, action_callback=None):
        super().__init__()
        self.os_type = platform.system()
        self.duration = max(1500, int(duration))
        self.variant = (variant or "info").lower()
        self.action_callback = action_callback

        color_map = {
            "success": {"accent": "#16a34a", "icon_bg": "#dcfce7", "icon_fg": "#166534", "icon": "✓"},
            "error": {"accent": "#dc2626", "icon_bg": "#fee2e2", "icon_fg": "#991b1b", "icon": "!"},
            "warning": {"accent": "#d97706", "icon_bg": "#ffedd5", "icon_fg": "#9a3412", "icon": "!"},
            "info": {"accent": "#2563eb", "icon_bg": "#dbeafe", "icon_fg": "#1e3a8a", "icon": "i"},
        }
        colors = color_map.get(self.variant, color_map["info"])
        self.accent = colors["accent"]

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("toastRoot")
        self.setStyleSheet("""
            QWidget#toastRoot {{
                background-color: #ffffff;
                border: 1px solid #dbe4f2;
                border-left: 4px solid {accent};
                border-radius: 14px;
            }}
            QLabel#toastTitle {{
                color: #0f172a;
                font-size: 12px;
                font-weight: 700;
            }}
            QLabel#toastMessage {{
                color: #475569;
                font-size: 11px;
            }}
            QLabel#toastIcon {{
                background: {icon_bg};
                border: 1px solid #dbe4f2;
                color: {icon_fg};
                border-radius: 12px;
                font-size: 12px;
                font-weight: 800;
                padding: 1px;
            }}
            QPushButton#toastClose {{
                background-color: #f8fafc;
                color: #64748b;
                border: 1px solid #e2e8f0;
                border-radius: 9px;
                font-size: 10px;
                font-weight: 700;
            }}
            QPushButton#toastClose:hover {{
                background-color: #eef2ff;
                color: #334155;
            }}
            QPushButton#toastAction {{
                background: #ffffff;
                color: #1e3a8a;
                border: 1px solid #bfdbfe;
                border-radius: 8px;
                font-size: 10px;
                font-weight: 700;
                padding: 3px 8px;
            }}
            QPushButton#toastAction:hover {{
                background: #eff6ff;
            }}
        """.format(
            accent=self.accent,
            icon_bg=colors["icon_bg"],
            icon_fg=colors["icon_fg"],
        ))
        try:
            effect = QGraphicsDropShadowEffect(self)
            effect.setBlurRadius(22)
            effect.setColor(QColor(15, 23, 42, 70))
            effect.setOffset(0, 8)
            self.setGraphicsEffect(effect)
        except Exception:
            logger.debug("Drop shadow not available for toast", exc_info=True)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 8, 10, 8)
        root_layout.setSpacing(8)

        content_row = QHBoxLayout()
        content_row.setSpacing(10)

        icon_label = QLabel(colors["icon"])
        icon_label.setObjectName("toastIcon")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setFixedSize(24, 24)
        content_row.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignTop)

        text_wrap = QWidget()
        text_layout = QVBoxLayout(text_wrap)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(3)

        title_label = QLabel(title)
        title_font = QFont("Segoe UI" if self.os_type == "Windows" else "San Francisco" if self.os_type == "Darwin" else "Ubuntu", 12, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setObjectName("toastTitle")
        text_layout.addWidget(title_label)

        message_label = QLabel(message)
        message_font = QFont("Segoe UI" if self.os_type == "Windows" else "San Francisco" if self.os_type == "Darwin" else "Ubuntu", 10)
        message_label.setFont(message_font)
        message_label.setObjectName("toastMessage")
        message_label.setWordWrap(True)
        message_label.setMaximumWidth(290)
        text_layout.addWidget(message_label)

        if action_label and callable(action_callback):
            action_btn = QPushButton(str(action_label))
            action_btn.setObjectName("toastAction")
            action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            action_btn.clicked.connect(self._run_action)
            text_layout.addWidget(action_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        content_row.addWidget(text_wrap, 1)

        close_btn = QPushButton("×")
        close_btn.setObjectName("toastClose")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setFixedSize(18, 18)
        close_btn.clicked.connect(self.close)
        content_row.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignTop)

        root_layout.addLayout(content_row)

        self.progress_track = QFrame()
        self.progress_track.setFixedHeight(3)
        self.progress_track.setStyleSheet("background:#eef2f7; border-radius:2px;")
        self.progress_layout = QHBoxLayout(self.progress_track)
        self.progress_layout.setContentsMargins(0, 0, 0, 0)
        self.progress_layout.setSpacing(0)

        self.progress_fill = QFrame()
        self.progress_fill.setFixedHeight(3)
        self.progress_fill.setStyleSheet(f"background:{self.accent}; border-radius:2px;")
        self.progress_layout.addWidget(self.progress_fill)
        root_layout.addWidget(self.progress_track)

        self.setFixedWidth(376)
        self.adjustSize()
        self.move_to_bottom_right()

        self._elapsed = 0
        self.close_timer = QTimer(self)
        self.close_timer.timeout.connect(self.close)
        self.close_timer.start(self.duration)

        self.progress_timer = QTimer(self)
        self.progress_timer.timeout.connect(self._tick_progress)
        self.progress_timer.start(50)
    
    def move_to_bottom_right(self):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        if self.os_type == "Darwin":
            x = screen.right() - self.width() - 24
            y = screen.bottom() - self.height() - 72
        else:
            x = screen.right() - self.width() - 16
            y = screen.bottom() - self.height() - 16
        self.move(x, y)
    
    def closeEvent(self, event):
        self.close_timer.stop()
        self.progress_timer.stop()

    def _tick_progress(self):
        self._elapsed += 50
        ratio = max(0.0, min(1.0, 1.0 - (self._elapsed / float(self.duration))))
        width = max(0, int(self.progress_track.width() * ratio))
        self.progress_fill.setFixedWidth(width)

    def _run_action(self):
        try:
            if callable(self.action_callback):
                self.action_callback()
        except Exception:
            logger.debug("Toast action callback failed", exc_info=True)
        self.close()


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
                border: 1px solid #dbe4f2;
            }
        """)
        
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #2e5bff, stop:1 #1f4df0);
                border-radius: 10px 10px 0 0;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 4, 8, 4)
        header_layout.setSpacing(6)
        
        icon_label = QLabel("🔔")
        icon_label.setStyleSheet("font-size: 12px; background: transparent;")
        header_layout.addWidget(icon_label)
        
        title = QLabel(f"New Issues · {len(notifications)}")
        font_family = "Segoe UI" if self.os_type == "Windows" else "San Francisco" if self.os_type == "Darwin" else "Ubuntu"
        title.setFont(QFont(font_family, 10, QFont.Weight.DemiBold))
        title.setStyleSheet("color: white; background: transparent;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(18, 18)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.15);
                color: white;
                border: none;
                font-size: 12px;
                font-weight: normal;
                border-radius: 9px;
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
        header.setFixedHeight(34)
        
        container_layout.addWidget(header)
        
        from PySide6.QtSvgWidgets import QSvgWidget
        import os
        total_frame = QFrame()
        total_frame.setStyleSheet("background: transparent;")
        total_frame.setFixedHeight(48)
        total_layout = QHBoxLayout(total_frame)
        total_layout.setContentsMargins(12, 8, 12, 8)
        total_layout.setSpacing(8)
        total_label = QLabel("Total notifications")
        total_label.setFont(QFont(font_family, 10, QFont.Weight.DemiBold))
        total_label.setStyleSheet("color: #0f172a;")
        total_layout.addWidget(total_label, alignment=Qt.AlignmentFlag.AlignLeft)
        badge = QLabel(str(len(notifications)))
        badge.setFont(QFont(font_family, 11, QFont.Weight.Bold))
        badge.setStyleSheet("background: #eef2ff; color: #3730a3; padding: 4px 10px; border-radius: 12px;")
        total_layout.addStretch()
        total_layout.addWidget(badge, alignment=Qt.AlignmentFlag.AlignRight)

        summary_widget = QWidget()
        summary_layout = QVBoxLayout(summary_widget)
        summary_layout.setContentsMargins(8, 4, 8, 8)
        summary_layout.setSpacing(6)
        summary_widget.setStyleSheet("background: transparent;")

        def classify_status(notif):
            raw_status = str(notif.get('status') or '').strip().lower()
            if raw_status in {'complete', 'completed'}:
                return 'Complete'
            if raw_status in {'in-progress', 'in progress'}:
                return 'In-progress'
            if raw_status in {'not started', 'not_started'}:
                return 'Not Started'
            if raw_status in {'n/a', 'na'}:
                return 'N/A'

            title_text = str(notif.get('title') or '').lower()
            if 'complete' in title_text:
                return 'Complete'
            if 'in-progress' in title_text or 'in progress' in title_text:
                return 'In-progress'
            if 'not started' in title_text:
                return 'Not Started'
            if 'delay' in title_text or 'overdue' in title_text or '지연' in title_text:
                return 'In-progress'
            return 'New'

        status_counts = {
            'New': 0,
            'Not Started': 0,
            'In-progress': 0,
            'Complete': 0,
            'N/A': 0,
        }
        for notif in notifications:
            status_key = classify_status(notif)
            status_counts[status_key] = status_counts.get(status_key, 0) + 1

        status_meta = {
            'New': {'bg': '#f1f5f9', 'border': '#cbd5e1', 'color': '#334155'},
            'Not Started': {'bg': '#fff7ed', 'border': '#fdba74', 'color': '#9a3412'},
            'In-progress': {'bg': '#eff6ff', 'border': '#93c5fd', 'color': '#1d4ed8'},
            'Complete': {'bg': '#ecfdf5', 'border': '#86efac', 'color': '#166534'},
            'N/A': {'bg': '#f8fafc', 'border': '#e2e8f0', 'color': '#64748b'},
        }

        for status_name in ['New', 'Not Started', 'In-progress', 'Complete', 'N/A']:
            count = status_counts.get(status_name, 0)
            if count <= 0:
                continue

            colors = status_meta[status_name]
            row_widget = QWidget()
            row_widget.setStyleSheet(f"""
                QWidget {{
                    background: {colors['bg']};
                    border: 1px solid {colors['border']};
                    border-radius: 10px;
                }}
            """)
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(9, 6, 9, 6)
            row_layout.setSpacing(8)

            status_label = QLabel(status_name)
            status_label.setStyleSheet(f"color:{colors['color']}; font-size:10px; font-weight:700;")
            row_layout.addWidget(status_label)
            row_layout.addStretch()

            count_badge = QLabel(str(count))
            count_badge.setStyleSheet(f"""
                background:#ffffff;
                color:{colors['color']};
                border:1px solid {colors['border']};
                border-radius:9px;
                padding:2px 7px;
                font-size:9px;
                font-weight:800;
            """)
            row_layout.addWidget(count_badge)
            summary_layout.addWidget(row_widget)

        container_layout.addWidget(total_frame)
        container_layout.addWidget(summary_widget)
        
        footer = QFrame()
        footer.setStyleSheet("""
            QFrame {
                background-color: #f8fafc;
                border-radius: 0 0 12px 12px;
            }
        """)
        footer.setFixedHeight(34)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(10, 4, 10, 4)
        
        footer_text = QLabel("Status summary only")
        footer_text.setFont(QFont(font_family, 8))
        footer_text.setStyleSheet("color: #64748b; background: transparent; padding-left: 4px;")
        footer_layout.addWidget(footer_text)
        footer_layout.addStretch()

        open_btn = QPushButton("Open Dashboard")
        open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_btn.setStyleSheet("""
            QPushButton {
                background:#2e5bff;
                color:#ffffff;
                border:1px solid #1d4ed8;
                border-radius:8px;
                padding:3px 9px;
                font-size:9px;
                font-weight:700;
            }
            QPushButton:hover { background:#1f4df0; }
        """)
        open_btn.clicked.connect(self.open_main_workspace)
        footer_layout.addWidget(open_btn)
        
        container_layout.addWidget(footer)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.addWidget(container)
        visible_status_rows = sum(1 for value in status_counts.values() if value > 0)
        self.setFixedSize(320, max(156, 96 + visible_status_rows * 28))
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

    def open_main_workspace(self):
        from PySide6.QtWidgets import QApplication
        for widget in QApplication.topLevelWidgets():
            if widget is self:
                continue
            if getattr(widget, '__class__', None) and getattr(widget, '__class__').__name__ == 'QMSDesktopClient' and hasattr(widget, 'open_module'):
                widget.open_module('/main')
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
        screen = QGuiApplication.primaryScreen().availableGeometry()
        if self.os_type == "Darwin":
            x = screen.right() - self.width() - 24
            y = screen.bottom() - self.height() - 72
        else:
            x = screen.right() - self.width() - 16
            y = screen.bottom() - self.height() - 16
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
        self.selected_module_filter = None
        self.quick_search_text = ""
        self.cached_tasks = []
        self.cached_notifications = []
        self.last_sync_text = "Never"
        self.ui_settings_file = self.root_dir / ".qms_desktop_ui.json"
        self.ui_settings = self.load_ui_settings()
        self.auto_refresh_enabled = bool(self.ui_settings.get("auto_refresh_enabled", True))
        self.auto_refresh_seconds = int(self.ui_settings.get("auto_refresh_seconds", 90))
        if self.auto_refresh_seconds < 30:
            self.auto_refresh_seconds = 30
        
        self.cookie_file = self.root_dir / ".qms_cookies"
        self.cookie_jar = LWPCookieJar(str(self.cookie_file))
        self.load_cookies()
        self.restore_session()
        
        self.setWindowTitle("RAMSCHIP QMS")
                                
        self.setMinimumSize(1180, 780)
        self.resize(1280, 860)
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

                                                                               
            # store file_menu so we can update it later after login
            self.file_menu = menu_bar.addMenu('File')
            # Garage files: available to authenticated users (download)
            try:
                garage_action = QAction('Garage files', self)
                garage_action.triggered.connect(self.show_garage_files)
                self.file_menu.addAction(garage_action)
            except Exception:
                logger.debug('Failed to add Garage files action', exc_info=True)
                user_email = self.current_user.get('email') if self.current_user else None
                try:
                    from core.config import GARAGE_ADMIN_EMAILS
                    if user_email and user_email.lower() in GARAGE_ADMIN_EMAILS:
                        upload_action = QAction('Upload to Garage', self)
                        upload_action.triggered.connect(self.upload_to_garage)
                        self.file_menu.addAction(upload_action)
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
        
        # Ensure admin actions (garage) are added if user present
        try:
            if self.current_user:
                self._maybe_add_garage_action()
        except Exception:
            logger.debug('Failed to apply garage admin actions on init', exc_info=True)

        if self.current_user:
            self.show_main_ui()
            QTimer.singleShot(1000, self.show_notification_popups)
        else:
            self.show_login_ui()
        
        self.start_notification_worker()
        self.setup_tray()
        self.setup_shortcuts()

        self.auto_refresh_timer = QTimer(self)
        self.auto_refresh_timer.timeout.connect(self.refresh_main_ui)
        self.apply_auto_refresh_settings()

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

            # Quick server session check to ensure server recognizes our login
            debug_resp = self.api_request('/api/garage/debug', silent=True)
            if not debug_resp or not debug_resp.get('session'):
                # fallback to global /api/me or /auth/api/me
                debug_resp = self.api_request('/api/me', silent=True) or self.api_request('/auth/api/me', silent=True)
            if not debug_resp or not (debug_resp.get('session') or debug_resp.get('authenticated')):
                QMessageBox.warning(self, 'Not authenticated on server', 'Your desktop session is not authenticated on the server. Please login (swlee@ramschip.com) via the desktop client or web interface and try again.')
                logger.warning('Attempted garage upload without server session: %s', debug_resp)
                return

            path, _ = QFileDialog.getOpenFileName(self, "Upload to Garage")
            if not path:
                return

            # gather file meta
            filename = os.path.basename(path)
            total_size = os.path.getsize(path)
            desired_chunk = 10 * 1024 * 1024

            # resume support records
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
                    logger.warning('Garage init failed: %s', init_resp)
                    msg = 'Failed to start upload session'
                    if isinstance(init_resp, dict) and init_resp.get('detail'):
                        msg = f"Failed to start upload session: {init_resp.get('detail')}"
                    QMessageBox.critical(self, 'Upload Failed', msg)
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

    def show_garage_files(self):
        """Open a dialog listing Garage files and allow downloading selected file."""
        try:
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QFileDialog, QMessageBox, QHBoxLayout
            dlg = QDialog(self)
            dlg.setWindowTitle('Garage files')
            dlg.setMinimumSize(700, 400)

            layout = QVBoxLayout()
            info = QLabel('Fetching files...')
            layout.addWidget(info)

            table = QTableWidget(0, 3)
            table.setHorizontalHeaderLabels(['Filename', 'Size', 'Uploaded'])
            from PySide6.QtWidgets import QAbstractItemView
            table.setSelectionBehavior(QAbstractItemView.SelectRows)
            table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            layout.addWidget(table)

            btn_layout = QHBoxLayout()
            download_btn = QPushButton('Download')
            zip_btn = QPushButton('Download Selected as ZIP')
            close_btn = QPushButton('Close')
            btn_layout.addWidget(download_btn)
            btn_layout.addWidget(zip_btn)
            btn_layout.addWidget(close_btn)
            layout.addLayout(btn_layout)

            dlg.setLayout(layout)

            # fetch files
            resp = self.api_request('/api/garage/files', silent=True)
            files = []
            if not resp or not resp.get('ok'):
                info.setText('Failed to fetch files')
            else:
                files = resp.get('files', [])
                info.setText(f"{len(files)} files")
                table.setRowCount(len(files))
                for i, f in enumerate(files):
                    table.setItem(i, 0, QTableWidgetItem(f.get('filename')))
                    table.setItem(i, 1, QTableWidgetItem(str(f.get('size'))))
                    table.setItem(i, 2, QTableWidgetItem(str(f.get('created'))))

            def do_download():
                sel = table.selectionModel().selectedRows()
                if not sel:
                    QMessageBox.information(dlg, 'No selection', 'Please select a file to download')
                    return
                row = sel[0].row()
                safe_name = files[row].get('safe_name')
                orig = files[row].get('filename')
                path, _ = QFileDialog.getSaveFileName(self, 'Save file as', orig)
                if not path:
                    return

                # perform download streaming in background thread
                threading.Thread(target=self._download_garage_file, args=(safe_name, path, files[row].get('size')), daemon=True).start()
                QMessageBox.information(dlg, 'Download started', f'Downloading {orig} to {path}')

            def do_zip_download():
                sel = table.selectionModel().selectedRows()
                if not sel:
                    QMessageBox.information(dlg, 'No selection', 'Please select one or more files to download as ZIP')
                    return
                safe_names = [files[r.row()].get('safe_name') for r in sel]
                path, _ = QFileDialog.getSaveFileName(self, 'Save ZIP as', 'garage_files.zip', 'ZIP files (*.zip)')
                if not path:
                    return
                threading.Thread(target=self._download_garage_zip, args=(safe_names, path), daemon=True).start()
                QMessageBox.information(dlg, 'Download started', f'Downloading {len(safe_names)} files as ZIP to {path}')

            download_btn.clicked.connect(do_download)
            zip_btn.clicked.connect(do_zip_download)
            close_btn.clicked.connect(dlg.close)

            dlg.exec()
        except Exception:
            logger.exception('Failed to show garage files dialog')

    def _download_garage_file(self, safe_name: str, path: str, total_size: int = None):
        """Download a file and show a progress dialog by polling the partial file size."""
        try:
            import requests
            s = requests.Session()
            cookies = {c.name: c.value for c in self.cookie_jar}
            s.cookies.update(cookies)
            url = f"{self.server_url.rstrip('/')}/api/garage/download/{safe_name}"

            # create control flags for progress polling
            status = {'done': False, 'error': None}

            # start downloader thread
            def _worker():
                try:
                    r = s.get(url, stream=True, timeout=60)
                    if r.status_code != 200:
                        status['error'] = f"Download failed: {r.status_code} {r.text}"
                        status['done'] = True
                        return
                    with open(path, 'wb') as out:
                        for chunk in r.iter_content(1024 * 1024):
                            if chunk:
                                out.write(chunk)
                    status['done'] = True
                except Exception as e:
                    status['error'] = str(e)
                    status['done'] = True

            t = threading.Thread(target=_worker, daemon=True)
            t.start()

            # progress dialog and poller
            try:
                from PySide6.QtWidgets import QProgressDialog, QMessageBox
                from PySide6.QtCore import QTimer

                if total_size and int(total_size) > 0:
                    progress = QProgressDialog('Downloading...', 'Cancel', 0, int(total_size), self)
                    progress.setWindowTitle('Downloading')
                    progress.setMinimumDuration(200)
                else:
                    progress = QProgressDialog('Downloading...', 'Cancel', 0, 0, self)
                    progress.setWindowTitle('Downloading')
                    progress.setMinimumDuration(200)
                    progress.setRange(0, 0)  # busy indicator

                def poll():
                    try:
                        if status.get('done'):
                            progress.close()
                            if status.get('error'):
                                QTimer.singleShot(0, lambda: QMessageBox.critical(self, 'Download failed', str(status.get('error'))))
                            else:
                                QTimer.singleShot(0, lambda: QMessageBox.information(self, 'Download complete', f'Downloaded to {path}'))
                            return
                        if progress.maximum() > 0:
                            try:
                                cur = os.path.getsize(path) if os.path.exists(path) else 0
                                progress.setValue(int(cur))
                            except Exception:
                                pass
                        QTimer.singleShot(300, poll)
                    except Exception:
                        pass

                poll()
            except Exception:
                # no GUI feedback; wait for thread to finish
                t.join(timeout=120)
                if status.get('error'):
                    logger.warning('Download thread error: %s', status.get('error'))
                else:
                    logger.info('Downloaded garage file %s to %s', safe_name, path)

            if status.get('error'):
                logger.warning('Download failed: %s', status.get('error'))
            else:
                logger.info('Downloaded garage file %s to %s', safe_name, path)
        except Exception:
            logger.exception('Failed to download garage file')

    def _download_garage_zip(self, safe_names: list, path: str):
        """Request a server-side ZIP and download it with progress bar."""
        try:
            import requests
            s = requests.Session()
            cookies = {c.name: c.value for c in self.cookie_jar}
            s.cookies.update(cookies)
            url = f"{self.server_url.rstrip('/')}/api/garage/download-zip"

            status = {'done': False, 'error': None}

            def _worker():
                try:
                    r = s.post(url, json={'safe_names': safe_names}, stream=True, timeout=120)
                    if r.status_code != 200:
                        status['error'] = f"Download failed: {r.status_code} {r.text}"
                        status['done'] = True
                        return
                    total = int(r.headers.get('content-length') or 0)
                    with open(path, 'wb') as out:
                        for chunk in r.iter_content(1024 * 1024):
                            if chunk:
                                out.write(chunk)
                    status['done'] = True
                except Exception as e:
                    status['error'] = str(e)
                    status['done'] = True

            t = threading.Thread(target=_worker, daemon=True)
            t.start()

            try:
                from PySide6.QtWidgets import QProgressDialog, QMessageBox
                from PySide6.QtCore import QTimer

                # attempt to get total size from server by HEAD first
                try:
                    head = s.post(url, json={'safe_names': safe_names}, stream=True, timeout=10)
                    total = int(head.headers.get('content-length') or 0)
                except Exception:
                    total = 0

                if total > 0:
                    progress = QProgressDialog('Downloading ZIP...', 'Cancel', 0, int(total), self)
                    progress.setWindowTitle('Downloading ZIP')
                    progress.setMinimumDuration(200)
                else:
                    progress = QProgressDialog('Downloading ZIP...', 'Cancel', 0, 0, self)
                    progress.setWindowTitle('Downloading ZIP')
                    progress.setMinimumDuration(200)
                    progress.setRange(0, 0)

                def poll():
                    try:
                        if status.get('done'):
                            progress.close()
                            if status.get('error'):
                                QTimer.singleShot(0, lambda: QMessageBox.critical(self, 'Download failed', str(status.get('error'))))
                            else:
                                QTimer.singleShot(0, lambda: QMessageBox.information(self, 'Download complete', f'Downloaded to {path}'))
                            return
                        if progress.maximum() > 0:
                            try:
                                cur = os.path.getsize(path) if os.path.exists(path) else 0
                                progress.setValue(int(cur))
                            except Exception:
                                pass
                        QTimer.singleShot(300, poll)
                    except Exception:
                        pass

                poll()
            except Exception:
                t.join(timeout=300)
                if status.get('error'):
                    logger.warning('ZIP download thread error: %s', status.get('error'))
                else:
                    logger.info('Downloaded ZIP to %s', path)

            if status.get('error'):
                logger.warning('ZIP download failed: %s', status.get('error'))
            else:
                logger.info('Downloaded ZIP to %s', path)
        except Exception:
            logger.exception('Failed to download garage ZIP')
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
                    logger.warning('Garage init failed: %s', init_resp)
                    msg = 'Failed to start upload session'
                    # If server returned a JSON error with 'detail', show it
                    if isinstance(init_resp, dict) and init_resp.get('detail'):
                        msg = f"Failed to start upload session: {init_resp.get('detail')}"
                    QMessageBox.critical(self, 'Upload Failed', msg)
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

    def load_ui_settings(self):
        try:
            if self.ui_settings_file.exists():
                return json.loads(self.ui_settings_file.read_text(encoding='utf-8'))
        except Exception:
            logger.debug("Failed to load ui settings", exc_info=True)
        return {
            "remember_email": False,
            "saved_email": "",
            "auto_refresh_enabled": True,
            "auto_refresh_seconds": 90,
        }

    def save_ui_settings(self):
        try:
            self.ui_settings_file.write_text(json.dumps(self.ui_settings, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception:
            logger.debug("Failed to save ui settings", exc_info=True)
    
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
                    if attempt < 1:
                        attempt += 1
                        time.sleep(0.4)
                        continue
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

    def _maybe_add_garage_action(self):
        """Add or remove the 'Upload to Garage' action on the File menu based on current_user.
        Idempotent and safe to call after login/logout to refresh UI."""
        try:
            user_email = self.current_user.get('email') if self.current_user else None
            from core.config import GARAGE_ADMIN_EMAILS
            # Remove existing action if present
            try:
                if hasattr(self, 'garage_action') and self.garage_action:
                    try:
                        if hasattr(self, 'file_menu') and self.file_menu:
                            self.file_menu.removeAction(self.garage_action)
                    except Exception:
                        pass
                    self.garage_action = None
            except Exception:
                pass

            if not (user_email and user_email.lower() in GARAGE_ADMIN_EMAILS):
                return

            # Ensure file_menu exists
            if not hasattr(self, 'file_menu') or self.file_menu is None:
                return

            # Add action
            self.garage_action = QAction('Upload to Garage', self)
            self.garage_action.triggered.connect(self.upload_to_garage)
            self.file_menu.addAction(self.garage_action)
        except Exception:
            logger.debug('Failed to add garage action', exc_info=True)
    
    def show_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()
    
    def show_login_ui(self):
        central_widget = QWidget()
        central_widget.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #eef2ff,
                stop:0.45 #f8fbff,
                stop:1 #f8fafc);
        """)
        self.setCentralWidget(central_widget)

        self.setMinimumSize(1000, 760)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(14)
        layout.setContentsMargins(120, 28, 120, 28)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        brand_head = QFrame()
        brand_head.setStyleSheet("background: transparent;")
        brand_head.setFixedHeight(132)
        brand_head_layout = QVBoxLayout(brand_head)
        brand_head_layout.setContentsMargins(0, 0, 0, 0)
        brand_head_layout.setSpacing(6)

        title = QLabel("RAMSCHIP QMS")
        font_family = "Segoe UI" if self.os_type == "Windows" else "San Francisco" if self.os_type == "Darwin" else "Ubuntu"
        title.setFont(QFont(font_family, 44, QFont.Weight.Bold))
        title.setStyleSheet("color: #2e5bff; background: transparent; letter-spacing: 1px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Enterprise Quality Management Workspace")
        subtitle.setFont(QFont(font_family, 13, QFont.Weight.Medium))
        subtitle.setStyleSheet("color: #64748b; background: transparent;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        badge_line = QLabel("Secure Access  •  Real-time Notifications  •  Desktop Optimized")
        badge_line.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge_line.setStyleSheet("""
            color: #475569;
            font-size: 11px;
            font-weight: 600;
            background: rgba(255,255,255,0.65);
            border: 1px solid #dbe4f2;
            border-radius: 12px;
            padding: 4px 10px;
        """)

        brand_head_layout.addWidget(title)
        brand_head_layout.addWidget(subtitle)
        brand_head_layout.addWidget(badge_line, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(brand_head)
        
        form_frame = QFrame()
        form_frame.setStyleSheet("""
            background-color: #ffffff;
            border-radius: 16px;
            border: 1px solid #dbe4f2;
        """)
        form_frame.setMaximumWidth(760)
        try:
            shadow = QGraphicsDropShadowEffect(form_frame)
            shadow.setBlurRadius(32)
            shadow.setColor(QColor(15, 23, 42, 40))
            shadow.setOffset(0, 12)
            form_frame.setGraphicsEffect(shadow)
        except Exception:
            logger.debug('Shadow not available for login frame', exc_info=True)

        form_layout = QVBoxLayout(form_frame)
        form_layout.setSpacing(14)
        form_layout.setContentsMargins(56, 42, 56, 42)

        form_title = QLabel("Sign in")
        form_title.setFont(QFont(font_family, 20, QFont.Weight.Bold))
        form_title.setStyleSheet("color: #0f172a;")
        form_layout.addWidget(form_title)

        form_hint = QLabel("Use your company account to continue")
        form_hint.setStyleSheet("color: #64748b; font-size: 12px;")
        form_layout.addWidget(form_hint)

        self.error_label = QLabel()
        self.error_label.setStyleSheet("""
            color: #b91c1c;
            font-size: 12px;
            font-weight: 600;
            background: #fef2f2;
            border: 1px solid #fecaca;
            border-radius: 8px;
            padding: 6px 10px;
        """)
        self.error_label.setVisible(False)
        form_layout.addWidget(self.error_label)

        email_label = QLabel("Email")
        email_label.setStyleSheet("font-size: 12px; font-weight: 700; color: #334155;")
        form_layout.addWidget(email_label)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("you@company.com")
        self.email_input.setFixedHeight(50)
        self.email_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.email_input.setMinimumWidth(500)
        self.email_input.setStyleSheet("""
            QLineEdit {
                padding: 10px 12px;
                border: 1px solid #d0dcf0;
                border-radius: 10px;
                font-size: 14px;
                font-family: Segoe UI;
                background-color: #fbfdff;
                color: #0f172a;
            }
            QLineEdit::placeholder {
                color: #94a3b8;
            }
            QLineEdit:focus {
                border: 1px solid #2e5bff;
                background-color: #ffffff;
            }
        """)
        if self.ui_settings.get("remember_email") and self.ui_settings.get("saved_email"):
            self.email_input.setText(self.ui_settings.get("saved_email", ""))
        form_layout.addWidget(self.email_input)

        pwd_label = QLabel("Password")
        pwd_label.setStyleSheet("font-size: 12px; font-weight: 700; color: #334155;")
        form_layout.addWidget(pwd_label)

        password_row = QWidget()
        password_row_layout = QHBoxLayout(password_row)
        password_row_layout.setContentsMargins(0, 0, 0, 0)
        password_row_layout.setSpacing(8)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setFixedHeight(50)
        self.password_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.password_input.setMinimumWidth(430)
        self.password_input.setStyleSheet("""
            QLineEdit {
                padding: 10px 12px;
                border: 1px solid #d0dcf0;
                border-radius: 10px;
                font-size: 14px;
                font-family: Segoe UI;
                background-color: #fbfdff;
                color: #0f172a;
            }
            QLineEdit::placeholder {
                color: #94a3b8;
            }
            QLineEdit:focus {
                border: 1px solid #2e5bff;
                background-color: #ffffff;
            }
        """)
        password_row_layout.addWidget(self.password_input, 1)

        self.toggle_password_btn = QPushButton("Show")
        self.toggle_password_btn.setFixedHeight(50)
        self.toggle_password_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_password_btn.setStyleSheet("""
            QPushButton {
                background: #f8fafc;
                color: #334155;
                border: 1px solid #d0dcf0;
                border-radius: 10px;
                font-size: 12px;
                font-weight: 700;
                padding: 0 14px;
            }
            QPushButton:hover {
                background: #eef2ff;
                border: 1px solid #a9c0ea;
            }
        """)
        self.toggle_password_btn.clicked.connect(self.toggle_password_visibility)
        password_row_layout.addWidget(self.toggle_password_btn)

        form_layout.addWidget(password_row)

        self.remember_email_checkbox = QCheckBox("Remember email")
        self.remember_email_checkbox.setChecked(bool(self.ui_settings.get("remember_email", False)))
        self.remember_email_checkbox.setStyleSheet("""
            QCheckBox {
                color: #475569;
                font-size: 12px;
                font-weight: 600;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 15px;
                height: 15px;
                border: 1px solid #c7d2e4;
                border-radius: 4px;
                background: #ffffff;
            }
            QCheckBox::indicator:checked {
                background: #2e5bff;
                border: 1px solid #1d4ed8;
            }
        """)
        form_layout.addWidget(self.remember_email_checkbox)

        login_btn = QPushButton("Login")
        login_btn.setFixedHeight(52)
        login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        login_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2e5bff, stop:1 #1f4df0);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 15px;
                font-weight: 800;
                padding: 10px 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3a6dff, stop:1 #2157f6);
            }
        """)
        login_btn.clicked.connect(self.handle_login)
        form_layout.addWidget(login_btn)

        self.email_input.returnPressed.connect(self.handle_login)
        self.password_input.returnPressed.connect(self.handle_login)

        form_layout.addStretch()

        footer = QLabel("Secure connection • Notifications enabled  • www.ramschip.com")
        footer.setStyleSheet("color: #64748b; font-size: 11px;")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        form_layout.addWidget(footer)

        layout.addWidget(form_frame, alignment=Qt.AlignmentFlag.AlignCenter)

    def toggle_password_visibility(self):
        if self.password_input.echoMode() == QLineEdit.EchoMode.Password:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_password_btn.setText("Hide")
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_password_btn.setText("Show")
    
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
                self.error_label.setVisible(False)
                self.current_user = result.get("user", {})
                self.save_cookies()

                self.ui_settings["remember_email"] = bool(self.remember_email_checkbox.isChecked())
                self.ui_settings["saved_email"] = email if self.ui_settings["remember_email"] else ""
                self.save_ui_settings()

                # Refresh admin UI elements (menu/tray) now that we're logged in
                try:
                    self._maybe_add_garage_action()
                except Exception:
                    logger.debug('Failed to add garage action after login', exc_info=True)
                try:
                    if hasattr(self, 'tray') and self.tray:
                        try:
                            self.tray.hide()
                        except Exception:
                            pass
                    self.setup_tray()
                except Exception:
                    logger.debug('Failed to refresh tray after login', exc_info=True)
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

    def setup_shortcuts(self):
        try:
            refresh_action = QAction(self)
            refresh_action.setShortcut(QKeySequence("Ctrl+R"))
            refresh_action.triggered.connect(self.refresh_main_ui)
            self.addAction(refresh_action)

            focus_search_action = QAction(self)
            focus_search_action.setShortcut(QKeySequence("Ctrl+F"))
            focus_search_action.triggered.connect(self.focus_quick_search)
            self.addAction(focus_search_action)

            browser_action = QAction(self)
            browser_action.setShortcut(QKeySequence("Ctrl+Shift+O"))
            browser_action.triggered.connect(self.open_browser)
            self.addAction(browser_action)
        except Exception:
            logger.debug("Failed to setup shortcuts", exc_info=True)

    def focus_quick_search(self):
        try:
            if hasattr(self, 'quick_search_input') and self.quick_search_input:
                self.quick_search_input.setFocus()
                self.quick_search_input.selectAll()
        except Exception:
            logger.debug("Failed to focus quick search", exc_info=True)

    def _matches_search(self, *values):
        query = (self.quick_search_text or "").strip().lower()
        if not query:
            return True
        merged = " ".join(str(value or "") for value in values).lower()
        return query in merged

    def refresh_dashboard_data(self):
        tasks = None
        notifications = None

        task_result = self.api_request("/rpmt/api/my-tasks", silent=True)
        if task_result and isinstance(task_result, dict):
            tasks = task_result.get("tasks") or []

        notif_result = self.api_request("/api/notifications", silent=True)
        if notif_result and isinstance(notif_result, dict):
            notifications = notif_result.get("notifications") or []

        if tasks is not None:
            self.cached_tasks = tasks
        if notifications is not None:
            self.cached_notifications = notifications
        self.last_sync_text = time.strftime("%Y-%m-%d %H:%M:%S")

    def set_quick_search(self, value):
        self.quick_search_text = (value or "").strip()
        self.show_main_ui()

    def apply_auto_refresh_settings(self):
        try:
            self.auto_refresh_timer.stop()
            if self.auto_refresh_enabled:
                self.auto_refresh_timer.start(max(30, self.auto_refresh_seconds) * 1000)
        except Exception:
            logger.debug("Failed to apply auto refresh settings", exc_info=True)

    def toggle_auto_refresh(self):
        self.auto_refresh_enabled = not self.auto_refresh_enabled
        self.ui_settings["auto_refresh_enabled"] = self.auto_refresh_enabled
        self.save_ui_settings()
        self.apply_auto_refresh_settings()
        self.show_main_ui()

    def cycle_auto_refresh_interval(self):
        cycle = [30, 60, 90, 120, 180]
        try:
            current_index = cycle.index(self.auto_refresh_seconds)
        except ValueError:
            current_index = 2
        self.auto_refresh_seconds = cycle[(current_index + 1) % len(cycle)]
        self.ui_settings["auto_refresh_seconds"] = self.auto_refresh_seconds
        self.save_ui_settings()
        self.apply_auto_refresh_settings()
        self.show_main_ui()

    def refresh_main_ui(self):
        self.show_main_ui(reload_data=True)

    def clear_module_filter(self):
        self.selected_module_filter = None
        self.show_main_ui()

    def _status_color(self, status_text):
        normalized = (status_text or "").strip().lower()
        if normalized in {"complete", "completed"}:
            return "#10b981"
        if normalized in {"in-progress", "in progress"}:
            return "#3b82f6"
        if normalized in {"not started", "not_started"}:
            return "#f59e0b"
        return "#64748b"

    def _module_name(self, module_key):
        module_map = {
            "rpmt": "RPMT",
            "svit": "SVIT",
            "cits": "CITS",
            "spec": "SPEC",
            "spec-center": "SPEC",
            "product-info": "PRODUCT-INFO",
            "apqp": "APQP",
        }
        return module_map.get((module_key or "").lower(), (module_key or "QMS").upper())

    def _module_route(self, module_key):
        route_map = {
            'rpmt': '/rpmt',
            'svit': '/svit',
            'cits': '/cits',
            'spec': '/spec-center',
            'spec-center': '/spec-center',
            'product-info': '/product-info',
            'apqp': '/apqp'
        }
        return route_map.get((module_key or '').lower(), '/main')

    def open_notification_item(self, notif):
        module_key = (notif.get('module') or '').lower()
        self.open_module(self._module_route(module_key))

    def open_task_item(self, task):
        module_key = (task.get('module') or '').lower()
        self.open_module(self._module_route(module_key))
    
    def show_main_ui(self, reload_data=False):
        if reload_data or (self.current_user and not (self.cached_tasks or self.cached_notifications)):
            self.refresh_dashboard_data()

        central_widget = QWidget()
        central_widget.setObjectName("mainRoot")
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        central_widget.setStyleSheet("""
            QWidget#mainRoot {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f4f7ff,
                    stop:0.4 #f8fbff,
                    stop:1 #f1f5f9);
            }
        """)
        
        navbar = self.create_navbar()
        layout.addWidget(navbar)
        
        tabs = QTabWidget()
        self.main_tabs = tabs
        tabs.setDocumentMode(True)
        tabs.setObjectName("mainTabs")
        tabs.setStyleSheet("""
            QTabWidget#mainTabs::pane {
                border: 1px solid #d6e1f0;
                border-radius: 16px;
                top: -1px;
                background-color: rgba(255, 255, 255, 0.9);
                margin: 0 16px 16px 16px;
            }
            QTabBar {
                background-color: transparent;
                left: 16px;
            }
            QTabBar::tab {
                background-color: rgba(255, 255, 255, 0.68);
                padding: 12px 22px;
                border: 1px solid #dbe4f2;
                border-bottom: none;
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
                font-family: Segoe UI;
                font-size: 13px;
                font-weight: 700;
                color: #6b7280;
                margin-right: 6px;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
                border-color: #c9d7ee;
                color: #0f172a;
            }
            QTabBar::tab:hover {
                background-color: rgba(231, 240, 255, 0.8);
            }
        """)
        
        tabs.addTab(self.create_tasks_tab(), "My Tasks")
        tabs.addTab(self.create_notifications_tab(), "Notifications")
        tabs.addTab(self.create_modules_tab(), "Quick Access")
        
        layout.addWidget(tabs)
    
    def create_navbar(self):
        navbar = QFrame()
        navbar.setObjectName("topNavbar")
        navbar.setStyleSheet("""
            QFrame#topNavbar {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #ffffff,
                    stop:1 #f5f9ff);
                border-bottom: 1px solid #d5e1f1;
            }
        """)
        navbar.setFixedHeight(112)
        root_layout = QVBoxLayout(navbar)
        root_layout.setContentsMargins(16, 8, 16, 8)
        root_layout.setSpacing(8)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        title_wrap = QWidget()
        title_layout = QVBoxLayout(title_wrap)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(0)

        title = QLabel("RAMSCHIP QMS")
        title_font = QFont("Segoe UI", 30, QFont.Weight.Bold)
        title_font.setLetterSpacing(QFont.AbsoluteSpacing, 0.4)
        title.setFont(title_font)
        title.setStyleSheet("color:#3b82f6; line-height:1;")
        title_layout.addWidget(title)

        subtitle = QLabel("Enterprise Workspace")
        subtitle.setStyleSheet("color:#64748b; font-size:11px; font-weight:600;")
        title_layout.addWidget(subtitle)
        top_row.addWidget(title_wrap)
        top_row.addStretch()

        if self.current_user:
            user_name = self.current_user.get('english_name', 'User')
            user_label = QLabel(f"👤 {user_name}")
            user_label.setStyleSheet("""
                color:#334155;
                padding:7px 12px;
                border-radius:10px;
                background:#eef2ff;
                border:1px solid #c7d2fe;
                font-size:11px;
                font-weight:700;
            """)
            top_row.addWidget(user_label)

        browser_btn = QPushButton("Open Browser")
        browser_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browser_btn.setMinimumWidth(124)
        browser_btn.setStyleSheet("""
            QPushButton {
                background:#2e5bff;
                color:#ffffff;
                border:1px solid #1e40af;
                border-radius:10px;
                padding:8px 14px;
                font-size:11px;
                font-weight:700;
            }
            QPushButton:hover { background:#1f4df0; }
        """)
        browser_btn.clicked.connect(self.open_browser)
        top_row.addWidget(browser_btn)

        logout_btn = QPushButton("Logout")
        logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        logout_btn.setMinimumWidth(96)
        logout_btn.setStyleSheet("""
            QPushButton {
                background:#64748b;
                color:#ffffff;
                border:1px solid #334155;
                border-radius:10px;
                padding:8px 14px;
                font-size:11px;
                font-weight:700;
            }
            QPushButton:hover { background:#475569; }
        """)
        logout_btn.clicked.connect(self.handle_logout)
        top_row.addWidget(logout_btn)
        root_layout.addLayout(top_row)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(8)

        task_count = len(self.cached_tasks)
        notif_count = len(self.cached_notifications)
        active_count = len([
            task for task in self.cached_tasks
            if str(task.get('status', '')).strip().lower() in {'in-progress', 'in progress'}
        ])

        summary_chip = QLabel(f"Tasks {task_count}  ·  Alerts {notif_count}  ·  Active {active_count}")
        summary_chip.setStyleSheet("""
            background:#eef2ff;
            color:#3730a3;
            border:1px solid #c7d2fe;
            border-radius:10px;
            padding:6px 10px;
            font-size:10px;
            font-weight:700;
        """)
        bottom_row.addWidget(summary_chip)

        self.quick_search_input = QLineEdit()
        self.quick_search_input.setPlaceholderText("Search tasks, notifications, modules (Ctrl+F)")
        self.quick_search_input.setText(self.quick_search_text)
        self.quick_search_input.setClearButtonEnabled(True)
        self.quick_search_input.setMinimumWidth(320)
        self.quick_search_input.setMaximumWidth(420)
        self.quick_search_input.setStyleSheet("""
            QLineEdit {
                background:#ffffff;
                color:#0f172a;
                border:1px solid #cbd5e1;
                border-radius:10px;
                padding:7px 10px;
                font-size:11px;
            }
            QLineEdit:focus {
                border:1px solid #60a5fa;
                background:#f8fbff;
            }
        """)
        self.quick_search_input.textChanged.connect(self.set_quick_search)
        bottom_row.addWidget(self.quick_search_input, 1)

        sync_label = QLabel(f"Updated {self.last_sync_text}")
        sync_label.setStyleSheet("color:#64748b; font-size:10px; font-weight:600;")
        bottom_row.addWidget(sync_label)

        notif_btn = QPushButton("Notifications")
        notif_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        notif_btn.setStyleSheet("""
            QPushButton {
                background:#ffffff;
                color:#334155;
                border:1px solid #cbd5e1;
                border-radius:10px;
                padding:6px 10px;
                font-size:11px;
                font-weight:700;
            }
            QPushButton:hover { background:#f1f5ff; }
        """)
        notif_btn.clicked.connect(self.show_notification_popups)
        bottom_row.addWidget(notif_btn)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background:#ffffff;
                color:#334155;
                border:1px solid #cbd5e1;
                border-radius:10px;
                padding:6px 12px;
                font-size:11px;
                font-weight:700;
            }
            QPushButton:hover { background:#eef2ff; }
        """)
        refresh_btn.clicked.connect(self.refresh_main_ui)
        bottom_row.addWidget(refresh_btn)

        if hasattr(self, 'selected_module_filter') and self.selected_module_filter:
            clear_filter_btn = QPushButton("Clear")
            clear_filter_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            clear_filter_btn.setStyleSheet("""
                QPushButton {
                    background:#fff7ed;
                    color:#9a3412;
                    border:1px solid #fed7aa;
                    border-radius:10px;
                    padding:6px 10px;
                    font-size:11px;
                    font-weight:700;
                }
                QPushButton:hover { background:#ffedd5; }
            """)
            clear_filter_btn.clicked.connect(self.clear_module_filter)
            bottom_row.addWidget(clear_filter_btn)

        root_layout.addLayout(bottom_row)

        return navbar
    
    def create_tasks_tab(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        container.setStyleSheet("background-color: transparent;")

        header = QFrame()
        header.setObjectName("quickAccessHeader")
        header.setStyleSheet("""
            QFrame#quickAccessHeader {
                background:#ffffff;
                border: 1px solid #d9e3f1;
                border-radius: 14px;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 9, 12, 9)
        header_layout.setSpacing(10)

        title = QLabel("My Tasks")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title.setStyleSheet("color:#0f172a;")
        header_layout.addWidget(title)

        if hasattr(self, 'selected_module_filter') and self.selected_module_filter:
            filter_banner = QLabel(f"Filter: {self._module_name(self.selected_module_filter)}")
            filter_banner.setStyleSheet("""
                background: #e0e7ff;
                color: #3730a3;
                padding: 4px 10px;
                border-radius: 10px;
                font-weight: 700;
            """)
            header_layout.addWidget(filter_banner)

        header_layout.addStretch()
        layout.addWidget(header)

        try:
            tasks = list(self.cached_tasks or [])

            if tasks:
                selected_filter = (getattr(self, 'selected_module_filter', None) or '').lower()
                if selected_filter:
                    tasks = [task for task in tasks if (task.get('module', '') or '').lower() == selected_filter]

                if self.quick_search_text:
                    tasks = [
                        task for task in tasks
                        if self._matches_search(task.get('title'), task.get('status'), task.get('due_date'), self._module_name(task.get('module')))
                    ]

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
                    scroll_layout.setSpacing(8)
                    
                    for task in tasks[:30]:
                        card = self.create_task_card(task)
                        scroll_layout.addWidget(card)

                    scroll_layout.addStretch()
                    scroll.setWidget(scroll_widget)
                    layout.addWidget(scroll)
                else:
                    empty_label = QLabel("No tasks assigned for current filter/search")
                    empty_label.setStyleSheet("color: #64748b; font-size: 12px; padding: 10px;")
                    layout.addWidget(empty_label)
                    layout.addStretch()
            else:
                fail_label = QLabel("No tasks available")
                fail_label.setStyleSheet("color: #64748b; font-size: 12px; padding: 10px;")
                layout.addWidget(fail_label)
                layout.addStretch()
        except Exception as e:
            error_label = QLabel(f"Error: {str(e)}")
            error_label.setStyleSheet("color:#b91c1c; padding: 10px;")
            layout.addWidget(error_label)
            layout.addStretch()

        return container
    
    def create_task_card(self, task):
        card = QFrame()
        card.setObjectName("taskCard")
        card.setStyleSheet("""
            QFrame#taskCard {
                background:#ffffff;
                border: 1px solid #d8e3f2;
                border-radius: 16px;
                margin: 0 2px;
                padding: 14px;
            }
            QFrame#taskCard:hover {
                background:#f8fbff;
                border: 1px solid #9fb7e4;
            }
        """)

        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(37, 99, 235, 28))
        card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(9)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        module_name = self._module_name(task.get('module', 'qms'))
        module_chip = QLabel(module_name)
        module_chip.setStyleSheet("background:#e0ecff; color:#1e3a8a; border:1px solid #bfdbfe; border-radius:10px; padding:3px 9px; font-size:10px; font-weight:700;")
        top_row.addWidget(module_chip)

        status = task.get('status', 'N/A')
        status_label = QLabel(f"● {status}")
        status_label.setStyleSheet(f"color: {self._status_color(status)}; font-size: 11px; font-weight: 700;")
        top_row.addWidget(status_label)
        top_row.addStretch()

        due_text = task.get('due_date')
        if due_text:
            due_badge = QLabel(f"DUE {due_text}")
            due_badge.setStyleSheet("color:#334155; background:#f8fafc; border:1px solid #dbe2ea; border-radius:9px; padding:3px 8px; font-size:10px; font-weight:700;")
            top_row.addWidget(due_badge)

        layout.addLayout(top_row)

        title = QLabel(task.get('title', 'Unknown'))
        title_font = QFont("Segoe UI", 14, QFont.Weight.DemiBold)
        title_font.setLetterSpacing(QFont.AbsoluteSpacing, 0.2)
        title.setFont(title_font)
        title.setStyleSheet("color: #0f172a; line-height: 1.35;")
        title.setWordWrap(True)
        layout.addWidget(title)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(8)
        bottom_row.addStretch()

        open_btn = QPushButton("Open")
        open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_btn.setStyleSheet("""
            QPushButton {
                background:#2e5bff;
                color:#ffffff;
                border:1px solid #1e40af;
                border-radius:10px;
                padding:7px 13px;
                font-size:11px;
                font-weight:700;
            }
            QPushButton:hover {
                background:#1f4df0;
            }
        """)
        open_btn.clicked.connect(lambda _=False, item=task: self.open_task_item(item))
        bottom_row.addWidget(open_btn)

        layout.addLayout(bottom_row)

        return card
    
    def create_notifications_tab(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        container.setStyleSheet("background-color: transparent;")

        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background:#ffffff;
                border: 1px solid #d9e3f1;
                border-radius: 14px;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 9, 12, 9)
        title = QLabel("Notifications")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title.setStyleSheet("color:#0f172a;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background:#ffffff;
                color:#334155;
                border:1px solid #c9d7ee;
                border-radius:8px;
                padding:5px 10px;
                font-size:11px;
                font-weight:700;
            }
            QPushButton:hover {
                background:#eef2ff;
                border:1px solid #aac2ea;
            }
        """)
        refresh_btn.clicked.connect(self.refresh_main_ui)
        header_layout.addWidget(refresh_btn)
        layout.addWidget(header)
        
        try:
            notifications = list(self.cached_notifications or [])

            if notifications:
                if self.quick_search_text:
                    notifications = [
                        notif for notif in notifications
                        if self._matches_search(
                            notif.get('title'),
                            notif.get('description'),
                            notif.get('time'),
                            self._module_name(notif.get('module')),
                            notif.get('status')
                        )
                    ]

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
                    scroll_layout.setSpacing(8)
                    
                    for notif in notifications[:30]:
                        card = self.create_notification_card(notif)
                        scroll_layout.addWidget(card)

                    scroll_layout.addStretch()
                    scroll.setWidget(scroll_widget)
                    layout.addWidget(scroll)
                else:
                    empty_label = QLabel("No notifications for current search")
                    empty_label.setStyleSheet("color: #64748b; font-size: 12px; padding: 10px;")
                    layout.addWidget(empty_label)
                    layout.addStretch()
            else:
                fail_label = QLabel("No notifications")
                fail_label.setStyleSheet("color: #64748b; font-size: 12px; padding: 10px;")
                layout.addWidget(fail_label)
                layout.addStretch()
        except Exception as e:
            error_label = QLabel(f"Error: {str(e)}")
            error_label.setStyleSheet("color:#b91c1c; padding: 10px;")
            layout.addWidget(error_label)
            layout.addStretch()

        return container
    
    def create_notification_card(self, notif):
        card = QFrame()
        card.setObjectName("notificationCard")
        card.setStyleSheet("""
            QFrame#notificationCard {
                background:#ffffff;
                border-left: 5px solid #3b82f6;
                border: 1px solid #dbe4f2;
                margin: 0 2px;
                padding: 12px 14px;
                border-radius: 14px;
            }
            QFrame#notificationCard:hover {
                background:#f8fbff;
                border: 1px solid #9fb7e4;
            }
        """)

        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 5)
        shadow.setColor(QColor(37, 99, 235, 24))
        card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(7)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        module_name = self._module_name(notif.get('module', 'qms'))
        module_chip = QLabel(module_name)
        module_chip.setStyleSheet("""
            background:#eef2ff;
            color:#3730a3;
            border:1px solid #c7d2fe;
            border-radius:10px;
            padding:2px 8px;
            font-size:10px;
            font-weight:700;
        """)
        top_row.addWidget(module_chip)
        top_row.addStretch()

        if notif.get('time'):
            time_label = QLabel(str(notif.get('time')))
            time_label.setStyleSheet("color:#64748b; font-size:10px; font-weight:600;")
            top_row.addWidget(time_label)

        layout.addLayout(top_row)

        title = QLabel(notif.get('title', 'Unknown'))
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.DemiBold))
        title.setStyleSheet("color: #0f172a;")
        layout.addWidget(title)

        if notif.get('description'):
            desc = QLabel(notif.get('description', ''))
            desc.setStyleSheet("color: #475569; font-size: 11px; line-height: 1.35;")
            desc.setWordWrap(True)
            layout.addWidget(desc)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(8)
        bottom_row.addStretch()

        open_btn = QPushButton("Open")
        open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_btn.setStyleSheet("""
            QPushButton {
                background:#2e5bff;
                color:#ffffff;
                border:1px solid #1e40af;
                border-radius:8px;
                padding:4px 10px;
                font-size:10px;
                font-weight:700;
            }
            QPushButton:hover {
                background:#1f4df0;
            }
        """)
        open_btn.clicked.connect(lambda _=False, item=notif: self.open_notification_item(item))
        bottom_row.addWidget(open_btn)
        layout.addLayout(bottom_row)

        return card
    
    def create_modules_tab(self):
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(10)

        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background:#ffffff;
                border: 1px solid #d9e3f1;
                border-radius: 14px;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 9, 12, 9)
        header_layout.setSpacing(10)

        title = QLabel("Quick Access")
        title.setObjectName("quickAccessTitle")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title.setStyleSheet("color:#0f172a; border:none; background:transparent; padding:0;")
        header_layout.addWidget(title)

        subtitle = QLabel("Open module dashboards quickly")
        subtitle.setObjectName("quickAccessSubtitle")
        subtitle.setStyleSheet("color:#64748b; font-size:11px; border:none; background:transparent; padding:0;")
        header_layout.addWidget(subtitle)
        header_layout.addStretch()

        open_main_btn = QPushButton("Main")
        open_main_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_main_btn.setStyleSheet("""
            QPushButton {
                background:#ffffff;
                color:#334155;
                border:1px solid #c9d7ee;
                border-radius:8px;
                padding:5px 10px;
                font-size:11px;
                font-weight:700;
            }
            QPushButton:hover {
                background:#eef2ff;
            }
        """)
        open_main_btn.clicked.connect(lambda: self.open_module('/main'))
        header_layout.addWidget(open_main_btn)
        main_layout.addWidget(header)

        modules = [
            {"name": "RPMT", "url": "/rpmt", "help": "/rpmt/help", "desc": "Project roadmap and weekly execution", "color": "#2e5bff", "icon": "📦"},
            {"name": "SVIT", "url": "/svit", "help": "/svit/help", "desc": "Shuttle and board validation management", "color": "#8b5cf6", "icon": "🧪"},
            {"name": "CITS", "url": "/cits", "help": "/cits/help", "desc": "Inquiry and issue tracking workflow", "color": "#ec4899", "icon": "🎫"},
            {"name": "APQP", "url": "/apqp", "help": None, "desc": "Advanced planning quality pipeline", "color": "#f59e0b", "icon": "📋"},
            {"name": "SPEC Center", "url": "/spec-center", "help": "/spec-center/help", "desc": "Specification documents and approvals", "color": "#10b981", "icon": "📚"},
            {"name": "PRODUCT-INFO", "url": "/product-info", "help": "/product-info/help", "desc": "Product matrix and version knowledge", "color": "#2563eb", "icon": "🧭"}
        ]

        if self.quick_search_text:
            modules = [
                module for module in modules
                if self._matches_search(module.get('name'), module.get('desc'))
            ]

        if not modules:
            empty = QLabel("No modules for current search")
            empty.setStyleSheet("color:#64748b; font-size:12px; padding:10px;")
            main_layout.addWidget(empty)
            main_layout.addStretch()
            return container

        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(14)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setColumnStretch(0, 1)
        grid_layout.setColumnStretch(1, 1)
        grid_layout.setColumnStretch(2, 1)

        for idx, module in enumerate(modules):
            card = self.create_module_card(module)
            row = idx // 3
            col = idx % 3
            grid_layout.addWidget(card, row, col)

        main_layout.addWidget(grid_widget)
        main_layout.addStretch()
        return container
    
    def create_module_card(self, module):
        module_color = module.get("color", "#667eea")
        module_icon = module.get("icon", "🧩")
        card = QFrame()
        card.setObjectName("moduleCard")
        card.setMinimumSize(230, 164)
        card.setMaximumHeight(194)
        card.setStyleSheet(f"""
            QFrame#moduleCard {{
                background: #ffffff;
                border-radius: 16px;
                border: 1px solid #dbe4f2;
            }}
            QFrame#moduleCard:hover {{
                background: #f8fbff;
                border: 1px solid {module_color};
            }}
            QFrame#moduleCard QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(37, 99, 235, 24))
        card.setGraphicsEffect(shadow)
        vbox = QVBoxLayout(card)
        vbox.setContentsMargins(12, 10, 12, 11)
        vbox.setSpacing(7)
        top_bar = QFrame()
        top_bar.setFixedHeight(4)
        top_bar.setStyleSheet(f"background: {module_color}; border-radius: 3px;")
        vbox.addWidget(top_bar)

        icon_label = QLabel(module_icon)
        icon_label.setStyleSheet("font-size: 18px; background:#ffffff; border:1px solid #dbe4f2; border-radius:14px; padding:3px 8px;")
        vbox.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignLeft)
        vbox.addSpacing(6)

        name = QLabel(module['name'])
        name.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        name.setStyleSheet("color:#0f172a;")
        name.setAlignment(Qt.AlignmentFlag.AlignLeft)
        vbox.addWidget(name)

        hint = QLabel(module.get("desc", "Open module workspace"))
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#64748b; font-size:11px;")
        vbox.addWidget(hint)

        vbox.addStretch()

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        btn_row.addStretch()

        open_btn = QPushButton("Open →")
        open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_btn.setStyleSheet(f"""
            QPushButton {{
                background:{module_color};
                color:#ffffff;
                border:1px solid {module_color};
                border-radius:10px;
                padding:6px 12px;
                font-size:11px;
                font-weight:700;
            }}
            QPushButton:hover {{
                background:#1f4df0;
            }}
        """)
        open_btn.clicked.connect(lambda _=False, url=module['url']: self.open_module(url))
        btn_row.addWidget(open_btn)

        help_url = module.get("help")
        if help_url:
            help_btn = QPushButton("Help")
            help_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            help_btn.setStyleSheet("""
                QPushButton {
                    background:#ffffff;
                    color:#334155;
                    border:1px solid #c9d7ee;
                    border-radius:10px;
                    padding:6px 12px;
                    font-size:11px;
                    font-weight:700;
                }
                QPushButton:hover {
                    background:#eef2ff;
                }
            """)
            help_btn.clicked.connect(lambda _=False, url=help_url: self.open_module(url))
            btn_row.addWidget(help_btn)

        vbox.addLayout(btn_row)

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
            try:
                self._maybe_add_garage_action()
            except Exception:
                logger.debug('Failed to remove garage action on logout', exc_info=True)
            try:
                if hasattr(self, 'tray') and self.tray:
                    try:
                        self.tray.hide()
                    except Exception:
                        pass
                    self.setup_tray()
            except Exception:
                logger.debug('Failed to refresh tray on logout', exc_info=True)
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

    def _cleanup_toast_refs(self):
        self.active_toasts = [widget for widget in self.active_toasts if widget is not None and widget.isVisible()]

    def _reflow_toasts(self):
        self._cleanup_toast_refs()
        toasts = [widget for widget in self.active_toasts if isinstance(widget, ToastNotification)]
        if not toasts:
            return

        screen = QGuiApplication.primaryScreen().availableGeometry()
        x = screen.right() - 390
        y = screen.bottom() - 16
        for toast in reversed(toasts):
            toast.adjustSize()
            toast.move(x, y - toast.height())
            y -= toast.height() + 10

    def _infer_notification_variant(self, title, message):
        text = f"{title or ''} {message or ''}".lower()
        if any(keyword in text for keyword in ['error', 'failed', 'fail', 'denied', 'unauthorized']):
            return 'error'
        if any(keyword in text for keyword in ['warning', 'delay', 'overdue', 'late', '주의', '지연']):
            return 'warning'
        if any(keyword in text for keyword in ['success', 'complete', 'completed', 'done', 'saved']):
            return 'success'
        return 'info'
    
    def show_notification(self, title, message):
        if platform.system() == "Darwin":
            import subprocess
            script = f'display notification "{message}" with title "{title}"'
            subprocess.run(["osascript", "-e", script])
        else:
            variant = self._infer_notification_variant(title, message)
            action_label = None
            action_callback = None

            if variant in {"error", "warning"}:
                action_label = "Open"
                action_callback = self.show_main_ui
            elif "task" in f"{title} {message}".lower():
                action_label = "Tasks"
                action_callback = lambda: self.open_module('/rpmt')

            toast = ToastNotification(
                title,
                message,
                duration=4600,
                variant=variant,
                action_label=action_label,
                action_callback=action_callback,
            )

            self._cleanup_toast_refs()
            active_toasts = [widget for widget in self.active_toasts if isinstance(widget, ToastNotification)]
            if len(active_toasts) >= 4:
                oldest = active_toasts[0]
                try:
                    oldest.close()
                except Exception:
                    logger.debug("Failed to close oldest toast", exc_info=True)

            self.active_toasts.append(toast)
            toast.show()
            self._reflow_toasts()

            def remove_toast_reference():
                if toast in self.active_toasts:
                    self.active_toasts.remove(toast)
                self._reflow_toasts()

            QTimer.singleShot(5000, remove_toast_reference)
    
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
