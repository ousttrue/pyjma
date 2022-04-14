import json
from typing import List, Optional, Tuple
import pathlib
import datetime
import asyncio
import logging
import ctypes
import jma
from pydear.utils import dockspace
from pydear import imgui as ImGui
logger = logging.getLogger(__name__)

# ひまわり
# https://www.jma.go.jp/bosai/himawari/data/satimg/{basetime}/fd/{validtime}/{band}/{prod}/{z}/{x}/{y}.jpg


def table_selector(headers: List[str], row_it, col_it, last_selected):
    flags = (
        ImGui.ImGuiTableFlags_.BordersV
        | ImGui.ImGuiTableFlags_.BordersOuterH
        | ImGui.ImGuiTableFlags_.Resizable
        | ImGui.ImGuiTableFlags_.RowBg
        | ImGui.ImGuiTableFlags_.NoBordersInBody
    )
    selected = None
    if ImGui.BeginTable("table_selector", len(headers), flags):
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


def area_selector(centers: List[jma.AreaNode], last_selected) -> Optional[Tuple[jma.AreaNode, ...]]:
    flags = (
        ImGui.ImGuiTableFlags_.BordersV
        | ImGui.ImGuiTableFlags_.BordersOuterH
        | ImGui.ImGuiTableFlags_.Resizable
        | ImGui.ImGuiTableFlags_.RowBg
        | ImGui.ImGuiTableFlags_.NoBordersInBody
    )
    selected: List[Tuple[jma.AreaNode, ...]] = [()]
    if ImGui.BeginTable("area_selector", 2, flags):
        # header
        ImGui.TableSetupColumn('name')
        ImGui.TableSetupColumn('key')
        ImGui.TableHeadersRow()

        def area_node(node: jma.AreaNode, parent_path: Tuple[jma.AreaNode, ...], default_open=False):
            path = parent_path + (node,)
            ImGui.TableNextRow()
            # name
            ImGui.TableNextColumn()
            tree_flag = ImGui.ImGuiTreeNodeFlags_.OpenOnArrow | ImGui.ImGuiTreeNodeFlags_.OpenOnDoubleClick | ImGui.ImGuiTreeNodeFlags_.SpanAvailWidth
            if path == last_selected:
                tree_flag |= ImGui.ImGuiTreeNodeFlags_.Selected
            if not node.children:
                tree_flag |= ImGui.ImGuiTreeNodeFlags_.Leaf
                tree_flag |= ImGui.ImGuiTreeNodeFlags_.Bullet
            if default_open:
                ImGui.SetNextItemOpen(True, ImGui.ImGuiCond_.FirstUseEver)
            open = ImGui.TreeNodeEx(node.name, tree_flag)
            if ImGui.IsItemClicked() and not ImGui.IsItemToggledOpen():
                selected[0] = path
                logger.debug(f'selected: {selected[0]}')
            # ImGui.SetItemAllowOverlap()
            # key
            ImGui.TableNextColumn()
            ImGui.TextUnformatted(node.key)

            if open:
                for child in node.children:
                    area_node(child, path)
                ImGui.TreePop()

        for node in centers:
            area_node(node, (), True)

        ImGui.EndTable()
    return selected[0]


def show_table(table_name, times, headers, data):
    name = data['area']['name']
    ImGui.TextUnformatted(f'{name}')
    flags = (
        ImGui.ImGuiTableFlags_.BordersV
        | ImGui.ImGuiTableFlags_.BordersOuterH
        | ImGui.ImGuiTableFlags_.Resizable
        | ImGui.ImGuiTableFlags_.RowBg
        | ImGui.ImGuiTableFlags_.NoBordersInBody
    )
    if ImGui.BeginTable(table_name, len(headers)+1, flags):
        # header
        ImGui.TableSetupColumn('time')
        for header in headers:
            ImGui.TableSetupColumn(header)
        ImGui.TableHeadersRow()

        # body
        for i, time in enumerate(times):
            # row
            ImGui.TableNextRow()
            # 0
            ImGui.TableNextColumn()
            ImGui.TextUnformatted(f'{time}')

            for header in headers:
                ImGui.TableNextColumn()
                value = data.get(header)
                if value:
                    # waves 無いとき
                    ImGui.TextUnformatted(f'{value[i]}')

        ImGui.EndTable()


