"""Shared per-job and global options editor."""
from PySide6.QtWidgets import (QWidget, QFormLayout, QLineEdit, QCheckBox, QComboBox, QSpinBox, QPlainTextEdit, QPushButton, QHBoxLayout, QFileDialog, QTabWidget, QVBoxLayout, QLabel, QScrollArea, QFrame)
from .config import Options, ADVANCED


class OptionsForm(QWidget):
    def __init__(self, options, parent=None):
        super().__init__(parent)
        self.controls = {}
        self.base = options.public_dict()
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        layout.addWidget(tabs)
        groups = [
            ("Saída", [
                ("destination", "Pasta de destino", "folder"),
                ("mode", "Conteúdo", [("Vídeo + áudio", "video"), ("Extrair áudio", "audio")]),
                ("container", "Contêiner para mesclagem", ["mkv", "mp4", "webm"]),
                ("video_recode", "Recodificar vídeo (mais lento)", [("Manter codecs originais", ""), ("MP4", "mp4"), ("MKV", "mkv"), ("WebM", "webm"), ("AVI", "avi"), ("MOV", "mov")]),
                ("audio_format", "Converter áudio para", ["mp3", "m4a", "opus", "flac", "wav", "best"]),
                ("audio_quality", "Áudio (kb/s, quando aplicável)", ["128", "192", "256", "320"]),
                ("filename", "Modelo de nome", "text"),
                ("existing", "Arquivos existentes", [("Preservar / retomar parciais", "skip"), ("Sobrescrever", "overwrite")]),
                ("playlist", "Permitir playlists / canais", "bool"),
                ("playlist_items", "Itens da playlist (ex.: 1:5,8)", "text"),
            ]),
            ("Legendas e mídia", [
                ("subtitles", "Baixar legendas disponíveis", "bool"),
                ("automatic_subtitles", "Incluir legendas automáticas", "bool"),
                ("subtitle_languages", "Idiomas (regex separados por vírgula)", "text"),
                ("subtitle_format", "Converter legendas para", [("Formato original", ""), ("SRT", "srt"), ("VTT", "vtt"), ("ASS", "ass")]),
                ("embed_subtitles", "Incorporar legendas", "bool"),
                ("thumbnail", "Salvar miniatura", "bool"),
                ("embed_thumbnail", "Incorporar miniatura (formato compatível)", "bool"),
                ("metadata", "Incorporar metadados", "bool"),
                ("chapters", "Preservar capítulos disponíveis", "bool"),
                ("split_chapters", "Dividir vídeo por capítulos existentes", "bool"),
                ("section_start", "Intervalo: início (HH:MM:SS)", "text"),
                ("section_end", "Intervalo: fim (vazio = até o final)", "text"),
            ]),
            ("Conexão", [
                ("rate_kib", "Limite por tarefa em KiB/s (0 = ilimitado)", (0, 1000000)),
                ("retries", "Tentativas por arquivo / fragmento", (0, 100)),
                ("concurrent", "Downloads simultâneos", (1, 8)),
                ("cookies_file", "Cookies Netscape (arquivo local)", "file"),
                ("ffmpeg", "FFmpeg (executável ou pasta, vazio = automático)", "file"),
            ]),
        ]
        for title, definitions in groups:
            page = QWidget()
            form = QFormLayout(page)
            form.setSpacing(12)
            for name, label, kind in definitions:
                if kind == "bool":
                    control = QCheckBox()
                elif isinstance(kind, list):
                    control = QComboBox()
                    for item in kind:
                        control.addItem(*item) if isinstance(item, tuple) else control.addItem(item, item)
                elif isinstance(kind, tuple):
                    control = QSpinBox()
                    control.setRange(*kind)
                else:
                    control = QLineEdit()
                self.controls[name] = control
                if kind in ("folder", "file"):
                    row = QWidget()
                    box = QHBoxLayout(row)
                    box.setContentsMargins(0, 0, 0, 0)
                    box.addWidget(control)
                    button = QPushButton("Escolher…")
                    button.clicked.connect(lambda checked=False, n=name, k=kind: self.browse(n, k))
                    box.addWidget(button)
                    form.addRow(label, row)
                else:
                    form.addRow(label, control)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setWidget(page)
            tabs.addTab(scroll, title)
        advanced_page = QWidget()
        box = QVBoxLayout(advanced_page)
        text = QLabel("Opções adicionais da API yt-dlp em JSON. Apenas chaves validadas são aceitas.\nEx.: {\"format\": \"bv*[height<=1080]+ba/b\", \"format_sort\": [\"codec:h264\"]}\nA opção format substitui a seleção da tabela. Nenhum comando de sistema é aceito.")
        text.setWordWrap(True)
        box.addWidget(text)
        self.controls["advanced"] = QPlainTextEdit()
        box.addWidget(self.controls["advanced"])
        allowed = QLabel("Chaves aceitas: " + ", ".join(ADVANCED))
        allowed.setWordWrap(True)
        box.addWidget(allowed)
        tabs.addTab(advanced_page, "Avançado")
        self.load(options)

    def browse(self, name, kind):
        if kind == "folder":
            path = QFileDialog.getExistingDirectory(self, "Pasta de destino", self.controls[name].text())
        else:
            path, _ = QFileDialog.getOpenFileName(self, "Selecionar arquivo", self.controls[name].text())
        if path:
            self.controls[name].setText(path)

    def load(self, options):
        self.base = options.public_dict()
        for name, control in self.controls.items():
            value = getattr(options, name)
            if isinstance(control, QCheckBox):
                control.setChecked(value)
            elif isinstance(control, QComboBox):
                control.setCurrentIndex(max(0, control.findData(value)))
            elif isinstance(control, QSpinBox):
                control.setValue(value)
            elif isinstance(control, QPlainTextEdit):
                control.setPlainText(value)
            else:
                control.setText(value)

    def value(self):
        result = dict(self.base)
        for name, control in self.controls.items():
            if isinstance(control, QCheckBox):
                result[name] = control.isChecked()
            elif isinstance(control, QComboBox):
                result[name] = control.currentData()
            elif isinstance(control, QSpinBox):
                result[name] = control.value()
            elif isinstance(control, QPlainTextEdit):
                result[name] = control.toPlainText()
            else:
                result[name] = control.text().strip()
        return Options.from_dict(result).validate()
