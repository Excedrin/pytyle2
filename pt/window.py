import time

import ptxcb
import config

from workspace import Workspace

class Window(object):
    WINDOWS = {}

    @staticmethod
    def add(wid):
        if wid not in Window.WINDOWS:
            if Window.manageable(wid):
                win = Window(wid)
                Window.WINDOWS[wid] = win

                return win
        return None

    @staticmethod
    def deep_lookup(wid):
        ret = Window.lookup(wid)

        if ret:
            return ret

        children = ptxcb.Window(wid).query_tree_children()

        if children:
            for child_wid in children:
                ret = Window.deep_lookup(child_wid)

                if ret:
                    return ret

        return None

    @staticmethod
    def lookup(wid):
        if wid in Window.WINDOWS:
            return Window.WINDOWS[wid]
        return None

    @staticmethod
    def manageable(wid):
        win = ptxcb.Window(wid)

        win_types = win.get_types()
        if not win_types or '_NET_WM_WINDOW_TYPE_NORMAL' in win_types:
            states = win.get_states()

            if ('_NET_WM_STATE_MODAL' not in states and
                '_NET_WM_STATE_SHADED' not in states and
                '_NET_WM_STATE_SKIP_TASKBAR' not in states and
                '_NET_WM_STATE_SKIP_PAGER' not in states and
                '_NET_WM_STATE_FULLSCREEN' not in states):
                return True
        return False

    @staticmethod
    def remove(wid):
        win = Window.lookup(wid)

        if win:
            del Window.WINDOWS[wid]
            win.monitor.remove_window(win)

            return win
        return None

    def __init__(self, wid):
        self.id = wid
        self._xwin = ptxcb.Window(wid)
        self.container = None
        self.monitor = None
        self.floating = False
        self.pytyle_moved_time = 0
        self.moving = False

        self.properties = {
            '_NET_WM_NAME': '',
            '_NET_WM_DESKTOP': '',
            '_NET_WM_WINDOW_TYPE': set(),
            '_NET_WM_STATE': set(),
            '_NET_WM_ALLOWED_ACTIONS': set(),
            '_PYTYLE_TYPE': set(),
            '_NET_FRAME_EXTENTS': {
                'top': 0, 'left': 0, 'right': 0, 'bottom': 0
            }
        }

        self.load_geometry()
        self.load_properties()

        self.ox, self.oy, self.owidth, self.oheight = self._xwin.get_geometry()
        self.omaximized = self.maximized()
        self.odecorated = self.decorated()

        self._xwin.listen()

    def activate(self):
        self._xwin.activate()

    def decorations(self, toggle):
        if toggle:
            self._xwin.add_decorations()
        else:
            self._xwin.remove_decorations()

    def get_property(self, pname):
        assert pname in self.properties

        return self.properties[pname]

    def get_tiler(self):
        if self.container and self.container.tiler:
            return self.container.tiler
        return None

    def get_winclass(self):
        cls = self._xwin.get_class()

        if cls:
            return cls[0]
        return ''

    def set_below(self, below):
        self._xwin.set_below(below)

    def lives(self):
        try:
            self._xwin.get_desktop_number()
            return True
        except:
            return False

    def load_geometry(self):
        self.x, self.y, self.width, self.height = self._xwin.get_geometry()

    def load_properties(self):
        property_order = [
            '_NET_WM_NAME',
            '_NET_WM_DESKTOP',
            '_NET_WM_WINDOW_TYPE',
            '_NET_WM_STATE',
            '_NET_WM_ALLOWED_ACTIONS',
            '_NET_FRAME_EXTENTS',
            '_PYTYLE_TYPE'
        ]

        for pname in property_order:
            self.update_property(pname)

    def maximize(self):
        self._xwin.maximize()

    def decorated(self):
        states = self.properties['_NET_WM_STATE']

        if '_OB_WM_STATE_UNDECORATED' in states:
            return False
        return True

    def maximized(self):
        states = self.properties['_NET_WM_STATE']

        if '_NET_WM_STATE_MAXIMIZED_VERT' in states and '_NET_WM_STATE_MAXIMIZED_HORZ' in states:
            return True
        return False

    def moveresize(self, x, y, width, height):
        self.x, self.y, self.width, self.height = x, y, width, height

        self.pytyle_moved_time = time.time()

        self._xwin.restore()

        self._xwin.moveresize(x, y, width, height)

    def original_state(self):
        self.decorations(self.odecorated)
        if self.omaximized:
            self.maximize()
        else:
            self._xwin.moveresize(self.ox, self.oy, self.owidth, self.oheight)

    def pytyle_place_holder(self):
        return '_PYTYLE_TYPE_PLACE_HOLDER' in self.properties['_PYTYLE_TYPE']

    def restack(self, below=False):
        self._xwin.stack(not below)

    def set_container(self, container):
        self.container = container

    def set_geometry(self, x, y, w, h):
        self.x, self.y, self.width, self.height = x, y, w, h

        self.update_monitor()

    def set_monitor(self, wsid, mid):
        new_mon = Workspace.WORKSPACES[wsid].get_monitor(mid)

        if new_mon != self.monitor:
            if self.monitor and self in self.monitor.windows:
                self.monitor.remove_window(self)

            self.monitor = new_mon
            self.monitor.add_window(self)

    def tilable(self):
        if self.floating:
            return False

        states = self.properties['_NET_WM_STATE']
        if '_NET_WM_STATE_HIDDEN' in states or self.pytyle_place_holder():
            return False

        return True

    def update_monitor(self):
        workspace = Workspace.WORKSPACES[self.properties['_NET_WM_DESKTOP']]
        new_mon = workspace.get_monitor_xy(self.x, self.y)

        if new_mon:
            self.set_monitor(new_mon.workspace.id, new_mon.id)

    def update_property(self, pname):
        mname = 'update%s' % pname
        if hasattr(self, mname):
            m = getattr(self, mname)
            m()

    def update_NET_WM_NAME(self):
        self.properties['_NET_WM_NAME'] = self._xwin.get_name() or 'N/A'
        self.name = self.properties['_NET_WM_NAME']

    def update_NET_FRAME_EXTENTS(self):
        self.properties['_NET_FRAME_EXTENTS'] = self._xwin.get_frame_extents()

        if self.container:
            self.container.fit_window()

    def update_NET_WM_DESKTOP(self):
        self.properties['_NET_WM_DESKTOP'] = self._xwin.get_desktop_number()

        self.load_geometry()
        self.update_monitor()

    def update_NET_WM_WINDOW_TYPE(self):
        self.properties['_NET_WM_WINDOW_TYPE'] = self._xwin.get_types()

    def update_NET_WM_STATE(self):
        old = self.properties['_NET_WM_STATE']
        new = self._xwin.get_states()

        self.properties['_NET_WM_STATE'] = new

        removed = old - new
        added = new - old

        if self.container:
            if '_OB_WM_STATE_UNDECORATED' in removed or '_OB_WM_STATE_UNDECORATED' in added:
                self.container.fit_window()
            elif '_NET_WM_STATE_HIDDEN' in added:
                self.container.tiler.remove(self)
        elif self.monitor and self.monitor.get_tiler() and '_NET_WM_STATE_HIDDEN' in removed:
            time.sleep(0.2)
            self.monitor.get_tiler().add(self)

    def update_NET_WM_ALLOWED_ACTIONS(self):
        self.properties['_NET_WM_ALLOWED_ACTIONS'] = self._xwin.get_allowed_actions()

    def update_PYTYLE_TYPE(self):
        self.properties['_PYTYLE_TYPE'] = self._xwin.get_pytyle_types()

    def __str__(self):
        length = 30
        padded_name = ''.join([' ' if ord(c) > 127 else c for c in self.name[0:length].strip()])
        spaces = length - len(padded_name)

        padded_name += ' ' * spaces

        return '%s - [ID: %d, WORKSPACE: %d, MONITOR: %d, X: %d, Y: %d, Width: %d, Height: %d]' % (
            padded_name, self.id, self.monitor.workspace.id, self.monitor.id, self.x, self.y, self.width, self.height
        )

    def DEBUG_sanity_move_resize(self):
        print '-' * 30

        print self.name
        print '-' * 15

        x1, y1, w1, h1 = self._xwin.get_geometry()
        print 'Originals'
        print x1, y1, w1, h1
        print '-' * 15

        self._xwin._moveresize(x1, y1, w1, h1)
        x2, y2, w2, h2 = self._xwin.get_geometry()

        print 'After move/resize'
        print x2, y2, w2, h2
        print '-' * 15

        if x1 == x2 and y1 == y2 and w1 == w2 and h1 == h2:
            print 'EXCELLENT!'
        else:
            print 'Bad form Peter...'

        print '-' * 30, '\n'

