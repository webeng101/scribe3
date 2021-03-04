import os
import subprocess
import threading
import _thread
import time
from queue import Queue
from functools import partial
from os.path import join
from pprint import pformat

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.logger import Logger

from ia_scribe import scribe_globals
from ia_scribe.cameras import camera_system
from ia_scribe.config.config import Scribe3Configuration
from ia_scribe.ia_services.ingestion_adapters import put_metric
from ia_scribe.scribe_globals import FAKE_CAMERAS
from ia_scribe.config.config import Scribe3Configuration

config = Scribe3Configuration()
fake_cameras = config.get('fake_cameras', FAKE_CAMERAS)

def capture_thread(q, cameras):
    config =  Scribe3Configuration()
    '''Manage the capture image process'''
    sound = SoundLoader.load('camera_shoot.wav')
    sound_delay = config.get('sound_delay', 0)
    has_single_camera = cameras.get_num_cameras() == 1

    if not config.is_true('stats_disabled'):
        from ia_scribe.breadcrumbs.api import log_event

    def psound(sound):
        try:
            Logger.info('Camera shoot sound delay is {}s'
                        .format(sound_delay))
            try:
                if float(sound_delay) < 0:
                    Logger.debug('ScribeWidget: Negative value in config '
                                 'for sound_delay. Camera shoot sound is '
                                 'disabled')
                    return
            except Exception:
                pass
            sound.seek(0)
            time.sleep(float(sound_delay))
            sound.play()
        except Exception as e:
            Logger.exception('Failed to play camera shoot '
                             'sound ({})'.format(e))

    Logger.info('Starting capture thread with Queue {} '
                .format(q))

    myfile = None
    clog = False
    if config.is_true('camera_logging'):
        myfile = open('/tmp/tts_shoot_times.csv', 'a')
        clog = True

    Logger.info('Camera logging {} with file {}'
                .format(clog, myfile))

    while True:
        camera_kwargs = q.get()
        Logger.info(
            'Capturing image using kwargs: {}{}'
            .format(os.linesep, pformat(camera_kwargs))
        )
        camera_side = camera_kwargs[camera_system.KEY_SIDE]
        path = camera_kwargs[camera_system.KEY_PATH]
        thumb_path = camera_kwargs[camera_system.KEY_THUMB_PATH]
        callback = camera_kwargs[camera_system.KEY_CALLBACK]
        stats = {}
        capture_error = None
        if camera_side == 'left':
            angle = 90
        elif camera_side == 'right':
            angle = -90
        else:
            angle = - config.get_integer('default_single_camera_rotation',180) \
                        if has_single_camera else 0

        port = cameras.get_camera_port(camera_side)
        Logger.info(
            'ScribeWidget: Capturing side {s} with '
            'port {p}, angle {a}, path {path} and fake {fake}'
            .format(s=camera_side, p=port, a=angle, path=path,
                    fake=fake_cameras)
        )
        camera_start = time.time()
        # Move this in try catch block when debug is finished

        Logger.info('ScribeWidget: Playing camera shoot sound')
        _thread.start_new_thread(psound, (sound,))
        Logger.info('Sound dispatched, now calling camera.shoot()')
        output = cameras.take_shot(camera_side, path)

        if type(output) is subprocess.CalledProcessError:
            capture_error = 'gphoto error: {}'.format(output.returncode)
            Logger.exception('ScribeWidget: Camera shoot failed')
        elif type(output) is Exception:
            capture_error = 'generic gphoto error'
            Logger.exception('ScribeWidget: Camera shoot failed with error {}'.format(output))

        stats['capture_time'] = time.time() - camera_start
        Logger.info('ScribeWidget: Camera took {t:.2f}s'
                    .format(t=stats['capture_time']))

        # Having a camera powered off won't cause an exception, so check
        # to see if the image was created
        if not os.path.exists(path):
            Logger.error('ScribeWidget: Camera failed to capture an image')
            capture_error = 'gphoto error'

        Logger.info('ScribeWidget: Generating thumbs...')
        thumb_start = time.time()
        if capture_error is None:
            try:
                size = (1500, 1000)  # (6000,4000)/4
                if config.is_true('low_res_proxies'):
                    size = (750, 500)  # (6000,4000)/8

                # size = (3000, 2000) # (6000,4000)/2
                image = Image.open(path)
                image.thumbnail(size)
                image = image.rotate(angle, expand=True)

                if fake_cameras is not False:
                    Logger.info('ScribeWidget: fake_cameras is {} '
                                '(not False) -> Drawing debug output'
                                .format(fake_cameras))
                    draw = ImageDraw.Draw(image)
                    font_color = (0, 0, 0)
                    font_filename = join(scribe_globals.FONTS_DIR,
                                         scribe_globals.UTF8_FONT + '.ttf')
                    font = ImageFont.truetype(font_filename, 50)
                    draw.text((0, 0),
                              os.path.basename(path),
                              font_color, font=font)
                    if angle % 360 == 0 or angle % 360 == 180:
                        height = size[1]
                    else:
                        height = size[0]
                    draw.text((0, height - 200),
                              '{} image'.format(camera_side),
                              fill=font_color,
                              font=font)
                    draw.text((0, height - 400),
                              'port {}'.format(port),
                              fill=font_color,
                              font=font)

                image.save(thumb_path, 'JPEG', quality=90)
            except Exception as e:
                capture_error = 'thumbnail error' + str(e)
                Logger.exception(
                    'ScribeWidget: Failed to create thumbnail: {}'
                    .format(thumb_path)
                )

        stats['thumb_time'] = time.time() - thumb_start
        Logger.info(
            'ScribeWidget: Generated thumbnail at '
            '{thumb_path}. Took {t:.2f}s'
            .format(t=stats['thumb_time'],
                    thumb_path=thumb_path)
        )

        if clog:
            ctime = '{t:.2f}s'.format(t=stats['capture_time'])
            ttime = '{t:.2f}s'.format(t=stats['thumb_time'])
            Logger.info(
                'ScribeWidget: Writing ctime = {ctime}, '
                'ttime = {ttime} to stats file {path}'
                .format(ttime=ttime, ctime=ctime, path=myfile.name)
            )
            lineout = (
                '{0},{1},{2},{3},{4},{5},{6},{7}\n'
                .format(time.time(), camera_side, port, angle, ctime,
                        ttime, path, threading.current_thread().ident)
            )
            myfile.write(lineout)


        report = {camera_system.KEY_SIDE: camera_side,
                  camera_system.KEY_THUMB_PATH: thumb_path,
                  camera_system.KEY_ERROR: capture_error,
                  camera_system.KEY_STATS: stats}

        if config.is_true('enable_camera_telemetry'):
            metrics_payload = {camera_system.KEY_SIDE: camera_side,
                               camera_system.KEY_ERROR: capture_error,
                           'angle': angle,
                           'thumb_time': stats['thumb_time'],
                           'path': path,
                               }
            put_metric('scribe3.camera.capture_time', stats['capture_time'], metrics_payload)

        if not config.is_true('stats_disabled'):
            log_event('camera', 'capture_time', stats['capture_time'], camera_side)

        widget = camera_kwargs.get(camera_system.KEY_IMAGE_WIDGET, None)
        if widget:
            report[camera_system.KEY_IMAGE_WIDGET] = widget
        extra = camera_kwargs.get(camera_system.KEY_EXTRA, None)
        if extra is not None:
            report[camera_system.KEY_EXTRA] = extra
        if callback is not None:
            Clock.schedule_once(partial(callback, report))
        q.task_done()


def _setup_camera_threads(cameras):
    '''This is used to initialize the capture_threads to manage capture
    image process.
    '''

    left_queue = Queue()
    right_queue = Queue()
    foldout_queue = Queue()


    t = threading.Thread(target=capture_thread,
                         args=(left_queue, cameras),
                         name='LeftCameraThread')
    t.daemon = True
    t.start()

    t = threading.Thread(target=capture_thread,
                         args=(right_queue,cameras),
                         name='RightCameraThread')
    t.daemon = True
    t.start()

    t = threading.Thread(target=capture_thread,
                         args=(foldout_queue, cameras),
                         name='FoldoutCameraThread')
    t.daemon = True
    t.start()

    return left_queue, right_queue, foldout_queue
