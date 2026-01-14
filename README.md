# ZAPLAVNIY_AI

Created by Zaplavny Alexandr. Blog: https://t.me/+ay37cKnFWtg3MDJi

Full setup and run instructions (Windows / PowerShell).

## 1) Install system dependencies
1. Python 3.10+ (add to PATH).
2. FFmpeg (add to PATH). Check: `ffmpeg -version`.
3. LaTeX (MiKTeX or TeX Live) - only needed if you use Tex/MathTex/Title in Manim.
4. Qwen CLI (npm) and model:
   - `npm i -g @qwen-ai/qwen` (example CLI install)
   - Verify `qwen` is available: `Get-Command qwen`

## 2) Create a virtual environment
```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## 3) Install Python dependencies
```
python -m pip install --upgrade pip
python -m pip install -r requirements.txt --only-binary=av
```

## 4) Configure the Qwen CLI path
Open `config.py` and set the path to `qwen.ps1`, for example:
```
QWEN_CLI = r"C:\Users\user\AppData\Roaming\npm\qwen.ps1"
QWEN_MODEL = "qwen"
```

## 5) Run the app
```
python main.py
```

## 6) If Qwen does not start
1. Check the path:
   ```
   Get-Command qwen
   ```
2. Set the real path in `config.py`.

## 7) Notes
- The app is configured to avoid Tex/MathTex/Title to remove the LaTeX requirement.
- If you want to use TeX objects in Manim, install LaTeX and add it to PATH.
