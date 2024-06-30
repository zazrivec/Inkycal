"""
Inkycal Agenda Module
Copyright by aceinnolab
"""
import arrow # noqa
from inkycal.custom import *
from inkycal.modules.ical_parser import iCalendar
from inkycal.modules.template import inkycal_module

logger = logging.getLogger(__name__)


class Agenda(inkycal_module):
    """Agenda class
    Create agenda and show events from given icalendars
    """

    name = "Agenda - Display upcoming events from given iCalendars"

    requires = {
        "ical_urls": {
            "label": "iCalendar URL/s, separate multiple ones with a comma",
        },

    }

    optional = {
        "ical_files": {
            "label": "iCalendar filepaths, separated with a comma",
        },

        "date_format": {
            "label": "Use an arrow-supported token for custom date formatting " +
                     "see https://arrow.readthedocs.io/en/stable/#supported-tokens, e.g. ddd D MMM",
            "default": "ddd D MMM",
        },

        "time_format": {
            "label": "Use an arrow-supported token for custom time formatting " +
                     "see https://arrow.readthedocs.io/en/stable/#supported-tokens, e.g. HH:mm",
            "default": "HH:mm",
        },

    }

    def __init__(self, config):
        """Initialize inkycal_agenda module"""

        super().__init__(config)

        config = config['config']

        # Check if all required parameters are present
        for param in self.requires:
            if param not in config:
                raise Exception(f'config is missing {param}')

        # module specific parameters
        self.date_format = config['date_format']
        self.time_format = config['time_format']
        self.language = config['language']

        # Check if ical_files is an empty string
        if config['ical_urls'] and isinstance(config['ical_urls'], str):
            self.ical_urls = config['ical_urls'].split(',')
        else:
            self.ical_urls = config['ical_urls']

        # Check if ical_files is an empty string
        if config['ical_files'] and isinstance(config['ical_files'], str):
            self.ical_files = config['ical_files'].split(',')
        else:
            self.ical_files = config['ical_files']

        # Additional config
        self.timezone = get_system_tz()

        self.icon_font = ImageFont.truetype(fonts['MaterialIcons'], size=self.fontsize)

        # give an OK message
        logger.debug(f'{__name__} loaded')

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

        # Calculate the max number of lines that can fit on the image
        line_spacing = 1

        text_bbox_height = self.font.getbbox("hg")
        line_height = text_bbox_height[3] + line_spacing
        line_width = im_width
        max_lines = im_height // line_height
        logger.debug(f'max lines: {max_lines}')

        # Create timeline for agenda
        now = arrow.now()
        today = now.floor('day')

        # Create a list of dates for the next days
        agenda_events = [
            {
                'begin': today.shift(days=+_),
                'title': today.shift(days=+_).format(
                    self.date_format, locale=self.language)
            }
            for _ in range(max_lines)]

        # Load icalendar from config
        self.ical = iCalendar()
        parser = self.ical

        if self.ical_urls:
            parser.load_url(self.ical_urls)

        if self.ical_files:
            parser.load_from_file(self.ical_files)

        # Load events from all icalendar in timerange
        upcoming_events = parser.get_events(today, agenda_events[-1]['begin'],
                                            self.timezone)

        # Sort events by beginning time
        parser.sort()
        # parser.show_events()

        # Set the width for date, time and event titles
        date_width = int(max([self.font.getlength(
            dates['begin'].format(self.date_format, locale=self.language))
            for dates in agenda_events]))
        logger.debug(f'date_width: {date_width}')

        # Calculate positions for each line
        line_pos = [(0, int(line * line_height)) for line in range(max_lines)]
        logger.debug(f'line_pos: {line_pos}')

        # Check if any events were filtered
        if upcoming_events:
            logger.info('Managed to parse events from urls')

            # Find out how much space the event times take

            time_width = int(max([self.font.getlength(
                events['begin'].format(self.time_format, locale=self.language))
                for events in upcoming_events]) + 10)
            logger.debug(f'time_width: {time_width}')

            # Calculate x-pos for time
            x_time = int(date_width/3)
            logger.debug(f'x-time: {x_time}')

            # Find out how much space is left for event titles
            event_width = im_width - time_width 
            logger.debug(f'width for events: {event_width}')

            # Calculate x-pos for event titles
            x_event = int(date_width/3) + time_width
            logger.debug(f'x-event: {x_event}')

            # Merge list of dates and list of events
            agenda_events += upcoming_events

            # Sort the combined list in chronological order of dates
            by_date = lambda event: event['begin']
            agenda_events.sort(key=by_date)

            # Delete more entries than can be displayed (max lines)
            del agenda_events[max_lines:]

            self._agenda_events = agenda_events

            cursor = 0
            for _ in agenda_events:
                title = _['title']

                # Check if item is a date
                if 'end' not in _:
                    ImageDraw.Draw(im_colour).line(
                        (0, line_pos[cursor][1], im_width, line_pos[cursor][1]),
                        fill='black')

                    write(im_black, line_pos[cursor], (date_width, line_height),
                          title, font=self.font, alignment='left')

                    cursor += 1

                # Check if item is an event
                if 'end' in _:
                    time = _['begin'].format(self.time_format, locale=self.language)

                    # Check if event is all day, if not, add the time
                    if not parser.all_day(_):
                        write(im_colour, (x_time, line_pos[cursor][1]),
                              (time_width, line_height), time,
                              font=self.font, alignment='right')
                    else:
                        write(im_black, (x_time, line_pos[cursor][1]),
                              (time_width, line_height), "\ue878",
                              font=self.icon_font, alignment='right')

                    write(im_black, (x_event, line_pos[cursor][1]),
                          (event_width, line_height),
                          ' • ' + title, font=self.font, alignment='left')
                    cursor += 1

        # If no events were found, write only dates and lines
        else:
            logger.info('no events found')

            cursor = 0
            for _ in agenda_events:
                title = _['title']
                ImageDraw.Draw(im_colour).line(
                    (0, line_pos[cursor][1], im_width, line_pos[cursor][1]),
                    fill='black')

                write(im_black, line_pos[cursor], (date_width, line_height),
                      title, font=self.font, alignment='left')

                cursor += 1

        # return the images ready for the display
        return im_black, im_colour
