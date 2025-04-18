"""
Custom image class for Inkycal Project
Takes care of handling images. Made to be used by other modules to handle
images.

Copyright by aceinnolab
"""
import logging
import os
from typing import Literal

import numpy
import PIL
import requests
from PIL import Image

logger = logging.getLogger(__name__)


class Inkyimage:
    """Custom Imgae class written for commonly used image operations."""

    def __init__(self, image=None):
        """Initialize InkyImage module"""

        # no image initially
        self.image = image

        # give an OK message
        logger.debug(f"{__name__} loaded")

    def load(self, path: str) -> None:
        """loads an image from a URL or filepath.

        Args:
          - path:The full path or url of the image file
            e.g. `https://sample.com/logo.png` or `/home/pi/Downloads/nice_pic.png`

        Raises:
          - FileNotFoundError: This Exception is raised when the file could not be
            found.
          - OSError: A OSError is raised when the URL doesn't point to the correct
            file-format, i.e. is not an image
          - TypeError: if the URLS doesn't start with htpp
        """
        # Try to open the image if it exists and is an image file
        try:
            if path.startswith("http"):
                logger.info("loading image from URL")
                image = Image.open(requests.get(path, stream=True).raw)
            else:
                logger.info("loading image from local path")
                image = Image.open(path)
        except FileNotFoundError:
            logger.error("No image file found", exc_info=True)
            raise Exception(f"Your file could not be found. Please check the filepath: {path}")

        except OSError:
            logger.error("Invalid Image file provided", exc_info=True)
            raise Exception("Please check if the path points to an image file.")

        logger.debug(f"width: {image.width}, height: {image.height}")

        image.convert(mode="RGBA")  # convert to a more suitable format
        self.image = image
        logger.info("loaded Image")

    def clear(self):
        """Removes currently saved image if present."""
        if self.image:
            self.image = None
            logger.info("cleared previous image")

    def _image_loaded(self):
        """returns True if image was loaded"""
        if self.image:
            return True
        else:
            logger.error("image not loaded")
            return False

    def flip(self, angle):
        """Flips the image by the given angle.

        Args:
          - angle:->int. A multiple of 90, e.g. 90, 180, 270, 360.
        """
        if self._image_loaded():

            image = self.image
            if not angle % 90 == 0:
                logger.error("Angle must be a multiple of 90")
                return

            image = image.rotate(angle, expand=True)
            self.image = image
            logger.info(f"flipped image by {angle} degrees")

    def autoflip(self, layout: str) -> None:
        """flips the image automatically to the given layout.

        Args:
          - layout:-> str. Choose `horizontal` or `vertical`.

        Checks the image's width and height.

        In horizontal mode, the image is flipped if the image height is greater
        than the image width.

        In vertical mode, the image is flipped if the image width is greater
        than the image height.
        """
        if self._image_loaded():

            image = self.image
            if layout == "horizontal":
                if image.height > image.width:
                    logger.info("image width greater than image height, flipping")
                    image = image.rotate(90, expand=True)

            elif layout == "vertical":
                if image.width > image.height:
                    logger.info("image width greater than image height, flipping")
                    image = image.rotate(90, expand=True)
            else:
                logger.error("layout not supported")
                return
            self.image = image

    def remove_alpha(self):
        """Removes transparency if image has transparency.

        Checks if an image has an alpha band and replaces the transparency with
        white pixels.
        """
        if self._image_loaded():
            image = self.image

            if len(image.getbands()) == 4:
                logger.info("removing alpha channel")
                bg = Image.new("RGBA", (image.width, image.height), "white")
                im = Image.alpha_composite(bg, image)

                self.image.paste(im, (0, 0))
                logger.info("removed transparency")

    def resize(self, width=None, height=None):
        """Resize an image to desired width or height"""
        if self._image_loaded():

            if not width and not height:
                logger.error("no height of width specified")
                return

            image = self.image

            if width:
                initial_width = image.width
                wpercent = width / float(image.width)
                hsize = int((float(image.height) * float(wpercent)))
                image = image.resize((width, hsize), Image.LANCZOS)
                logger.info(f"resized image from {initial_width} to {image.width}")
                self.image = image

            if height:
                initial_height = image.height
                hpercent = height / float(image.height)
                wsize = int(float(image.width) * float(hpercent))
                image = image.resize((wsize, height), Image.LANCZOS)
                logger.info(f"resized image from {initial_height} to {image.height}")
                self.image = image

    @staticmethod
    def merge(image1, image2):
        """Merges two images into one.

        Replaces white pixels of the first image with transparent ones. Then pastes
        the first image on the second one.

        Args:
          - image1: A PIL Image object in 'RGBA' mode.
          - image2: A PIL Image object in 'RGBA' mode.

        Returns:
          - A single image.
        """

        def clear_white(img):
            """Replace all white pixels from image with transparent pixels"""
            x = numpy.asarray(img.convert("RGBA")).copy()
            x[:, :, 3] = (255 * (x[:, :, :3] != 255).any(axis=2)).astype(numpy.uint8)
            return Image.fromarray(x)

        image2 = clear_white(image2)
        image1.paste(image2, (0, 0), image2)
        logger.info("merged given images into one")

        return image1


