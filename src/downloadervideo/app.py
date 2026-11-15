"""Responsive Qt desktop UI. All network and extraction work uses child processes."""
import base64
from pathlib import Path
import sys
from PySide6.QtCore import Qt, QTimer, QUrl, QLockFile
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QStackedWidget, QPlainTextEdit, QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox, QDialog, QDialogButtonBox, QScrollArea, QComboBox, QTabWidget, QListWidget, QTextBrowser, QSplitter)
from . import __version__
from .config import Options, validate_url, data_dir
from .forms import OptionsForm
from .manager import Manager, STATES, ACTIVE
from .process import Worker
from .store import Store
from .theme import STYLE


def bytes_text(value):
    if value is None:
        return "—"
    size = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024 or unit == "TiB":
            return f"{size:.1f} {unit}"
        size /= 1024


def duration(value):
    if value is None:
        return "—"
    value = int(value)
    return f"{value // 3600:02d}:{value // 60 % 60:02d}:{value % 60:02d}"


def button(text, callback, primary=False):
    control = QPushButton(text)
    if primary:
        control.setObjectName("primary")
    control.clicked.connect(callback)
    return control


def table(headers):
    control = QTableWidget(0, len(headers))
    control.setHorizontalHeaderLabels(headers)
    control.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    control.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    control.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    control.setAlternatingRowColors(True)
    control.verticalHeader().hide()
    control.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    control.horizontalHeader().setStretchLastSection(True)
    return control


