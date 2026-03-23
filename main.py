import os
import re
import shutil
import threading
from pathlib import Path
from tkinter import DoubleVar, Menu, Tk, StringVar, Text, filedialog, messagebox
from tkinter import ttk

try:
    from yt_dlp import YoutubeDL
except ImportError:
    YoutubeDL = None


APP_BG = "#f4efe6"
PANEL_BG = "#fffaf2"
ACCENT = "#c46f2d"
ACCENT_DARK = "#8c4718"
TEXT = "#2d2117"
MUTED = "#6f5a48"
BORDER = "#e8d9c7"


class YouTubeDownloaderApp:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title("YouTube Video Downloader")
        self.root.geometry("760x720")
        self.root.minsize(760, 720)
        self.root.maxsize(760, 720)
        self.root.resizable(False, False)
        self.root.configure(bg=APP_BG)

        self.url_var = StringVar()
        self.path_var = StringVar(value=str(Path.home() / "Downloads"))
        self.filename_var = StringVar()
        self.quality_var = StringVar()
        self.format_var = StringVar(value="mp4")
        self.status_var = StringVar(value="Вставьте ссылку на YouTube и нажмите «Загрузить качества».")
        self.video_title_var = StringVar(value="Видео не выбрано")
        self.progress_var = DoubleVar(value=0)
        self.progress_text_var = StringVar(value="0%")

        self.available_resolutions: list[str] = []
        self.video_options: dict[str, dict[str, str]] = {"mp4": {}, "webm": {}}
        self.video_info: dict | None = None
        self.is_busy = False
        self.ffmpeg_available = bool(shutil.which("ffmpeg"))
        self.js_runtime = self._detect_js_runtime()

        self._configure_styles()
        self._build_ui()

    def _configure_styles(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("App.TFrame", background=APP_BG)
        style.configure("Card.TFrame", background=PANEL_BG, borderwidth=1, relief="solid")
        style.configure(
            "Title.TLabel",
            background=APP_BG,
            foreground=TEXT,
            font=("Segoe UI Semibold", 22),
        )
        style.configure(
            "Subtitle.TLabel",
            background=APP_BG,
            foreground=MUTED,
            font=("Segoe UI", 10),
        )
        style.configure(
            "CardTitle.TLabel",
            background=PANEL_BG,
            foreground=TEXT,
            font=("Segoe UI Semibold", 11),
        )
        style.configure(
            "Body.TLabel",
            background=PANEL_BG,
            foreground=TEXT,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Status.TLabel",
            background=APP_BG,
            foreground=ACCENT_DARK,
            font=("Segoe UI Semibold", 10),
        )
        style.configure(
            "Accent.TButton",
            font=("Segoe UI Semibold", 10),
            padding=(16, 10),
            background=ACCENT,
            foreground="white",
            borderwidth=0,
        )
        style.map(
            "Accent.TButton",
            background=[("active", ACCENT_DARK), ("disabled", "#d1a37f")],
            foreground=[("disabled", "#fff7f0")],
        )
        style.configure(
            "Secondary.TButton",
            font=("Segoe UI", 10),
            padding=(14, 10),
            background="#f0e1cf",
            foreground=TEXT,
            borderwidth=0,
        )
        style.map(
            "Secondary.TButton",
            background=[("active", "#e6d0b8"), ("disabled", "#f2ebe2")],
            foreground=[("disabled", "#9a8b7f")],
        )
        style.configure(
            "TEntry",
            padding=8,
            fieldbackground="white",
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            foreground=TEXT,
        )
        style.configure(
            "TCombobox",
            padding=8,
            fieldbackground="white",
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            foreground=TEXT,
        )
        style.configure(
            "Downloader.Horizontal.TProgressbar",
            troughcolor="#eadfce",
            background=ACCENT,
            darkcolor=ACCENT,
            lightcolor="#d8894e",
            bordercolor=BORDER,
            thickness=14,
        )

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, style="App.TFrame", padding=22)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)

        ttk.Label(outer, text="Загрузка видео с YouTube", style="Title.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            outer,
            text="Выберите ссылку, качество, формат и папку. Окно специально зафиксировано по размеру.",
            style="Subtitle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 16))

        card = ttk.Frame(outer, style="Card.TFrame", padding=18)
        card.grid(row=2, column=0, sticky="nsew")
        card.columnconfigure(0, weight=1)
        card.columnconfigure(1, weight=0)
        card.columnconfigure(2, weight=0)

        ttk.Label(card, text="Ссылка на видео", style="CardTitle.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w"
        )
        url_entry = ttk.Entry(card, textvariable=self.url_var, width=60)
        url_entry.grid(row=1, column=0, sticky="ew", pady=(8, 10), padx=(0, 12))
        self._enable_entry_shortcuts(url_entry)
        ttk.Button(card, text="Вставить", style="Secondary.TButton", command=lambda: self._paste_into_entry(url_entry)).grid(
            row=1, column=1, sticky="ew", pady=(8, 10), padx=(0, 12)
        )
        ttk.Button(card, text="Очистить", style="Secondary.TButton", command=self.clear_url).grid(
            row=1, column=2, sticky="ew", pady=(8, 10)
        )
        ttk.Button(card, text="Загрузить качества", style="Accent.TButton", command=self.load_formats).grid(
            row=2, column=0, columnspan=3, sticky="ew", pady=(0, 12)
        )

        ttk.Label(card, text="Название", style="CardTitle.TLabel").grid(
            row=3, column=0, columnspan=3, sticky="w", pady=(0, 0)
        )
        ttk.Label(card, textvariable=self.video_title_var, style="Body.TLabel", wraplength=660).grid(
            row=4, column=0, columnspan=3, sticky="w", pady=(8, 10)
        )

        ttk.Label(card, text="Имя файла (необязательно)", style="CardTitle.TLabel").grid(
            row=5, column=0, columnspan=3, sticky="w"
        )
        filename_entry = ttk.Entry(card, textvariable=self.filename_var)
        filename_entry.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(8, 14))
        self._enable_entry_shortcuts(filename_entry)

        ttk.Label(card, text="Качество", style="CardTitle.TLabel").grid(row=7, column=0, sticky="w")
        ttk.Label(card, text="Формат", style="CardTitle.TLabel").grid(row=7, column=1, columnspan=2, sticky="w")

        self.quality_combo = ttk.Combobox(
            card,
            textvariable=self.quality_var,
            state="readonly",
            values=[],
        )
        self.quality_combo.grid(row=8, column=0, sticky="ew", pady=(8, 14), padx=(0, 12))

        self.format_combo = ttk.Combobox(
            card,
            textvariable=self.format_var,
            state="readonly",
            values=["mp4", "webm", "m4a", "mp3"],
        )
        self.format_combo.grid(row=8, column=1, columnspan=2, sticky="ew", pady=(8, 14))
        self.format_combo.bind("<<ComboboxSelected>>", self._on_format_changed)

        ttk.Label(card, text="Папка сохранения", style="CardTitle.TLabel").grid(
            row=9, column=0, columnspan=3, sticky="w"
        )
        path_entry = ttk.Entry(card, textvariable=self.path_var)
        path_entry.grid(row=10, column=0, columnspan=2, sticky="ew", pady=(8, 0), padx=(0, 12))
        self._enable_entry_shortcuts(path_entry)
        ttk.Button(card, text="Выбрать папку", style="Secondary.TButton", command=self.choose_folder).grid(
            row=10, column=2, sticky="ew", pady=(8, 0)
        )

        info = ttk.Frame(outer, style="App.TFrame")
        info.grid(row=3, column=0, sticky="ew", pady=(16, 10))
        info.columnconfigure(0, weight=1)

        ttk.Label(outer, textvariable=self.status_var, style="Status.TLabel", wraplength=700).grid(
            row=4, column=0, sticky="w", pady=(4, 8)
        )

        progress_row = ttk.Frame(outer, style="App.TFrame")
        progress_row.grid(row=5, column=0, sticky="ew", pady=(0, 10))
        progress_row.columnconfigure(0, weight=1)
        progress_row.columnconfigure(1, weight=0)

        self.progress_bar = ttk.Progressbar(
            progress_row,
            variable=self.progress_var,
            maximum=100,
            mode="determinate",
            style="Downloader.Horizontal.TProgressbar",
        )
        self.progress_bar.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        ttk.Label(progress_row, textvariable=self.progress_text_var, style="Status.TLabel").grid(
            row=0, column=1, sticky="e"
        )

        ttk.Button(outer, text="Скачать", style="Accent.TButton", command=self.download_video).grid(
            row=6, column=0, sticky="ew"
        )

        log_card = ttk.Frame(outer, style="Card.TFrame", padding=14)
        log_card.grid(row=7, column=0, sticky="nsew", pady=(16, 0))
        log_card.columnconfigure(0, weight=1)
        outer.rowconfigure(7, weight=1)

        ttk.Label(log_card, text="Подсказки", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")

        self.hint_box = Text(
            log_card,
            height=8,
            wrap="word",
            bg=PANEL_BG,
            fg=TEXT,
            font=("Segoe UI", 10),
            relief="flat",
            padx=4,
            pady=8,
        )
        self.hint_box.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        self.hint_box.insert(
            "1.0",
            "1. Нажмите «Загрузить качества», чтобы получить список реальных разрешений для ссылки.\n"
            "2. Если ffmpeg не установлен, приложение скачивает только готовые объединенные потоки без склейки.\n"
            "3. Форматы mp3 и m4a требуют ffmpeg, иначе конвертация аудио не сработает.\n"
            "4. Если в системе нет node или deno, YouTube может не показать часть форматов.\n"
            "5. Если ссылка ведет на плейлист, приложение скачает только первое видео.",
        )
        self.hint_box.configure(state="disabled")

    def _enable_entry_shortcuts(self, entry: ttk.Entry) -> None:
        context_menu = Menu(self.root, tearoff=False)
        context_menu.add_command(label="Вырезать", command=lambda: self._cut_entry(entry))
        context_menu.add_command(label="Копировать", command=lambda: self._copy_entry(entry))
        context_menu.add_command(label="Вставить", command=lambda: self._paste_into_entry(entry))
        context_menu.add_command(label="Выделить всё", command=lambda: self._select_all(entry))

        entry.bind("<Control-v>", lambda event: self._paste_into_entry(event.widget))
        entry.bind("<Control-V>", lambda event: self._paste_into_entry(event.widget))
        entry.bind("<Shift-Insert>", lambda event: self._paste_into_entry(event.widget))
        entry.bind("<Button-3>", lambda event: self._show_context_menu(context_menu, event))
        entry.bind("<ButtonRelease-3>", lambda event: "break")

    def _show_context_menu(self, menu: Menu, event) -> str:
        menu.tk_popup(event.x_root, event.y_root)
        return "break"

    def _paste_into_entry(self, widget) -> str:
        try:
            widget.focus_set()
            text = self.root.clipboard_get()
        except Exception:
            return "break"

        try:
            if widget.selection_present():
                start = widget.index("sel.first")
                end = widget.index("sel.last")
                widget.delete(start, end)
                widget.insert(start, text)
            else:
                widget.insert(widget.index("insert"), text)
        except Exception:
            try:
                widget.insert("end", text)
            except Exception:
                pass
        return "break"

    def _copy_entry(self, widget) -> None:
        try:
            widget.focus_set()
            selected = widget.selection_get()
            self.root.clipboard_clear()
            self.root.clipboard_append(selected)
        except Exception:
            pass

    def _cut_entry(self, widget) -> None:
        try:
            self._copy_entry(widget)
            start = widget.index("sel.first")
            end = widget.index("sel.last")
            widget.delete(start, end)
        except Exception:
            pass

    def _select_all(self, widget) -> None:
        widget.focus_set()
        widget.selection_range(0, "end")
        widget.icursor("end")

    def _detect_js_runtime(self) -> str | None:
        for runtime in ("node", "deno", "bun"):
            if shutil.which(runtime):
                return runtime
        return None

    def _base_ydl_opts(self) -> dict:
        opts = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
        }
        if self.js_runtime:
            opts["js_runtimes"] = {self.js_runtime: shutil.which(self.js_runtime)}
        return opts

    def _environment_notice(self) -> str:
        notes = []
        if not self.ffmpeg_available:
            notes.append("ffmpeg не найден")
        if not self.js_runtime:
            notes.append("JS runtime не найден")
        return "; ".join(notes)

    def choose_folder(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.path_var.get() or str(Path.home()))
        if selected:
            self.path_var.set(selected)

    def clear_url(self) -> None:
        self.url_var.set("")

    def _on_format_changed(self, _event=None) -> None:
        if self.format_var.get() in {"mp4", "webm"}:
            self._refresh_quality_choices()
        else:
            self.quality_combo.configure(values=[])
            self.quality_var.set("")

    def set_busy(self, busy: bool) -> None:
        self.is_busy = busy

    def _reset_progress(self) -> None:
        self.progress_var.set(0)
        self.progress_text_var.set("0%")

    def _update_progress(self, percent: float, text: str | None = None) -> None:
        clamped = max(0.0, min(percent, 100.0))
        self.progress_var.set(clamped)
        self.progress_text_var.set(text or f"{clamped:.1f}%")

    def _progress_hook(self, data: dict) -> None:
        status = data.get("status")
        if status == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate")
            downloaded = data.get("downloaded_bytes") or 0
            if total:
                percent = (downloaded / total) * 100
                speed = data.get("speed")
                speed_text = self._format_speed(speed)
                eta_text = self._format_eta(data.get("eta"))
                parts = [f"{percent:.1f}%"]
                if speed_text:
                    parts.append(speed_text)
                if eta_text:
                    parts.append(f"осталось {eta_text}")
                self.root.after(0, self._update_progress, percent, " | ".join(parts))
            else:
                self.root.after(0, self._update_progress, 0, "Скачивание...")
        elif status == "finished":
            self.root.after(0, self._update_progress, 100, "Обработка...")

    def _format_speed(self, speed: float | None) -> str:
        if not speed:
            return ""
        units = ["Б/с", "КБ/с", "МБ/с", "ГБ/с"]
        value = float(speed)
        unit_index = 0
        while value >= 1024 and unit_index < len(units) - 1:
            value /= 1024
            unit_index += 1
        return f"{value:.1f} {units[unit_index]}"

    def _format_eta(self, eta: float | int | None) -> str:
        if eta is None:
            return ""
        seconds = max(0, int(eta))
        minutes, secs = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours:d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:d}:{secs:02d}"

    def _safe_filename(self, value: str) -> str:
        cleaned = re.sub(r'[<>:\"/\\\\|?*]', "", value).strip().rstrip(".")
        return cleaned[:150]

    def load_formats(self) -> None:
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Нужна ссылка", "Введите ссылку на YouTube-видео.")
            return
        if self.is_busy:
            return

        self.set_busy(True)
        self._reset_progress()
        notice = self._environment_notice()
        suffix = f" ({notice})" if notice else ""
        self.status_var.set(f"Получаю список качеств с YouTube...{suffix}")
        self.video_title_var.set("Загрузка информации...")
        self.video_options = {"mp4": {}, "webm": {}}
        self.quality_combo.configure(values=[])
        self.quality_var.set("")

        threading.Thread(target=self._load_formats_worker, args=(url,), daemon=True).start()

    def _load_formats_worker(self, url: str) -> None:
        try:
            if YoutubeDL is None:
                raise RuntimeError("Установите зависимость: python -m pip install -r requirements.txt")
            ydl_opts = self._base_ydl_opts()
            ydl_opts["skip_download"] = True
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            video_options = self._collect_video_options(info)
            if not video_options["mp4"] and not video_options["webm"]:
                raise ValueError("Не удалось найти доступные видео-разрешения для этой ссылки.")

            self.video_info = info
            self.video_options = video_options
            self.root.after(0, self._apply_formats_loaded, info.get("title", "Без названия"))
        except Exception as exc:
            self.root.after(0, self._handle_error, f"Не удалось загрузить качества: {exc}")
        finally:
            self.root.after(0, lambda: self.set_busy(False))

    def _collect_video_options(self, info: dict) -> dict[str, dict[str, str]]:
        options: dict[str, dict[str, str]] = {"mp4": {}, "webm": {}}
        progressive_scores: dict[str, dict[str, float]] = {"mp4": {}, "webm": {}}
        adaptive_heights: dict[str, set[int]] = {"mp4": set(), "webm": set()}

        for fmt in info.get("formats", []):
            if fmt.get("vcodec") == "none":
                continue

            height = fmt.get("height")
            ext = fmt.get("ext")
            if not height or ext not in {"mp4", "webm"}:
                continue

            label = f"{height}p"
            has_audio = fmt.get("acodec") not in {None, "none"}
            score = float(fmt.get("tbr") or fmt.get("filesize") or fmt.get("filesize_approx") or 0)

            if has_audio:
                current_score = progressive_scores[ext].get(label, -1)
                if score >= current_score:
                    progressive_scores[ext][label] = score
                    options[ext][label] = str(fmt["format_id"])
            elif self.ffmpeg_available:
                adaptive_heights[ext].add(height)

        if self.ffmpeg_available:
            for ext, heights in adaptive_heights.items():
                for height in heights:
                    label = f"{height}p"
                    options[ext][label] = self._build_exact_selector(height, ext)

        return {
            "mp4": dict(sorted(options["mp4"].items(), key=lambda item: int(item[0][:-1]), reverse=True)),
            "webm": dict(sorted(options["webm"].items(), key=lambda item: int(item[0][:-1]), reverse=True)),
        }

    def _refresh_quality_choices(self) -> None:
        current_format = self.format_var.get()
        qualities = list(self.video_options.get(current_format, {}).keys())
        self.available_resolutions = qualities
        self.quality_combo.configure(values=qualities)
        if qualities:
            if self.quality_var.get() not in qualities:
                self.quality_var.set(qualities[0])
        else:
            self.quality_var.set("")

    def _apply_formats_loaded(self, title: str) -> None:
        self.video_title_var.set(title)
        if not self.filename_var.get().strip():
            self.filename_var.set(title)
        self._refresh_quality_choices()
        notice = self._environment_notice()
        suffix = f". Ограничения среды: {notice}" if notice else ""
        current_format = self.format_var.get()
        resolutions = self.available_resolutions
        if current_format in {"mp4", "webm"} and not resolutions:
            self.status_var.set(f"Для формата {current_format} доступных качеств не найдено{suffix}")
            return
        self.status_var.set(f"Найдено качеств для {current_format}: {', '.join(resolutions)}{suffix}")

    def download_video(self) -> None:
        url = self.url_var.get().strip()
        save_path = self.path_var.get().strip()
        custom_name = self.filename_var.get().strip()
        selected_quality = self.quality_var.get().strip()
        selected_format = self.format_var.get().strip()

        if not url:
            messagebox.showwarning("Нужна ссылка", "Введите ссылку на YouTube-видео.")
            return
        if not selected_quality and selected_format in {"mp4", "webm"}:
            messagebox.showwarning("Нужно качество", "Сначала загрузите и выберите качество видео.")
            return
        if not save_path:
            messagebox.showwarning("Нужна папка", "Выберите папку для сохранения файла.")
            return
        if selected_format in {"mp3", "m4a"} and not self.ffmpeg_available:
            messagebox.showwarning(
                "Нужен ffmpeg",
                "Для форматов mp3 и m4a нужен ffmpeg. Установите ffmpeg или выберите mp4/webm.",
            )
            return

        os.makedirs(save_path, exist_ok=True)

        if self.is_busy:
            return

        self.set_busy(True)
        self._reset_progress()
        self.status_var.set("Скачивание началось...")
        threading.Thread(
            target=self._download_worker,
            args=(url, save_path, custom_name, selected_quality, selected_format),
            daemon=True,
        ).start()

    def _download_worker(
        self,
        url: str,
        save_path: str,
        custom_name: str,
        quality: str,
        selected_format: str,
    ) -> None:
        try:
            if YoutubeDL is None:
                raise RuntimeError("Установите зависимость: python -m pip install -r requirements.txt")
            ydl_opts = self._base_ydl_opts()
            base_name = self._safe_filename(custom_name) if custom_name else "%(title)s"
            ydl_opts["outtmpl"] = os.path.join(save_path, f"{base_name}.%(ext)s")
            ydl_opts["progress_hooks"] = [self._progress_hook]

            if selected_format in {"mp3", "m4a"}:
                ydl_opts["format"] = "bestaudio/best"
                ydl_opts["postprocessors"] = [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": selected_format,
                        "preferredquality": "192",
                    }
                ]
            else:
                format_selector = self.video_options.get(selected_format, {}).get(quality)
                if not format_selector:
                    raise RuntimeError(
                        f"Для формата {selected_format} качество {quality} сейчас недоступно."
                    )
                ydl_opts["format"] = format_selector
                if self.ffmpeg_available and "+" in format_selector:
                    ydl_opts["merge_output_format"] = selected_format

            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            ffmpeg_state = "найден" if self.ffmpeg_available else "не найден"
            js_state = self.js_runtime or "не найден"
            self.root.after(
                0,
                lambda: self._handle_success(
                    f"Готово. Файл сохранен в {save_path}. ffmpeg: {ffmpeg_state}. JS runtime: {js_state}."
                ),
            )
        except Exception as exc:
            self.root.after(0, self._handle_error, f"Ошибка скачивания: {exc}")
        finally:
            self.root.after(0, lambda: self.set_busy(False))

    def _build_exact_selector(self, height: int, container: str) -> str:
        if container == "mp4":
            return (
                f"bestvideo[height={height}][ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/"
                f"bestvideo[height={height}][ext=mp4][vcodec^=avc1]+bestaudio/"
                f"bestvideo[height={height}][ext=mp4][vcodec^=h264]+bestaudio[ext=m4a]/"
                f"bestvideo[height={height}][ext=mp4][vcodec^=h264]+bestaudio/"
                f"bestvideo[height={height}][ext=mp4]+bestaudio[ext=m4a]/"
                f"bestvideo[height={height}][ext=mp4]+bestaudio/"
                f"best[height={height}][ext=mp4]/best[height={height}]"
            )
        return (
            f"bestvideo[height={height}][ext=webm]+bestaudio[ext=webm]/"
            f"bestvideo[height={height}][ext=webm]+bestaudio/"
            f"best[height={height}][ext=webm]/best[height={height}]"
        )

    def _handle_success(self, text: str) -> None:
        self._update_progress(100, "100%")
        self.status_var.set(text)
        messagebox.showinfo("Скачивание завершено", text)

    def _handle_error(self, text: str) -> None:
        self.status_var.set(text)
        messagebox.showerror("Ошибка", text)


def main() -> None:
    root = Tk()
    YouTubeDownloaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