class BogusWindow(Window):
    def __init__(self, wsid, x, y, w, h, color=0x000000):
        #self._fx, self._fy = x, y
        #self._fw, self._fh = w, h

        self._xwin = ptxcb.BlankWindow(wsid, x, y, w, h, color)
        self.id = self._xwin.wid
        self.container = None
        self.monitor = None
        self.floating = False
        self.pytyle_moved_time = 0
        self.moving = False
        self.name = 'Place holder'

        self.properties = {
            '_NET_WM_NAME': 'Place holder',
            '_NET_WM_DESKTOP': wsid,
            '_NET_WM_WINDOW_TYPE': set(),
            '_NET_WM_STATE': set(),
            '_NET_WM_ALLOWED_ACTIONS': set(),
            '_PYTYLE_TYPE': set('_PYTYLE_TYPE_PLACE_HOLDER'),
            '_NET_FRAME_EXTENTS': {
                'top': 0, 'left': 0, 'right': 0, 'bottom': 0
            }
        }

        self.x, self.y = x, y
        self.width, self.height = w, h

        self.update_monitor()

        #self.ox, self.oy, self.owidth, self.oheight = self._xwin.get_geometry()
        self.omaximized = self.maximized()
        self.odecorated = self.decorated()

        self._xwin.listen()

        Window.WINDOWS[self.id] = self

    def pytyle_place_holder(self):
        return True

    def tilable(self):
        return False

    def close(self):
        self._xwin.close()

        if self.monitor:
            self.monitor.remove_window(self)
