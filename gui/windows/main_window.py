"""
Janela principal do Video Downloader GUI
"""

import requests
from typing import Optional
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QProgressBar, QComboBox, QSystemTrayIcon,
    QMenu, QMessageBox, QFrame, QSplitter, QGroupBox
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread, QSize
from PySide6.QtGui import QIcon, QAction, QColor, QFont, QPixmap, QPainter, QBrush


SERVER_URL = "http://127.0.0.1:5050"


class ApiWorker(QThread):
    """Worker thread para chamadas de API sem bloquear a UI."""

    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, endpoint: str, method: str = "GET", data: dict = None):
        super().__init__()
        self.endpoint = endpoint
        self.method = method
        self.data = data

    def run(self):
        try:
            url = f"{SERVER_URL}{self.endpoint}"
            if self.method == "GET":
                response = requests.get(url, timeout=5)
            elif self.method == "POST":
                response = requests.post(url, json=self.data, timeout=10)
            else:
                response = requests.request(self.method, url, json=self.data, timeout=10)

            self.finished.emit(response.json())
        except requests.exceptions.ConnectionError:
            self.error.emit("Servidor offline")
        except requests.exceptions.Timeout:
            self.error.emit("Timeout na conexão")
        except Exception as e:
            self.error.emit(str(e))


class DownloadItemWidget(QWidget):
    """Widget customizado para cada item de download."""

    cancel_requested = Signal(str)

    def __init__(self, download_id: str, title: str, url: str):
        super().__init__()
        self.download_id = download_id
        self.setup_ui(title, url)

    def setup_ui(self, title: str, url: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        # Estilo do widget container
        self.setStyleSheet("""
            DownloadItemWidget {
                background: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }
        """)
        self.setAutoFillBackground(True)

        # Linha superior: título e botão cancelar
        top_layout = QHBoxLayout()

        self.title_label = QLabel(title[:50] + "..." if len(title) > 50 else title)
        self.title_label.setFont(QFont("", 12, QFont.Bold))
        self.title_label.setStyleSheet("color: #333; background: transparent;")
        top_layout.addWidget(self.title_label, 1)

        self.status_label = QLabel("Aguardando...")
        self.status_label.setStyleSheet("color: #666; background: transparent; font-size: 12px;")
        top_layout.addWidget(self.status_label)

        self.cancel_btn = QPushButton("✕")
        self.cancel_btn.setFixedSize(24, 24)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background: #ff5252;
                color: white;
                border: none;
                border-radius: 12px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #ff1744;
            }
        """)
        self.cancel_btn.clicked.connect(lambda: self.cancel_requested.emit(self.download_id))
        top_layout.addWidget(self.cancel_btn)

        layout.addLayout(top_layout)

        # URL (truncada)
        url_display = url[:60] + "..." if len(url) > 60 else url
        self.url_label = QLabel(url_display)
        self.url_label.setStyleSheet("color: #666; font-size: 11px; background: transparent;")
        self.url_label.setToolTip(url)
        layout.addWidget(self.url_label)

        # Barra de progresso
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 4px;
                background: #e8e8e8;
                text-align: center;
                color: #333;
                font-size: 11px;
                font-weight: bold;
            }
            QProgressBar::chunk {
                border-radius: 4px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
            }
        """)
        layout.addWidget(self.progress_bar)

        # Info adicional (velocidade, ETA)
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #888; font-size: 11px; background: transparent;")
        layout.addWidget(self.info_label)

    def update_progress(self, percent: float, speed: str = "", eta: str = ""):
        self.progress_bar.setValue(int(percent))

        info_parts = []
        if speed:
            info_parts.append(speed)
        if eta:
            info_parts.append(f"ETA: {eta}")

        self.info_label.setText(" • ".join(info_parts))

    def set_status(self, status: str):
        status_colors = {
            "queued": ("#ff9800", "Na fila"),
            "downloading": ("#2196f3", "Baixando..."),
            "processing": ("#9c27b0", "Processando..."),
            "completed": ("#4caf50", "Concluído"),
            "failed": ("#f44336", "Falhou"),
            "cancelled": ("#757575", "Cancelado")
        }

        color, text = status_colors.get(status, ("#666", status))
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 12px; background: transparent;")

        if status in ("completed", "failed", "cancelled"):
            self.cancel_btn.setEnabled(False)
            self.cancel_btn.setStyleSheet("""
                QPushButton {
                    background: #ccc;
                    color: white;
                    border: none;
                    border-radius: 12px;
                    font-size: 12px;
                }
            """)


