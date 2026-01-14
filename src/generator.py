import logging
import re
import subprocess
from pathlib import Path

from config import LLM_COMMAND, OUTPUT_DIR

try:
    from config import SYSTEM_PROMPT
except Exception:
    SYSTEM_PROMPT = ""


logger = logging.getLogger(__name__)


class CodeGenerator:
    def __init__(self, command=LLM_COMMAND, output_dir=OUTPUT_DIR, system_prompt=None):
        self.command = list(command)
        self.output_dir = Path(output_dir)
        self.system_prompt = SYSTEM_PROMPT if system_prompt is None else system_prompt

    def generate(self, prompt):
        full_prompt = self._build_prompt(prompt)
        cmd, stdin_data = self._build_command(full_prompt)
        logger.info("Running LLM command: %s", " ".join(cmd))

        try:
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE if stdin_data is not None else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except FileNotFoundError as exc:
            logger.error("LLM command not found: %s", cmd[0])
            raise RuntimeError(
                f"LLM command not found: {cmd[0]}. "
                "Ensure it is installed and available in PATH, or use an absolute path."
            ) from exc

        stdout, stderr = process.communicate(stdin_data)

        if stderr:
            logger.debug("LLM stderr:\n%s", stderr)
        if process.returncode != 0:
            logger.error("LLM command failed with code %s", process.returncode)
            raise RuntimeError("LLM command failed")

        cleaned = self._clean_response(stdout)
        if not cleaned.strip():
            raise RuntimeError("LLM returned empty script")

        self.output_dir.mkdir(parents=True, exist_ok=True)
        script_path = self.output_dir / "script.py"
        script_path.write_text(cleaned, encoding="utf-8")
        logger.info("Wrote script to %s", script_path)
        return str(script_path)

    def _build_prompt(self, prompt):
        parts = []
        if self.system_prompt:
            parts.append(self.system_prompt.strip())
        if prompt:
            parts.append(prompt.strip())
        if not parts:
            return ""
        return "\n\n".join(parts) + "\n"

    def _build_command(self, full_prompt):
        cmd = list(self.command)
        stdin_data = full_prompt
        if any("{prompt}" in part for part in cmd):
            cmd = [part.replace("{prompt}", full_prompt) for part in cmd]
            stdin_data = None
        return cmd, stdin_data

    def _clean_response(self, text):
        if not text:
            return ""
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        start = text.find("from manim")
        if start != -1:
            text = text[start:]

        if "```" in text:
            last_fence = text.rfind("```")
            if last_fence != -1:
                text = text[:last_fence]
            text = text.replace("```python", "").replace("```", "")

        text = self._sanitize_no_tex(text)
        text = self._strip_trailing_non_code(text)
        return text.strip() + "\n"

    def _sanitize_no_tex(self, text):
        replacements = {
            "MathTex(": "Text(",
            "Tex(": "Text(",
            "Title(": "Text(",
        }
        for src, dst in replacements.items():
            text = text.replace(src, dst)

        text = re.sub(r"\\.get_x_axis_label\\([^)]*\\)", 'Text("x")', text)
        text = re.sub(r"\\.get_y_axis_label\\([^)]*\\)", 'Text("y")', text)
        text = re.sub(r"\\.get_axis_labels\\([^)]*\\)", 'VGroup(Text("x"), Text("y"))', text)
        return text

    def _strip_trailing_non_code(self, text):
        lines = text.splitlines()
        while lines and not lines[-1].strip():
            lines.pop()

        def is_code_line(line):
            stripped = line.lstrip()
            if not stripped:
                return True
            if line != stripped:
                return True
            if stripped.startswith("#"):
                return True
            for kw in (
                "from ",
                "import ",
                "class ",
                "def ",
                "if ",
                "elif ",
                "else:",
                "for ",
                "while ",
                "with ",
                "try:",
                "except ",
                "finally:",
                "return ",
                "pass",
                "break",
                "continue",
                "raise ",
                "@",
            ):
                if stripped.startswith(kw):
                    return True
            if any(tok in stripped for tok in ("=", "(", ")", "{", "}", "[", "]")):
                return True
            return False

        while lines and not is_code_line(lines[-1]):
            lines.pop()
            while lines and not lines[-1].strip():
                lines.pop()
        return "\n".join(lines)
