"""Helper utils, usually to convert units"""

VALID_NUMBERS = 3


def convert_size(size):
    """Convert size in bytes to higher units"""
    units = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB")

    if not str(size).isnumeric():
        return size

    size = int(size)
    index = 0

    while size >= 10240:
        size = size / 1024
        index += 1
    round_size = max(VALID_NUMBERS + 2 - len(str(size // 1)), 0)
    if round_size == 0:
        round_size = None
    return str(round(size, round_size)) + units[index]


def convert_count(size):
    """Add suffix to number"""
    units = ("", "K", "M", "G", "T", "P", "E", "Z")
    if not str(size).isnumeric():
        return size
    size = int(size)
    index = 0

    while size >= 10240:
        size = size / 1024
        index += 1
    round_size = max(VALID_NUMBERS + 2 - len(str(size // 1)), 0)
    if round_size == 0:
        round_size = None
    return str(round(size, round_size)) + units[index]


def add_percent(input_string):
    """Add percent sign to input"""
    return str(input_string) + "%"


def add_second(input_string):
    """Add percent sign to input"""
    return str(input_string) + "s"


def convert_to_percent(input_string):
    """Multiply by 100 and add percent sign"""
    return add_percent(input_string * 100)


def convert_time_ns(time):
    """Convert ns to higher units"""
    units = ("ns", "us", "ms", "s", "min", "h", "d", "y")
    if not str(time).split(".", maxsplit=1)[0].replace("-", "").isnumeric():
        return time

    if time != 0:
        coef = int(time) / abs(int(time))
        time = abs(int(time))
    else:
        coef = 1

    step = (1000, 1000, 1000, 60, 60, 24, 365)
    time = int(time)
    index = 0
    try:
        while time >= step[index] * 10:
            time = time / step[index]
            index += 1
    except IndexError:
        pass
    round_time = max(VALID_NUMBERS + 2 - len(str(time // 1)), 0)
    if round_time == 0:
        round_time = None
    return str(round(time * coef, round_time)) + units[index]


def convert_time_s(time):
    """Convert seconds to higher units"""
    return convert_time_ns(int(time) * 1000000000)


def bool_to_str(input_bool):
    """Convert bool to y or n"""
    if input_bool is True:
        return "y"
    return "n"


def cat(input_data):
    """Return input unmodified"""
    return input_data


def split_on_words(input_string, max_length):
    """Split input to lines with limited length"""
    delimiters = (" ", ",", ".")
    if len(input_string) < max_length:
        return [input_string]
    sub_str = input_string[0:max_length]
    latest_delimiter = max_length
    for delimiter in delimiters:
        pos = sub_str[::-1].find(delimiter)
        if -1 < pos < latest_delimiter:
            latest_delimiter = pos
        if latest_delimiter == max_length:
            return [sub_str[0:max_length]] + split_on_words(input_string[max_length:], max_length)
    return [sub_str[0 : max_length - latest_delimiter]] + split_on_words(
        input_string[max_length - latest_delimiter + 0 :], max_length
    )
