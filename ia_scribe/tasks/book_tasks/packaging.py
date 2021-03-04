import os, subprocess, zipfile, traceback
from os.path import join
from PIL import Image
from distutils.spawn import find_executable
from ia_scribe.ia_services.iabdash import push_event
from ia_scribe import scribe_globals
from ia_scribe.config.config import Scribe3Configuration
from ia_scribe.exceptions import ScribeException
from ia_scribe.book.upload_status import UploadStatus
from ia_scribe.detectors.blur_detector import is_blurred

config = Scribe3Configuration()
def blur_detect(book):
    try:
        jpgs = book.get_thumb_jpegs()
        map_result = []
        for n, jpg_file in enumerate(jpgs):
            res, variance = is_blurred(jpg_file)
            map_result.append((res, variance))
            msg = 'Blur Detect: [{n}/{total}] {name} -> {result} ({value})'.format(
                name = jpg_file[-8:],
                n =n,
                total =len(jpgs),
                result = res,
                value = variance,
            )
            book.logger.info(msg)
            short_msg = 'Blur detect | {percent}% | {n}/{total}'.format(
                percent=n * 100/ len(jpgs),
                n=n,
                total=len(jpgs),
                result=res,
                value=variance,
            )
            book.update_message(short_msg)
        blurry_pages = [x for x in map_result if x[0]==True]
        res = len(blurry_pages) == 0
        it = list(zip(jpgs, map_result))
        book.logger.info('Blur detection complete. Success -> {}.'.format(res))

        for image, result in it:
            leaf_number = int(image.split('.jpg')[0][-4:])
            book.scandata.set_blurriness(leaf_number, *result)
            if result[0]:
                book.scandata.set_note(leaf_number,
                                       'This page has been detected as blurry')

        book.logger.info('Saving blur informtion in scandata')
        book.scandata.save()

        if res:
            book.logger.info('Blur detection success: no blurry pages found')
            book.do_finish_blur_detection_success()
        else:
            book.logger.info('{} blurry images found'.format(len(blurry_pages)))
            book.do_error_blur_detection()
    except Exception as e:
        book.logger.info('Exception while blur detecting: {}'.format(e))
        book.do_error_blur_detection()
        raise e

def create_imagestack(book):
    try:
        jpegs = book.get_jpegs()
        def select_hald_file():
            if os.path.exists(scribe_globals.HALD_FILE_CUSTOM):
                book.logger.info('Found a custom hald file at {}. Using that.'.format(scribe_globals.HALD_FILE_CUSTOM))
                return scribe_globals.HALD_FILE_CUSTOM
            else:
                book.logger.info('Using standard hald image at {}'.format(scribe_globals.HALD_FILE))
                return scribe_globals.HALD_FILE

        def correct_color(path):
            input_file = path
            hald_file = select_hald_file()
            output_file = input_file + "_converted.jpg"
            command = ['convert', input_file, hald_file, '-hald-clut', output_file]
            book.logger.info('Correcting color {} -> {}'.format(input_file, output_file))
            subprocess.check_output(command)
            return output_file

        book.logger.debug('CreateJP2: Compressing image stack. Is exiftool available? {} '
                          '(If False EXIF tags won\'t be copied.)'
                          .format(scribe_globals.EXIFTOOL))
        env = os.environ.copy()
        env['LD_LIBRARY_PATH'] = scribe_globals.KAKADU_DIR
        jp2s = []

        num_threads = config.get('compression_threads', 4)
        color_correction = config.is_true('ffs_color_correction')
        imagemagick_present = find_executable('convert')
        book.logger.debug(
            'CreateJP2: Now converting {} to JPEG2000 using {} threads'.format(jpegs[0].split('0000.jpg')[0],
                                                                               num_threads))
        stack = book.get_jpegs()
        for n, item in enumerate(stack):
                path = item.split('.jpg')[0]
                source_jpg_path = item
                # Apply color correction
                if imagemagick_present and color_correction:
                    source_jpg_path = correct_color(item)
                im = Image.open(source_jpg_path)
                tmp_path = str(path + '_interchange.bmp')
                im.save(tmp_path, 'BMP')

                command = [scribe_globals.KAKADU_COMPRESS, '-i', tmp_path,
                           '-o', path + '.jp2', '-slope', scribe_globals.KAKADU_SLOPE, '-num_threads', str(num_threads)]
                subprocess.check_call(command,
                                      env=env,
                                      stdout=open(os.devnull, 'wb'),
                                      stderr=open(os.devnull, 'wb'))
                jp2s.append(path + '.jp2')
                book.logger.debug("CreateJP2: Compressed {}/{}".format(n + 1, len(jpegs)))
                os.remove(tmp_path)
                try:
                    if scribe_globals.EXIFTOOL:
                        command = [scribe_globals.EXIFTOOL, '-tagsFromFile',
                                   item, '-All:All', '-IFD1:All', '--Orientation',
                                   path + '.jp2']
                        subprocess.check_call(command,
                                              stdout=open(os.devnull, 'wb'),
                                              stderr=open(os.devnull, 'wb'))
                        t_file = path + '.jp2' + '_original'
                        book.logger.debug("CreateJP2: EXIF tags ported: {}/{}".format(n + 1, len(jpegs)))
                except Exception as e:
                    book.logger.exception('CreateJP2: Exiftool not available or '
                                          'error in porting EXIF tags for image {}'
                                          .format(path + '.jp2'))
                short_msg = 'Compression | {percent:.1f}% | {n}/{total}'.format(
                    percent=n * 100 / len(stack),
                    n=n,
                    total=len(stack),
                )
                book.update_message(short_msg)

    except Exception as e:
        book.do_error_image_stack()
        raise Exception('CreateJP2: Encountered error {} while compressing image stack to JPEG2000'
                              .format(e))

    book.do_finish_image_stack()

    book.logger.info("CreateJP2: Done compressing {} images".format(len(jpegs)))

def create_preimage_zip(book):
    logger = book.logger

    if book['status'] >= UploadStatus.uploaded.value:
        return

    logger.info('Package book: Creating preimage.zip')
    #Clock.schedule_once(partial(self.set_status_callback,
    #                            'Now creating book upload bundle for {}'.format(book.get('identifier', ''))))
    try:

        zip_path = join(book['path'],
                        '{id}_preimage.zip'.format(id=book['identifier']))

        compression = zipfile.ZIP_STORED
        allow_zip64 = True
        target = book.get_imagestack()

        if target == None or len(target) == 0:
            raise ScribeException('Could not find jpegs to compress.')

        with zipfile.ZipFile(zip_path, 'w', compression,
                             allow_zip64) as preimage_zip:
            for jpeg in target:
                logger.debug('adding ' + jpeg + ' to ' + zip_path)
                arcname = ('{id}_preimage/{j}'
                           .format(id=book['identifier'],
                                   j=os.path.basename(jpeg)))
                preimage_zip.write(jpeg, arcname)

            scandata = join(book['path'], 'scandata.json')
            if os.path.exists(scandata):
                arcname = ('{id}_preimage/scandata.json'
                           .format(id=book['identifier']))
                preimage_zip.write(scandata, arcname)

        book.do_finish_preimage_zip()

    except Exception as e:
        book.error = e
        book.logger.error(traceback.format_exc())
        book.do_error_preimage_zip()

        payload = {'local_id': book['uuid'],
                   'status': book['status'],
                   'exception': str(e)}

        push_event('tts-book-packaging-exception', payload,
                   'book', book['identifier'])
        raise ScribeException('Could not create preimage.zip - {}'.format(str(e)))