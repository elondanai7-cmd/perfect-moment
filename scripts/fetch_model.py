"""Download the MediaPipe FaceLandmarker model into models/face_landmarker.task.

The model file is gitignored (binary, ~a few MB, fetched on demand — SKILL.md pitfall
about not hand-vendoring model weights into the repo). Run once after `pip install -r
requirements.txt`:

    python scripts/fetch_model.py
"""

import urllib.request
from pathlib import Path

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/1/face_landmarker.task"
)

DEST = Path(__file__).resolve().parent.parent / "models" / "face_landmarker.task"


def main() -> None:
    DEST.parent.mkdir(parents=True, exist_ok=True)
    if DEST.exists():
        print(f"Already present: {DEST}")
        return
    print(f"Downloading {MODEL_URL} -> {DEST}")
    urllib.request.urlretrieve(MODEL_URL, DEST)
    print("Done.")


if __name__ == "__main__":
    main()
