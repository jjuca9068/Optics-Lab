import time
import threading
import logging
from pylablib.devices import Thorlabs

logger = logging.getLogger("motor_controller")

# Standard scaling factor for Thorlabs Z8 / MTS50 stages
Z8_COUNTS_PER_MM = 34304


class MotorController:
    def __init__(self, serial_number: str, use_real_hardware: bool = True, scale=None):
        self.serial_number = str(serial_number)
        self.use_real_hardware = use_real_hardware
        self.device = None
        self._mock_position = 0.0
        
        # State tracking
        self._is_homing = False
        self._is_executing_sequence = False
        self._is_paused = False
        self._stop_requested = False
        
        # Global speed profiles (restored after sequences)
        self.global_velocity = 1.0
        self.global_acceleration = 1.0
        
        # Stored home offset baseline
        self.home_offset = 0.0  
        self.lock = threading.Lock()

        if self.use_real_hardware:
            try:
                actual_scale = scale if (scale is not None and isinstance(scale, (int, float))) else Z8_COUNTS_PER_MM
                self.device = Thorlabs.KinesisMotor(self.serial_number, scale=actual_scale)
                
                if hasattr(self.device, "enable_channel"):
                    self.device.enable_channel()
                
                logger.info(f"Successfully connected and enabled motor {self.serial_number}")
            except Exception as e:
                logger.error(f"Failed to initialize Thorlabs motor {self.serial_number}: {e}")
                logger.info("Falling back to mock software mode for this controller.")
                self.use_real_hardware = False

    def set_custom_home(self):
        with self.lock:
            if self.use_real_hardware and self.device:
                self.home_offset = self.device.get_position()
            else:
                self._mock_position = 0.0
                self.home_offset = 0.0
        return {"status": "custom_home_set", "raw_offset": round(self.home_offset, 4)}

    def set_velocity_profile(self, velocity: float, acceleration: float):
        """Sets the global maximum velocity and acceleration on the physical device."""
        with self.lock:
            self.global_velocity = float(velocity)
            self.global_acceleration = float(acceleration)
            if self.use_real_hardware and self.device:
                try:
                    self.device.setup_velocity(max_velocity=self.global_velocity, acceleration=self.global_acceleration)
                except Exception as e:
                    logger.error(f"Failed to set velocity profile on motor {self.serial_number}: {e}")

    def stop(self):
        """Immediately halts hardware movement and breaks out of sequence loops."""
        self._stop_requested = True
        self._is_paused = False  
        if self.use_real_hardware and self.device:
            with self.lock:
                self.device.stop()
        return {"status": "stopped"}

    def pause(self):
        """Halts hardware mid-move and puts sequence thread into a waiting state."""
        self._is_paused = True
        if self.use_real_hardware and self.device:
            with self.lock:
                self.device.stop()
        return {"status": "paused"}

    def resume(self):
        """Releases the pause lock so the sequence thread re-issues the move command."""
        self._is_paused = False
        return {"status": "resumed"}

    def home(self):
        """Drives stage back to the stored custom home position."""
        if self._is_homing or self._is_executing_sequence:
            return {"status": "busy"}

        self._is_homing = True
        self._stop_requested = False
        self._is_paused = False

        def _home_task():
            try:
                if self.use_real_hardware and self.device:
                    with self.lock:
                        if hasattr(self.device, "enable_channel"):
                            self.device.enable_channel()
                        
                        try:
                            self.device.setup_velocity(max_velocity=self.global_velocity, acceleration=self.global_acceleration)
                        except: pass
                        
                        self.device.stop()
                        time.sleep(0.1)
                        self.device.move_to(self.home_offset)

                    time.sleep(0.2)
                    start_time = time.time()
                    while self.is_moving_check():
                        if self._stop_requested:
                            with self.lock:
                                self.device.stop()
                            break
                        
                        time.sleep(0.1)
                        if time.time() - start_time > 45:
                            logger.warning(f"Homing wait timed out for motor {self.serial_number}")
                            break
                else:
                    time.sleep(2.0)
                    self._mock_position = 0.0
            except Exception as e:
                logger.error(f"Exception during homing on motor {self.serial_number}: {e}")
            finally:
                self._is_homing = False

        threading.Thread(target=_home_task, daemon=True).start()
        return {"status": "homing_started"}

    def move_to(self, position_mm: float, wait: bool = False, velocity: float = None, acceleration: float = None):
        target_raw = float(position_mm) + self.home_offset

        if self.use_real_hardware and self.device:
            with self.lock:
                if hasattr(self.device, "enable_channel"):
                    self.device.enable_channel()
                
                if velocity is not None and acceleration is not None:
                    try:
                        self.device.setup_velocity(max_velocity=float(velocity), acceleration=float(acceleration))
                    except Exception: pass

                self.device.move_to(target_raw)
            
            if wait:
                time.sleep(0.1)
                while True:
                    # 1. Check stop
                    if self._stop_requested:
                        with self.lock:
                            self.device.stop()
                        break
                    
                    # 2. Check pause
                    if self._is_paused:
                        while self._is_paused and not self._stop_requested:
                            time.sleep(0.1)
                        
                        if self._stop_requested:
                            break
                            
                        # Resumed: re-issue the hardware command to finish the rest of the distance
                        with self.lock:
                            if velocity is not None and acceleration is not None:
                                try:
                                    self.device.setup_velocity(max_velocity=float(velocity), acceleration=float(acceleration))
                                except Exception: pass
                            self.device.move_to(target_raw)
                        
                        # Wait briefly so the motor registers as 'moving' before the next check
                        time.sleep(0.1)
                        continue

                    # 3. Securely check if we are actually done moving
                    if not self.is_moving_check():
                        # Prevent the race condition: double check we didn't just get paused/stopped
                        if not self._is_paused and not self._stop_requested:
                            break
                            
                    time.sleep(0.05)
        else:
            self._mock_position = float(position_mm)

    def is_moving_check(self) -> bool:
        if self.use_real_hardware and self.device:
            try:
                with self.lock:
                    return self.device.is_moving()
            except Exception:
                return False
        return False

    def run_sequence(self, steps: list):
        if self._is_executing_sequence:
            return {"status": "already_running"}

        self._is_executing_sequence = True
        self._stop_requested = False
        self._is_paused = False

        def _sequence_task():
            try:
                for step in steps:
                    if self._stop_requested:
                        break
                        
                    target_pos = step.get("pos", step.get("position", 0.0))
                    pause_time = step.get("pause", step.get("pause_after", 0.0))
                    step_vel = step.get("velocity", None)
                    step_accel = step.get("acceleration", None)
                    
                    self.move_to(target_pos, wait=True, velocity=step_vel, acceleration=step_accel)
                    
                    if self._stop_requested:
                        break
                        
                    # Safely handle the post-move sleep timer
                    if pause_time > 0:
                        start_pause = time.time()
                        elapsed = 0.0
                        
                        while elapsed < pause_time:
                            if self._stop_requested:
                                break
                            
                            if self._is_paused:
                                while self._is_paused and not self._stop_requested:
                                    time.sleep(0.1)
                                
                                # Resume the clock where we left off (freezing the timer)
                                start_pause = time.time() - elapsed
                            
                            time.sleep(0.05)
                            elapsed = time.time() - start_pause
                            
            except Exception as e:
                logger.error(f"Sequence error on motor {self.serial_number}: {e}")
            finally:
                if self.use_real_hardware and self.device:
                    try:
                        with self.lock:
                            self.device.setup_velocity(max_velocity=self.global_velocity, acceleration=self.global_acceleration)
                    except: pass
                
                self._is_executing_sequence = False
                self._stop_requested = False
                self._is_paused = False

        threading.Thread(target=_sequence_task, daemon=True).start()
        return {"status": "sequence_started"}

    def get_status(self):
        if self.use_real_hardware and self.device:
            try:
                with self.lock:
                    raw_pos = self.device.get_position()
                    relative_pos = raw_pos - self.home_offset
                    moving = self.device.is_moving() or self._is_homing or self._is_executing_sequence
                return {
                    "position": round(relative_pos, 4),
                    "raw_position": round(raw_pos, 4),
                    "is_moving": moving,
                    "is_homing": self._is_homing,
                    "is_executing_sequence": self._is_executing_sequence,
                    "running": self._is_executing_sequence,
                    "paused": self._is_paused,
                    "connected": True
                }
            except Exception as e:
                return {
                    "position": 0.0,
                    "is_moving": False,
                    "is_homing": False,
                    "connected": False,
                    "error": str(e)
                }
        else:
            return {
                "position": round(self._mock_position, 4),
                "is_moving": self._is_homing or self._is_executing_sequence,
                "is_homing": self._is_homing,
                "running": self._is_executing_sequence,
                "paused": self._is_paused,
                "connected": False
            }

    def close(self):
        if self.use_real_hardware and self.device:
            try:
                with self.lock:
                    self.device.close()
            except Exception:
                pass