class MainWindow(QMainWindow):
    """Janela principal do aplicativo."""

    def __init__(self):
        super().__init__()
        self.download_widgets = {}
        self.workers = []
        self.setup_ui()
        self.setup_tray()
        self.setup_timers()

    def setup_ui(self):
        """Configura a interface do usuário."""
        self.setWindowTitle("Video Downloader")
        self.setMinimumSize(600, 500)
        self.resize(700, 600)

        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # Header com status do servidor
        header = self.create_header()
        main_layout.addWidget(header)

        # Seção de novo download
        new_download = self.create_new_download_section()
        main_layout.addWidget(new_download)

        # Lista de downloads
        downloads_section = self.create_downloads_section()
        main_layout.addWidget(downloads_section, 1)

        # Aplicar estilo global
        self.apply_styles()

    def create_header(self) -> QWidget:
        """Cria o cabeçalho com status do servidor."""
        header = QFrame()
        header.setObjectName("header")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 12, 16, 12)

        # Título
        title = QLabel("Video Downloader")
        title.setFont(QFont("", 18, QFont.Bold))
        title.setStyleSheet("color: white;")
        layout.addWidget(title)

        layout.addStretch()

        # Status do servidor
        self.server_indicator = QLabel("●")
        self.server_indicator.setStyleSheet("color: #ff5252; font-size: 16px;")
        layout.addWidget(self.server_indicator)

        self.server_status_label = QLabel("Verificando...")
        self.server_status_label.setStyleSheet("color: white;")
        layout.addWidget(self.server_status_label)

        return header

    def create_new_download_section(self) -> QWidget:
        """Cria a seção para adicionar novo download."""
        group = QGroupBox("Novo Download")
        layout = QVBoxLayout(group)

        # Linha de URL
        url_layout = QHBoxLayout()

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Cole a URL do vídeo aqui...")
        self.url_input.returnPressed.connect(self.add_download)
        url_layout.addWidget(self.url_input, 1)

        layout.addLayout(url_layout)

        # Opções
        options_layout = QHBoxLayout()

        options_layout.addWidget(QLabel("Qualidade:"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Melhor", "1080p", "720p", "480p", "360p", "Apenas áudio"])
        self.quality_combo.setCurrentIndex(0)
        options_layout.addWidget(self.quality_combo)

        options_layout.addSpacing(16)

        options_layout.addWidget(QLabel("Formato:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["MP4", "WebM", "MKV", "MP3"])
        self.format_combo.setCurrentIndex(0)
        options_layout.addWidget(self.format_combo)

        options_layout.addStretch()

        self.add_btn = QPushButton("Adicionar Download")
        self.add_btn.setObjectName("primaryButton")
        self.add_btn.clicked.connect(self.add_download)
        options_layout.addWidget(self.add_btn)

        layout.addLayout(options_layout)

        return group

    def create_downloads_section(self) -> QWidget:
        """Cria a seção de lista de downloads."""
        group = QGroupBox("Downloads")
        layout = QVBoxLayout(group)

        # Toolbar
        toolbar = QHBoxLayout()

        self.downloads_count_label = QLabel("0 downloads")
        toolbar.addWidget(self.downloads_count_label)

        toolbar.addStretch()

        self.refresh_btn = QPushButton("Atualizar")
        self.refresh_btn.clicked.connect(self.refresh_downloads)
        toolbar.addWidget(self.refresh_btn)

        self.clear_completed_btn = QPushButton("Limpar Concluídos")
        self.clear_completed_btn.clicked.connect(self.clear_completed)
        toolbar.addWidget(self.clear_completed_btn)

        layout.addLayout(toolbar)

        # Container de downloads (scroll area simulado)
        self.downloads_container = QWidget()
        self.downloads_layout = QVBoxLayout(self.downloads_container)
        self.downloads_layout.setContentsMargins(0, 0, 0, 0)
        self.downloads_layout.setSpacing(8)
        self.downloads_layout.addStretch()

        # Placeholder quando vazio
        self.empty_label = QLabel("Nenhum download na fila.\nAdicione uma URL acima para começar.")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: #999; padding: 40px;")
        self.downloads_layout.insertWidget(0, self.empty_label)

        from PySide6.QtWidgets import QScrollArea
        scroll = QScrollArea()
        scroll.setWidget(self.downloads_container)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        layout.addWidget(scroll)

        return group

    def setup_tray(self):
        """Configura o ícone na bandeja do sistema."""
        # Cria ícone programaticamente
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(QColor("#667eea")))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(2, 2, 28, 28)
        painter.setBrush(QBrush(QColor("white")))
        # Seta de download simplificada
        painter.drawRect(14, 8, 4, 10)
        points = [(10, 16), (22, 16), (16, 24)]
        from PySide6.QtGui import QPolygon
        from PySide6.QtCore import QPoint
        painter.drawPolygon(QPolygon([QPoint(x, y) for x, y in points]))
        painter.end()

        self.tray_icon = QSystemTrayIcon(QIcon(pixmap), self)

        # Menu do tray
        tray_menu = QMenu()

        show_action = QAction("Mostrar", self)
        show_action.triggered.connect(self.show_and_activate)
        tray_menu.addAction(show_action)

        tray_menu.addSeparator()

        quit_action = QAction("Sair", self)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_activated)
        self.tray_icon.show()

    def setup_timers(self):
        """Configura timers para polling."""
        # Timer para verificar status do servidor
        self.server_timer = QTimer()
        self.server_timer.timeout.connect(self.check_server_status)
        self.server_timer.start(5000)  # A cada 5 segundos

        # Timer para atualizar lista de downloads
        self.downloads_timer = QTimer()
        self.downloads_timer.timeout.connect(self.refresh_downloads)
        self.downloads_timer.start(2000)  # A cada 2 segundos

        # Verificação inicial
        self.check_server_status()
        self.refresh_downloads()

    def apply_styles(self):
        """Aplica estilos CSS à janela."""
        self.setStyleSheet("""
            QMainWindow {
                background: #f5f5f5;
            }

            #header {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                border-radius: 8px;
            }

            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                color: #333;
                border: 1px solid #ddd;
                border-radius: 8px;
                margin-top: 16px;
                padding: 16px 12px 12px 12px;
                background: white;
            }

            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 12px;
                top: 4px;
                padding: 0 8px;
                background: white;
                color: #667eea;
            }

            QLabel {
                color: #333;
                font-size: 13px;
            }

            QLineEdit {
                padding: 10px 12px;
                border: 1px solid #ddd;
                border-radius: 6px;
                background: white;
                font-size: 13px;
                color: #333;
            }

            QLineEdit:focus {
                border-color: #667eea;
            }

            QComboBox {
                padding: 8px 12px;
                border: 1px solid #ddd;
                border-radius: 6px;
                background: white;
                min-width: 120px;
                color: #333;
                font-size: 13px;
            }

            QComboBox::drop-down {
                border: none;
                padding-right: 8px;
            }

            QComboBox QAbstractItemView {
                background: white;
                color: #333;
                selection-background-color: #667eea;
                selection-color: white;
            }

            QPushButton {
                padding: 8px 16px;
                border: 1px solid #ddd;
                border-radius: 6px;
                background: white;
                color: #333;
                font-size: 13px;
            }

            QPushButton:hover {
                background: #f0f0f0;
                border-color: #ccc;
            }

            #primaryButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                color: white;
                border: none;
                font-weight: bold;
                padding: 10px 20px;
            }

            #primaryButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #5a6fd6, stop:1 #6a4190);
            }

            #primaryButton:disabled {
                background: #ccc;
                color: #888;
            }

            QScrollArea {
                border: none;
                background: transparent;
            }

            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
        """)

    def check_server_status(self):
        """Verifica o status do servidor."""
        worker = ApiWorker("/api/status")
        worker.finished.connect(self.on_server_status)
        worker.error.connect(self.on_server_error)
        self.workers.append(worker)
        worker.start()

    def on_server_status(self, data: dict):
        """Callback quando o servidor responde."""
        self.server_indicator.setStyleSheet("color: #4caf50; font-size: 16px;")
        self.server_status_label.setText("Servidor Online")
        self.add_btn.setEnabled(True)

    def on_server_error(self, error: str):
        """Callback quando há erro de conexão."""
        self.server_indicator.setStyleSheet("color: #ff5252; font-size: 16px;")
        self.server_status_label.setText("Servidor Offline")
        self.add_btn.setEnabled(False)

    def add_download(self):
        """Adiciona um novo download."""
        url = self.url_input.text().strip()
        if not url:
            return

        # Validar URL - não aceitar URLs blob:
        if url.startswith("blob:"):
            QMessageBox.warning(
                self,
                "URL Inválida",
                "URLs 'blob:' não são suportadas.\n\n"
                "Por favor, cole a URL real do vídeo.\n"
                "Exemplo: https://www.youtube.com/watch?v=XXXXX"
            )
            return

        format_map = {
            "MP4": "mp4",
            "WebM": "webm",
            "MKV": "mkv",
            "MP3": "mp3"
        }

        output_format = format_map.get(self.format_combo.currentText(), "mp4")

        data = {
            "url": url,
            "outputFormat": output_format,  # Formato de saída (mp4, mp3, etc)
        }

        worker = ApiWorker("/api/download", "POST", data)
        worker.finished.connect(self.on_download_added)
        worker.error.connect(self.on_download_error)
        self.workers.append(worker)
        worker.start()

        self.url_input.clear()
        self.add_btn.setEnabled(False)
        self.add_btn.setText("Adicionando...")

    def on_download_added(self, data: dict):
        """Callback quando download é adicionado."""
        self.add_btn.setEnabled(True)
        self.add_btn.setText("Adicionar Download")

        if data.get("success"):
            self.refresh_downloads()
        else:
            QMessageBox.warning(self, "Erro", data.get("error", "Erro ao adicionar download"))

    def on_download_error(self, error: str):
        """Callback quando há erro ao adicionar download."""
        self.add_btn.setEnabled(True)
        self.add_btn.setText("Adicionar Download")
        QMessageBox.warning(self, "Erro", f"Erro de conexão: {error}")

    def refresh_downloads(self):
        """Atualiza a lista de downloads."""
        worker = ApiWorker("/api/queue")
        worker.finished.connect(self.on_downloads_received)
        worker.error.connect(lambda e: None)  # Ignora erros silenciosamente
        self.workers.append(worker)
        worker.start()

    def on_downloads_received(self, data: dict):
        """Callback com a lista de downloads."""
        downloads = data.get("downloads", [])

        # Atualiza contador
        self.downloads_count_label.setText(f"{len(downloads)} download(s)")

        # Mostra/esconde placeholder
        self.empty_label.setVisible(len(downloads) == 0)

        # Atualiza widgets existentes ou cria novos
        current_ids = set()

        for dl in downloads:
            dl_id = dl.get("id")
            current_ids.add(dl_id)

            if dl_id in self.download_widgets:
                # Atualiza widget existente
                widget = self.download_widgets[dl_id]
                widget.set_status(dl.get("status", "queued"))
                widget.update_progress(
                    dl.get("progress", 0),
                    dl.get("speed", ""),
                    dl.get("eta", "")
                )
            else:
                # Cria novo widget
                widget = DownloadItemWidget(
                    dl_id,
                    dl.get("title", "Download"),
                    dl.get("url", "")
                )
                widget.cancel_requested.connect(self.cancel_download)
                widget.set_status(dl.get("status", "queued"))

                # Insere antes do stretch
                self.downloads_layout.insertWidget(
                    self.downloads_layout.count() - 1,
                    widget
                )
                self.download_widgets[dl_id] = widget

        # Remove widgets de downloads que não existem mais
        for dl_id in list(self.download_widgets.keys()):
            if dl_id not in current_ids:
                widget = self.download_widgets.pop(dl_id)
                widget.deleteLater()

        # Notificações para downloads concluídos
        for dl in downloads:
            if dl.get("status") == "completed":
                dl_id = dl.get("id")
                if dl_id in self.download_widgets:
                    # Verifica se já notificou
                    widget = self.download_widgets[dl_id]
                    if not hasattr(widget, "_notified"):
                        widget._notified = True
                        self.show_notification(
                            "Download Concluído",
                            dl.get("title", "Download finalizado!")
                        )

    def cancel_download(self, download_id: str):
        """Cancela um download."""
        worker = ApiWorker(f"/api/download/{download_id}/cancel", "POST")
        worker.finished.connect(lambda d: self.refresh_downloads())
        worker.error.connect(lambda e: QMessageBox.warning(self, "Erro", f"Erro ao cancelar: {e}"))
        self.workers.append(worker)
        worker.start()

    def clear_completed(self):
        """Remove downloads concluídos da lista."""
        worker = ApiWorker("/api/clear", "POST")
        worker.finished.connect(lambda d: self.refresh_downloads())
        worker.error.connect(lambda e: None)  # Ignora erros
        self.workers.append(worker)
        worker.start()

    def show_notification(self, title: str, message: str):
        """Exibe notificação do sistema."""
        if self.tray_icon.isVisible():
            self.tray_icon.showMessage(title, message, QSystemTrayIcon.Information, 3000)

    def show_and_activate(self):
        """Mostra e ativa a janela."""
        self.show()
        self.raise_()
        self.activateWindow()

    def tray_activated(self, reason):
        """Callback quando o ícone do tray é ativado."""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_and_activate()

    def closeEvent(self, event):
        """Override do evento de fechar - minimiza para tray."""
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "Video Downloader",
            "Aplicativo minimizado para a bandeja do sistema.",
            QSystemTrayIcon.Information,
            2000
        )

    def quit_app(self):
        """Fecha o aplicativo completamente."""
        self.tray_icon.hide()
        # Para todos os workers
        for worker in self.workers:
            if worker.isRunning():
                worker.quit()
                worker.wait()
        from PySide6.QtWidgets import QApplication
        QApplication.quit()
