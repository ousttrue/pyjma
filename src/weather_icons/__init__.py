import pathlib

HERE = pathlib.Path(__file__).absolute().parent


def get_path() -> pathlib.Path:
    return HERE / 'assets/weathericons-regular-webfont.ttf'
