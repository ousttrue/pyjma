from typing import List, Any
import datetime
import asyncio
import aiohttp
import logging
import ctypes
from pydear import glo
from pydear.utils import dockspace
from pydear import imgui as ImGui
logger = logging.getLogger(__name__)

DATE_FORMAT = '%Y%m%d%H%M%S'

AMEDAS_STALBE_URL = 'https://www.jma.go.jp/bosai/amedas/const/amedastable.json'
TIMES_URL = 'https://www.jma.go.jp/bosai/himawari/data/satimg/targetTimes_fd.json'


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

# ひまわり
# https://www.jma.go.jp/bosai/himawari/data/satimg/{basetime}/fd/{validtime}/{band}/{prod}/{z}/{x}/{y}.jpg


async def get_json_async(url: str):
    logger.info(f'get {url}...')
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            value = await response.json()
            logger.debug(f'{url} done')
            return value


def table_selector(headers: List[str], row_it, col_it, last_selected):
    flags = (
        ImGui.ImGuiTableFlags_.BordersV
        | ImGui.ImGuiTableFlags_.BordersOuterH
        | ImGui.ImGuiTableFlags_.Resizable
        | ImGui.ImGuiTableFlags_.RowBg
        | ImGui.ImGuiTableFlags_.NoBordersInBody
    )
    selected = None
    if ImGui.BeginTable("jsontree_table", len(headers), flags):
        # header
        for header in headers:
            ImGui.TableSetupColumn(header)
        ImGui.TableHeadersRow()

        # body
        for key, row in row_it:
            # row
            ImGui.TableNextRow()
            it = col_it(row)
            # 0
            ImGui.TableNextColumn()
            col = next(it)
            if ImGui.Selectable(f'{col}###{key}', key == last_selected, ImGui.ImGuiSelectableFlags_.SpanAllColumns):
                logger.debug(f'select: {key}')
                selected = key
            while True:
                try:
                    col = next(it)
                    ImGui.TableNextColumn()
                    ImGui.TextUnformatted(str(col))
                except StopIteration:
                    break

        ImGui.EndTable()

    return selected


class Gui(dockspace.DockingGui):
    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        from pydear.utils.loghandler import ImGuiLogHandler
        log_handler = ImGuiLogHandler()
        log_handler.setFormatter(logging.Formatter(
            '%(name)s:%(lineno)s[%(levelname)s]%(message)s'))
        log_handler.register_root()

        docks = [
            dockspace.Dock('log',
                           (ctypes.c_bool * 1)(True), log_handler.draw),
            dockspace.Dock('stable',
                           (ctypes.c_bool * 1)(True), self.select_stable),
            dockspace.Dock('times',
                           (ctypes.c_bool * 1)(True), self.select_time),
            dockspace.Dock('amedas',
                           (ctypes.c_bool * 1)(True), self.show_amedas),
        ]
        super().__init__(loop, docks)

        self.times = []
        self.time_selected = None
        self.stable = None
        self.stable_selected = None
        self.amedas = None
        self.loop.create_task(self.start_async())

    def _setup_font(self):
        io = ImGui.GetIO()
        io.Fonts.AddFontFromFileTTF(
            'C:/windows/fonts/msgothic.ttc', 24, None, io.Fonts.GetGlyphRangesJapanese())
        io.Fonts.Build()

    async def start_async(self):
        stable = await get_json_async(AMEDAS_STALBE_URL)
        self.stable = stable

        times = await get_json_async(TIMES_URL)
        self.times = [to_datetime(t['validtime']) for t in times]

    def select_stable(self, p_open: ctypes.Array):
        if ImGui.Begin('stable', p_open):
            if isinstance(self.stable, dict):
                selected = table_selector(
                    ['key', 'value'], [(k, (k, v)) for k, v in self.stable.items()], iter, self.stable_selected)
                if selected:
                    self.stable_selected = selected
        ImGui.End()

    def select_time(self, p_open: ctypes.Array):
        if ImGui.Begin('times', p_open):
            selected = table_selector(
                ['value'], enumerate(self.times), lambda v: iter([v]), self.time_selected)
            if selected:
                self.time_selected = selected
            # if isinstance(selected, int):
            #     self.loop.create_task(
            #         self.select_time_async(self.times[selected]))
        ImGui.End()

    async def select_time_async(self, time: datetime.datetime):
        url = f'https://www.jma.go.jp/bosai/amedas/data/map/{time.strftime(DATE_FORMAT)}.json'
        self.amedas = await get_json_async(url)

    def show_amedas(self, p_open: ctypes.Array):
        if ImGui.Begin('amedas', p_open):
            pass
            # print(self.amedas)
        ImGui.End()


def main():
    logging.basicConfig(level=logging.DEBUG)

    from pydear.utils import glfw_app
    app = glfw_app.GlfwApp('pyjma')

    gui = Gui(app.loop)
    from pydear.backends import impl_glfw
    impl_glfw = impl_glfw.ImplGlfwInput(app.window)
    while app.clear():
        impl_glfw.process_inputs()
        gui.render()
    del gui


if __name__ == '__main__':
    main()
