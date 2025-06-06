from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import subprocess
import configparser
import json
import threading
import time
from gamepad_control import GamepadController

app = Flask(__name__)
CORS(app)

class BotOpsBackend:
    def __init__(self):
        self.controller = None
        self.chrome_path = 'C:/Program Files/Google/Chrome/Application/chrome.exe'
        self.shortcuts_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Shortcuts")
        self.bo6_url = "https://www.xbox.com/en-US/play/launch/call-of-duty-black-ops-6---cross-gen-bundle/9PF528M6CRHQ"
        
        # Load config
        self.config = configparser.ConfigParser()
        self.config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini")
        self.load_config()
        
        # State tracking
        self.browser_sessions_opened = False
        self.active_sessions_count = 0
        self.available_profiles = self.scan_profiles()

    def load_config(self):
        """Load configuration from file"""
        try:
            self.config.read(self.config_path)
            
            # Ensure sections exist
            if not self.config.has_section('Movement'):
                self.config.add_section('Movement')
            if not self.config.has_section('AntiAFK'):
                self.config.add_section('AntiAFK')
                
            # Set defaults if not present
            movement_defaults = {
                'look_intensity': '1.5',
                'move_intensity': '0.3',
                'forward_intensity': '1.0',
                'jump_chance': '0.15',
                'jump_interval': '3.0',
                'weapon_switch_chance': '0.1',
                'weapon_switch_interval': '5.0',
                'min_movement_duration': '2.0',
                'max_movement_duration': '8.0',
                'min_break_duration': '3.0',
                'max_break_duration': '12.0'
            }
            
            afk_defaults = {
                'interval': '60.0',
                'right_bumper_duration': '0.1',
                'left_bumper_duration': '0.2',
                'delay_between_buttons': '1.0'
            }
            
            for key, value in movement_defaults.items():
                if not self.config.has_option('Movement', key):
                    self.config.set('Movement', key, value)
                    
            for key, value in afk_defaults.items():
                if not self.config.has_option('AntiAFK', key):
                    self.config.set('AntiAFK', key, value)
            
            self.save_config()
            
        except Exception as e:
            print(f"Error loading config: {e}")

    def save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_path, 'w') as configfile:
                self.config.write(configfile)
        except Exception as e:
            print(f"Error saving config: {e}")

    def scan_profiles(self):
        """Scan for available Chrome profiles in shortcuts directory"""
        profiles = []
        print(f"Scanning for profiles in: {self.shortcuts_path}")
        
        # Create shortcuts directory if it doesn't exist
        if not os.path.exists(self.shortcuts_path):
            print(f"Creating shortcuts directory: {self.shortcuts_path}")
            try:
                os.makedirs(self.shortcuts_path)
            except Exception as e:
                print(f"Failed to create shortcuts directory: {e}")
                return profiles
        
        # Scan for profile shortcuts
        if os.path.exists(self.shortcuts_path):
            files_found = os.listdir(self.shortcuts_path)
            print(f"Files in shortcuts directory: {files_found}")
            
            for i in range(1, 21):  # b1 through b20
                profile_name = f"b{i}"
                shortcut_path = os.path.join(self.shortcuts_path, f"{profile_name}.lnk")
                
                if os.path.exists(shortcut_path):
                    profiles.append({
                        'name': profile_name,
                        'path': shortcut_path,
                        'display_name': f"Bot {i}"
                    })
                    print(f"Found profile: {profile_name}")
        
        print(f"Total profiles found: {len(profiles)}")
        return profiles

