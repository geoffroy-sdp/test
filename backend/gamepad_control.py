import vgamepad as vg
import time
import random
import math
import threading
import configparser
import os
 
class GamepadController:
    def __init__(self):
        self.gamepad = None
        self.running = False
        self.movement_enabled = False
        self.anti_afk_enabled = False
        self.thread = None
        self.anti_afk_thread = None
        
        # Load config
        self.config = configparser.ConfigParser()
        self.config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini")
        self.load_config()
    
    def load_config(self):
        """Load settings from config file"""
        self.config.read(self.config_path)
        
        # Movement settings
        self.look_intensity = self.config.getfloat('Movement', 'look_intensity', fallback=1.5)  # Increased default
        self.move_intensity = self.config.getfloat('Movement', 'move_intensity', fallback=0.3)
        self.forward_intensity = self.config.getfloat('Movement', 'forward_intensity', fallback=1.0)
        self.ads_chance = self.config.getfloat('Movement', 'ads_chance', fallback=0.1)
        self.jump_chance = self.config.getfloat('Movement', 'jump_chance', fallback=0.15)
        self.jump_interval = self.config.getfloat('Movement', 'jump_interval', fallback=3.0)
        self.weapon_switch_chance = self.config.getfloat('Movement', 'weapon_switch_chance', fallback=0.1)
        self.weapon_switch_interval = self.config.getfloat('Movement', 'weapon_switch_interval', fallback=5.0)
        self.strafe_chance = self.config.getfloat('Movement', 'strafe_chance', fallback=0.2)
        self.forward_bias = self.config.getfloat('Movement', 'forward_bias', fallback=0.7)
        self.shoot_chance = self.config.getfloat('Movement', 'shoot_chance', fallback=0.3)
        self.shoot_duration = self.config.getfloat('Movement', 'shoot_duration', fallback=0.2)
        self.crouch_chance = self.config.getfloat('Movement', 'crouch_chance', fallback=0.3)
        self.x_button_chance = self.config.getfloat('Movement', 'x_button_chance', fallback=0.3)
        self.x_button_interval = self.config.getfloat('Movement', 'x_button_interval', fallback=5.0)
        self.min_movement_duration = self.config.getfloat('Movement', 'min_movement_duration', fallback=2.0)
        self.max_movement_duration = self.config.getfloat('Movement', 'max_movement_duration', fallback=8.0)
        self.min_break_duration = self.config.getfloat('Movement', 'min_break_duration', fallback=3.0)
        self.max_break_duration = self.config.getfloat('Movement', 'max_break_duration', fallback=12.0)
        
        # Anti-AFK settings
        self.anti_afk_interval = self.config.getfloat('AntiAFK', 'interval', fallback=60)
        self.right_bumper_duration = self.config.getfloat('AntiAFK', 'right_bumper_duration', fallback=0.1)
        self.left_bumper_duration = self.config.getfloat('AntiAFK', 'left_bumper_duration', fallback=0.1)
        self.delay_between_buttons = self.config.getfloat('AntiAFK', 'delay_between_buttons', fallback=0.5)
    
    def save_config(self):
        """Save current settings to config file"""
        # Movement settings
        self.config['Movement'] = {
            'look_intensity': str(self.look_intensity),
            'move_intensity': str(self.move_intensity),
            'forward_intensity': str(self.forward_intensity),
            'ads_chance': str(self.ads_chance),
            'jump_chance': str(self.jump_chance),
            'jump_interval': str(self.jump_interval),
            'weapon_switch_chance': str(self.weapon_switch_chance),
            'weapon_switch_interval': str(self.weapon_switch_interval),
            'strafe_chance': str(self.strafe_chance),
            'forward_bias': str(self.forward_bias),
            'shoot_chance': str(self.shoot_chance),
            'shoot_duration': str(self.shoot_duration),
            'crouch_chance': str(self.crouch_chance),
            'x_button_chance': str(self.x_button_chance),
            'x_button_interval': str(self.x_button_interval),
            'min_movement_duration': str(self.min_movement_duration),
            'max_movement_duration': str(self.max_movement_duration),
            'min_break_duration': str(self.min_break_duration),
            'max_break_duration': str(self.max_break_duration)
        }
        
        # Anti-AFK settings
        self.config['AntiAFK'] = {
            'interval': str(self.anti_afk_interval),
            'right_bumper_duration': str(self.right_bumper_duration),
            'left_bumper_duration': str(self.left_bumper_duration),
            'delay_between_buttons': str(self.delay_between_buttons)
        }
        
        with open(self.config_path, 'w') as configfile:
            self.config.write(configfile)
    
    def update_config(self, section, key, value):
        """Update a specific config value"""
        if section == 'Movement':
            if key == 'look_intensity': self.look_intensity = float(value)
            elif key == 'move_intensity': self.move_intensity = float(value)
            elif key == 'forward_intensity': self.forward_intensity = float(value)
            elif key == 'ads_chance': self.ads_chance = float(value)
            elif key == 'jump_chance': self.jump_chance = float(value)
            elif key == 'jump_interval': self.jump_interval = float(value)
            elif key == 'weapon_switch_chance': self.weapon_switch_chance = float(value)
            elif key == 'weapon_switch_interval': self.weapon_switch_interval = float(value)
            elif key == 'strafe_chance': self.strafe_chance = float(value)
            elif key == 'forward_bias': self.forward_bias = float(value)
            elif key == 'shoot_chance': self.shoot_chance = float(value)
            elif key == 'shoot_duration': self.shoot_duration = float(value)
            elif key == 'crouch_chance': self.crouch_chance = float(value)
            elif key == 'x_button_chance': self.x_button_chance = float(value)
            elif key == 'x_button_interval': self.x_button_interval = float(value)
            elif key == 'min_movement_duration': self.min_movement_duration = float(value)
            elif key == 'max_movement_duration': self.max_movement_duration = float(value)
            elif key == 'min_break_duration': self.min_break_duration = float(value)
            elif key == 'max_break_duration': self.max_break_duration = float(value)
        elif section == 'AntiAFK':
            if key == 'interval': self.anti_afk_interval = float(value)
            elif key == 'right_bumper_duration': self.right_bumper_duration = float(value)
            elif key == 'left_bumper_duration': self.left_bumper_duration = float(value)
            elif key == 'delay_between_buttons': self.delay_between_buttons = float(value)
    
    def connect(self):
        """Connect the virtual gamepad"""
        if self.gamepad is None:
            self.gamepad = vg.VX360Gamepad()
            time.sleep(1)  # Wait for gamepad to initialize
            return True
        return False
    
    def disconnect(self):
        """Disconnect the virtual gamepad"""
        self.stop()
        if self.gamepad:
            self.gamepad = None
    
    def _smooth_value(self, current, target, smooth_factor=0.1):
        """Smoothly interpolate between current and target value"""
        return current + (target - current) * smooth_factor
    
    def _generate_smooth_random(self, intensity):
        """Generate a smooth random value between -intensity and +intensity"""
        return (random.random() * 2 - 1) * intensity
    
    def _anti_afk_loop(self):
        """Anti-AFK loop that periodically presses buttons"""
        print("Anti-AFK loop started")
        while self.running and self.gamepad:
            try:
                if not self.anti_afk_enabled:
                    time.sleep(0.1)
                    continue
 
                print("Anti-AFK: Pressing right bumper")
                self.gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER)
                self.gamepad.update()
                time.sleep(self.right_bumper_duration)
                self.gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER)
                self.gamepad.update()
 
                time.sleep(self.delay_between_buttons)
 
                print("Anti-AFK: Pressing left bumper")
                self.gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER)
                self.gamepad.update()
                time.sleep(self.left_bumper_duration)
                self.gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER)
                self.gamepad.update()
 
                print(f"Anti-AFK: Waiting {self.anti_afk_interval} seconds")
                time.sleep(self.anti_afk_interval)
 
            except Exception as e:
                print(f"Error in anti-AFK loop: {e}")
                time.sleep(1)
 
        print("Anti-AFK loop ended")
    
    def start(self):
        """Start the controller"""
        if not self.running and self.gamepad:
            print("Starting controller...")
            self.running = True
            self.movement_enabled = False  # Start with movement disabled
            
            # Start movement thread
            self.thread = threading.Thread(target=self._movement_loop)
            self.thread.daemon = True
            self.thread.start()
            
            print("Controller started")
    
    def stop(self):
        """Stop the controller"""
        self.running = False
        self.movement_enabled = False
        self.anti_afk_enabled = False
        if self.thread:
            self.thread.join(timeout=1)
            self.thread = None
        if self.anti_afk_thread:
            self.anti_afk_thread.join(timeout=1)
            self.anti_afk_thread = None
        print("Controller stopped")
    
    def toggle_movement(self):
        """Toggle movement bot"""
        print(f"Toggling movement from {self.movement_enabled} to {not self.movement_enabled}")
        self.movement_enabled = not self.movement_enabled
        return self.movement_enabled
    
    def toggle_anti_afk(self):
        """Toggle anti-AFK"""
        print(f"Toggling anti-AFK from {self.anti_afk_enabled} to {not self.anti_afk_enabled}")
        if not self.anti_afk_enabled:
            self.anti_afk_enabled = True
            self.anti_afk_thread = threading.Thread(target=self._anti_afk_loop)
            self.anti_afk_thread.daemon = True
            self.anti_afk_thread.start()
        else:
            self.anti_afk_enabled = False
            if self.anti_afk_thread:
                self.anti_afk_thread.join(timeout=1)
                self.anti_afk_thread = None
        return self.anti_afk_enabled
    
    def select_class(self):
        """Select a class by pressing A button 5 times"""
        if not self.gamepad:
            print("Gamepad not connected")
            return False
            
        print("Selecting class...")
        time.sleep(2)  # Initial wait
        
        for i in range(5):
            print(f"Class selection press {i+1}/5")
            self.gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_A)
            self.gamepad.update()
            time.sleep(0.1)  # Short press duration
            self.gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_A)
            self.gamepad.update()
            time.sleep(0.9)  # Wait remaining time to make it 1 second total
            
        print("Class selection complete")
        return True
    
    def _movement_loop(self):
        """Movement loop that simulates random controller inputs with breaks"""
        print("Movement loop started")
        last_x_press = 0  # Track last X button press time
        last_movement_was_forward = False  # Track last movement direction
        current_move_x = 0  # Track current movement values for smooth transitions
        current_move_y = 0
        current_look_x = 0
        current_look_y = 0
        last_jump_time = 0  # Track last jump time
        last_weapon_switch_time = 0  # Track last weapon switch time
        
        while self.running and self.gamepad:
            try:
                if not self.movement_enabled:
                    # Reset controller state when movement is disabled
                    self.gamepad.left_joystick_float(x_value_float=0, y_value_float=0)
                    self.gamepad.right_joystick_float(x_value_float=0, y_value_float=0)
                    self.gamepad.left_trigger_float(value_float=0)
                    self.gamepad.right_trigger_float(value_float=0)
                    self.gamepad.update()
                    time.sleep(0.1)
                    continue
                
                # Automatically disable Anti-AFK when movement starts
                if self.anti_afk_enabled:
                    print("Automatically disabling Anti-AFK")
                    self.toggle_anti_afk()
                
                # Randomize movement duration for this cycle
                current_movement_duration = random.uniform(self.min_movement_duration, self.max_movement_duration)
                current_break_duration = random.uniform(self.min_break_duration, self.max_break_duration)
                
                # Movement phase
                print(f"Starting movement phase for {current_movement_duration:.1f} seconds")
                movement_start_time = time.time()
                
                # Choose movement type based on previous movement
                if last_movement_was_forward:
                    movement_type = 'backward'
                else:
                    movement_type = 'forward'
                last_movement_was_forward = (movement_type == 'forward')
                
                print(f"Movement type: {movement_type}")
                
                # Continue movement until duration is reached or movement is disabled
                while self.running and self.movement_enabled and (time.time() - movement_start_time) < current_movement_duration:
                    current_time = time.time()
                    
                    # X button press check
                    if current_time - last_x_press >= self.x_button_interval and random.random() < self.x_button_chance:
                        print("X button pressed")
                        self.gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_X)
                        self.gamepad.update()
                        time.sleep(0.1)
                        self.gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_X)
                        self.gamepad.update()
                        last_x_press = current_time
                    
                    # Jump check
                    if current_time - last_jump_time >= self.jump_interval and random.random() < self.jump_chance:
                        print("Jumping")
                        self.gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_A)
                        self.gamepad.update()
                        time.sleep(0.1)
                        self.gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_A)
                        self.gamepad.update()
                        last_jump_time = current_time
                    
                    # Weapon switch check
                    if current_time - last_weapon_switch_time >= self.weapon_switch_interval and random.random() < self.weapon_switch_chance:
                        print("Switching weapon")
                        self.gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_Y)
                        self.gamepad.update()
                        time.sleep(0.1)
                        self.gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_Y)
                        self.gamepad.update()
                        last_weapon_switch_time = current_time
                    
                    # Generate target look values
                    target_look_x = random.uniform(-1, 1) * self.look_intensity * 1.5  # Increased look intensity
                    target_look_y = random.uniform(-1, 1) * self.look_intensity * 1.5  # Increased look intensity
                    
                    # Smoothly interpolate look values
                    current_look_x = self._smooth_value(current_look_x, target_look_x, 0.1)
                    current_look_y = self._smooth_value(current_look_y, target_look_y, 0.1)
                    
                    # Set movement based on type with smooth transitions
                    target_move_x = random.uniform(-0.3, 0.3) * self.move_intensity  # Small side-to-side movement
                    if movement_type == 'forward':
                        target_move_y = random.uniform(0.7, 1.0) * self.forward_intensity
                    else:  # backward
                        target_move_y = random.uniform(-0.7, -1.0) * self.forward_intensity
                    
                    # Smoothly interpolate movement values
                    current_move_x = self._smooth_value(current_move_x, target_move_x, 0.15)
                    current_move_y = self._smooth_value(current_move_y, target_move_y, 0.15)
                    
                    # Apply movements with clamping
                    current_look_x = max(min(current_look_x, 1), -1)
                    current_look_y = max(min(current_look_y, 1), -1)
                    current_move_x = max(min(current_move_x, 1), -1)
                    current_move_y = max(min(current_move_y, 1), -1)
                    
                    print(f"Movement: type={movement_type}, pos=({current_move_x:.2f}, {current_move_y:.2f})")
                    
                    self.gamepad.right_joystick_float(x_value_float=current_look_x, y_value_float=current_look_y)
                    self.gamepad.left_joystick_float(x_value_float=current_move_x, y_value_float=current_move_y)
                    
                    # Random actions with configured chances
                    if random.random() < self.ads_chance:
                        print("ADS triggered")
                        self.gamepad.left_trigger_float(value_float=1.0)
                        time.sleep(0.1)
                    else:
                        self.gamepad.left_trigger_float(value_float=0.0)
                    
                    if random.random() < self.shoot_chance:
                        print("Shooting")
                        self.gamepad.right_trigger_float(value_float=1.0)
                        self.gamepad.update()
                        time.sleep(self.shoot_duration)
                        self.gamepad.right_trigger_float(value_float=0.0)
                        self.gamepad.update()
                    
                    self.gamepad.update()
                    time.sleep(0.01)  # Small sleep to prevent excessive CPU usage
                
                # Break phase - only if movement is still enabled
                if self.running and self.movement_enabled:
                    print(f"Starting break phase for {current_break_duration:.1f} seconds")
                    
                    # Reset controller state during break
                    self.gamepad.left_joystick_float(x_value_float=0, y_value_float=0)
                    self.gamepad.right_joystick_float(x_value_float=0, y_value_float=0)
                    self.gamepad.left_trigger_float(value_float=0)
                    self.gamepad.right_trigger_float(value_float=0)
                    self.gamepad.update()
                    
                    break_start = time.time()
                    while self.running and self.movement_enabled and (time.time() - break_start) < current_break_duration:
                        time.sleep(0.1)  # Check movement state every 100ms
                    
                    print("Break phase complete")
            
            except Exception as e:
                print(f"Error in movement loop: {e}")
                time.sleep(1)
        
        print("Movement loop ended")
 
if __name__ == "__main__":
    # Example usage
    controller = GamepadController()
    
    try:
        print("Connecting gamepad...")
        if controller.connect():
            print("Gamepad connected.")
        else:
            print("Failed to connect gamepad.")
            exit(1)
        
        print("Starting controller automation...")
        controller.start()
        
        # Keep running until Ctrl+C
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nStopping automation...")
        controller.stop()
        controller.disconnect()
