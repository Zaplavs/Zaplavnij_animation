import logging
import subprocess
from pathlib import Path

from config import OUTPUT_DIR, SCENE_NAME


logger = logging.getLogger(__name__)


class ManimRenderer:
    def __init__(
        self,
        script_path=None,
        scene_name=SCENE_NAME,
        quality_flag="-qm",
        media_dir="media",
    ):
        if script_path is None:
            script_path = Path(OUTPUT_DIR) / "script.py"
        self.script_path = Path(script_path)
        self.scene_name = scene_name
        self.quality_flag = quality_flag
        self.media_dir = Path(media_dir)
        self.last_stdout = ""
        self.last_stderr = ""
        self.last_returncode = None

    def render(self):
        cmd = ["manim", self.quality_flag, str(self.script_path), self.scene_name]
        logger.info("Running manim: %s", " ".join(cmd))

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.last_stdout = result.stdout or ""
        self.last_stderr = result.stderr or ""
        self.last_returncode = result.returncode
        if self.last_stdout:
            logger.debug("manim stdout:\n%s", result.stdout)
        if self.last_stderr:
            logger.debug("manim stderr:\n%s", result.stderr)
        if result.returncode != 0:
            raise RuntimeError(f"manim failed with exit code {result.returncode}")

        output_path = self._find_output()
        logger.info("Rendered video at %s", output_path)
        return output_path

    def _find_output(self):
        if not self.media_dir.exists():
            raise FileNotFoundError("Media directory not found")

        pattern = f"videos/**/{self.scene_name}.mp4"
        candidates = list(self.media_dir.glob(pattern))
        if not candidates:
            raise FileNotFoundError("Rendered video not found")

        latest = max(candidates, key=lambda path: path.stat().st_mtime)
        return str(latest)
