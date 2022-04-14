from typing import NamedTuple, Dict, List
import pkgutil
import xml.etree.ElementTree
import io


class Icon(NamedTuple):
    name: str
    codepoint: int

    def __str__(self) -> str:
        return f'{self.name}:{self.codepoint:x}'


def print_range():
    data = pkgutil.get_data('weather_icons', 'assets/weathericons.xml')
    assert data

    tree = xml.etree.ElementTree.parse(io.BytesIO(data))
    root = tree.getroot()

    icon_map: Dict[int, List[str]] = {}
    for tag in root:
        name = tag.attrib['name']
        cp = ord(tag.text)
        names = icon_map.get(cp)
        if names:
            names.append(name)
        else:
            icon_map[cp] = [name]

    keys = sorted(icon_map.keys())

    last = keys[0]
    start = last
    for key in keys[1:]:
        if key!=last+1:
            print(f'{start:x}, {last+1:x}')
            start = key
        else:
            pass
        last = key
    print(f'{start:x}, {last+1:x}')


if __name__ == '__main__':
    print_range()
