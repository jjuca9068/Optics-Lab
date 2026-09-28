import threading
import io
import numpy as np
from PIL import Image

class CameraController:
    """Wraps the PixeLINK camera. Set use_real_hardware=True once the camera is connected."""

    def __init__(self, use_real_hardware=False):
        self.use_real_hardware = use_real_hardware
        self._lock = threading.Lock()  # prevents concurrent requests from corrupting camera comms

        # mock-mode state
        self._exposure = 10.0  # ms, arbitrary default
        self._gain = 1.0       # arbitrary default (dB or unitless depending on camera)
        self._width = 640      # pixels
        self._height = 480     # pixels

        if self.use_real_hardware:
            try:
                from pixelinkWrapper import PxLApi
                ret = PxLApi.initialize(0)
                
                if PxLApi.apiSuccess(ret[0]):
                    self.handle = ret[1]
                    # camera must be streaming before frames can be grabbed
                    PxLApi.setStreamState(self.handle, PxLApi.StreamState.START)
                    print("Successfully connected to physical PixeLINK camera.")
                    
                    # Apply initial defaults
                    self.set_exposure(30.0)
                    self.set_gain(6.0)
                else:
                    print(f"Failed to initialize PixeLINK camera. API Error Code: {ret[0]}")
                    print("Falling back to mock software mode.")
                    self.use_real_hardware = False
            except Exception as e:
                print(f"PixeLINK library error: {e}")
                print("Falling back to mock software mode.")
                self.use_real_hardware = False

    # --- Frame grabbing ---

    def get_frame_jpeg(self):
        """Returns a single frame already encoded as JPEG bytes, ready to stream to a browser."""
        with self._lock:
            if self.use_real_hardware:
                return self._get_real_frame_jpeg()
            else:
                # FAKE FRAME: Lightweight pulsing frame for testing
                import time
                pulse_val = int((time.time() * 50) % 200) + 25 
                arr = np.full((self._height, self._width), pulse_val, dtype=np.uint8)
                image = Image.fromarray(arr)
                buffer = io.BytesIO()
                image.save(buffer, format="JPEG")
                return buffer.getvalue()

    def _get_real_frame_jpeg(self):
        from pixelinkWrapper import PxLApi
        import ctypes

        raw_buffer = ctypes.create_string_buffer(self._width * self._height * 4)

        ret = PxLApi.getNextFrame(self.handle, raw_buffer)
        if not PxLApi.apiSuccess(ret[0]):
            return None 
        frame_descriptor = ret[1]
        ret2 = PxLApi.formatImage(raw_buffer, frame_descriptor, PxLApi.ImageFormat.JPEG)
        if not PxLApi.apiSuccess(ret2[0]):
            return None

        return ret2[1]  # already JPEG-encoded bytes

    # --- Exposure ---

    def set_exposure(self, exposure_ms):
        with self._lock:
            if self.use_real_hardware:
                from pixelinkWrapper import PxLApi
                PxLApi.setFeature(
                    self.handle, PxLApi.FeatureId.EXPOSURE,
                    PxLApi.FeatureFlags.MANUAL, [exposure_ms / 1000.0]  # PixeLINK expects seconds
                )
            else:
                self._exposure = exposure_ms

    def get_exposure(self):
        with self._lock:
            if self.use_real_hardware:
                from pixelinkWrapper import PxLApi
                ret = PxLApi.getFeature(self.handle, PxLApi.FeatureId.EXPOSURE)
                return ret[2][0] * 1000.0  # convert back to ms
            return self._exposure

    # --- Gain ---

    def set_gain(self, gain):
        with self._lock:
            if self.use_real_hardware:
                from pixelinkWrapper import PxLApi
                PxLApi.setFeature(
                    self.handle, PxLApi.FeatureId.GAIN,
                    PxLApi.FeatureFlags.MANUAL, [gain]
                )
            else:
                self._gain = gain

    def get_gain(self):
        with self._lock:
            if self.use_real_hardware:
                from pixelinkWrapper import PxLApi
                ret = PxLApi.getFeature(self.handle, PxLApi.FeatureId.GAIN)
                return ret[2][0]
            return self._gain

    # --- Resolution (ROI: region of interest width/height) ---

    def set_resolution(self, width, height):
        """width/height in pixels. PixeLINK's ROI feature expects [offsetX, offsetY, width, height]."""
        with self._lock:
            if self.use_real_hardware:
                from pixelinkWrapper import PxLApi
                
                # Maximum sensor resolution (based on your camera's max capability)
                MAX_SENSOR_WIDTH = 5472
                MAX_SENSOR_HEIGHT = 3648
                
                # Calculate offsets to perfectly center the ROI on the sensor
                # (We do integer division by 2, and multiply by 2 to ensure even numbers, 
                # as some camera sensors require offsets to be even pixels)
                offset_x = int((MAX_SENSOR_WIDTH - width) / 2) // 2 * 2
                offset_y = int((MAX_SENSOR_HEIGHT - height) / 2) // 2 * 2
                
                # Failsafe to prevent negative offsets if a larger resolution is passed
                offset_x = max(0, offset_x)
                offset_y = max(0, offset_y)

                PxLApi.setStreamState(self.handle, PxLApi.StreamState.STOP)
                # Pass the calculated offsets instead of [0, 0]
                PxLApi.setFeature(
                    self.handle, PxLApi.FeatureId.ROI,
                    PxLApi.FeatureFlags.MANUAL, [offset_x, offset_y, width, height]
                )
                PxLApi.setStreamState(self.handle, PxLApi.StreamState.START)
                
                self._width = width
                self._height = height
            else:
                self._width = width
                self._height = height

    def get_resolution(self):
        with self._lock:
            if self.use_real_hardware:
                from pixelinkWrapper import PxLApi
                ret = PxLApi.getFeature(self.handle, PxLApi.FeatureId.ROI)
                _, _, width, height = ret[2]
                return {"width": int(width), "height": int(height)}
            return {"width": self._width, "height": self._height}

    # --- Auto-Exposure & Gain Scaling ---

    def auto_scale(self, target_brightness=120.0):
        """
        Automatically scales exposure first. If exposure reaches its upper limit 
        and the image is still too dark, it scales up the gain.
        """
        frame_bytes = self.get_frame_jpeg()
        if not frame_bytes:
            return {"status": "error", "message": "Could not grab frame for auto-scaling."}

        # Measure current mean brightness using a grayscale conversion
        image = Image.open(io.BytesIO(frame_bytes)).convert('L')
        arr = np.array(image)
        mean_brightness = float(np.mean(arr))

        current_exp = self.get_exposure()
        current_gain = self.get_gain()
        
        # Define limits (adjust max exposure/gain based on your hardware specifics)
        max_exposure = 100.0  # ms
        min_exposure = 1.0    # ms
        max_gain = 20.0       # dB or unitless
        min_gain = 0.0

        error = target_brightness - mean_brightness

        if abs(error) > 8:  # Tolerance window to prevent jitter
            adjustment_factor = target_brightness / (mean_brightness + 1e-5)
            
            if error > 0:
                # Image is too dark: Increase exposure first
                new_exp = current_exp * adjustment_factor
                if new_exp > max_exposure:
                    # Exposure is maxed out, start increasing gain instead
                    self.set_exposure(max_exposure)
                    new_gain = min(max_gain, current_gain * 1.2)
                    self.set_gain(new_gain)
                else:
                    self.set_exposure(max(min_exposure, new_exp))
            else:
                # Image is too bright: Reduce gain first, then reduce exposure
                if current_gain > min_gain + 0.5:
                    new_gain = max(min_gain, current_gain / 1.2)
                    self.set_gain(new_gain)
                else:
                    new_exp = max(min_exposure, current_exp * adjustment_factor)
                    self.set_exposure(new_exp)

        return {
            "status": "success",
            "brightness": mean_brightness,
            "exposure": self.get_exposure(),
            "gain": self.get_gain()
        }