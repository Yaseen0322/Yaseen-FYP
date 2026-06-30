"""
Webcam Presence Detection Service
Uses MediaPipe for face detection - privacy preserving (no images stored)
"""
import os
import importlib
from datetime import datetime, timezone
from enum import Enum
from contextlib import asynccontextmanager
import multiprocessing as mp
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import time

# MediaPipe imports Matplotlib lazily on some systems. Give it a writable cache
# location so imports remain stable after abrupt power loss or config drift.
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-webcam-service")
os.makedirs(os.environ["MPLCONFIGDIR"], exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    detector.start()
    try:
        yield
    finally:
        detector.stop()


app = FastAPI(
    title="Webcam Presence Service",
    version="1.0.0",
    description="Privacy-preserving presence detection - no images stored",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PresenceState(str, Enum):
    PRESENT = "present"
    ABSENT = "absent"
    CAMERA_OFF = "camera_off"


class PresenceStatus(BaseModel):
    state: PresenceState
    confidence: float
    timestamp: str
    is_running: bool


STATE_TO_CODE = {
    PresenceState.CAMERA_OFF: 0,
    PresenceState.PRESENT: 1,
    PresenceState.ABSENT: 2,
}

CODE_TO_STATE = {
    0: PresenceState.CAMERA_OFF,
    1: PresenceState.PRESENT,
    2: PresenceState.ABSENT,
}


def _write_text_buffer(buffer, value: str) -> None:
    encoded = (value or "").encode("utf-8")[: len(buffer) - 1]
    buffer[:] = b"\x00" * len(buffer)
    buffer[: len(encoded)] = encoded


def _read_text_buffer(buffer) -> str:
    raw = bytes(buffer[:])
    return raw.split(b"\x00", 1)[0].decode("utf-8", errors="ignore")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def detection_worker(state_code, confidence_value, running_value, timestamp_buffer, error_buffer,
                     stop_event, fps, process_width, process_height,
                     present_threshold, absent_threshold):
    import cv2

    mp_face_detection = None
    import_paths = [
        "mediapipe.solutions.face_detection",
        "mediapipe.python.solutions.face_detection",
    ]
    for import_path in import_paths:
        try:
            mp_face_detection = importlib.import_module(import_path)
            break
        except Exception:
            continue

    if mp_face_detection is None:
        state_code.value = STATE_TO_CODE[PresenceState.CAMERA_OFF]
        confidence_value.value = 0.0
        running_value.value = False
        _write_text_buffer(error_buffer, "MediaPipe face detection module unavailable")
        return

    cap = None
    face_detection = None
    consecutive_present = 0
    consecutive_absent = 0

    try:
        face_detection = mp_face_detection.FaceDetection(
            model_selection=0,
            min_detection_confidence=0.5,
        )

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            state_code.value = STATE_TO_CODE[PresenceState.CAMERA_OFF]
            confidence_value.value = 0.0
            running_value.value = False
            _write_text_buffer(error_buffer, "Camera unavailable")
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)

        running_value.value = True
        _write_text_buffer(error_buffer, "")

        while not stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                state_code.value = STATE_TO_CODE[PresenceState.CAMERA_OFF]
                confidence_value.value = 0.0
                _write_text_buffer(error_buffer, "Camera read failed")
                break

            small_frame = cv2.resize(
                frame,
                (process_width, process_height),
                interpolation=cv2.INTER_AREA,
            )
            rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            results = face_detection.process(rgb_frame)

            face_detected = results.detections is not None and len(results.detections) > 0
            if face_detected:
                confidence_value.value = float(results.detections[0].score[0])
                consecutive_present += 1
                consecutive_absent = 0
                if consecutive_present >= present_threshold:
                    state_code.value = STATE_TO_CODE[PresenceState.PRESENT]
            else:
                confidence_value.value = 0.0
                consecutive_absent += 1
                consecutive_present = 0
                if consecutive_absent >= absent_threshold:
                    state_code.value = STATE_TO_CODE[PresenceState.ABSENT]

            _write_text_buffer(timestamp_buffer, utc_now_iso())
            time.sleep(1.0 / fps)

    except Exception as exc:
        state_code.value = STATE_TO_CODE[PresenceState.CAMERA_OFF]
        confidence_value.value = 0.0
        _write_text_buffer(error_buffer, str(exc))
    finally:
        if cap:
            cap.release()
        if face_detection:
            face_detection.close()
        running_value.value = False


class PresenceDetector:
    def __init__(self):
        self.current_state = PresenceState.CAMERA_OFF
        self.confidence = 0.0
        self.is_running = False
        self.process = None
        self.stop_event = None
        self.state_code = None
        self.confidence_value = None
        self.running_value = None
        self.timestamp_buffer = None
        self.error_buffer = None
        
        self.present_threshold = 3  # frames needed to confirm present
        self.absent_threshold = 5   # frames needed to confirm absent
        
        # State change callback
        self.on_state_change = None
        
        # Detection interval
        self.fps = 2  # Low FPS to reduce CPU usage
        self.process_width = 320
        self.process_height = 180

    def start(self):
        if self.is_running:
            return
        
        if self.process and self.process.is_alive():
            self.is_running = True
            return

        if self.state_code is None:
            self.state_code = mp.Value('i', STATE_TO_CODE[self.current_state])
            self.confidence_value = mp.Value('d', float(self.confidence))
            self.running_value = mp.Value('b', False)
            self.timestamp_buffer = mp.Array('b', 64)
            self.error_buffer = mp.Array('b', 128)
            _write_text_buffer(self.timestamp_buffer, utc_now_iso())
            _write_text_buffer(self.error_buffer, "")
        self.stop_event = mp.Event()
        self.is_running = True
        self.process = mp.Process(
            target=detection_worker,
            args=(
                self.state_code,
                self.confidence_value,
                self.running_value,
                self.timestamp_buffer,
                self.error_buffer,
                self.stop_event,
                self.fps,
                self.process_width,
                self.process_height,
                self.present_threshold,
                self.absent_threshold,
            ),
            daemon=True,
        )
        self.process.start()

    def stop(self):
        if self.stop_event is not None:
            self.stop_event.set()
        self.is_running = False
        if self.process:
            self.process.join(timeout=2)
            if self.process.is_alive():
                self.process.terminate()
        self.current_state = PresenceState.CAMERA_OFF
        self.confidence = 0.0

    def _sync_from_shared_state(self):
        if self.state_code is None:
            return

        self.current_state = CODE_TO_STATE.get(int(self.state_code.value), PresenceState.CAMERA_OFF)
        self.confidence = float(self.confidence_value.value or 0.0)
        self.is_running = bool(self.running_value.value) and bool(self.process and self.process.is_alive())
        if self.process and not self.process.is_alive():
            self.is_running = False
            self.current_state = PresenceState.CAMERA_OFF
            self.confidence = 0.0

    def get_status(self) -> PresenceStatus:
        self._sync_from_shared_state()
        return PresenceStatus(
            state=self.current_state,
            confidence=self.confidence,
            timestamp=utc_now_iso(),
            is_running=self.is_running
        )

    def get_last_error(self) -> str:
        if self.error_buffer is None:
            return ""
        return _read_text_buffer(self.error_buffer)


# Global detector instance
detector = PresenceDetector()


@app.get("/")
async def root():
    return {
        "service": "Webcam Presence Detection",
        "version": "1.0.0",
        "privacy": "No images stored - only presence state"
    }


@app.get("/status", response_model=PresenceStatus)
async def get_status():
    """Get current presence status"""
    return detector.get_status()


@app.post("/start")
async def start_detection():
    """Start presence detection"""
    detector.start()
    return {"message": "Detection started", "status": detector.get_status()}


@app.post("/stop")
async def stop_detection():
    """Stop presence detection"""
    detector.stop()
    return {"message": "Detection stopped", "status": detector.get_status()}


@app.get("/health")
async def health():
    detector._sync_from_shared_state()
    return {
        "status": "healthy",
        "detection_running": detector.is_running,
        "presence_state": detector.current_state,
        "last_error": detector.get_last_error(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
