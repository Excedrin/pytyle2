import ptxcb
import config

from window import BogusWindow

class Container(object):
    idinc = 1
    active = None

    @staticmethod
    def manage_focus(win):
        if win and win.container:
            win.container.borders_activate(win.container.tiler.decor)
        elif Container.active:
            Container.active.borders_normal(Container.active.tiler.decor)

    def __init__(self, tiler, win=None):
        self.tiler = tiler
        self.id = Container.idinc
        self.x, self.y, self.w, self.h = 0, 0, 1, 1
        self.empty = True
        self.default_color = self.tiler.get_option('borders_inactive_color')
        self.set_window(win)

        Container.idinc += 1

        self._box = {
            'htop': None, 'hbot': None,
            'vleft': None, 'vright': None
        }

    def activate(self):
        if self.win:
            self.win.activate()
        else:
            self.borders_activate(self.tiler.decor)

    def borders_activate(self, decor):
        if Container.active and Container.active != self:
            Container.active.borders_normal(Container.active.tiler.decor)

        Container.active = self

        if not decor:
            self.box_show(self.tiler.get_option('borders_active_color'))

    def borders_normal(self, decor):
        if not decor:
            self.box_show(self.default_color)

    def box_hide(self):
        for box in self._box.values():
            if box:
                box.close()

    def box_show(self, color):
        if not self.tiler.borders:
            return

        x, y, w, h = self.x, self.y, self.w, self.h

        bw = self.tiler.get_option('border_width')

        self.box_hide()

        if self.tiler.workspace.id == ptxcb.XROOT.get_current_desktop():
            self._box['htop'] = ptxcb.LineWindow(self.tiler.workspace.id, x, y, w, bw, color)
            self._box['hbot'] = ptxcb.LineWindow(self.tiler.workspace.id, x, y + h, w, bw, color)
            self._box['vleft'] = ptxcb.LineWindow(self.tiler.workspace.id, x, y, bw, h, color)
            self._box['vright'] = ptxcb.LineWindow(self.tiler.workspace.id, x + w - bw, y, bw, h, color)

    def decorations(self, decor, do_window=True):
        if do_window and self.win:
            self.win.decorations(decor)

        if not decor:
            if self == Container.active or (self.win and self.win.id == ptxcb.XROOT.get_active_window()):
                self.borders_activate(decor)
            else:
                self.borders_normal(decor)
        else:
            self.box_hide()

    def fit_window(self):
        # Don't do anything if the pointer is on the window...
        if not self.win or self.win.moving:
            return

        if (self.x >= 0 and self.y >= 0
            and self.w > 0 and self.h > 0):
            x, y, w, h = self.x, self.y, self.w, self.h

            padding = self.tiler.get_option('padding')
            if padding and len(padding) == 4:
                # padding = top(0) right(1) bottom(2) left(3)
                x += padding[3]
                y += padding[0]
                w -= padding[1] + padding[3]
                h -= padding[0] + padding[2]

            self.win.moveresize(x, y, w, h)

    def get_name(self):
        if not self.win:
            return 'Container #%d' % self.id

        return self.win.name

    def moveresize(self, x, y, width, height):
        self.x, self.y, self.w, self.h = x, y, width, height
        self.fit_window()

        self.decorations(self.tiler.decor)

    def still(self):
        self.moveresize(self.x, self.y, self.w, self.h)

    def window_lower(self):
        if self.win:
            self.win.restack(below=True)

    def window_raise(self):
        if self.win:
            self.win.restack()

    def window_below(self, below):
        if self.win:
            self.win.set_below(below)

    def remove(self, reset_window=False):
        if self.win:
            if isinstance(self.win, BogusWindow):
                self.win.close()
            elif reset_window:
                self.reset()
            else:
                self.win.decorations(True)

            self.win.set_container(None)

        self.box_hide()

        if self == Container.active:
            Container.active = None

        self.win = None
        self.empty = True

    def reset(self, reset_window=False):
        self.win.original_state()
        self.win.set_below(False)

    def set_window(self, win=None, force=False):
        if hasattr(self, 'win'):
            if not force and (self.win == win or isinstance(win, BogusWindow)):
                return

            if self.win:
                if isinstance(self.win, BogusWindow):
                    self.win.close()
                else:
                    self.win.set_container(None)
                    self.win.decorations(True)

        if not win:
            self.win = BogusWindow(
                self.tiler.workspace.id,
                self.x, self.y, self.w, self.h,
                self.tiler.get_option('placeholder_bg_color')
            )
            self.empty = True
        else:
            self.win = win
            self.empty = False

        self.win.set_container(self)

    def switch(self, cont):
        self.win.container, cont.win.container = cont.win.container, self.win.container
        self.win, cont.win = cont.win, self.win

        if Container.active == cont:
            self.borders_activate(self.tiler.decor)
        elif Container.active == self:
            cont.borders_activate(cont.tiler.decor)

        self.empty = isinstance(self.win, BogusWindow)
        cont.empty = isinstance(cont.win, BogusWindow)

        self.fit_window()
        cont.fit_window()

    def __str__(self):
        ret = 'Container #%d' % self.id

        if self.win:
            ret += '\n\t' + str(self.win)
        else:
            ret += ' - Empty'

        return ret