class Gui(dockspace.DockingGui):
    def __init__(self, loop: asyncio.AbstractEventLoop, cache_dir: pathlib.Path) -> None:
        from pydear.utils.loghandler import ImGuiLogHandler
        log_handler = ImGuiLogHandler()
        log_handler.setFormatter(logging.Formatter(
            '%(name)s:%(lineno)s[%(levelname)s]%(message)s'))
        log_handler.register_root()

        docks = [
            dockspace.Dock('log', log_handler.draw,
                           (ctypes.c_bool * 1)(True)),
            dockspace.Dock('area', self.select_area,
                           (ctypes.c_bool * 1)(True)),
            dockspace.Dock('times', self.select_time,
                           (ctypes.c_bool * 1)(True)),
            dockspace.Dock('selected', self.show_selected,
                           (ctypes.c_bool * 1)(True)),
            dockspace.Dock('forecast', self.show_forecast,
                           (ctypes.c_bool * 1)(True)),
            dockspace.Dock('metrics', ImGui.ShowMetricsWindow,
                           (ctypes.c_bool * 1)(True)),
        ]
        super().__init__(loop, docks=docks)

        self.times = []
        self.time_selected = None
        self.area = None
        self.area_selected = None
        self.stable = None
        self.stable_selected = None
        self.amedas = None
        self.forecast = None

        import jma.http_getter
        self.getter = jma.http_getter.HttpGetter(loop, cache_dir)
        self.loop.create_task(self.start_async())

    def _setup_font(self):
        io = ImGui.GetIO()
        font_size = 24

        io.Fonts.AddFontFromFileTTF('C:/Windows/Fonts/MSGothic.ttc',
                                    font_size, None, io.Fonts.GetGlyphRangesJapanese())

        import pkgutil
        font = pkgutil.get_data(
            'weather_icons', 'assets/weathericons-regular-webfont.ttf')
        assert font
        font_range = [
            0xf000, 0xf00e,
            0xf010, 0xf01f,
            0xf021, 0xf03f,
            0xf040, 0xf049,
            0xf04a, 0xf04f,
            0xf050, 0xf059,
            0xf062, 0xf06f,
            0xf070, 0xf07f,
            0xf080, 0xf0ec,
            0
        ]
        font_range = (ctypes.c_ushort * len(font_range))(*font_range)

        font_cfg = ImGui.ImFontConfig()
        font_cfg.FontDataOwnedByAtlas = True
        font_cfg.OversampleH = 3  # FIXME: 2 may be a better default?
        font_cfg.OversampleV = 1
        font_cfg.GlyphMaxAdvanceX = 9999
        font_cfg.RasterizerMultiply = 1.0
        font_cfg.EllipsisChar = 65535
        font_cfg.MergeMode = True
        import weather_icons
        io.Fonts.AddFontFromFileTTF(str(weather_icons.get_path()), font_size, font_cfg, font_range)

        io.Fonts.Build()

    async def start_async(self):
        area = await self.getter.get_json_async(jma.AREA_URL)
        self.area = jma.area_tree(area)

        stable = await self.getter.get_json_async(jma.AMEDAS_STALBE_URL)
        self.stable = stable

        times = await self.getter.get_json_async(jma.HIMAWARI_TIMES_URL)
        self.times = [jma.to_datetime(t['validtime']) for t in times]

    def select_area(self, p_open: ctypes.Array):
        if ImGui.Begin('area', p_open):
            if self.area:
                selected = area_selector(self.area, self.area_selected)
                if selected:
                    self.area_selected = selected
                    if len(self.area_selected) > 1:
                        office = self.area_selected[1]
                        self.loop.create_task(self.get_forecast(office))
        ImGui.End()

    async def get_forecast(self, office: jma.AreaNode):
        url = f'https://www.jma.go.jp/bosai/forecast/data/forecast/{office.key}.json'
        self.forecast = await self.getter.get_json_async(url, use_cache=False)

    def _show_forecast_3day(self, data):
        times = [datetime.datetime.fromisoformat(
            t) for t in data['timeDefines']]
        for area in data['areas']:
            show_table(f'forecast3', times,
                       ['weatherCodes', 'weathers', 'winds \uf058', 'waves'], area)

    def _show_forecast_rain6(self, data):
        times = [datetime.datetime.fromisoformat(
            t) for t in data['timeDefines']]
        for area in data['areas']:
            show_table('rain6', times, ['pops'], area)

    def _show_forecast_temperature(self, data):
        times = [datetime.datetime.fromisoformat(
            t) for t in data['timeDefines']]
        for area in data['areas']:
            show_table('temperature', times, ['temps'], area)

    def show_forecast(self, p_open: ctypes.Array):
        if ImGui.Begin('forecast', p_open):
            if self.forecast:
                latest, week = self.forecast
                forecast3day, rain6, temperature = latest['timeSeries']
                self._show_forecast_3day(forecast3day)
                self._show_forecast_rain6(rain6)
                self._show_forecast_temperature(temperature)
                week_forecast, week_temperature = week['timeSeries']
                temp_average = week['tempAverage']
                precip_average = week['precipAverage']
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
        url = f'https://www.jma.go.jp/bosai/amedas/data/map/{time.strftime(jma.DATE_FORMAT)}.json'
        self.amedas = await self.getter.get_json_async(url)

    def show_selected(self, p_open: ctypes.Array):
        if ImGui.Begin('amedas', p_open):
            if self.area_selected:
                ImGui.TextUnformatted(f'center: {self.area_selected[0].name}')
                if len(self.area_selected) > 1:
                    ImGui.TextUnformatted(
                        f'office: {self.area_selected[1].name}')
            if self.time_selected:
                ImGui.TextUnformatted(f'{self.times[self.time_selected]}')
        ImGui.End()


def main():
    logging.basicConfig(level=logging.DEBUG)

    from pydear.utils import glfw_app
    app = glfw_app.GlfwApp('pyjma')

    gui = Gui(app.loop, pathlib.Path('.') / 'cache')
    from pydear.backends import impl_glfw
    impl_glfw = impl_glfw.ImplGlfwInput(app.window)
    while app.clear():
        impl_glfw.process_inputs()
        gui.render()
    del gui


if __name__ == '__main__':
    main()