class MainWindow(QMainWindow):
    def __init__(self, store=None):
        super().__init__()
        self.store = store or Store()
        self.options = self.store.settings()
        self.job_options = Options.from_dict(self.options.public_dict())
        self.manager = Manager(self.store, self)
        self.background = []
        self.analysis_worker = None
        self.info = None
        self.analyzed_url = None
        self.extractors = []
        self.setWindowTitle("DownloaderVideo")
        self.resize(1280, 850)
        self.setMinimumSize(980, 680)
        central = QWidget()
        self.setCentralWidget(central)
        shell = QHBoxLayout(central)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(214)
        nav = QVBoxLayout(sidebar)
        nav.setContentsMargins(18, 28, 18, 22)
        brand = QLabel("Downloader\nVideo")
        brand.setObjectName("brand")
        nav.addWidget(brand)
        caption = QLabel("SEUS LINKS. SEUS ARQUIVOS.")
        caption.setObjectName("muted")
        caption.setStyleSheet("font-size: 9px; padding: 12px 0 24px;")
        nav.addWidget(caption)
        self.pages = QStackedWidget()
        self.nav_buttons = []
        for index, label in enumerate(["Novo download", "Fila e histórico", "Configurações", "Sobre e ferramentas"]):
            item = button(label, lambda checked=False, i=index: self.navigate(i))
            item.setObjectName("nav")
            item.setCheckable(True)
            nav.addWidget(item)
            self.nav_buttons.append(item)
        nav.addStretch()
        footer = QLabel(f"v{__version__}  •  yt-dlp + FFmpeg\nArquivos no seu computador")
        footer.setObjectName("muted")
        footer.setWordWrap(True)
        nav.addWidget(footer)
        shell.addWidget(sidebar)
        shell.addWidget(self.pages, 1)
        self.make_new()
        self.make_queue()
        self.make_settings()
        self.make_about()
        self.navigate(0)
        self.manager.changed.connect(self.refresh_queue)
        self.refresh_queue()
        self.statusBar().showMessage("Pronto. Cole um link para consultar as opções reais da mídia.")
        self.call({"action": "about", "options": self.options.public_dict()}, self.receive_about)

    def page(self, title, subtitle):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 22)
        layout.setSpacing(15)
        heading = QLabel(title)
        heading.setObjectName("heading")
        layout.addWidget(heading)
        description = QLabel(subtitle)
        description.setObjectName("muted")
        description.setWordWrap(True)
        layout.addWidget(description)
        self.pages.addWidget(page)
        return layout

    def navigate(self, index):
        self.pages.setCurrentIndex(index)
        for i, item in enumerate(self.nav_buttons):
            item.setChecked(i == index)

    def fail(self, message):
        QMessageBox.warning(self, "Não foi possível concluir", str(message))

    def call(self, request, callback, on_end=None):
        worker = Worker(request, self)
        self.background.append(worker)
        def event(value):
            if value["type"] == "result":
                callback(value["result"])
        def ended(ok, message):
            if worker in self.background:
                self.background.remove(worker)
            if on_end:
                on_end(ok, message)
            elif not ok and not worker.cancelled:
                self.fail(message)
            worker.deleteLater()
        worker.event.connect(event)
        worker.ended.connect(ended)
        worker.start()
        return worker

    def make_new(self):
        layout = self.page("Um novo download", "Analise a mídia, escolha um formato disponível e envie para a fila.")
        self.urls = QPlainTextEdit()
        self.urls.setPlaceholderText("Cole um ou mais links HTTP/HTTPS, um por linha…")
        self.urls.setMaximumHeight(85)
        self.urls.textChanged.connect(self.invalidate_analysis)
        layout.addWidget(self.urls)
        actions = QHBoxLayout()
        self.analyze_button = button("Analisar primeiro link", self.start_analysis, True)
        actions.addWidget(self.analyze_button)
        self.cancel_analysis_button = button("Cancelar análise", self.cancel_analysis)
        self.cancel_analysis_button.setEnabled(False)
        actions.addWidget(self.cancel_analysis_button)
        actions.addStretch()
        actions.addWidget(button("Opções deste download…", self.edit_job_options))
        layout.addLayout(actions)
        self.media_title = QLabel("Nenhuma mídia analisada")
        self.media_title.setStyleSheet("font-size: 18px; font-weight: 600;")
        self.media_title.setTextFormat(Qt.TextFormat.PlainText)
        self.media_title.setWordWrap(True)
        layout.addWidget(self.media_title)
        details = QHBoxLayout()
        self.thumbnail = QLabel()
        self.thumbnail.setFixedSize(176, 99)
        self.thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail.setText("Prévia da mídia")
        details.addWidget(self.thumbnail)
        self.media_detail = QLabel("Título, duração, faixas e legendas serão consultados no yt-dlp.")
        self.media_detail.setTextFormat(Qt.TextFormat.PlainText)
        self.media_detail.setWordWrap(True)
        details.addWidget(self.media_detail, 1)
        layout.addLayout(details)
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Filtrar formatos"))
        self.format_filter = QLineEdit()
        self.format_filter.setPlaceholderText("Resolução, codec, idioma ou contêiner…")
        self.format_filter.textChanged.connect(self.filter_formats)
        filter_row.addWidget(self.format_filter)
        self.audio_track = QComboBox()
        self.audio_track.addItem("Áudio automático", "")
        filter_row.addWidget(self.audio_track)
        layout.addLayout(filter_row)
        self.formats = table(["ID", "Contêiner", "Resolução", "Vídeo", "Áudio", "Idioma", "Tamanho / estimativa", "Detalhe"])
        layout.addWidget(self.formats, 1)
        self.playlist_entries = QListWidget()
        self.playlist_entries.setMaximumHeight(110)
        self.playlist_entries.hide()
        self.playlist_entries.itemDoubleClicked.connect(self.analyze_playlist_item)
        layout.addWidget(self.playlist_entries)
        bottom = QHBoxLayout()
        self.selection_note = QLabel("Sem seleção: melhor qualidade disponível. Mesclagem e conversão exigem FFmpeg.")
        self.selection_note.setObjectName("muted")
        self.selection_note.setWordWrap(True)
        bottom.addWidget(self.selection_note, 1)
        bottom.addWidget(button("Usar automático", self.formats.clearSelection))
        bottom.addWidget(button("Adicionar à fila", self.enqueue, True))
        layout.addLayout(bottom)

    def invalidate_analysis(self):
        self.info = None
        self.analyzed_url = None
        self.formats.setRowCount(0)
        self.audio_track.clear()
        self.audio_track.addItem("Áudio automático", "")
        self.playlist_entries.hide()
        self.media_title.setText("Nenhuma mídia analisada")
        self.media_detail.setText("Analise o link para consultar formatos disponíveis.")
        self.thumbnail.clear()

    def get_urls(self):
        urls = [validate_url(u.strip()) for u in self.urls.toPlainText().splitlines() if u.strip()]
        if not urls:
            raise ValueError("Cole pelo menos um link.")
        return urls

    def start_analysis(self):
        try:
            url = self.get_urls()[0]
            options = self.job_options.validate()
        except ValueError as exc:
            self.fail(exc)
            return
        self.cancel_analysis()
        self.analyze_button.setEnabled(False)
        self.cancel_analysis_button.setEnabled(True)
        self.media_title.setText("Analisando…")
        self.urls.setReadOnly(True)
        def ended(ok, message):
            self.analysis_worker = None
            self.analyze_button.setEnabled(True)
            self.cancel_analysis_button.setEnabled(False)
            self.urls.setReadOnly(False)
            if not ok:
                self.media_title.setText("Análise cancelada ou indisponível")
                self.media_detail.setText(message)
        self.analysis_worker = self.call({"action": "analyze", "url": url, "options": options.public_dict()}, lambda result: self.show_analysis(url, result), ended)

    def cancel_analysis(self):
        if self.analysis_worker:
            self.analysis_worker.cancel()

    def show_analysis(self, url, info):
        self.info = info
        self.analyzed_url = url
        self.formats.setRowCount(0)
        self.audio_track.clear()
        self.audio_track.addItem("Áudio automático", "")
        self.playlist_entries.clear()
        self.playlist_entries.setVisible(info.get("playlist", False))
        self.media_title.setText(info.get("title") or "Mídia sem título")
        if info.get("playlist"):
            self.media_detail.setText(f"{info.get('count', 0)} itens consultados • {info.get('extractor', '')}\nDuplo clique em um item para analisar seus formatos. Para baixar a coleção, mantenha o link e habilite playlists nas opções.")
            for entry in info.get("entries", []):
                self.playlist_entries.addItem(entry.get("title") or entry.get("id") or "Item")
            return
        subtitles = ", ".join((info.get("subtitles") or {}).keys()) or "nenhuma"
        automatic = ", ".join((info.get("automatic_captions") or {}).keys()) or "nenhuma"
        self.media_detail.setText(f"{info.get('channel') or info.get('uploader') or 'Autor não informado'} • {info.get('extractor', '')} • {duration(info.get('duration'))}\nLegendas: {subtitles}\nAutomáticas: {automatic}\nCapítulos: {len(info.get('chapters') or [])}")
        for index, f in enumerate(info.get("formats", [])):
            self.formats.insertRow(index)
            resolution = f"{f['width']}×{f['height']}" if f.get("height") else ("Áudio" if f.get("vcodec") == "none" else "Não informado")
            values = [f.get("format_id"), f.get("ext"), resolution, f.get("vcodec"), f.get("acodec"), f.get("language"), bytes_text(f.get("filesize") or f.get("filesize_approx")), f.get("format_note")]
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value or "—"))
                self.formats.setItem(index, col, item)
            self.formats.item(index, 0).setData(Qt.ItemDataRole.UserRole, f)
            if f.get("vcodec") == "none" and f.get("acodec") not in {None, "none"}:
                self.audio_track.addItem(f"{f.get('language') or 'Áudio'} • {f['format_id']} • {f.get('acodec')}", f["format_id"])
        if info.get("thumbnail"):
            def preview(encoded):
                if self.analyzed_url == url:
                    pixmap = QPixmap()
                    pixmap.loadFromData(base64.b64decode(encoded))
                    self.thumbnail.setPixmap(pixmap.scaled(176, 99, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self.call({"action": "thumbnail", "url": info["thumbnail"]}, preview, lambda ok, message: None)
        self.filter_formats()

    def filter_formats(self):
        text = self.format_filter.text().casefold()
        for row in range(self.formats.rowCount()):
            self.formats.setRowHidden(row, text not in " ".join(self.formats.item(row, col).text() for col in range(self.formats.columnCount())).casefold())

    def analyze_playlist_item(self, item):
        entry = self.info["entries"][self.playlist_entries.row(item)]
        url = entry.get("webpage_url") or entry.get("url")
        try:
            url = validate_url(url or "")
        except ValueError:
            self.fail("Este item não fornece um link HTTP direto. Use o download da playlist.")
            return
        self.urls.setPlainText(url)
        self.start_analysis()

    def edit_job_options(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Opções deste download")
        dialog.resize(780, 640)
        layout = QVBoxLayout(dialog)
        form = OptionsForm(self.job_options)
        layout.addWidget(form)
        form.controls["concurrent"].setEnabled(False)
        form.controls["concurrent"].setToolTip("Este limite é global. Altere-o em Configurações.")
        if self.info and not self.info.get("playlist"):
            available = {
                "subtitles": bool(self.info.get("subtitles")),
                "automatic_subtitles": bool(self.info.get("automatic_captions")),
                "split_chapters": bool(self.info.get("chapters")),
                "thumbnail": bool(self.info.get("thumbnail")),
                "embed_thumbnail": bool(self.info.get("thumbnail")),
            }
            for name, supported in available.items():
                form.controls[name].setEnabled(supported)
                if not supported:
                    form.controls[name].setChecked(False)
                    form.controls[name].setToolTip("Não disponível na análise desta mídia.")
            if not (available["subtitles"] or available["automatic_subtitles"]):
                form.controls["embed_subtitles"].setChecked(False)
                form.controls["embed_subtitles"].setEnabled(False)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        def save():
            try:
                self.job_options = form.value()
                dialog.accept()
            except ValueError as exc:
                self.fail(exc)
        buttons.accepted.connect(save)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()

    def enqueue(self):
        try:
            urls = self.get_urls()
            options = Options.from_dict(self.job_options.public_dict())
            rows = self.formats.selectionModel().selectedRows()
            if rows:
                if len(urls) != 1 or urls[0] != self.analyzed_url:
                    raise ValueError("A seleção de formato pertence apenas ao link analisado. Use automático para múltiplos links.")
                f = self.formats.item(rows[0].row(), 0).data(Qt.ItemDataRole.UserRole)
                if f.get("vcodec") == "none" and options.mode != "audio":
                    raise ValueError("Esta faixa contém apenas áudio. Escolha Extrair áudio nas opções.")
                if options.mode == "audio" and f.get("acodec") == "none":
                    raise ValueError("Este formato não contém áudio. Escolha uma faixa de áudio.")
                options.format_id = f["format_id"]
                if f.get("vcodec") != "none" and f.get("acodec") == "none":
                    options.format_id += "+" + (self.audio_track.currentData() or "bestaudio")
            elif self.audio_track.currentData():
                options.format_id = "bestvideo+" + self.audio_track.currentData() if options.mode == "video" else self.audio_track.currentData()
            self.manager.add(urls, options, (self.info or {}).get("title", ""))
            self.navigate(1)
        except ValueError as exc:
            self.fail(exc)

    def make_queue(self):
        layout = self.page("Fila e histórico", "Acompanhe a transferência e o processamento. Arquivos parciais são preservados para retomada.")
        self.queue_summary = QLabel()
        layout.addWidget(self.queue_summary)
        self.queue_filter = QComboBox()
        self.queue_filter.addItems(["Todas as tarefas", "Em andamento", "Histórico", "Falhas / interrompidas"])
        self.queue_filter.currentIndexChanged.connect(self.refresh_queue)
        layout.addWidget(self.queue_filter)
        self.queue_table = table(["Título", "Estado", "Progresso do arquivo", "Transferido / total", "Velocidade", "Restante"])
        self.queue_table.itemSelectionChanged.connect(self.show_job_detail)
        layout.addWidget(self.queue_table, 1)
        self.job_detail = QPlainTextEdit()
        self.job_detail.setReadOnly(True)
        self.job_detail.setMaximumHeight(115)
        layout.addWidget(self.job_detail)
        row = QHBoxLayout()
        row.addWidget(button("Cancelar", self.cancel_selected))
        row.addWidget(button("Repetir / retomar", self.retry_selected))
        row.addWidget(button("Abrir arquivo", self.open_file))
        row.addWidget(button("Abrir pasta", self.open_folder))
        row.addStretch()
        row.addWidget(button("Limpar histórico", self.clear_history))
        layout.addLayout(row)

    def selected_job(self):
        row = self.queue_table.currentRow()
        item = self.queue_table.item(row, 0) if row >= 0 else None
        return self.manager.get(item.data(Qt.ItemDataRole.UserRole)) if item else None

    def refresh_queue(self):
        selected = self.selected_job()
        selected_id = selected["id"] if selected else None
        self.queue_table.blockSignals(True)
        self.queue_table.setRowCount(0)
        choice = self.queue_filter.currentIndex()
        jobs = self.manager.jobs
        for job in jobs:
            if choice == 1 and job["state"] not in ACTIVE:
                continue
            if choice == 2 and job["state"] in ACTIVE:
                continue
            if choice == 3 and job["state"] not in {"error", "interrupted"}:
                continue
            row = self.queue_table.rowCount()
            self.queue_table.insertRow(row)
            percent = min(100, job.get("downloaded", 0) / job["total"] * 100) if job.get("total") else None
            progress = "Finalizado" if job["state"] == "completed" else (f"{percent:.1f}%" if percent is not None else "Indeterminado")
            values = [job["title"], STATES[job["state"]], progress, f"{bytes_text(job.get('downloaded', 0))} / {bytes_text(job.get('total'))}", bytes_text(job["speed"]) + "/s" if job.get("speed") else "—", duration(job.get("eta"))]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                self.queue_table.setItem(row, col, item)
            self.queue_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, job["id"])
            if job["id"] == selected_id:
                self.queue_table.selectRow(row)
        self.queue_table.blockSignals(False)
        active = sum(j["state"] in ACTIVE for j in jobs)
        completed = sum(j["state"] == "completed" for j in jobs)
        self.queue_summary.setText(f"{active} em andamento   •   {completed} concluídos   •   Limite: {self.manager.limit} downloads simultâneos")
        self.show_job_detail()

    def show_job_detail(self):
        job = self.selected_job()
        if job:
            self.job_detail.setPlainText(f"{job['url']}\n{job.get('message', '')}\nDestino: {job['options']['destination']}\n" + "\n".join(job.get("files", [])))
        else:
            self.job_detail.setPlainText("Selecione uma tarefa para ver os detalhes.")

    def cancel_selected(self):
        job = self.selected_job()
        if job:
            self.manager.cancel(job["id"])

    def retry_selected(self):
        job = self.selected_job()
        if job:
            self.manager.retry(job["id"])

    def open_file(self):
        job = self.selected_job()
        if job:
            files = [p for p in job.get("files", []) if Path(p).is_file()]
            if not files:
                self.fail("Nenhum arquivo final disponível para esta tarefa.")
            else:
                QDesktopServices.openUrl(QUrl.fromLocalFile(files[-1]))

    def open_folder(self):
        job = self.selected_job()
        if job:
            path = Path(job["options"]["destination"]).expanduser()
            if path.is_dir():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
            else:
                self.fail("A pasta de destino ainda não existe.")

    def clear_history(self):
        if QMessageBox.question(self, "Limpar histórico", "Remover registros de tarefas encerradas? Os arquivos serão preservados.") == QMessageBox.StandardButton.Yes:
            self.manager.clear_history()

    def make_settings(self):
        layout = self.page("Configurações", "Preferências globais aplicadas às novas tarefas. Tarefas existentes mantêm suas próprias opções.")
        self.settings_form = OptionsForm(self.options)
        layout.addWidget(self.settings_form, 1)
        row = QHBoxLayout()
        row.addWidget(button("Restaurar padrões", lambda: self.settings_form.load(Options())))
        row.addStretch()
        row.addWidget(button("Salvar preferências", self.save_settings, True))
        layout.addLayout(row)

    def save_settings(self):
        try:
            options = self.settings_form.value()
            self.store.save_settings(options)
            self.options = options
            self.job_options = Options.from_dict(options.public_dict())
            self.manager.limit = options.concurrent
            self.manager.pump()
            self.statusBar().showMessage("Preferências salvas. Novos downloads usarão estes valores.", 10000)
            self.call({"action": "about", "options": options.public_dict()}, self.receive_about)
        except ValueError as exc:
            self.fail(exc)

    def make_about(self):
        layout = self.page("Sobre e ferramentas", "Capacidades consultadas na instalação atual. Um extrator não garante acesso a todo conteúdo da plataforma.")
        tabs = QTabWidget()
        layout.addWidget(tabs)
        sites = QWidget()
        box = QVBoxLayout(sites)
        self.extractor_count = QLabel("Carregando extratores instalados…")
        box.addWidget(self.extractor_count)
        search = QLineEdit()
        search.setPlaceholderText("Pesquisar sites e extratores…")
        search.textChanged.connect(self.search_extractors)
        self.extractor_search = search
        box.addWidget(search)
        self.extractor_list = QListWidget()
        box.addWidget(self.extractor_list)
        tabs.addTab(sites, "Sites")
        capabilities = QTextBrowser()
        capabilities.setOpenExternalLinks(True)
        capabilities.setHtml("""<h2>Formatos e recursos</h2><p>A tabela de análise mostra somente formatos oferecidos pelo conteúdo: contêiner, resolução, codecs e faixas. Não há uma lista fixa de resoluções disponíveis.</p><h3>Saída e conversão</h3><p>Mesclagem em MKV, MP4 ou WebM usa FFmpeg e depende da compatibilidade dos codecs. A seleção de contêiner não recodifica vídeo; para isso, use Recodificar vídeo nas opções (mais lento). Extração de áudio: MP3, M4A, Opus, FLAC, WAV ou melhor formato original. A qualidade em kb/s aplica-se à codificação com perdas.</p><h3>Legendas e miniaturas</h3><p>Idiomas reais aparecem na análise. O yt-dlp pode obter legendas como SRT, VTT, ASS e TTML conforme a plataforma. Miniaturas podem ser JPEG, PNG ou WebP; incorporação e conversão dependem do formato de saída. Uma opção solicitada pode não existir para a mídia; avisos reais aparecem na tarefa.</p><h3>Gerenciamento</h3><p>Fila simultânea, cancelamento de processos e FFmpeg, tentativas, retomada de arquivos parciais quando o servidor permite, histórico persistente e recuperação manual após interrupções. O progresso é por arquivo/faixa, e reinicia em uma nova faixa ou item de playlist. Conclusão ocorre após o término de todo pós-processamento.</p><h3>Avançado</h3><p>Metadados, capítulos existentes, divisão de capítulos, intervalos (corte pode depender de keyframes), legendas, miniaturas, modelos de nomes, seleção de itens e opções validadas da API. Cookies Netscape são lidos de um arquivo escolhido pelo usuário; não são importados de navegadores nem armazenados no banco.</p><h3>Limitações de acesso</h3><p>Não há suporte para remover DRM ou ultrapassar permissões de acesso. Plataformas podem exigir cookies, runtime JavaScript, sessão válida ou acesso regional. Playlists são listadas sem analisar cada mídia; use duplo clique para consultar um item. Análises de canais muito grandes podem demorar: limite os itens nas opções ou cancele.</p>""")
        tabs.addTab(capabilities, "Formatos e recursos")
        technical = QWidget()
        box = QVBoxLayout(technical)
        self.dependencies_label = QLabel("Consultando dependências…")
        self.dependencies_label.setTextFormat(Qt.TextFormat.PlainText)
        self.dependencies_label.setWordWrap(True)
        box.addWidget(self.dependencies_label)
        box.addWidget(button("Verificar atualizações", self.check_updates))
        self.updates_label = QLabel("Atualizações são verificadas no PyPI e nos repositórios oficiais do GitHub. Instalação manual mantém os downloads e o pacote distribuído protegidos.")
        self.updates_label.setTextFormat(Qt.TextFormat.PlainText)
        self.updates_label.setWordWrap(True)
        box.addWidget(self.updates_label)
        for label, url in [("Versões do aplicativo", "https://github.com/Vitor456-arch/DownloaderVideo/releases"), ("Versões oficiais do yt-dlp", "https://github.com/yt-dlp/yt-dlp/releases"), ("Obter FFmpeg", "https://ffmpeg.org/download.html")]:
            box.addWidget(button(label, lambda checked=False, u=url: QDesktopServices.openUrl(QUrl(u))))
        credits = QTextBrowser()
        credits.setOpenExternalLinks(True)
        credits.setHtml(f"<h3>DownloaderVideo {__version__}</h3><p>Aplicativo: licença MIT. <a href='https://github.com/yt-dlp/yt-dlp'>yt-dlp</a>: Unlicense (distribuições podem conter componentes com outras licenças). <a href='https://www.qt.io/licensing/'>PySide6 / Qt</a>: LGPLv3 ou comercial. FFmpeg: LGPL/GPL conforme a compilação. Consulte THIRD_PARTY_NOTICES.md e os textos de licença no pacote distribuído.</p><p>As atualizações do aplicativo são distribuídas como novos instaladores. Para atualizar a ferramenta na versão em código-fonte: feche o aplicativo e use o comando documentado no README. A versão empacotada requer novo build. Não substituímos executáveis automaticamente.</p>")
        box.addWidget(credits, 1)
        tabs.addTab(technical, "Versões e créditos")

    def receive_about(self, result):
        self.extractors = result["extractors"]
        self.search_extractors(self.extractor_search.text())
        deps = result["dependencies"]
        self.dependencies_label.setText(f"Aplicativo {__version__}\nyt-dlp {deps['yt_dlp']}\nPython {deps['python']}\n{deps['ffmpeg']}\n{deps['ffprobe']}\nDados: {self.store.db.execute('PRAGMA database_list').fetchone()[2]}")

    def search_extractors(self, text):
        values = [x for x in self.extractors if text.casefold() in x.casefold()]
        self.extractor_list.clear()
        self.extractor_list.addItems(values)
        self.extractor_count.setText(f"{len(self.extractors)} extratores instalados • {len(values)} encontrados")

    def check_updates(self):
        self.updates_label.setText("Consultando PyPI e repositórios oficiais…")
        def result(value):
            self.updates_label.setText(f"yt-dlp instalado: {value['installed']} • Última versão no PyPI: {value['latest']}\nAplicativo: {value['application_status']}\nFFmpeg: {value['ffmpeg_status']}\nAtualize com o aplicativo fechado; a versão empacotada requer um novo instalador.")
        def ended(ok, message):
            if not ok:
                self.updates_label.setText("Não foi possível verificar: " + message)
        self.call({"action": "updates"}, result, ended)

    def closeEvent(self, event):
        if self.manager.workers or any(j["state"] == "queued" for j in self.manager.jobs):
            if QMessageBox.question(self, "Encerrar", "Interromper tarefas e fechar? Será possível retomá-las no próximo início.") != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
        self.manager.shutdown()
        for worker in list(self.background):
            worker.cancel()
            worker.process.waitForFinished(3000)
            worker.force_stop()
            worker.process.waitForFinished(1000)
        self.store.close()
        event.accept()


def main():
    if "--worker" in sys.argv:
        from .worker import run
        return run()
    application = QApplication(sys.argv)
    from .diagnostics import configure, safe_message
    logger = configure()
    lock = QLockFile(str(data_dir() / "application.lock"))
    if not lock.tryLock(100):
        QMessageBox.information(None, "DownloaderVideo", "O aplicativo já está aberto nesta conta.")
        return 1
    def handle_error(kind, value, traceback):
        logger.error("Unhandled %s: %s", kind.__name__, safe_message(value))
        QMessageBox.critical(None, "Erro inesperado", safe_message(value))
    sys.excepthook = handle_error
    logger.info("Application started version=%s", __version__)
    application.setApplicationName("DownloaderVideo")
    application.setOrganizationName("DownloaderVideo")
    application.setStyle("Fusion")
    application.setStyleSheet(STYLE)
    window = MainWindow()
    window.show()
    return application.exec()
