import os, subprocess, time, shutil
from ia_scribe import scribe_globals
from kivy.event import EventDispatcher
from kivy.properties import DictProperty, BooleanProperty
from ia_scribe.abstract import singleton
from ia_scribe.config.config import Scribe3Configuration

config = Scribe3Configuration()
fake_cameras = config.get('fake_cameras', scribe_globals.FAKE_CAMERAS)
@singleton
class Cameras(EventDispatcher):
    camera_ports = DictProperty({'left': None,
                                'right': None,
                                 'foldout': None})
    _calibrated = BooleanProperty(False)

    def initialize(self):
        self.camera_ports = {'left': None,
                             'right': None,
                             'foldout': None}
        ret = self._detect_cameras()
        if len(ret) == 1:
            model, port = ret[0]
            self.assign_port_to_side(port, 'foldout', model)
        elif len(ret) == 2:
            sides = ['right', 'left']
            for model, port in ret:
                self.assign_port_to_side(port, sides.pop(), model)
        elif len(ret) == 3:
            sides = ['right', 'left', 'foldout']
            for model, port in ret:
                self.assign_port_to_side(port, sides.pop(), model)

    def on_camera_ports(self, *args, **kwargs):
        pass

    def get_active_cameras(self):
        return {k: v for k, v in self.camera_ports.items() if v is not None}

    def get_current_config(self):
        return self.camera_ports

    def get_num_cameras(self):
        return len(self.get_active_cameras())

    @staticmethod
    def _set_environment(driver):
        for env_setting in ['CAMLIBS', 'IOLIBS', 'LD_LIBRARY_PATH']:
            os.environ[env_setting] = os.path.join(scribe_globals.APP_WORKING_DIR, driver['path'],
                                                   driver[env_setting])

    def _get_driver(self):
        driver = {
            'path': 'libs/gphoto',
            'command': 'bin/gphoto2',
            'LD_LIBRARY_PATH': 'lib',
            'CAMLIBS': 'lib/libgphoto2/2.5.22.1',
            'IOLIBS': 'lib/libgphoto2_port/0.12.0'
        }
        command = os.path.join(scribe_globals.APP_WORKING_DIR,
                    driver['path'],
                    driver['command'],)
        self._set_environment(driver)
        return driver, command

    def _safe_run_gphoto(self, command_line):
        if type(command_line) is not list:
            raise TypeError('Command line must be a list of arguments')
        driver, command = self._get_driver()
        concrete_command_line = [command] + command_line
        try:
            output = subprocess.check_output(concrete_command_line)
            output = output.decode('utf-8')
        except Exception as e:
            output = e
        return output

    def _parse_gphoto_output(self, output):
        lines = output.split('\n')
        ret = []
        for line in lines[2:]:
            line = line.strip()
            if '' == line:
                continue
            parts = line.split()
            if parts[-1].startswith('usb:'):
                port = parts[-1]
                model = ' '.join(parts[:-1])
                cam_tuple = (model, port)
                ret.append(cam_tuple)
        return ret

    def _detect_cameras(self):
        if fake_cameras:
            if fake_cameras == 1:
                return [('Nikon J3','USB:010')]
            elif fake_cameras == 2:
                return [('Nikon J3','USB:020'), ('Nikon J3','USB:021'), ]
            elif fake_cameras == 3:
                return [('Nikon J3','USB:001'), ('Nikon J3','USB:002'), ('Nikon J3','USB:003'), ]

        output = self._safe_run_gphoto(['--auto-detect', ])
        if type(output) in [Exception, subprocess.CalledProcessError]:
            return []
        else:
            return self._parse_gphoto_output(output)

    def assign_port_to_side(self, port, side, model):
        self.camera_ports[side] = {'port': port, 'model': model}

    def swap(self):
        camera_ports_copy = self.camera_ports.copy()
        self.camera_ports['left'] = camera_ports_copy['right']
        self.camera_ports['right'] = camera_ports_copy['left']

    def get_camera_info(self, side):
        port = self.camera_ports[side]['port']
        output = self._safe_run_gphoto(['--list-config', '--port', port])
        return output

    def get_camera_port(self, side):
        side = self.camera_ports[side]
        ret = side.get('port', None) if side is not None else None
        return ret

    def take_shot(self, side, destination_path):
        if not  self.camera_ports[side]:
            return Exception('{} camera not detected'.format(side))
        port = self.camera_ports[side]['port']
        call_line = [
                     '--capture-image-and-download',
                     '--port', port,
                     '--filename', destination_path,
                     '--force-overwrite',
                     '--quiet']
        if fake_cameras:
            time.sleep(0.2)
            shutil.copyfile(scribe_globals.FAKE_IMAGE, destination_path)
            result = destination_path
        else:
            result = self._safe_run_gphoto(call_line)
        return result

    def are_calibrated(self):
        return self._calibrated

    def set_calibrated(self):
        self._calibrated = True

    def get_name(self):
        active_cams = self.get_active_cameras()
        if len(active_cams) == 0:
            return None
        active_model = set([y['model'] for x, y in active_cams.items()]).pop()
        return active_model

    def list_camera_properties(self, side):
        port = self.camera_ports[side]['port']
        args_list = ['--port', port, '--list-config']
        res = self._safe_run_gphoto(args_list)
        if type(res) in [Exception, subprocess.CalledProcessError]:
            return []
        ret = res.split('\n')
        return ret

    def get_camera_property(self, side, property_name):
        port = self.camera_ports[side]['port']
        args_list = ['--port', port, '--get-config', property_name]
        res = self._safe_run_gphoto(args_list)
        if type(res) in [Exception, subprocess.CalledProcessError]:
            return []
        ret = res.split('Current: ')[1].split('\n')[0]
        return ret

    def add_camera_property(self, side, key, value):
        camera = self.camera_ports[side]
        if camera is not None:
            if key not in ['port', 'model']:
                camera[key] = value
