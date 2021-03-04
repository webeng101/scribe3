from os.path import splitext

from PIL import Image
from kivy.core.image._img_sdl2 import load_from_filename
from kivy.core.image.img_sdl2 import ImageLoaderSDL2

from ia_scribe.scribe_globals import BLUR_VARIANCE_THRESHOLD

KERNEL_SIZE = (3, 3)
KERNEL = (
    -1, -1, -1,
    -1, 8, -1,
    -1, -1, -1
)
SDL2_IMAGE_EXTENSIONS = set(ImageLoaderSDL2.extensions())


def is_blurred(filename, threshold=BLUR_VARIANCE_THRESHOLD):
    ext = splitext(filename)[1].lower().replace('.', '')
    if ext in SDL2_IMAGE_EXTENSIONS:
        info = load_from_filename(filename)
        mode = info[2].upper()
        image = Image.frombytes(mode, (info[0], info[1]), info[3],
                                'raw', mode, 0, 1)
    else:
        image = Image.open(filename)
        image.load()
    converted = image.im.convert('L', Image.FLOYDSTEINBERG)
    filtered = converted.filter(KERNEL_SIZE, 1, 0, KERNEL)
    histogram = filtered.histogram()
    sum1 = sum2 = 0.0
    n = 1.0 * histogram[0]
    for i in range(1, 256):
        n += histogram[i]
        sum1 += i * histogram[i]
        sum2 += (i ** 2.0) * histogram[i]
    variance = (sum2 - (sum1 ** 2.0) / n) / n
    return variance < threshold, variance
