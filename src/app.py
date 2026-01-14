import logging
import os
import shutil
import subprocess
import threading
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
from PIL import Image

from config import OUTPUT_DIR, SCENE_NAME, MAX_FIX_ATTEMPTS
from src.generator import CodeGenerator
from src.renderer import ManimRenderer

try:
    from tkvideoplayer import TkinterVideo
except Exception:
    try:
        from tkVideoPlayer import TkinterVideo
    except Exception:
        TkinterVideo = None


logger = logging.getLogger(__name__)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("dark-blue")

        self.title("ЗАПЛАВНЫЙ_AI")
        self.geometry("1100x700")
        self.minsize(980, 620)

        logging.basicConfig(level=logging.INFO)

        self.generator = CodeGenerator()
        self.last_video_path = None
        self.output_dir = Path(OUTPUT_DIR)
        self.output_video_path = None
        self._preview_image = None
        self._preview_source_image = None
        self._preview_image_path = None
        self._progress_percent = 0

        self._translations = {
            "EN": {
                "language": "Language",
                "quality": "Quality",
                "clear": "Clear",
                "generate": "Generate & Render",
                "preview": "Preview",
                "preview_area": "Preview in development",
                "save": "Save Video",
                "open_external": "Open External",
                "prompt_placeholder": "Describe the animation...",
                "prompt_empty": "Prompt is empty.",
                "log_generating": "Generating code...",
                "log_rendering_start": "Code generated, launching Manim...",
                "log_rendered": "Rendered video: {path}",
                "log_cleared": "Cleared.",
                "log_no_video_save": "No rendered video to save.",
                "log_no_video_open": "No rendered video to open.",
                "log_video_not_found": "Rendered video not found.",
                "log_video_saved": "Video saved: {path}",
                "log_opened": "Opened in system player.",
                "log_open_failed": "Failed to open player: {error}",
                "log_error": "Error: {error}",
                "progress": "Progress: {percent}%",
                "progress_error": "Progress: error",
                "paste": "Paste",
                "log_fixing": "Render failed, attempting fix #{attempt}...",
                "log_retry_limit": "Auto-fix stopped after {attempts} attempts.",
            },
            "RU": {
                "language": "Язык",
                "quality": "Качество",
                "clear": "Очистить",
                "generate": "Сгенерировать и рендерить",
                "preview": "Предпросмотр",
                "preview_area": "Предпросмотр пока в разработке",
                "save": "Сохранить видео",
                "open_external": "Открыть внешним плеером",
                "prompt_placeholder": "Опиши анимацию...",
                "prompt_empty": "Промпт пуст.",
                "log_generating": "Генерация кода...",
                "log_rendering_start": "Код сгенерирован, запуск Manim...",
                "log_rendered": "Видео готово: {path}",
                "log_cleared": "Очищено.",
                "log_no_video_save": "Нет видео для сохранения.",
                "log_no_video_open": "Нет видео для открытия.",
                "log_video_not_found": "Видео не найдено.",
                "log_video_saved": "Видео сохранено: {path}",
                "log_opened": "Открыто в системном плеере.",
                "log_open_failed": "Не удалось открыть плеер: {error}",
                "log_error": "Ошибка: {error}",
                "progress": "Прогресс: {percent}%",
                "progress_error": "Прогресс: ошибка",
                "paste": "Вставить",
                "log_fixing": "Рендер провалился, попытка исправления #{attempt}...",
                "log_retry_limit": "Автоисправление остановлено после {attempts} попыток.",
            },
        }
        self.lang_var = ctk.StringVar(value="EN")
        self._prompt_placeholder = self._t("prompt_placeholder")
        self._prompt_placeholder_active = True
        self._prompt_text_color = "white"

        self._setup_layout()
        self._apply_language()
        self._set_action_state(False)

        self.bind_all("<Control-v>", self._on_paste)
        self.bind_all("<Control-V>", self._on_paste)

    def _setup_layout(self):
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=2)
        self.grid_columnconfigure(2, weight=2)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        self.sidebar = ctk.CTkFrame(self, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(5, weight=1)

        title = ctk.CTkLabel(
            self.sidebar,
            text="ЗАПЛАВНЫЙ_AI",
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        title.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        self.language_label = ctk.CTkLabel(self.sidebar, text=self._t("language"))
        self.language_label.grid(row=1, column=0, padx=20, pady=(10, 4), sticky="w")

        self.language_menu = ctk.CTkSegmentedButton(
            self.sidebar,
            values=["EN", "RU"],
            command=self._on_language_change,
            variable=self.lang_var,
        )
        self.language_menu.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")

        self.quality_label = ctk.CTkLabel(self.sidebar, text=self._t("quality"))
        self.quality_label.grid(row=3, column=0, padx=20, pady=(10, 4), sticky="w")

        self.quality_var = ctk.StringVar(value="Medium")
        self.quality_menu = ctk.CTkOptionMenu(
            self.sidebar,
            values=["Low", "Medium", "High"],
            variable=self.quality_var,
        )
        self.quality_menu.grid(row=4, column=0, padx=20, pady=(0, 10), sticky="ew")

        self.clear_button = ctk.CTkButton(
            self.sidebar,
            text=self._t("clear"),
            command=self._on_clear,
        )
        self.clear_button.grid(row=6, column=0, padx=20, pady=(10, 20), sticky="ew")

        self.center = ctk.CTkFrame(self, corner_radius=0)
        self.center.grid(row=0, column=1, sticky="nsew")
        self.center.grid_rowconfigure(3, weight=1)
        self.center.grid_columnconfigure(0, weight=1)

        self.prompt_text = ctk.CTkTextbox(self.center, height=220)
        self.prompt_text.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="nsew")
        self.prompt_text.bind("<FocusIn>", self._on_prompt_focus_in)
        self.prompt_text.bind("<FocusOut>", self._on_prompt_focus_out)
        self.prompt_text.bind("<Control-v>", self._on_paste)
        self.prompt_text.bind("<Control-V>", self._on_paste)
        self.prompt_text.bind("<Shift-Insert>", self._on_paste)
        self._set_prompt_placeholder()

        self.prompt_actions = ctk.CTkFrame(self.center, corner_radius=0, fg_color="transparent")
        self.prompt_actions.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.prompt_actions.grid_columnconfigure(0, weight=1)

        self.paste_button = ctk.CTkButton(
            self.prompt_actions,
            text=self._t("paste"),
            width=120,
            command=self._paste_from_clipboard,
        )
        self.paste_button.grid(row=0, column=0, sticky="w")

        self.generate_button = ctk.CTkButton(
            self.center,
            text=self._t("generate"),
            height=44,
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self._on_generate_render,
        )
        self.generate_button.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")

        self.log_text = ctk.CTkTextbox(self.center, height=200)
        self.log_text.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.log_text.configure(state="disabled")

        self.preview = ctk.CTkFrame(self, corner_radius=0)
        self.preview.grid(row=0, column=2, sticky="nsew")
        self.preview.grid_columnconfigure(0, weight=1)
        self.preview.grid_rowconfigure(1, weight=1)

        self.preview_label = ctk.CTkLabel(
            self.preview,
            text=self._t("preview"),
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.preview_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="n")

        self.preview_area = ctk.CTkFrame(self.preview, height=420)
        self.preview_area.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="nsew")
        self.preview_area.grid_propagate(False)
        self.preview_area.bind("<Configure>", self._on_preview_resize)

        self.preview_surface = ctk.CTkFrame(
            self.preview_area,
            corner_radius=0,
            width=720,
            height=405,
        )
        self.preview_surface.place(relx=0.5, rely=0.5, anchor="center")

        self.video_player = None
        self.preview_image_label = None
        if TkinterVideo is not None:
            self.video_player = TkinterVideo(self.preview_surface, scaled=True)
            self.video_player.pack(expand=True, fill="both")
        else:
            self.preview_image_label = ctk.CTkLabel(
                self.preview_surface,
                text=self._t("preview_area"),
                text_color="gray70",
            )
            self.preview_image_label.pack(expand=True, fill="both")

        self.save_button = ctk.CTkButton(
            self.preview,
            text=self._t("save"),
            command=self._on_save_video,
        )
        self.save_button.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")

        self.open_button = ctk.CTkButton(
            self.preview,
            text=self._t("open_external"),
            command=self._on_open_player,
        )
        self.open_button.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="ew")

        self.footer = ctk.CTkFrame(self, corner_radius=0)
        self.footer.grid(row=1, column=0, columnspan=3, sticky="ew")
        self.footer.grid_columnconfigure(1, weight=1)

        self.progress_label = ctk.CTkLabel(self.footer, text=self._t("progress", percent=0))
        self.progress_label.grid(row=0, column=0, padx=(20, 10), pady=12, sticky="w")

        self.progress_bar = ctk.CTkProgressBar(self.footer)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=0, column=1, padx=(0, 20), pady=12, sticky="ew")

    def _t(self, key, **kwargs):
        text = self._translations.get(self.lang_var.get(), {}).get(key, key)
        try:
            return text.format(**kwargs)
        except Exception:
            return text

    def _on_language_change(self, _value=None):
        self._apply_language()

    def _apply_language(self):
        self.language_label.configure(text=self._t("language"))
        self.quality_label.configure(text=self._t("quality"))
        self.clear_button.configure(text=self._t("clear"))
        self.paste_button.configure(text=self._t("paste"))
        self.generate_button.configure(text=self._t("generate"))
        self.preview_label.configure(text=self._t("preview"))
        self.save_button.configure(text=self._t("save"))
        self.open_button.configure(text=self._t("open_external"))
        self._prompt_placeholder = self._t("prompt_placeholder")
        if self._prompt_placeholder_active:
            self._set_prompt_placeholder()
        if self.video_player is None and self._preview_image is None:
            self._show_preview_placeholder()
        self._set_progress(self._progress_percent)
        self._on_preview_resize()

    def _on_prompt_focus_in(self, _event):
        if self._prompt_placeholder_active:
            self.prompt_text.delete("1.0", "end")
            self.prompt_text.configure(text_color=self._prompt_text_color)
            self._prompt_placeholder_active = False

    def _on_prompt_focus_out(self, _event):
        content = self.prompt_text.get("1.0", "end").strip()
        if not content:
            self._set_prompt_placeholder()

    def _on_paste(self, event):
        self._paste_from_clipboard()
        return "break"

    def _paste_from_clipboard(self):
        if self._prompt_placeholder_active:
            self.prompt_text.delete("1.0", "end")
            self.prompt_text.configure(text_color=self._prompt_text_color)
            self._prompt_placeholder_active = False

        try:
            data = self.clipboard_get()
        except Exception:
            return

        try:
            self.prompt_text.insert("insert", data)
        except Exception:
            return

    def _set_prompt_placeholder(self):
        self.prompt_text.configure(text_color="gray70")
        self.prompt_text.delete("1.0", "end")
        self.prompt_text.insert("1.0", self._prompt_placeholder)
        self._prompt_placeholder_active = True

    def _get_prompt(self):
        if self._prompt_placeholder_active:
            return ""
        return self.prompt_text.get("1.0", "end").strip()

    def _append_log(self, message, tag=None):
        def _write():
            self.log_text.configure(state="normal")
            textbox = getattr(self.log_text, "_textbox", self.log_text)
            if tag and hasattr(textbox, "tag_config"):
                if tag not in textbox.tag_names():
                    textbox.tag_config(tag, foreground="#ff6b6b")
                textbox.insert("end", message + "\n", tag)
            else:
                textbox.insert("end", message + "\n")
            textbox.see("end")
            self.log_text.configure(state="disabled")

        self.after(0, _write)

    def _set_generate_state(self, enabled):
        def _apply():
            self.generate_button.configure(state="normal" if enabled else "disabled")

        self.after(0, _apply)

    def _set_action_state(self, enabled):
        def _apply():
            state = "normal" if enabled else "disabled"
            self.save_button.configure(state=state)
            self.open_button.configure(state=state)

        self.after(0, _apply)

    def _set_progress(self, percent, text=None):
        percent = max(0, min(100, int(percent)))

        def _apply():
            self._progress_percent = percent
            self.progress_bar.set(percent / 100)
            label_text = text or self._t("progress", percent=percent)
            self.progress_label.configure(text=label_text)

        self.after(0, _apply)

    def _quality_flag(self):
        value = self.quality_var.get()
        return {"Low": "-ql", "Medium": "-qm", "High": "-qh"}.get(value, "-qm")

    def _build_fix_prompt(self, user_prompt, error, script_path):
        code = ""
        if script_path:
            try:
                code = Path(script_path).read_text(encoding="utf-8")
            except Exception:
                code = ""

        parts = [
            user_prompt.strip() if user_prompt else "",
            "The previous Manim code failed to render.",
            f"Error output:\n{error}".strip(),
            f"Previous code:\n{code}".strip(),
            "Fix the code and output the complete corrected script only.",
        ]
        return "\n\n".join(part for part in parts if part) + "\n"

    def _on_generate_render(self):
        prompt = self._get_prompt()
        if not prompt:
            self._append_log(self._t("prompt_empty"))
            return

        self._set_generate_state(False)
        self._set_action_state(False)
        self._set_progress(5)
        thread = threading.Thread(target=self._run_pipeline, args=(prompt,), daemon=True)
        thread.start()

    def _run_pipeline(self, prompt):
        attempt = 0
        last_error = ""
        script_path = None

        try:
            while True:
                attempt += 1
                renderer = None
                if MAX_FIX_ATTEMPTS and attempt > MAX_FIX_ATTEMPTS:
                    self._append_log(self._t("log_retry_limit", attempts=MAX_FIX_ATTEMPTS), tag="error")
                    self._set_progress(0, text=self._t("progress_error"))
                    break

                try:
                    self._set_progress(20)
                    if attempt == 1:
                        self._append_log(self._t("log_generating"))
                        script_path = self.generator.generate(prompt)
                    else:
                        self._append_log(self._t("log_fixing", attempt=attempt - 1))
                        fix_prompt = self._build_fix_prompt(prompt, last_error, script_path)
                        script_path = self.generator.generate(fix_prompt)
                except Exception as exc:
                    logger.exception("Generation failed")
                    self._append_log(self._t("log_error", error=exc), tag="error")
                    self._set_progress(0, text=self._t("progress_error"))
                    break

                try:
                    self._append_log(self._t("log_rendering_start"))
                    self._set_progress(55)
                    renderer = ManimRenderer(quality_flag=self._quality_flag())
                    video_path = renderer.render()
                except Exception as exc:
                    logger.exception("Render failed")
                    stderr = ""
                    if renderer is not None:
                        stderr = (renderer.last_stderr or "").strip()
                    last_error = stderr or str(exc)
                    if last_error:
                        self._append_log(last_error, tag="error")
                    else:
                        self._append_log(self._t("log_error", error=exc), tag="error")
                    continue

                output_path = self._store_rendered_video(video_path)
                self.last_video_path = output_path
                self._append_log(self._t("log_rendered", path=output_path))
                preview_image_path = None
                if self.video_player is None:
                    preview_image_path = self._generate_preview_image(output_path)
                self._update_preview(output_path, preview_image_path)
                self._set_progress(100)
                self._set_action_state(True)
                break
        finally:
            self._set_generate_state(True)

    def _on_clear(self):
        self._set_prompt_placeholder()
        self.last_video_path = None
        self.output_video_path = None
        self._set_action_state(False)
        self._reset_preview()
        self._set_progress(0)
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
        self._append_log(self._t("log_cleared"))

    def _on_save_video(self):
        source_path = self.output_video_path or self.last_video_path
        if not source_path:
            self._append_log(self._t("log_no_video_save"))
            return
        source = Path(source_path)
        if not source.exists():
            self._append_log(self._t("log_video_not_found"))
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            initialfile=source.name,
            filetypes=[("MP4 Video", "*.mp4")],
        )
        if not file_path:
            return

        shutil.copy2(source, file_path)
        self._append_log(self._t("log_video_saved", path=file_path))

    def _on_open_player(self):
        source_path = self.output_video_path or self.last_video_path
        if not source_path:
            self._append_log(self._t("log_no_video_open"))
            return
        path = Path(source_path)
        if not path.exists():
            self._append_log(self._t("log_video_not_found"))
            return

        try:
            if os.name == "nt":
                os.startfile(str(path))
            elif os.uname().sysname.lower().startswith("darwin"):
                subprocess.run(["open", str(path)], check=False)
            else:
                subprocess.run(["xdg-open", str(path)], check=False)
            self._append_log(self._t("log_opened"))
        except Exception as exc:
            self._append_log(self._t("log_open_failed", error=exc))

    def _store_rendered_video(self, video_path):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        output_path = self.output_dir / f"{SCENE_NAME}.mp4"
        shutil.copy2(video_path, output_path)
        self.output_video_path = str(output_path)
        return self.output_video_path

    def _generate_preview_image(self, video_path):
        preview_path = self.output_dir / "preview.png"
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-frames:v",
            "1",
            str(preview_path),
        ]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            logger.warning("Preview generation failed: %s", result.stderr)
            return None
        return str(preview_path)

    def _update_preview(self, video_path, preview_image_path=None):
        def _apply():
            self._on_preview_resize()
            if self.video_player is not None:
                self._preview_source_image = None
                self._preview_image_path = None
                try:
                    self.video_player.stop()
                except Exception:
                    pass
                try:
                    self.video_player.load(video_path)
                    self.video_player.play()
                    return
                except Exception as exc:
                    logger.warning("Video preview failed: %s", exc)

            if preview_image_path:
                self._preview_image_path = preview_image_path
                self._show_preview_image(preview_image_path)
            else:
                self._show_preview_placeholder()

        self.after(0, _apply)

    def _on_preview_resize(self, _event=None):
        if not hasattr(self, "preview_area") or not hasattr(self, "preview_surface"):
            return
        width = self.preview_area.winfo_width()
        height = self.preview_area.winfo_height()
        if width <= 0 or height <= 0:
            return
        target_w = width
        target_h = int(width * 9 / 16)
        if target_h > height:
            target_h = height
            target_w = int(height * 16 / 9)
        self.preview_surface.configure(width=target_w, height=target_h)
        self.preview_surface.place(relx=0.5, rely=0.5, anchor="center")
        if self.video_player is not None:
            try:
                self.video_player.set_size((target_w, target_h), keep_aspect=True)
            except Exception:
                pass
        if self.video_player is None and self._preview_source_image is not None:
            self._show_preview_image(None)

    def _show_preview_image(self, preview_image_path):
        try:
            if preview_image_path:
                self._preview_image_path = preview_image_path
                self._preview_source_image = Image.open(preview_image_path)
            if self._preview_source_image is None:
                self._show_preview_placeholder()
                return
            self.preview_surface.update_idletasks()
            width = max(int(self.preview_surface.cget("width")), 320)
            height = max(int(self.preview_surface.cget("height")), 180)
            image = self._preview_source_image.resize((width, height), Image.LANCZOS)
            self._preview_image = ctk.CTkImage(
                light_image=image,
                dark_image=image,
                size=(width, height),
            )
            label = self._ensure_preview_label()
            label.configure(image=self._preview_image, text="")
        except Exception as exc:
            logger.warning("Preview image load failed: %s", exc)
            self._show_preview_placeholder()

    def _show_preview_placeholder(self):
        label = self._ensure_preview_label()
        label.configure(text=self._t("preview_area"), image=None, text_color="gray70")

    def _ensure_preview_label(self):
        if isinstance(self.preview_image_label, ctk.CTkLabel):
            return self.preview_image_label
        if self.video_player is not None:
            try:
                self.video_player.stop()
            except Exception:
                pass
            self.video_player.destroy()
            self.video_player = None
        self.preview_image_label = ctk.CTkLabel(
            self.preview_surface,
            text=self._t("preview_area"),
            text_color="gray70",
        )
        self.preview_image_label.pack(expand=True, fill="both")
        return self.preview_image_label

    def _reset_preview(self):
        def _apply():
            if self.video_player is not None:
                try:
                    self.video_player.stop()
                except Exception:
                    pass
            if self.preview_image_label is not None:
                self.preview_image_label.configure(image=None, text=self._t("preview_area"))
            self._preview_source_image = None
            self._preview_image_path = None
            self._on_preview_resize()

        self.after(0, _apply)
