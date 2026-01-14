#!/usr/bin/env python3
"""
Video Downloader GUI - Entry Point

Gerenciador de downloads com interface gráfica PySide6.
Comunica com o servidor Flask para processar downloads via yt-dlp.
"""

import sys
import os

# Adiciona o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from windows.main_window import MainWindow


def main():
    """Função principal do aplicativo."""
    # Habilita High DPI
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)

    # Configurações do aplicativo
    app.setApplicationName("Video Downloader")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("VideoDownloader")

    # Fonte padrão
    font = QFont()
    font.setPointSize(12)
    app.setFont(font)

    # Não fecha quando a última janela é fechada (continua no tray)
    app.setQuitOnLastWindowClosed(False)

    # Cria e mostra a janela principal
    window = MainWindow()
    window.show()

    # Executa o loop principal
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
