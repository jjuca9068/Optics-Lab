import os
import json
import time
import logging
import asyncio
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Query, Request, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import cv2
import numpy as np

from motor_controller import MotorController
from camera_controller import CameraController

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main_app")

app = FastAPI(title="Quantum Optics Lab Controller")

MOTOR1_SERIAL = "27270997"
MOTOR2_SERIAL = "27271282"

motor1: Optional[MotorController] = None
motor2: Optional[MotorController] = None
camera: Optional[CameraController] = None

# Permanent optical calibration values (microns per pixel)
calibration_data = {
    "1x": 1.1152,
    "2x": 0.5984,
    "3x": 0.3973,
    "4x": 0.28655
}

# ==========================================
# --- Persistent Sequence Storage Logic  ---
# ==========================================
SEQUENCES_FILE = "sequences.json"

if os.path.exists(SEQUENCES_FILE):
    try:
        with open(SEQUENCES_FILE, "r") as f:
            saved_sequences: Dict[str, List[Dict[str, Any]]] = json.load(f)
        logger.info(f"Loaded {len(saved_sequences)} saved sequences from disk.")
    except Exception as e:
        logger.error(f"Failed to read {SEQUENCES_FILE}: {e}")
        saved_sequences: Dict[str, List[Dict[str, Any]]] = {}
else:
    saved_sequences: Dict[str, List[Dict[str, Any]]] = {}

def save_sequences_to_disk():
    try:
        with open(SEQUENCES_FILE, "w") as f:
            json.dump(saved_sequences, f, indent=4)
    except Exception as e:
        logger.error(f"Failed to save sequences to {SEQUENCES_FILE}: {e}")

class SequenceStep(BaseModel):
    position: Optional[float] = None
    pos: Optional[float] = None
    velocity: Optional[float] = None
    acceleration: Optional[float] = None
    pause_after: Optional[float] = 0.0
    pause: Optional[float] = 0.0

class SequencePayload(BaseModel):
    steps: List[SequenceStep]
    name: Optional[str] = None

class DualSequencePayload(BaseModel):
    motor1_steps: List[SequenceStep] = []
    motor2_steps: List[SequenceStep] = []
    motor1_name: Optional[str] = None
    motor2_name: Optional[str] = None

class VelocityPayload(BaseModel):
    velocity: float
    acceleration: float

class SavedSequence(BaseModel):
    name: str
    steps: List[SequenceStep]

def get_motor(motor_id: str) -> MotorController:
    if motor_id == "motor1":
        m = motor1
    elif motor_id == "motor2":
        m = motor2
    else:
        raise HTTPException(status_code=400, detail="Invalid motor ID")

    if m is None:
        raise HTTPException(status_code=500, detail=f"{motor_id} driver not initialized.")
    return m

@app.on_event("startup")
async def startup_hardware_init():
    global motor1, motor2, camera
    logger.info("Initializing Thorlabs Motor Controllers...")
    motor1 = MotorController(serial_number=MOTOR1_SERIAL, use_real_hardware=True)
    motor2 = MotorController(serial_number=MOTOR2_SERIAL, use_real_hardware=True)
    
    logger.info("Initializing Camera Controller...")
    camera = CameraController(use_real_hardware=True)

@app.on_event("shutdown")
async def shutdown_hardware():
    logger.info("Closing motor connections...")
    if motor1:
        motor1.close()
    if motor2:
        motor2.close()

