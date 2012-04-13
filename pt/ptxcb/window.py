import struct, traceback, time

import xcb.xproto, xcb.xcb

import connection
from atom import Atom
from events import events

class Window(object):
    queue = []

    @staticmethod
    def exec_queue():
        for tup in Window.queue:
            tup[0](*tup[1:])
        Window.queue = []

    def __init__(self, wid):
        self.wid = wid

    # Helpers
    def _get_geometry(self):
        try:
            raw = connection.get_core().GetGeometry(self.wid).reply()

            return (raw.x, raw.y, raw.width, raw.height)
        except:
            return False

    def _get_property(self, atom_name):
        try:
            if not Atom.get_type_name(atom_name):
                return ''

            rsp = connection.get_core().GetProperty(
                False,
                self.wid,
                Atom.get_atom(atom_name),
                Atom.get_atom_type(atom_name),
                0,
                (2 ** 32) - 1
            ).reply()

            if Atom.get_type_name(atom_name) in ('UTF8_STRING', 'STRING'):
                if atom_name == 'WM_CLASS':
                    return Atom.null_terminated_to_strarray(rsp.value)
                else:
                    return Atom.ords_to_str(rsp.value)
            elif Atom.get_type_name(atom_name) in ('UTF8_STRING[]', 'STRING[]'):
                return Atom.null_terminated_to_strarray(rsp.value)
            else:
                return list(struct.unpack('I' * (len(rsp.value) / 4), rsp.value.buf()))
        except:
            pass

    def _moveresize(self, x, y, width, height):
        #print self.get_wmname(), x, y, width, height
        self._send_client_event(
            Atom.get_atom('_NET_MOVERESIZE_WINDOW'),
            [
                xcb.xproto.Gravity.NorthWest
                | 1 << 8 | 1 << 9 | 1 << 10 | 1 << 11 | 1 << 13,
                x,
                y,
                width,
                height
            ],
            32,
            xcb.xproto.EventMask.StructureNotify
        )

        connection.push()

    def _send_client_event(self, message_type, data, format=32, event_mask=xcb.xproto.EventMask.SubstructureRedirect):
        XROOT._send_client_event_exec(self.wid, message_type, data, format, event_mask)

    def _send_client_event_exec(self, to_wid, message_type, data, format=32, event_mask=xcb.xproto.EventMask.SubstructureRedirect):
        try:
            data = data + ([0] * (5 - len(data)))
            packed = struct.pack(
                'BBH7I',
                events['ClientMessageEvent'],
                format,
                0,
                to_wid,
                message_type,
                data[0], data[1], data[2], data[3], data[4]
            )

            connection.get_core().SendEvent(
                False,
                self.wid,
                event_mask,
                packed
            )
        except:
            print traceback.format_exc()

    def _set_property(self, atom_name, value):
        try:
            if isinstance(value, list):
                data = struct.pack(len(value) * 'I', *value)
                data_len = len(value)
            else:
                value = str(value)
                data_len = len(value)
                data = value

            connection.get_core().ChangeProperty(
                xcb.xproto.PropMode.Replace,
                self.wid,
                Atom.get_atom(atom_name),
                Atom.get_atom_type(atom_name),
                Atom.get_atom_length(atom_name),
                data_len,
                data
            )
        except:
            print traceback.format_exc()

    def activate(self):
        self._send_client_event(
            Atom.get_atom('_NET_ACTIVE_WINDOW'),
            [
                2,
                xcb.xcb.CurrentTime,
                self.wid
            ]
        )
        self.stack(True)

    def add_decorations(self):
        if XROOT.wm() == 'openbox':
            self._send_client_event(
                Atom.get_atom('_NET_WM_STATE'),
                [
                    0,
                    Atom.get_atom('_OB_WM_STATE_UNDECORATED')
                ]
            )
        else:
            self._set_property('_MOTIF_WM_HINTS', [2, 0, 1, 0, 0])

        connection.push()

    def button_pressed(self):
        pointer = self.query_pointer()

        if xcb.xproto.KeyButMask.Button1 & pointer.mask:
            return True
        return False

    def close(self):
        self._send_client_event(
            Atom.get_atom('_NET_CLOSE_WINDOW'),
            [
                xcb.xproto.Time.CurrentTime,
                2,
                0,
                0,
                0
            ]
        )

    def get_allowed_actions(self):
        return set([Atom.get_atom_name(anum) for anum in self._get_property('_NET_WM_ALLOWED_ACTIONS')])

    def get_class(self):
        return self._get_property('WM_CLASS')

    def get_desktop_number(self):
        ret = self._get_property('_NET_WM_DESKTOP')[0]

        if ret == 0xFFFFFFFF:
            return 'all'

        return ret

    def get_geometry(self):
        try:
            # Need to move up two parents to get proper coordinates
            # and size for KWin
            if XROOT.wm() == 'kwin':
                x, y, w, h = self.query_tree_parent().query_tree_parent()._get_geometry()
            else:
                x, y, w, h = self.query_tree_parent()._get_geometry()

            return (
                x,
                y,
                w,
                h
            )
        except:
            return False

    def get_name(self):
        return self._get_property('_NET_WM_NAME')

    def get_wmname(self):
        return self._get_property('WM_NAME')

    def get_pytyle_types(self):
        return set([Atom.get_atom_name(anum) for anum in self._get_property('_PYTYLE_TYPE')])

    def get_states(self):
        return set([Atom.get_atom_name(anum) for anum in self._get_property('_NET_WM_STATE')])

    def get_strut(self):
        raw = self._get_property('_NET_WM_STRUT')

        if not raw:
            return None

        return {
            'left': raw[0],
            'right': raw[1],
            'top': raw[2],
            'bottom': raw[3]
        }

    def get_strut_partial(self):
        raw = self._get_property('_NET_WM_STRUT_PARTIAL')

        if not raw:
            return None

        return {
            'left': raw[0], 'right': raw[1],
            'top': raw[2], 'bottom': raw[3],
            'left_start_y': raw[4], 'left_end_y': raw[5],
            'right_start_y': raw[6], 'right_end_y': raw[7],
            'top_start_x': raw[8], 'top_end_x': raw[9],
            'bottom_start_x': raw[10], 'bottom_end_x': raw[11]
        }

    def get_types(self):
        return set([Atom.get_atom_name(anum) for anum in self._get_property('_NET_WM_WINDOW_TYPE')])

    def get_visible_name(self):
        return self._get_property('_NET_WM_VISIBLE_NAME')

    def get_frame_extents(self):
        raw = self._get_property('_NET_FRAME_EXTENTS')

        if raw:
            return {
                'left': raw[0],
                'right': raw[1],
                'top': raw[2],
                'bottom': raw[3]
            }
        else:
            return {
                'left': 0, 'right': 0,
                'top': 0, 'bottom': 0
            }

    def listen(self):
        self.set_event_masks(
            xcb.xproto.EventMask.PropertyChange |
            xcb.xproto.EventMask.FocusChange
        )

    def maximize(self):
        self._send_client_event(
            Atom.get_atom('_NET_WM_STATE'),
            [
                1, # _NET_WM_STATE_REMOVE = 0, _NET_WM_STATE_ADD = 1, _NET_WM_STATE_TOGGLE = 2
                Atom.get_atom('_NET_WM_STATE_MAXIMIZED_VERT'),
                Atom.get_atom('_NET_WM_STATE_MAXIMIZED_HORZ')
            ]
        )

        connection.push()

    def moveresize(self, x, y, width, height):
        Window.queue.append(
            (Window.moveresize_exec, self, x, y, width, height)
        )

    def moveresize_exec(self, x, y, width, height):
        try:
            # KWin reports _NET_FRAME_EXTENTS correctly...
            if XROOT.wm() == 'kwin':
                borders = self.get_frame_extents()

                w = width - (borders['left'] + borders['right'])
                h = height - (borders['top'] + borders['bottom'])
            else:
                rx, ry, rwidth, rheight = self._get_geometry()
                px, py, pwidth, pheight = self.get_geometry()

                w = width - (pwidth - rwidth)
                h = height - (pheight - rheight)

            x = 0 if x < 0 else x
            y = 0 if y < 0 else y
            w = 1 if w <= 0 else w
            h = 1 if h <= 0 else h

            self._moveresize(x, y, w, h)
        except:
            return False

    def query_pointer(self):
        return connection.get_core().QueryPointer(self.wid).reply()

    def query_tree_children(self):
        try:
            children = connection.get_core().QueryTree(self.wid).reply().children

            return [wid for wid in children]
        except:
            return False

    def query_tree_parent(self):
        try:
            return Window(connection.get_core().QueryTree(self.wid).reply().parent)
        except:
            return False

    def remove_decorations(self):
        if XROOT.wm() == 'openbox':
            self._send_client_event(
                Atom.get_atom('_NET_WM_STATE'),
                [
                    1,
                    Atom.get_atom('_OB_WM_STATE_UNDECORATED')
                ]
            )
        else:
            self._set_property('_MOTIF_WM_HINTS', [2, 0, 0, 0, 0])

        connection.push()

    def restack(self, below=False):
        self._send_client_event(
            Atom.get_atom('_NET_RESTACK_WINDOW'),
            [
                2 if not below else 1,
                self.wid,
                0
            ]
        )

    def restore(self):
        self._send_client_event(
            Atom.get_atom('_NET_WM_STATE'),
            [
                0, # _NET_WM_STATE_REMOVE = 0, _NET_WM_STATE_ADD = 1, _NET_WM_STATE_TOGGLE = 2
                Atom.get_atom('_NET_WM_STATE_MAXIMIZED_VERT'),
                Atom.get_atom('_NET_WM_STATE_MAXIMIZED_HORZ')
            ]
        )

        connection.push()

    def set_below(self, below):
        self._send_client_event(
            Atom.get_atom('_NET_WM_STATE'),
            [
                1 if below else 0,
                Atom.get_atom('_NET_WM_STATE_BELOW'),
            ]
        )

        connection.push()

    def stack(self, above):
        try:
            connection.get_core().ConfigureWindow(
                self.wid,
                xcb.xproto.ConfigWindow.StackMode,
                [xcb.xproto.StackMode.Above if above else xcb.xproto.StackMode.Below]
            )
        except:
            return False

    def set_desktop(self, desk):
        self._send_client_event(
            Atom.get_atom('_NET_WM_DESKTOP'),
            [
                desk,
                2
            ]
        )

    def set_event_masks(self, event_masks):
        try:
            connection.get_core().ChangeWindowAttributes(
                self.wid,
                xcb.xproto.CW.EventMask,
                [event_masks]
            )
        except:
            print traceback.format_exc()

    def set_override_redirect(self, override_redirect):
        try:
            connection.get_core().ChangeWindowAttributes(
                self.wid,
                xcb.xproto.CW.OverrideRedirect,
                [override_redirect]
            )
        except:
            print traceback.format_exc()

    def grab_key(self, key, modifiers):
        try:
            addmods = [
                0,
                xcb.xproto.ModMask.Lock,
                xcb.xproto.ModMask._2,
                xcb.xproto.ModMask._2 | xcb.xproto.ModMask.Lock
            ]

            for mod in addmods:
                cook = connection.get_core().GrabKeyChecked(
                    True,
                    self.wid,
                    modifiers | mod,
                    key,
                    xcb.xproto.GrabMode.Async,
                    xcb.xproto.GrabMode.Async
                )

                cook.check()

            return True
        except xcb.xproto.BadAccess:
            return False

    def ungrab_key(self, key, modifiers):
        try:
            addmods = [
                0,
                xcb.xproto.ModMask.Lock,
                xcb.xproto.ModMask._2,
                xcb.xproto.ModMask._2 | xcb.xproto.ModMask.Lock
            ]

            for mod in addmods:
                cook = connection.get_core().UngrabKeyChecked(
                    key,
                    self.wid,
                    modifiers | mod,
                )

                cook.check()
        except:
            print traceback.format_exc()
            print 'Could not ungrab key:', modifiers, '---', key

    def unlisten(self):
        self.set_event_masks(0)