# Initialize backend
backend = BotOpsBackend()

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get backend status"""
    controller_connected = False
    movement_running = False
    anti_afk_running = False
    
    try:
        if backend.controller and hasattr(backend.controller, 'gamepad'):
            controller_connected = backend.controller.gamepad is not None
            if hasattr(backend.controller, 'movement_enabled'):
                movement_running = backend.controller.movement_enabled
            if hasattr(backend.controller, 'anti_afk_enabled'):
                anti_afk_running = backend.controller.anti_afk_enabled
    except Exception as e:
        print(f"Error getting controller status: {e}")
    
    return jsonify({
        'status': 'running',
        'controller_connected': controller_connected,
        'movement_running': movement_running,
        'anti_afk_running': anti_afk_running,
        'browser_sessions_opened': backend.browser_sessions_opened,
        'active_sessions_count': backend.active_sessions_count
    })

@app.route('/api/profiles', methods=['GET'])
def get_profiles():
    """Get available profiles"""
    # Refresh profiles list
    backend.available_profiles = backend.scan_profiles()
    
    return jsonify({
        'profiles': backend.available_profiles,
        'count': len(backend.available_profiles)
    })

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration"""
    settings = {}
    
    try:
        # Get Movement settings
        if backend.config.has_section('Movement'):
            for key in backend.config.options('Movement'):
                try:
                    settings[key] = backend.config.getfloat('Movement', key)
                except ValueError:
                    settings[key] = backend.config.get('Movement', key)
        
        # Get AntiAFK settings
        if backend.config.has_section('AntiAFK'):
            for key in backend.config.options('AntiAFK'):
                try:
                    settings[key] = backend.config.getfloat('AntiAFK', key)
                except ValueError:
                    settings[key] = backend.config.get('AntiAFK', key)
    except Exception as e:
        print(f"Error getting config: {e}")
    
    return jsonify({
        'settings': settings
    })

