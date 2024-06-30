"""
Inkycal weather module
Copyright by aceinnolab
"""
import decimal
import logging
import math
from typing import Tuple

import arrow
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

from inkycal.custom.functions import draw_border
from inkycal.custom.functions import fonts
from inkycal.custom.functions import get_system_tz
from inkycal.custom.functions import internet_available
from inkycal.custom.functions import write
from inkycal.custom.inkycal_exceptions import NetworkNotReachableError
from inkycal.custom.openweathermap_wrapper import OpenWeatherMap
from inkycal.modules.template import inkycal_module

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


class Weather(inkycal_module):
    """Weather class
    parses weather details from openweathermap
    """
    name = "Weather (openweathermap) - Get weather forecasts from openweathermap"

    requires = {

        "api_key": {
            "label": "Please enter openweathermap api-key. You can create one for free on openweathermap",
        },

        "location": {
            "label": "Please enter your location in the following format: City, Country-Code. " +
                     "You can also enter the location ID found in the url " +
                     "e.g. https://openweathermap.org/city/4893171 -> ID is 4893171"
        }
    }

    optional = {

        "round_temperature": {
            "label": "Round temperature to the nearest degree?",
            "options": [True, False],
        },

        "round_wind_speed": {
            "label": "Round windspeed?",
            "options": [True, False],
        },

        "forecast_interval": {
            "label": "Please select the forecast interval",
            "options": ["daily", "hourly"],
        },

        "units": {
            "label": "Which units should be used?",
            "options": ["metric", "imperial"],
        },

        "hour_format": {
            "label": "Which hour format do you prefer?",
            "options": [24, 12],
        },

        "use_beaufort": {
            "label": "Use beaufort scale for windspeed?",
            "options": [True, False],
        },

    }

    def __init__(self, config):
        """Initialize inkycal_weather module"""

        super().__init__(config)

        config = config['config']

        self.timezone = get_system_tz()

        # Check if all required parameters are present
        for param in self.requires:
            if param not in config:
                raise Exception(f'config is missing {param}')

        # required parameters
        self.api_key = config['api_key']
        self.location = config['location']

        # optional parameters
        self.round_temperature = config['round_temperature']
        self.round_wind_speed = config['round_windspeed']
        self.forecast_interval = config['forecast_interval']
        self.hour_format = int(config['hour_format'])
        if config['units'] == "imperial":
            self.temp_unit = "fahrenheit"
        else:
            self.temp_unit = "celsius"

        if config['use_beaufort']:
            self.wind_unit = "beaufort"
        elif config['units'] == "imperial":
            self.wind_unit = "miles_hour"
        else:
            self.wind_unit = "meters_sec"
        self.locale = config['language']
        # additional configuration

        self.owm = OpenWeatherMap(
            api_key=self.api_key,
            city_id=self.location,
            wind_unit=self.wind_unit,
            temp_unit=self.temp_unit,
            language=self.locale,
            tz_name=self.timezone
        )

        self.weatherfont = ImageFont.truetype(
            fonts['weathericons-regular-webfont'], size=self.fontsize)

        if self.wind_unit == "beaufort":
            self.windDispUnit = "bft"
        elif self.wind_unit == "knots":
            self.windDispUnit = "kn"
        elif self.wind_unit == "km_hour":
            self.windDispUnit = "km/h"
        elif self.wind_unit == "miles_hour":
            self.windDispUnit = "mph"
        else:
            self.windDispUnit = "m/s"
        if self.temp_unit == "fahrenheit":
            self.tempDispUnit = "F"
        elif self.temp_unit == "celsius":
            self.tempDispUnit = "°"

        # give an OK message
        logger.debug(f"{__name__} loaded")

    def generate_image(self):
        """Generate image for this module"""

        # Define new image size with respect to padding
        im_width = int(self.width - (2 * self.padding_left))
        im_height = int(self.height - (2 * self.padding_top))
        im_size = im_width, im_height
        logger.debug(f'Image size: {im_size}')

        # Create an image for black pixels and one for coloured pixels
        im_black = Image.new('RGB', size=im_size, color='white')
        im_colour = Image.new('RGB', size=im_size, color='white')

        # Check if internet is available
        if internet_available():
            logger.debug('Connection test passed')
        else:
            logger.error("Network not reachable. Please check your connection.")
            raise NetworkNotReachableError

        def get_moon_phase():
            """Calculate the current (approximate) moon phase

            Returns:
                The corresponding moonphase-icon.
            """

            dec = decimal.Decimal
            diff = now - arrow.get(2001, 1, 1)
            days = dec(diff.days) + (dec(diff.seconds) / dec(86400))
            lunations = dec("0.20439731") + (days * dec("0.03386319269"))
            position = lunations % dec(1)
            index = math.floor((position * dec(8)) + dec("0.5"))
            return {
                0: '\uf095',
                1: '\uf099',
                2: '\uf09c',
                3: '\uf0a0',
                4: '\uf0a3',
                5: '\uf0a7',
                6: '\uf0aa',
                7: '\uf0ae'
            }[int(index) & 7]

        def is_negative(temp: str):
            """Check if temp is below freezing point of water (0°C/32°F)
            returns True if temp below freezing point, else False"""
            answer = False

            if self.temp_unit == 'celsius' and round(float(temp.split(self.tempDispUnit)[0])) <= 0:
                answer = True
            elif self.temp_unit == 'fahrenheit' and round(float(temp.split(self.tempDispUnit)[0])) <= 32:
                answer = True
            return answer

        # Lookup-table for weather icons and weather codes
        weather_icons = {
            '01d': '\uf00d',
            '02d': '\uf002',
            '03d': '\uf013',
            '04d': '\uf012',
            '09d': '\uf01a',
            '10d': '\uf019',
            '11d': '\uf01e',
            '13d': '\uf01b',
            '50d': '\uf014',
            '01n': '\uf02e',
            '02n': '\uf013',
            '03n': '\uf013',
            '04n': '\uf013',
            '09n': '\uf037',
            '10n': '\uf036',
            '11n': '\uf03b',
            '13n': '\uf038',
            '50n': '\uf023'
        }

        def draw_icon(image: Image, xy: Tuple[int, int], box_size: Tuple[int, int], icon: str, rotation=None):
            """Custom function to add icons of weather font on the image.

            Args:
                - image:
                    the image on which image should the text be added
                - xy:
                    coordinates as tuple -> (x,y)
                - box_size:
                    size of text-box -> (width,height)
                - icon:
                    icon-unicode, looks this up in weather-icons dictionary

            """

            icon_size_correction = {
                '\uf00d': 10 / 60,
                '\uf02e': 51 / 150,
                '\uf019': 21 / 60,
                '\uf01b': 21 / 60,
                '\uf0b5': 51 / 150,
                '\uf050': 25 / 60,
                '\uf013': 51 / 150,
                '\uf002': 0,
                '\uf031': 29 / 100,
                '\uf015': 21 / 60,
                '\uf01e': 52 / 150,
                '\uf056': 51 / 150,
                '\uf053': 14 / 150,
                '\uf012': 51 / 150,
                '\uf01a': 51 / 150,
                '\uf014': 51 / 150,
                '\uf037': 42 / 150,
                '\uf036': 42 / 150,
                '\uf03b': 42 / 150,
                '\uf038': 42 / 150,
                '\uf023': 35 / 150,
                '\uf07a': 35 / 150,
                '\uf051': 18 / 150,
                '\uf052': 18 / 150,
                '\uf0aa': 0,
                '\uf095': 0,
                '\uf099': 0,
                '\uf09c': 0,
                '\uf0a0': 0,
                '\uf0a3': 0,
                '\uf0a7': 0,
                '\uf0ae': 0
            }

            x, y = xy
            box_width, box_height = box_size
            text = icon
            font = self.weatherfont

            # Increase fontsize to fit specified height and width of text box
            size = 8
            font = ImageFont.truetype(font.path, size)
            text_width, text_height = font.getbbox(text)[2:]

            while text_width < int(box_width * 0.9) and text_height < int(box_height * 0.9):
                size += 1
                font = ImageFont.truetype(font.path, size)
                text_width, text_height = font.getbbox(text)[2:]

            text_width, text_height = font.getbbox(text)[2:]

            # Align text to desired position
            x = int((box_width / 2) - (text_width / 2))
            y = int((box_height / 2) - (text_height / 2))

            space = Image.new('RGBA', (box_width, box_height))
            ImageDraw.Draw(space).text((x, y), text, fill='black', font=font)

            if rotation:
                space.rotate(rotation, expand=True)

            # Update only region with text (add text with transparent background)
            image.paste(space, xy, space)

        #   column1    column2    column3    column4    column5    column6    column7
        # |----------|----------|----------|----------|----------|----------|----------|
        # |  time    | temperat.| moonphase| forecast1| forecast2| forecast3| forecast4|
        # | current  |----------|----------|----------|----------|----------|----------|
        # | weather  | humidity |  sunrise |  icon1   |  icon2   |  icon3   |  icon4   |
        # |  icon    |----------|----------|----------|----------|----------|----------|
        # |          | windspeed|  sunset  | temperat.| temperat.| temperat.| temperat.|
        # |----------|----------|----------|----------|----------|----------|----------|

        # Calculate size rows and columns
        col_width = im_width // 7

        # Ratio width height
        image_ratio = im_width / im_height

        if image_ratio >= 4:
            row_height = im_height // 3
        else:
            logger.info('Please consider decreasing the height.')
            row_height = int((im_height * (1 - im_height / im_width)) / 3)

        logger.debug(f"row_height: {row_height} | col_width: {col_width}")

        # Calculate spacings for better centering
        spacing_top = int((im_width % col_width) / 2)
        spacing_left = int((im_height % row_height) / 2)

        # Define sizes for weather icons
        icon_small = int(col_width / 3)
        icon_medium = icon_small * 2
        icon_large = icon_small * 3

        # Calculate the x-axis position of each col
        col1 = spacing_top
        col2 = col1 + col_width
        col3 = col2 + col_width
        col4 = col3 + col_width
        col5 = col4 + col_width
        col6 = col5 + col_width
        col7 = col6 + col_width

        # Calculate the y-axis position of each row
        line_gap = int((im_height - spacing_top - 3 * row_height) // 4)

        row1 = line_gap
        row2 = row1 + line_gap + row_height
        row3 = row2 + line_gap + row_height

        # Draw lines on each row and border
        ###########################################################################
        #    draw = ImageDraw.Draw(im_black)
        #    draw.line((0, 0, im_width, 0), fill='red')
        #    draw.line((0, im_height-1, im_width, im_height-1), fill='red')
        #    draw.line((0, row1, im_width, row1), fill='black')
        #    draw.line((0, row1+row_height, im_width, row1+row_height), fill='black')
        #    draw.line((0, row2, im_width, row2), fill='black')
        #    draw.line((0, row2+row_height, im_width, row2+row_height), fill='black')
        #    draw.line((0, row3, im_width, row3), fill='black')
        #    draw.line((0, row3+row_height, im_width, row3+row_height), fill='black')
        ###########################################################################

        # Positions for current weather details
        weather_icon_pos = (col1, 0)
        temperature_icon_pos = (col2, row1)
        temperature_pos = (col2 + icon_small, row1)
        humidity_icon_pos = (col2, row2)
        humidity_pos = (col2 + icon_small, row2)
        windspeed_icon_pos = (col2, row3)
        windspeed_pos = (col2 + icon_small, row3)

        # Positions for sunrise, sunset, moonphase
        moonphase_pos = (col3, row1)
        sunrise_icon_pos = (col3, row2)
        sunrise_time_pos = (col3 + icon_small, row2)
        sunset_icon_pos = (col3, row3)
        sunset_time_pos = (col3 + icon_small, row3)

        # Positions for forecast 1
        stamp_fc1 = (col4, row1) # noqa
        icon_fc1 = (col4, row1 + row_height) # noqa
        temp_fc1 = (col4, row3) # noqa

        # Positions for forecast 2
        stamp_fc2 = (col5, row1) # noqa
        icon_fc2 = (col5, row1 + row_height) # noqa
        temp_fc2 = (col5, row3) # noqa

        # Positions for forecast 3
        stamp_fc3 = (col6, row1) # noqa
        icon_fc3 = (col6, row1 + row_height) # noqa
        temp_fc3 = (col6, row3) # noqa

        # Positions for forecast 4
        stamp_fc4 = (col7, row1) # noqa
        icon_fc4 = (col7, row1 + row_height) # noqa
        temp_fc4 = (col7, row3) # noqa

        # Create current-weather and weather-forecast objects
        logging.debug('looking up location by ID')
        current_weather = self.owm.get_current_weather()
        weather_forecasts = self.owm.get_weather_forecast()

        # Set decimals
        dec_temp = 0 if self.round_temperature == True else 1
        dec_wind = 0 if self.round_wind_speed == True else 1

        logging.debug(f'temperature unit: {self.temp_unit}')
        logging.debug(f'decimals temperature: {dec_temp} | decimals wind: {dec_wind}')

        # Get current time
        now = arrow.utcnow().to(self.timezone)

        fc_data = {}

        if self.forecast_interval == 'hourly':

            logger.debug("getting hourly forecasts")

            # Add next 4 forecasts to fc_data dictionary, since we only have
            fc_data = {}
            for index, forecast in enumerate(weather_forecasts[0:4]):
                fc_data['fc' + str(index + 1)] = {
                    'temp': f"{forecast['temp']:.{dec_temp}f}{self.tempDispUnit}",
                    'icon': forecast["icon"],
                    'stamp': forecast["datetime"].strftime("%I %p" if self.hour_format == 12 else "%H:%M")
                }

        elif self.forecast_interval == 'daily':

            logger.debug("getting daily forecasts")

            daily_forecasts = [self.owm.get_forecast_for_day(days) for days in range(1, 5)]

            for index, forecast in enumerate(daily_forecasts):
                fc_data['fc' + str(index + 1)] = {
                    'temp': f'{forecast["temp_min"]:.{dec_temp}f}{self.tempDispUnit}/{forecast["temp_max"]:.{dec_temp}f}{self.tempDispUnit}',
                    'icon': forecast['icon'],
                    'stamp': forecast['datetime'].strftime("%A")
                }
        else:
            logger.error(f"Invalid forecast interval specified: {self.forecast_interval}. Check your settings!")

        for key, val in fc_data.items():
            logger.debug((key, val))

        # Get some current weather details

        temperature = f"{current_weather['temp']:.{dec_temp}f}{self.tempDispUnit}"

        weather_icon = current_weather["weather_icon_name"]
        humidity = str(current_weather["humidity"])

        sunrise_raw = arrow.get(current_weather["sunrise"]).to(self.timezone)
        sunset_raw = arrow.get(current_weather["sunset"]).to(self.timezone)

        logger.debug(f'weather_icon: {weather_icon}')

        if self.hour_format == 12:
            logger.debug('using 12 hour format for sunrise/sunset')
            sunrise = sunrise_raw.format('h:mm a')
            sunset = sunset_raw.format('h:mm a')
        else:
            # 24 hours format
            logger.debug('using 24 hour format for sunrise/sunset')
            sunrise = sunrise_raw.format('H:mm')
            sunset = sunset_raw.format('H:mm')

        # Format the wind-speed to user preference
        logging.debug(f'getting wind speed in {self.windDispUnit}')
        wind = f"{current_weather['wind']:.{dec_wind}f} {self.windDispUnit}"

        moon_phase = get_moon_phase()

        # Fill weather details in col 1 (current weather icon)
        draw_icon(im_colour, weather_icon_pos, (col_width, im_height),
                  weather_icons[weather_icon])

        # Fill weather details in col 2 (temp, humidity, wind)
        draw_icon(im_colour, temperature_icon_pos, (icon_small, row_height),
                  '\uf053')

        if is_negative(temperature):
            write(im_black, temperature_pos, (col_width - icon_small, row_height),
                  temperature, font=self.font)
        else:
            write(im_black, temperature_pos, (col_width - icon_small, row_height),
                  temperature, font=self.font)

        draw_icon(im_colour, humidity_icon_pos, (icon_small, row_height),
                  '\uf07a')

        write(im_black, humidity_pos, (col_width - icon_small, row_height),
              humidity + '%', font=self.font)

        draw_icon(im_colour, windspeed_icon_pos, (icon_small, icon_small),
                  '\uf050')

        write(im_black, windspeed_pos, (col_width - icon_small, row_height),
              wind, font=self.font)

        # Fill weather details in col 3 (moonphase, sunrise, sunset)
        draw_icon(im_colour, moonphase_pos, (col_width, row_height), moon_phase)

        draw_icon(im_colour, sunrise_icon_pos, (icon_small, icon_small), '\uf051')
        write(im_black, sunrise_time_pos, (col_width - icon_small, row_height),
              sunrise, font=self.font)

        draw_icon(im_colour, sunset_icon_pos, (icon_small, icon_small), '\uf052')
        write(im_black, sunset_time_pos, (col_width - icon_small, row_height), sunset,
              font=self.font)

        # Add the forecast data to the correct places
        for pos in range(1, len(fc_data) + 1):
            stamp = fc_data[f'fc{pos}']['stamp']
            # check if we're using daily forecasts
            if "day" in stamp:
                stamp = arrow.get(fc_data[f'fc{pos}']['stamp'], "dddd").format("dddd", locale=self.locale)

            icon = weather_icons[fc_data[f'fc{pos}']['icon']]
            temp = fc_data[f'fc{pos}']['temp']

            write(im_black, eval(f'stamp_fc{pos}'), (col_width, row_height),
                  stamp, font=self.font)
            draw_icon(im_colour, eval(f'icon_fc{pos}'), (col_width, row_height + line_gap * 2),
                      icon)
            write(im_black, eval(f'temp_fc{pos}'), (col_width, row_height),
                  temp, font=self.font)

        border_h = row3 + row_height
        border_w = col_width - 3  # leave 3 pixels gap

        # Add borders around each subsection
        draw_border(im_black, (col1, row1), (col_width * 3 - 3, border_h),
                    shrinkage=(0, 0))

        for _ in range(4, 8):
            draw_border(im_black, (eval(f'col{_}'), row1), (border_w, border_h),
                        shrinkage=(0, 0))

        # return the images ready for the display
        return im_black, im_colour


if __name__ == '__main__':
    print(f'running {__name__} in standalone mode')