class BlankWindow(Window):
    def __init__(self, wsid, x, y, width, height, color=0x000000):
        self._root_depth = connection.setup.roots[0].root_depth
        self._root_visual = connection.setup.roots[0].root_visual
        self._pixel = color

        self.wid  = connection.conn.generate_id()

        connection.get_core().CreateWindow(
            self._root_depth,
            self.wid,
            XROOT.wid,
            x,
            y,
            width,
            height,
            0,
            xcb.xproto.WindowClass.InputOutput,
            self._root_visual,
            xcb.xproto.CW.BackPixel,
            [self._pixel]
        )

        self._set_property('_NET_WM_NAME', 'Place holder')
        self.set_desktop(wsid)
        self._set_property('WM_NAME', 'pytyle-internal-window')
        self._set_property('WM_PROTOCOLS', [Atom.get_atom('WM_DELETE_WINDOW')])
        self._set_property(
            '_PYTYLE_TYPE',
            [
                Atom.get_atom('_PYTYLE_TYPE_PLACE_HOLDER')
            ]
        )

        #self.set_override_redirect(True)
        connection.get_core().MapWindow(self.wid)
        connection.push()
        self._moveresize(x, y, width, height)
        connection.push()
        #self.set_override_redirect(False)
        connection.push()

    def close(self):
        connection.get_core().DestroyWindow(self.wid)