@app.route('/api/config', methods=['POST'])
def save_config():
    """Save configuration"""
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
            
        settings = data.get('settings', {})
        if not settings:
            return jsonify({'success': False, 'error': 'No settings provided'}), 400
        
        # Update config
        for key, value in settings.items():
            try:
                # Determine which section this setting belongs to
                if key in ['interval', 'right_bumper_duration', 'left_bumper_duration', 'delay_between_buttons']:
                    backend.config.set('AntiAFK', key, str(value))
                else:
                    backend.config.set('Movement', key, str(value))
            except Exception as e:
                print(f"Error setting config value {key}={value}: {e}")
        
        backend.save_config()
        
        # Update controller config if connected
        if backend.controller and hasattr(backend.controller, 'load_config'):
            try:
                backend.controller.load_config()
            except Exception as e:
                print(f"Error updating controller config: {e}")
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error saving config: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/browser/open', methods=['POST'])
def open_browser_sessions():
    """Open browser sessions - handled by Electron frontend"""
    try:
        data = request.json
        print(f"Received browser open request: {data}")
        
        # Get requested count, default to 1 if not provided
        requested_count = 1
        if data and 'count' in data:
            try:
                requested_count = int(data['count'])
            except (ValueError, TypeError):
                print(f"Invalid count value: {data.get('count')}, using default 1")
                requested_count = 1
        
        print(f"Requested count: {requested_count}")
        
        # Validate count
        if requested_count < 1:
            error_msg = 'Invalid count: must be at least 1'
            print(f"Error: {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 400
        
        # Refresh profiles list
        backend.available_profiles = backend.scan_profiles()
        print(f"Available profiles: {len(backend.available_profiles)}")
        
        # Handle case where no profiles are found
        if not backend.available_profiles:
            # For development/testing, create mock profiles
            print("No profiles found, creating mock profiles for testing")
            mock_profiles = []
            for i in range(1, min(requested_count + 1, 6)):  # Create up to 5 mock profiles
                mock_profiles.append({
                    'name': f'b{i}',
                    'path': f'mock_path_{i}',
                    'display_name': f'Bot {i}'
                })
            
            backend.available_profiles = mock_profiles
            print(f"Created {len(mock_profiles)} mock profiles")
        
        if requested_count > len(backend.available_profiles):
            error_msg = f'Not enough profiles available. Found {len(backend.available_profiles)}, requested {requested_count}'
            print(f"Error: {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 400
        
        # Update backend state
        backend.browser_sessions_opened = True
        backend.active_sessions_count = requested_count
        
        # Select profiles to use
        profiles_to_use = backend.available_profiles[:requested_count]
        
        print(f"Opening {requested_count} browser sessions with profiles: {[p['name'] for p in profiles_to_use]}")
        
        return jsonify({
            'success': True,
            'profiles': profiles_to_use,
            'count': requested_count,
            'base_url': 'https://xbox.com/play',
            'message': f'Ready to create {requested_count} sessions'
        })
        
    except Exception as e:
        print(f"Error opening browser sessions: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/browser/launch', methods=['POST'])
def launch_black_ops():
    """Launch Black Ops 6 in browser sessions"""
    try:
        if not backend.browser_sessions_opened:
            error_msg = 'Browser sessions not opened'
            print(f"Error: {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 400
        
        # Return launch information for Electron to use
        profiles_to_use = backend.available_profiles[:backend.active_sessions_count]
        
        print(f"Launching Black Ops 6 in {backend.active_sessions_count} sessions")
        
        return jsonify({
            'success': True,
            'profiles': profiles_to_use,
            'count': backend.active_sessions_count,
            'launch_url': backend.bo6_url,
            'message': f'Launching Black Ops 6 in {backend.active_sessions_count} sessions'
        })
        
    except Exception as e:
        print(f"Error launching Black Ops 6: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/browser/close', methods=['POST'])
def close_browser_sessions():
    """Close browser sessions"""
    try:
        print(f"Closing {backend.active_sessions_count} browser sessions")
        
        # Reset state
        backend.browser_sessions_opened = False
        backend.active_sessions_count = 0
        
        return jsonify({
            'success': True,
            'message': 'Sessions closed successfully'
        })
        
    except Exception as e:
        print(f"Error closing browser sessions: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/controller/connect', methods=['POST'])
def connect_controller():
    """Connect controller"""
    try:
        if not backend.controller:
            backend.controller = GamepadController()
        
        # Check if controller has gamepad attribute and if it's None
        if not hasattr(backend.controller, 'gamepad') or backend.controller.gamepad is None:
            if hasattr(backend.controller, 'connect') and backend.controller.connect():
                if hasattr(backend.controller, 'start'):
                    backend.controller.start()
                return jsonify({'success': True, 'message': 'Controller connected successfully'})
            else:
                return jsonify({'success': False, 'error': 'Failed to connect controller - no gamepad found'}), 500
        else:
            return jsonify({'success': True, 'message': 'Controller already connected'})
            
    except Exception as e:
        print(f"Controller connection error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/controller/disconnect', methods=['POST'])
def disconnect_controller():
    """Disconnect controller"""
    try:
        if backend.controller:
            if hasattr(backend.controller, 'disconnect'):
                backend.controller.disconnect()
            backend.controller = None
        
        return jsonify({'success': True, 'message': 'Controller disconnected'})
        
    except Exception as e:
        print(f"Controller disconnection error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/movement/toggle', methods=['POST'])
def toggle_movement():
    """Toggle movement bot"""
    try:
        if not backend.controller:
            return jsonify({'success': False, 'error': 'Controller not connected'}), 400
        
        if not hasattr(backend.controller, 'toggle_movement'):
            return jsonify({'success': False, 'error': 'Controller does not support movement toggle'}), 400
        
        is_enabled = backend.controller.toggle_movement()
        return jsonify({
            'success': True,
            'running': is_enabled,
            'message': f'Movement bot {"started" if is_enabled else "stopped"}'
        })
        
    except Exception as e:
        print(f"Movement toggle error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/anti-afk/toggle', methods=['POST'])
def toggle_anti_afk():
    """Toggle anti-AFK"""
    try:
        if not backend.controller:
            return jsonify({'success': False, 'error': 'Controller not connected'}), 400
        
        if not hasattr(backend.controller, 'toggle_anti_afk'):
            return jsonify({'success': False, 'error': 'Controller does not support anti-AFK toggle'}), 400
        
        is_enabled = backend.controller.toggle_anti_afk()
        return jsonify({
            'success': True,
            'running': is_enabled,
            'message': f'Anti-AFK {"started" if is_enabled else "stopped"}'
        })
        
    except Exception as e:
        print(f"Anti-AFK toggle error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/class/select', methods=['POST'])
def select_class():
    """Select class"""
    try:
        if not backend.controller:
            return jsonify({'success': False, 'error': 'Controller not connected'}), 400
        
        if not hasattr(backend.controller, 'select_class'):
            return jsonify({'success': False, 'error': 'Controller does not support class selection'}), 400
        
        success = backend.controller.select_class()
        return jsonify({
            'success': success,
            'message': 'Class selection completed' if success else 'Class selection failed'
        })
        
    except Exception as e:
        print(f"Class selection error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    print("Bot Ops Backend starting...")
    print(f"Shortcuts directory: {backend.shortcuts_path}")
    print(f"Found {len(backend.available_profiles)} profiles")
    for profile in backend.available_profiles:
        print(f"  - {profile['name']}: {profile['path']}")
    
    # Run the Flask app
    app.run(
        host='localhost',
        port=8080,
        debug=False,  # Set to True for development
        threaded=True
    )