# ==========================================
# --- Camera & Optics Calibration Routes ---
# ==========================================
def frame_generator():
    while True:
        if camera:
            frame = camera.get_frame_jpeg()
            if frame:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(
        frame_generator(), 
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.get("/calibration")
async def get_calibration():
    return calibration_data

@app.post("/calibration")
async def save_calibration(request: Request):
    data = await request.json()
    zoom = data.get("zoom")
    microns_per_pixel = data.get("microns_per_pixel")
    if zoom and microns_per_pixel:
        calibration_data[zoom] = microns_per_pixel
    return calibration_data

@app.post("/camera/settings")
async def update_camera_settings(request: Request):
    if not camera:
        raise HTTPException(status_code=500, detail="Camera not initialized")
    
    data = await request.json()
    if "exposure" in data:
        camera.set_exposure(data["exposure"])
    if "gain" in data:
        camera.set_gain(data["gain"])
    if "width" in data and "height" in data:
        camera.set_resolution(data["width"], data["height"])
        
    return camera.get_resolution()

@app.post("/camera/auto_scale")
async def api_camera_auto_scale():
    if not camera:
        return {"status": "error", "message": "Camera not initialized"}
    result = camera.auto_scale(target_brightness=120.0)
    return result

@app.post("/camera/capture")
async def capture_image():
    if not camera:
        return {"error": "Camera not initialized"}
    
    frame_bytes = camera.get_frame_jpeg()
    if not frame_bytes:
        return {"error": "Failed to grab frame from camera"}
        
    os.makedirs(os.path.join("static", "captures"), exist_ok=True)
    
    filename = f"capture_{int(time.time())}.jpg"
    filepath = os.path.join("static", "captures", filename)
    
    with open(filepath, "wb") as f:
        f.write(frame_bytes)
        
    return {"filename": filename}

@app.get("/captures/list")
async def list_captures():
    captures_dir = os.path.join("static", "captures")
    captures = []
    if os.path.exists(captures_dir):
        for filename in sorted(os.listdir(captures_dir), reverse=True):
            if filename.endswith(".jpg"):
                captures.append({
                    "filename": filename,
                    "url": f"/captures/{filename}"
                })
    return captures

@app.post("/camera/measure_fiber")
async def measure_fiber():
    """Automatically measures fiber thickness by analyzing vertical gradients in the image."""
    if not camera:
        return {"error": "Camera not initialized"}
    
    frame_bytes = camera.get_frame_jpeg()
    if not frame_bytes:
        return {"error": "Failed to grab frame"}

    np_arr = np.frombuffer(frame_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_GRAYSCALE)

    if img is None:
        return {"error": "Failed to decode image"}

    # Isolate the center vertical slice to minimize noise from the edges
    h, w = img.shape
    center_x = w // 2
    roi = img[:, center_x-20:center_x+20]

    # Average the slice horizontally to create a clean 1D intensity profile
    profile = np.mean(roi, axis=1)

    # Calculate the gradient (1st derivative) to find sharp contrast edges
    gradient = np.abs(np.gradient(profile))

    # The fiber cladding boundaries represent the highest gradients (dark -> bright and bright -> dark)
    # Threshold at 30% of the maximum gradient peak to filter noise
    threshold = np.max(gradient) * 0.3
    edge_peaks = np.where(gradient > threshold)[0]

    if len(edge_peaks) < 2:
        return {"error": "Could not clearly detect outer fiber edges."}

    top_edge = edge_peaks[0]
    bottom_edge = edge_peaks[-1]
    pixel_width = float(bottom_edge - top_edge)

    return {"pixel_width": pixel_width}

# ==========================================
# --- Saved Sequences Routes ---
# ==========================================
@app.get("/sequences")
async def get_saved_sequences():
    return saved_sequences

@app.post("/sequences")
async def save_new_sequence(payload: SavedSequence):
    formatted_steps = []
    for s in payload.steps:
        formatted_steps.append({
            "position": s.position if s.position is not None else s.pos,
            "velocity": s.velocity,
            "acceleration": s.acceleration,
            "pause_after": s.pause_after if s.pause_after else s.pause
        })
    saved_sequences[payload.name] = formatted_steps
    save_sequences_to_disk()
    return saved_sequences

@app.delete("/sequences/{name}")
async def delete_saved_sequence(name: str):
    if name in saved_sequences:
        del saved_sequences[name]
        save_sequences_to_disk()
    return saved_sequences

@app.post("/sequences/upload")
async def upload_sequence_text_file(file: UploadFile = File(...)):
    """Accepts a text or CSV file formatted as: position, velocity, acceleration, pause"""
    content = await file.read()
    text = content.decode('utf-8')
    steps = []
    
    for line in text.splitlines():
        parts = line.split(',')
        if not parts or not parts[0].strip():
            continue
        try:
            pos = float(parts[0].strip())
            vel = float(parts[1].strip()) if len(parts) > 1 and parts[1].strip() else None
            acc = float(parts[2].strip()) if len(parts) > 2 and parts[2].strip() else None
            pause = float(parts[3].strip()) if len(parts) > 3 and parts[3].strip() else 0.0
            steps.append({
                "pos": pos,
                "velocity": vel,
                "acceleration": acc,
                "pause": pause
            })
        except ValueError:
            continue  # Skip headers or badly formatted lines

    if not steps:
        return {"error": "No valid sequence steps found in the file."}

    name = file.filename.rsplit('.', 1)[0]
    saved_sequences[name] = steps
    save_sequences_to_disk()
    
    return {"message": f"Sequence '{name}' uploaded successfully", "name": name}

# ==========================================
# --- Explicit Motor 1 Routes ---
# ==========================================
@app.get("/motor1/status")
async def get_motor1_status():
    return get_motor("motor1").get_status()

@app.post("/motor1/set_zero")
async def set_motor1_zero():
    return get_motor("motor1").set_custom_home()

@app.post("/motor1/move")
async def move_motor1(position: float = Query(...)):
    m = get_motor("motor1")
    m.move_to(position, wait=False)
    return {"status": "moving", "target_position": position}

@app.post("/motor1/home")
async def home_motor1():
    return get_motor("motor1").home()

@app.post("/motor1/velocity")
async def set_motor1_velocity(payload: VelocityPayload):
    m = get_motor("motor1")
    m.set_velocity_profile(payload.velocity, payload.acceleration)
    return {"status": "velocity_updated"}

@app.post("/motor1/stop")
async def stop_motor1():
    return get_motor("motor1").stop()

@app.post("/motor1/pause")
async def pause_motor1():
    return get_motor("motor1").pause()

@app.post("/motor1/resume")
async def resume_motor1():
    return get_motor("motor1").resume()

@app.post("/motor1/sequence")
async def run_motor1_sequence(payload: SequencePayload):
    formatted_steps = []
    for s in payload.steps:
        formatted_steps.append({
            "pos": s.position if s.position is not None else s.pos,
            "pause": s.pause_after if s.pause_after else s.pause,
            "velocity": s.velocity,
            "acceleration": s.acceleration
        })
    return get_motor("motor1").run_sequence(formatted_steps)

# ==========================================
# --- Explicit Motor 2 Routes ---
# ==========================================
@app.get("/motor2/status")
async def get_motor2_status():
    return get_motor("motor2").get_status()

@app.post("/motor2/set_zero")
async def set_motor2_zero():
    return get_motor("motor2").set_custom_home()

@app.post("/motor2/move")
async def move_motor2(position: float = Query(...)):
    m = get_motor("motor2")
    m.move_to(position, wait=False)
    return {"status": "moving", "target_position": position}

@app.post("/motor2/home")
async def home_motor2():
    return get_motor("motor2").home()

@app.post("/motor2/velocity")
async def set_motor2_velocity(payload: VelocityPayload):
    m = get_motor("motor2")
    m.set_velocity_profile(payload.velocity, payload.acceleration)
    return {"status": "velocity_updated"}

@app.post("/motor2/stop")
async def stop_motor2():
    return get_motor("motor2").stop()

@app.post("/motor2/pause")
async def pause_motor2():
    return get_motor("motor2").pause()

@app.post("/motor2/resume")
async def resume_motor2():
    return get_motor("motor2").resume()

@app.post("/motor2/sequence")
async def run_motor2_sequence(payload: SequencePayload):
    formatted_steps = []
    for s in payload.steps:
        formatted_steps.append({
            "pos": s.position if s.position is not None else s.pos,
            "pause": s.pause_after if s.pause_after else s.pause,
            "velocity": s.velocity,
            "acceleration": s.acceleration
        })
    return get_motor("motor2").run_sequence(formatted_steps)

# ==========================================
# --- Multi-Motor Sequence Route ---
# ==========================================
@app.post("/sequence/run_both")
async def run_both_sequences(payload: DualSequencePayload):
    def _run_synchronized_threads():
        m1 = get_motor("motor1")
        m2 = get_motor("motor2")
        
        steps1 = [{
            "pos": s.position if s.position is not None else s.pos, 
            "pause": s.pause_after if s.pause_after else s.pause,
            "velocity": s.velocity,
            "acceleration": s.acceleration
        } for s in payload.motor1_steps]
        
        steps2 = [{
            "pos": s.position if s.position is not None else s.pos, 
            "pause": s.pause_after if s.pause_after else s.pause,
            "velocity": s.velocity,
            "acceleration": s.acceleration
        } for s in payload.motor2_steps]
        
        res1 = m1.run_sequence(steps1) if steps1 else {"status": "no_steps"}
        res2 = m2.run_sequence(steps2) if steps2 else {"status": "no_steps"}
        return res1, res2

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _run_synchronized_threads)
    
    return {"status": "both_sequences_started"}

app.mount("/", StaticFiles(directory="static", html=True), name="static")