class LineWindow(Window):
    def __init__(self, wsid, x, y, width, height, color=0x000000):
        if x < 0 or y < 0 or width < 1 or height < 1:
            self.wid = 0
            return

        self._root_depth = connection.setup.roots[0].root_depth
        self._root_visual = connection.setup.roots[0].root_visual
        self._pixel = color

        self.wid  = connection.conn.generate_id()

        connection.get_core().CreateWindow(
            self._root_depth,
            self.wid,
            XROOT.wid,
            x,
            y,
            width,
            height,
            0,
            xcb.xproto.WindowClass.InputOutput,
            self._root_visual,
            xcb.xproto.CW.BackPixel,
            [self._pixel]
        )

        self.set_override_redirect(True)
        self._set_property('_NET_WM_NAME', 'Internal PyTyle Window')
        connection.get_core().MapWindow(self.wid)
        connection.push()

    def close(self):
        connection.get_core().UnmapWindow(self.wid)

class RootWindow(Window):
    _singleton = None

    @staticmethod
    def get_root_window():
        if RootWindow._singleton is None:
            RootWindow._singleton = RootWindow()

        return RootWindow._singleton

    def __init__(self):
        if RootWindow._singleton is not None:
            raise RootWindow._singleton

        self.wid = connection.setup.roots[0].root
        Atom.build_cache()
        self.windows = set()

        self.listen()

    def get_active_window(self):
        raw = self._get_property('_NET_ACTIVE_WINDOW')
        if raw:
            return raw[0]

    def get_current_desktop(self):
        return self._get_property('_NET_CURRENT_DESKTOP')[0]

    def get_desktop_geometry(self):
        raw = self._get_property('_NET_DESKTOP_GEOMETRY')

        return {
            'width': raw[0],
            'height': raw[1]
        }

    def get_desktop_layout(self):
        raw = self._get_property('_NET_DESKTOP_LAYOUT')

        return {
            # _NET_WM_ORIENTATION_HORZ = 0
            # _NET_WM_ORIENTATION_VERT = 1
            'orientation': raw[0],
            'columns': raw[1],
            'rows': raw[2],

            # _NET_WM_TOPLEFT = 0, _NET_WM_TOPRIGHT = 1
            # _NET_WM_BOTTOMRIGHT = 2, _NET_WM_BOTTOMLEFT = 3
            'starting_corner': raw[3]
        }

    def get_desktop_names(self):
        return self._get_property('_NET_DESKTOP_NAMES')

    def get_desktop_viewport(self):
        return self._get_property('_NET_DESKTOP_VIEWPORT')

    def get_name(self):
        return 'ROOT'

    def get_number_of_desktops(self):
        return self._get_property('_NET_NUMBER_OF_DESKTOPS')[0]

    def get_pointer_position(self):
        raw = self.query_pointer()

        return (raw.root_x, raw.root_y)

    def get_supported_hints(self):
        return [Atom.get_atom_name(anum) for anum in self._get_property('_NET_SUPPORTED')]

    def get_visible_name(self):
        return self.get_name()

    def get_window_ids(self):
        return self._get_property('_NET_CLIENT_LIST')

    def get_window_stacked_ids(self):
        return self._get_property('_NET_CLIENT_LIST_STACKING')

    def get_window_manager_name(self):
        return Window(self._get_property('_NET_SUPPORTING_WM_CHECK')[0]).get_name().lower()

    def get_workarea(self):
        raw = self._get_property('_NET_WORKAREA')
        ret = []

        for i in range(len(raw) / 4):
            i *= 4
            ret.append({
                'x': raw[i + 0],
                'y': raw[i + 1],
                'width': raw[i + 2],
                'height': raw[i + 3]
            })

        return ret

    def is_showing_desktop(self):
        if self._get_property('_NET_SHOWING_DESKTOP')[0] == 1:
            return True
        return False

    def listen(self):
        self.set_event_masks(
            xcb.xproto.EventMask.SubstructureNotify |
            xcb.xproto.EventMask.PropertyChange
        )

    def wm(self):
        return self.get_window_manager_name()

XROOT = RootWindow.get_root_window()
