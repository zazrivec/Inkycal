"""
Inkycal Image Module
Copyright by aceinnolab
"""
from inkycal.custom import *
from inkycal.modules.inky_image import image_to_palette
from inkycal.modules.inky_image import Inkyimage as Images
from inkycal.modules.template import inkycal_module

logger = logging.getLogger(__name__)


class Inkyimage(inkycal_module):
    """Displays an image from URL or local path"""

    name = "Inkycal Image - show an image from a URL or local path"

    requires = {
        "path": {
            "label": "Path to a local folder, e.g. /home/pi/Desktop/images. "
            "Only PNG and JPG/JPEG images are used for the slideshow."
        },
        "palette": {"label": "Which palette should be used for converting images?", "options": ["bw", "bwr", "bwy"]},
    }

    optional = {
        "autoflip": {"label": "Should the image be flipped automatically?", "options": [True, False]},
        "orientation": {"label": "Please select the desired orientation", "options": ["vertical", "horizontal"]},
    }

    def __init__(self, config):
        """Initialize module"""

        super().__init__(config)

        config = config["config"]

        # required parameters
        for param in self.requires:
            if not param in config:
                raise Exception(f"config is missing {param}")

        # optional parameters
        self.path = config["path"]
        self.palette = config["palette"]
        self.autoflip = config["autoflip"]
        self.orientation = config["orientation"]
        self.dither = True
        if "dither" in config and config["dither"] == False:
            self.dither = False

        # give an OK message
        logger.debug(f"{__name__} loaded")

    def generate_image(self):
        """Generate image for this module"""

        # Define new image size with respect to padding
        im_width = int(self.width - (2 * self.padding_left))
        im_height = int(self.height - (2 * self.padding_top))
        im_size = im_width, im_height

        logger.info(f"Image size: {im_size}")

        # initialize custom image class
        im = Images()

        # use the image at the first index
        im.load(self.path)

        # Remove background if present
        im.remove_alpha()

        # if auto-flip was enabled, flip the image
        if self.autoflip:
            im.autoflip(self.orientation)

        # resize the image so it can fit on the epaper
        im.resize(width=im_width, height=im_height)

        # convert images according to specified palette
        im_black, im_colour = image_to_palette(image=im.image.convert("RGB"), palette=self.palette, dither=self.dither)

        # with the images now send, clear the current image
        im.clear()

        # return images
        return im_black, im_colour


if __name__ == "__main__":
    print(f"running {__name__} in standalone/debug mode")
