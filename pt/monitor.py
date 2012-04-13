# Library imports
import config
import ptxcb
import tilers

# Class imports
from workspace import Workspace

class Monitor(object):
    @staticmethod
    def add(wsid, xinerama):
        for mid, screen in enumerate(xinerama):
            new_mon = Monitor(
                Workspace.WORKSPACES[wsid],
                mid,
                screen['x'],
                screen['y'],
                screen['width'],
                screen['height']
            )

            Workspace.WORKSPACES[wsid].monitors[mid] = new_mon

    @staticmethod
    def remove(wsid):
        for mon in Workspace.WORKSPACES[wsid].iter_monitors():
            for tiler in mon.tilers:
                tiler.destroy()

        Workspace.WORKSPACES[wsid].monitors = {}

    def __init__(self, workspace, mid, x, y, width, height):
        self.workspace = workspace

        self.id = mid
        self.x = x
        self.y = y
        self.width = width
        self.height = height

        self.windows = set()
        self.active = None

        self.tiler = None
        self.auto = True
        self.tilers = []

        # Attach tilers...
        for tile_name in config.get_option('tilers', self.workspace.id, self.id):
            if hasattr(tilers, tile_name):
                tiler = getattr(tilers, tile_name)
                self.add_tiler(tiler(self))

    def add_tiler(self, tiler):
        if tiler.get_name() in config.get_option('all_tilers'):
            self.tilers.append(tiler)

    def add_window(self, win):
        self.windows.add(win)

        if win.id == ptxcb.XROOT.get_active_window():
            self.active = win

        if self.get_tiler():
            self.get_tiler().add(win)

    def calculate_workarea(self):
        self.wa_x = self.x
        self.wa_y = self.y
        self.wa_width = self.width
        self.wa_height = self.height

        if self.get_tiler():
            margin = self.get_tiler().get_option('margin')
        else:
            margin = config.get_option('margin', self.workspace.id, self.id)

        if margin and len(margin) == 4:
            # margin = top(0) right(1) bottom(2) left(3)
            self.wa_x += margin[3]
            self.wa_y += margin[0]
            self.wa_width -= margin[1] + margin[3]
            self.wa_height -= margin[0] + margin[2]
        else:
            wids = ptxcb.XROOT.get_window_ids()

            # Keep track of what we've added...
            # If we come across a window with the same exact
            # size/position/struts, skip it!
            log = []

            for wid in wids:
                win = ptxcb.Window(wid)

                # We're listening to _NET_WORKAREA, so a panel
                # might have died before _NET_CLIENT_LIST was updated...
                try:
                    x, y, w, h = win.get_geometry()
                    d = win.get_desktop_number()
                except:
                    continue

                if self.workspace.contains(win.get_desktop_number()) and self.contains(x, y):
                    struts = win.get_strut_partial()

                    if not struts:
                        struts = win.get_strut()

                    key = (x, y, w, h, struts)

                    if key in log:
                        continue

                    log.append(key)

                    if struts and not all([struts[i] == 0 for i in struts]):
                        if struts['left'] or struts['right']:
                            if struts['left']:
                                self.wa_x += w
                            self.wa_width -= w

                        if struts['top'] or struts['bottom']:
                            if struts['top']:
                                self.wa_y += h
                            self.wa_height -= h
                    elif struts:
                        # When accounting for struts on left/right, and
                        # struts are reported properly, x shouldn't be
                        # zero. Similarly for top/bottom and y.

                        if x > 0 and self.width == (x + w):
                            self.wa_width -= w
                        elif y > 0 and self.height == (y + h):
                            self.wa_height -= h
                        elif x > 0 and self.wa_x == x:
                            self.wa_x += w
                            self.wa_width -= w
                        elif y > 0 and self.wa_y == y:
                            self.wa_y += h
                            self.wa_height -= h

        self.tile()

    def contains(self, x, y):
        if x >= self.x and y >= self.y and x < (self.x + self.width) and y < (self.y + self.height):
            return True

        if (x < 0 or y < 0) and self.x == 0 and self.y == 0:
            return True

        return False

    def cycle(self, tiler_name=None):
        force_tiling = False

        named = [t.get_name() for t in self.tilers]
        named_tiler = None
        if tiler_name and tiler_name in named:
            named_tiler = self.tilers[named.index(tiler_name)]
            force_tiling=True
        elif tiler_name:
            return

        if self.get_tiler() and self.get_tiler().tiling:
            force_tiling = True
            self.get_tiler().detach()

        if named_tiler:
            self.tiler = named_tiler
        else:
            self.tiler = self.tilers[
                (self.tilers.index(self.tiler) + 1) % len(self.tilers)
            ]

        self.calculate_workarea()
        self.tile(force_tiling)

    def get_active(self):
        if not self.active:
            if self.windows:
                self.active = [w for w in self.windows][0]

        return self.active

    def get_tiler(self):
        if not self.tilers:
            return None

        if not self.tiler:
            self.tiler = self.tilers[0]

        return self.tiler

    def iter_windows(self):
        copy = set(self.windows)
        for win in copy:
            yield win

    def refresh_bounds(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def remove_window(self, win):
        if win in self.windows:
            self.windows.remove(win)

        if self.active == win:
            if self.windows:
                self.active = [w for w in self.windows][0]
            else:
                self.active = None

        if self.get_tiler():
            self.get_tiler().remove(win)

    def tile(self, force_tiling=False):
        tiler = self.get_tiler()
        if tiler:
            self.get_tiler().enqueue(force_tiling=force_tiling)

    def tile_reset(self):
        i = self.tilers.index(self.get_tiler())
        tile_name = self.tilers[i].get_name()

        if hasattr(tilers, tile_name):
            self.get_tiler().detach()
            self.tilers[i] = getattr(tilers, tile_name)(self)
            self.tiler = self.tilers[i]

            self.tile(force_tiling=True)

    def __str__(self):
        return 'Monitor %d - [WORKSPACE: %d, X: %d, Y: %d, Width: %d, Height: %d]' % (
            self.id, self.workspace.id, self.x, self.y, self.width, self.height
        )
