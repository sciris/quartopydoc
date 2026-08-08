# Note: griffe used to require the `allow_section_blank_line` option to permit
# linebreaks inside numpy parameter tables. That is griffe's default behavior as
# of griffe 1.x, and passing the option raises a TypeError on griffe 2.x.
DEFAULT_OPTIONS = {}


def get_parser_defaults(name: str):
    return DEFAULT_OPTIONS.get(name, {})