def image_to_palette(
    image: Image, palette: Literal = ["bwr", "bwy", "bw", "16gray"], dither: bool = True
) -> (PIL.Image, PIL.Image):
    """Maps an image to a given colour palette.

    Maps each pixel from the image to a colour from the palette.

    Args:
        - palette: A supported token. (see below)
        - dither:->bool. Use dithering? Set to `False` for solid colour fills.

    Returns:
        - two images: one for the coloured band and one for the black band.

    Raises:
        - ValueError if palette token is not supported

    Supported palette tokens:

    >>> 'bwr' # black-white-red
    >>> 'bwy' # black-white-yellow
    >>> 'bw'  # black-white
    >>> '16gray' # 16 shades of gray
    """

    if palette == "bwr":
        # black-white-red palette
        pal = [255, 255, 255, 0, 0, 0, 255, 0, 0]

    elif palette == "bwy":
        # black-white-yellow palette
        pal = [255, 255, 255, 0, 0, 0, 255, 255, 0]

    elif palette == "bw":
        pal = None
    elif palette == "16gray":
        pal = [x for x in range(0, 256, 16)] * 3
        pal.sort()

    else:
        logger.error("The given palette is unsupported.")
        raise ValueError(f"The given palette ({palette}) is not supported.")

    if pal:
        # The palette needs to have 256 colors, for this, the black-colour
        # is added until the
        colours = len(pal) // 3
        # print(f'The palette has {colours} colours')

        if 256 % colours != 0:
            # print('Filling palette with black')
            pal += (256 % colours) * [0, 0, 0]

        # print(pal)
        colours = len(pal) // 3
        # print(f'The palette now has {colours} colours')

        # Create a dummy image to be used as a palette
        palette_im = Image.new("P", (1, 1))

        # Attach the created palette. The palette should have 256 colours
        # equivalent to 768 integers
        palette_im.putpalette(pal * (256 // colours))

        # Quantize the image to given palette
        quantized_im = image.quantize(palette=palette_im, dither=dither)
        quantized_im = quantized_im.convert("RGB")

        # get rgb of the non-black-white colour from the palette
        rgb = [pal[x : x + 3] for x in range(0, len(pal), 3)]
        rgb = [col for col in rgb if col != [0, 0, 0] and col != [255, 255, 255]][0]
        r_col, g_col, b_col = rgb
        # print(f'r:{r_col} g:{g_col} b:{b_col}')

        # Create an image buffer for black pixels
        buffer1 = numpy.array(quantized_im)

        # Get RGB values of each pixel
        r, g, b = buffer1[:, :, 0], buffer1[:, :, 1], buffer1[:, :, 2]

        # convert coloured pixels to white
        buffer1[numpy.logical_and(r == r_col, g == g_col)] = [255, 255, 255]

        # reconstruct image for black-band
        im_black = Image.fromarray(buffer1)

        # Create a buffer for coloured pixels
        buffer2 = numpy.array(quantized_im)

        # Get RGB values of each pixel
        r, g, b = buffer2[:, :, 0], buffer2[:, :, 1], buffer2[:, :, 2]

        # convert black pixels to white
        buffer2[numpy.logical_and(r == 0, g == 0)] = [255, 255, 255]

        # convert non-white pixels to black
        buffer2[numpy.logical_and(g == g_col, b == 0)] = [0, 0, 0]

        # reconstruct image for colour-band
        im_colour = Image.fromarray(buffer2)

        # self.preview(im_black)
        # self.preview(im_colour)

    else:
        im_black = image.convert("1", dither=dither)
        im_colour = Image.new(mode="1", size=im_black.size, color="white")

    logger.info("mapped image to specified palette")

    return im_black, im_colour


if __name__ == "__main__":
    print(f"running {__name__} in standalone/debug mode")
