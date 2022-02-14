from typing import List
import datetime

DATE_FORMAT = '%Y%m%d%H%M%S'


def to_datetime(src: str) -> datetime.datetime:
    # {"basetime" : "20220211225000", "validtime" : "20220211225000"}
    assert(len(src) == 14)
    year = src[0:4]
    month = src[4:6]
    day = src[6:8]
    hour = src[8:10]
    minute = src[10:12]
    second = src[12:14]
    return datetime.datetime(year=int(year), month=int(month), day=int(day), hour=int(hour), minute=int(minute), second=int(second))


BASE_URL = 'https://www.jma.go.jp/bosai'
AREA_URL = f'{BASE_URL}/common/const/area.json'
AMEDAS_STALBE_URL = f'{BASE_URL}/amedas/const/amedastable.json'
HIMAWARI_TIMES_URL = f'{BASE_URL}/himawari/data/satimg/targetTimes_fd.json'

OVERVIEW_URL = f'{BASE_URL}/forecast/data/overview_forecast/%(office)s.json'
FORECAST_URL = f'{BASE_URL}/forecast/data/forecast/%(office)s.json'

class AreaNode:
    def __init__(self, key, name) -> None:
        self.key = key
        self.name = name
        self.children: List[AreaNode] = []


def area_tree(area) -> List[AreaNode]:
    node_map = {}

    def create_node(data):
        nodes = []
        for k, v in data.items():
            node = AreaNode(k, v['name'])
            node_map[k] = node
            for child in v.get('children', []):
                if child == k:
                    continue
                node.children.append(node_map[child])
            nodes.append(node)
        return nodes
    create_node(area['class20s'])
    create_node(area['class15s'])
    create_node(area['class10s'])
    create_node(area['offices'])
    return create_node(area['centers'])
