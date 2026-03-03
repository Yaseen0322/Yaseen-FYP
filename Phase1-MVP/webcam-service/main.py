"""
Webcam Presence Detection Service
Uses MediaPipe for face detection - privacy preserving (no images stored)
"""
import asyncio
from datetime import datetime
from enum import Enum
from typing import Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import threading
import time

app = FastAPI(
    title="Webcam Presence Service",
    version="1.0.0",
    description="Privacy-preserving presence detection - no images stored"
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


class PresenceDetector:
    def __init__(self):
        self.current_state = PresenceState.CAMERA_OFF
        self.confidence = 0.0
        self.is_running = False
        self.thread = None
        self.stop_event = threading.Event()
        
        # Smoothing parameters
        self.consecutive_present = 0
        self.consecutive_absent = 0
        self.present_threshold = 3  # frames needed to confirm present
        self.absent_threshold = 5   # frames needed to confirm absent
        
        # State change callback
        self.on_state_change = None
        
        # Detection interval
        self.fps = 2  # Low FPS to reduce CPU usage

    def start(self):
        if self.is_running:
            return
        
        self.stop_event.clear()
        self.is_running = True
        self.thread = threading.Thread(target=self._detection_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=2)
        self.current_state = PresenceState.CAMERA_OFF

    def _detection_loop(self):
        import cv2
        import mediapipe as mp
        
        mp_face_detection = mp.solutions.face_detection
        face_detection = mp_face_detection.FaceDetection(
            model_selection=0,  # 0 for short-range, 1 for full-range
            min_detection_confidence=0.5
        )
        
        cap = None
        try:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                self.current_state = PresenceState.CAMERA_OFF
                self.is_running = False
                return
            
            while not self.stop_event.is_set():
                ret, frame = cap.read()
                if not ret:
                    self.current_state = PresenceState.CAMERA_OFF
                    break
                
                # Convert to RGB for MediaPipe
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = face_detection.process(rgb_frame)
                
                # Check if face detected
                face_detected = results.detections is not None and len(results.detections) > 0
                
                if face_detected:
                    self.confidence = results.detections[0].score[0]
                    self.consecutive_present += 1
                    self.consecutive_absent = 0
                    
                    if self.consecutive_present >= self.present_threshold:
                        if self.current_state != PresenceState.PRESENT:
                            self.current_state = PresenceState.PRESENT
                else:
                    self.confidence = 0.0
                    self.consecutive_absent += 1
                    self.consecutive_present = 0
                    
                    if self.consecutive_absent >= self.absent_threshold:
                        if self.current_state != PresenceState.ABSENT:
                            self.current_state = PresenceState.ABSENT
                
                # Sleep to maintain target FPS
                time.sleep(1.0 / self.fps)
        
        except Exception as e:
            print(f"Detection error: {e}")
            self.current_state = PresenceState.CAMERA_OFF
        
        finally:
            if cap:
                cap.release()
            face_detection.close()
            self.is_running = False

    def get_status(self) -> PresenceStatus:
        return PresenceStatus(
            state=self.current_state,
            confidence=self.confidence,
            timestamp=datetime.utcnow().isoformat(),
            is_running=self.is_running
        )


# Global detector instance
detector = PresenceDetector()


@app.on_event("startup")
async def startup():
    # Auto-start detection
    detector.start()


@app.on_event("shutdown")
async def shutdown():
    detector.stop()


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
    return {
        "status": "healthy",
        "detection_running": detector.is_running
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
