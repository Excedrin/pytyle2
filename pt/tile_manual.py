import ptxcb

from tile import Tile
from container import Container

class ManualTile(Tile):
    def __init__(self, monitor):
        Tile.__init__(self, monitor)
        self.root = None
        self.catchall = None

    #
    # Helper methods
    #

    def add(self, win):
        if (
            win.tilable() and self.tiling and self.root and
            win.get_winclass().lower() not in self.get_option('ignore')
        ):
            possible = self.get_open_leaf()

            if possible:
                possible.cont.set_window(win)
            else:
                self.get_last_active().activate()

            self.enqueue()

    def remove(self, win, reset_window=False):
        if win.container and not win.pytyle_place_holder() and self.tiling:
            win.container.set_window()
            self.enqueue()

    def find_container(self, cont):
        assert self.root

        for child in self.root.childs():
            if child.cont == cont:
                return child
        return None

    def get_active(self):
        assert self.root

        active = self.monitor.get_active()

        if active:
            if active.container:
                find_leaf = self.find_container(active.container)
                if find_leaf:
                    return find_leaf

        return self.root.childs().next()

    def get_active_cont(self):
        return self.get_active().cont

    def get_last_active(self):
        assert self.root

        possibles = self.get_last_active_list()

        return possibles[-1] or self.root.childs().next()

    def get_last_active_list(self):
        assert self.root

        wids = ptxcb.XROOT.get_window_stacked_ids()
        possibles = {}
        for win in self.monitor.iter_windows():
            if win.id in wids and win.container and win.container.tiler == self:
                leaf = self.find_container(win.container)
                if leaf:
                    possibles[wids.index(win.id)] = leaf

        retval = []
        for i in sorted(possibles):
            retval.append(possibles[i])

        return retval

    def get_open_leaf(self):
        assert self.root

        if self.catchall and self.catchall.cont.empty:
            return self.catchall

        for leaf in self.get_last_active_list()[::-1]:
            if leaf.cont.empty:
                return leaf

        for child in self.root.childs():
            if child.cont.empty:
                return child

        return None

    def iter_hidden(self):
        for win in self.monitor.iter_windows():
            if (
                not win.container and win.tilable() and
                win.get_winclass().lower() not in self.get_option('ignore')
            ):
                yield win

    def promote(self):
        possible = self.get_open_leaf()

        if possible:
            for win in self.iter_hidden():
                possible.cont.set_window(win)
                possible = self.get_open_leaf()

                if not possible:
                    break

    def borders_add(self, do_window=True):
        assert self.root

        for child in self.root.childs():
            child.cont.decorations(False, do_window)

    def borders_remove(self, do_window=True):
        assert self.root

        for child in self.root.childs():
            child.cont.decorations(True, do_window)

    def mouse_find(self, x, y):
        assert self.root

        for child in self.root.childs():
            x1, x2 = child.x, child.x + child.w
            y1, y2 = child.y, child.y + child.h

            if (
                x >= x1 and x <= x2 and
                y >= y1 and y <= y2
            ):
                return child.cont

        return None

    def mouse_switch(self, cont, x, y):
        assert self.root

        switch = self.mouse_find(x, y)
        if switch:
            cont.switch(switch)

    def destroy(self):
        if self.root:
            self.cmd_untile()

    def detach(self):
        self.tiling = False

        if self.root:
            for win in self.iter_hidden():
                win.set_below(False)

            for child in self.root.childs():
                child.cont.remove()

    #
    # Commands
    #

    def cmd_close_frame(self):
        assert self.root

        frm = self.get_active()

        if frm == self.root:
            return

        frm.parent.remove_child(frm)

        if not frm.cont.win.pytyle_place_holder():
            frm.cont.win.restack(True)

        frm.cont.remove(True)

        self.get_last_active().activate()

        self.promote()

        self.enqueue()

    def cmd_only(self):
        assert self.root

        only = self.get_active()

        if only == self.root:
            return

        for child in self.root.childs():
            child.cont.remove()
        self.root = None

        self.enqueue()

    def cmd_cycle(self):
        assert self.root

        frm = self.get_active()

        for child in self.root.childs():
            if frm != child and child.hidden:
                child.reset_cycle()
                frm.reset_cycle()

        hidden = frm.get_hidden_list()

        if len(hidden) > 1:
            ind = frm.cyc_ind % len(hidden)

            if hidden[ind] == frm.cont.win:
                ind += 1
                ind %= len(hidden)

            frm.cont.window_below(True)
            frm.cont.remove()
            frm.cont.set_window(hidden[ind])
            frm.cont.still()
            frm.cont.window_below(False)

            frm.cyc_ind += 1
            frm.activate()

    def cmd_toggle_catchall(self):
        assert self.root

        frm = self.get_active()

        if self.catchall:
            self.catchall.cont.default_color = self.get_option(
                'borders_inactive_color'
            )

            if self.catchall != frm:
                self.catchall.cont.still()

        if self.catchall != frm:
            self.catchall = frm
            self.catchall.cont.default_color = self.get_option(
                'borders_catchall_color'
            )
        else:
            self.catchall = None

    def cmd_float(self):
        assert self.root

        active = self.monitor.get_active()

        if (
            active and active.monitor.workspace.id == self.workspace.id and
            active.monitor.id == self.monitor.id
        ):
            if not active.floating:
                active.floating = True
                self.remove(active, reset_window=True)
            else:
                active.floating = False
                self.add(active)

    def cmd_hsplit(self):
        assert self.root

        try:
            cont = Container(self, self.iter_hidden().next())
        except StopIteration:
            cont = Container(self)

        self.get_active().hsplit(cont)

        self.enqueue()

    def cmd_vsplit(self):
        assert self.root

        try:
            cont = Container(self, self.iter_hidden().next())
        except StopIteration:
            cont = Container(self)

        self.get_active().vsplit(cont)

        self.enqueue()

    def cmd_up(self):
        assert self.root

        frm = self.get_active().up()

        if frm:
            frm.activate()

    def cmd_up_move(self):
        assert self.root

        active = self.get_active()
        frm = active.up()

        if active and frm:
            active.cont.switch(frm.cont)

    def cmd_up_resize(self):
        assert self.root

        frm = self.get_active()
        if not frm.down(self.get_option('shallow_resize')):
            frm.set_up_proportion(self.get_option('step_size'))
        else:
            frm.set_down_proportion(-self.get_option('step_size'))

        self.enqueue()

    def cmd_up_increase(self):
        assert self.root

        frm = self.get_active()
        frm.set_up_proportion(self.get_option('step_size'))

        self.enqueue()

    def cmd_up_decrease(self):
        assert self.root

        frm = self.get_active()
        frm.set_down_proportion(-self.get_option('step_size'))

        self.enqueue()

    def cmd_down(self):
        assert self.root

        frm = self.get_active().down()

        if frm:
            frm.activate()

    def cmd_down_move(self):
        assert self.root

        active = self.get_active()
        frm = active.down()

        if active and frm:
            active.cont.switch(frm.cont)

    def cmd_down_resize(self):
        assert self.root

        frm = self.get_active()
        if not frm.down(self.get_option('shallow_resize')):
            frm.set_up_proportion(-self.get_option('step_size'))
        else:
            frm.set_down_proportion(self.get_option('step_size'))

        self.enqueue()

    def cmd_down_increase(self):
        assert self.root

        frm = self.get_active()
        frm.set_down_proportion(self.get_option('step_size'))

        self.enqueue()

    def cmd_down_decrease(self):
        assert self.root

        frm = self.get_active()
        frm.set_up_proportion(-self.get_option('step_size'))

        self.enqueue()

    def cmd_left(self):
        assert self.root

        frm = self.get_active().left()

        if frm:
            frm.activate()

    def cmd_left_move(self):
        assert self.root

        active = self.get_active()
        frm = active.left()

        if active and frm:
            active.cont.switch(frm.cont)

    def cmd_left_resize(self):
        assert self.root

        frm = self.get_active()
        if not frm.right(self.get_option('shallow_resize')):
            frm.set_left_proportion(self.get_option('step_size'))
        else:
            frm.set_right_proportion(-self.get_option('step_size'))

        self.enqueue()

    def cmd_left_increase(self):
        assert self.root

        frm = self.get_active()
        frm.set_left_proportion(self.get_option('step_size'))

        self.enqueue()

    def cmd_left_decrease(self):
        assert self.root

        frm = self.get_active()
        frm.set_right_proportion(-self.get_option('step_size'))

        self.enqueue()

    def cmd_right(self):
        assert self.root

        frm = self.get_active().right()

        if frm:
            frm.activate()

    def cmd_right_move(self):
        assert self.root

        active = self.get_active()
        frm = active.right()

        if active and frm:
            active.cont.switch(frm.cont)

    def cmd_right_resize(self):
        assert self.root

        frm = self.get_active()
        if not frm.right(self.get_option('shallow_resize')):
            frm.set_left_proportion(-self.get_option('step_size'))
        else:
            frm.set_right_proportion(self.get_option('step_size'))

        self.enqueue()

    def cmd_right_increase(self):
        assert self.root

        frm = self.get_active()
        frm.set_right_proportion(self.get_option('step_size'))

        self.enqueue()

    def cmd_right_decrease(self):
        assert self.root

        frm = self.get_active()
        frm.set_left_proportion(-self.get_option('step_size'))

        self.enqueue()

    def cmd_tile(self):
        Tile.cmd_tile(self)

        if not self.root:
            self.root = LeafFrame(self, None, Container(self))

            active = self.monitor.get_active()

            if active:
                self.add(active)

            for win in self.monitor.iter_windows():
                if win != active:
                    self.add(win)
        else:
            self.promote()
            for child in self.root.childs():
                if child.cont.empty and not child.cont.win:
                    child.cont.set_window(force=True)

        self.root.moveresize(
            self.monitor.wa_x, self.monitor.wa_y,
            self.monitor.wa_width, self.monitor.wa_height
        )

        for win in self.iter_hidden():
            win.set_below(True)

        for child in self.root.childs():
            child.cont.window_below(False)
            child.reset_cycle()

    def cmd_untile(self):
        assert self.root

        Tile.cmd_untile(self)

        for win in self.iter_hidden():
            win.set_below(False)

        for child in self.root.childs():
            child.cont.remove(reset_window=True)

        self.root = None

    def cmd_print_tree(self):
        print '-' * 30
        print 'Hidden:', [leaf for leaf in self.iter_hidden()]
        print 'Catchall:', self.catchall
        print '-' * 15
        self.root.print_tree()
        print '-' * 30

class Frame(object):
    def __init__(self, tiler, parent):
        self.tiler = tiler
        self.parent = parent
        self.children = []
        self.proportion = 1.0

        self.x = 0
        self.y = 0
        self.w = 1
        self.h = 1

    def print_tree(self, depth=0):
        tp = ('\t' * depth) + '%d,%d,%d,%d,%s' % (self.x, self.y, self.w, self.h, self.__class__.__name__)
        print tp

        for child in self.children:
            child.print_tree(depth + 1)

    def childs(self):
        for child in self.children:
            if isinstance(child, LeafFrame):
                yield child
            else:
                for c1 in child.childs():
                    yield c1

    def add_child(self, frame, before_index=None):
        assert (
            isinstance(frame, Frame) and frame not in self.children and
            (before_index is None or before_index < len(self.children))
        )

        # Add the child
        if before_index is not None:
            self.children.insert(before_index, frame)
        else:
            self.children.append(frame)

    def remove_child(self, frame):
        assert isinstance(frame, Frame) and frame in self.children

        # Remove the child
        self.children.remove(frame)

        # If there is only one remaning child, then merge them!
        if len(self.children) == 1:
            child = self.children[0]
            child.proportion = self.proportion
            child.parent = self.parent

            if not child.parent:
                child.tiler.root = child
            else:
                child.parent.replace_child(self, child)
        else:
            # How much are we adding to each remaining child?
            add = frame.proportion / len(self.children)

            # Apply it!
            for child in self.children:
                child.proportion += add

    def replace_child(self, find, replace):
        assert (
            isinstance(find, Frame) and
            isinstance(replace, Frame) and
            find in self.children
        )

        self.children[self.children.index(find)] = replace

    def moveresize(self, x, y, w, h):
        self._moveresize(x, y, w, h)

    def _moveresize(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h

class LeafFrame(Frame):
    def __init__(self, tiler, parent, cont):
        Frame.__init__(self, tiler, parent)
        self.cont = cont
        self.cyc_ind = 0
        self.hidden = []

    def print_tree(self, depth=0):
        tp = ('\t' * depth) + '%d,%d,%d,%d,%f,LEAF' % (self.x, self.y, self.w, self.h, self.proportion)
        if self.cont.win:
            tp += ' --- ' + self.cont.win.__str__()
        print tp

    def childs(self):
        yield self

    def add_child(self, frame):
        pass

    def remove_child(self, frame):
        pass

    def activate(self):
        self.cont.activate()

    def get_hidden_list(self):
        if self.hidden:
            return self.hidden

        self.hidden = []
        for child in self.tiler.iter_hidden():
            self.hidden.append(child)
        self.hidden.append(self.cont.win)

        return self.hidden

    def reset_cycle(self):
        self.hidden = []
        self.cyc_ind = 0

    def moveresize(self, x, y, w, h):
        self._moveresize(x, y, w, h)

        if self.parent:
            siblings = self.parent.children
            right = siblings[siblings.index(self) + 1:]

            new_x = x + w
            new_w_subtract = (self.parent.w - new_x) / len(right)

            for sibling in right:
                width = sibling.w - new_w_subtract
                sibling._moveresize(new_x, sibling.y, width, sibling.h)
                new_x += width

    def _moveresize(self, x, y, w, h):
        Frame._moveresize(self, x, y, w, h)

        self.cont.moveresize(x, y, w, h)
        self.cont.window_raise()

    def _find_like_parent(self, cls, no_child_index):
        child = self
        parent = self.parent

        while parent:
            if (isinstance(parent, cls) and
                parent.children[no_child_index] != child):
                break
            child = parent
            parent = parent.parent

        return parent, child

    def select(self, **args):
        return self

    def set_up_proportion(self, prop_change):
        parent, child = self.parent, self
        if not self.tiler.get_option('shallow_resize'):
            parent, child = self._find_like_parent(VerticalFrame, 0)

        if parent:
            parent.set_up_proportion(child, prop_change)

    def set_down_proportion(self, prop_change):
        parent, child = self.parent, self
        if not self.tiler.get_option('shallow_resize'):
            parent, child = self._find_like_parent(VerticalFrame, -1)

        if parent:
            parent.set_down_proportion(child, prop_change)

    def set_left_proportion(self, prop_change):
        parent, child = self.parent, self
        if not self.tiler.get_option('shallow_resize'):
            parent, child = self._find_like_parent(HorizontalFrame, 0)

        if parent:
            parent.set_left_proportion(child, prop_change)

    def set_right_proportion(self, prop_change):
        parent, child = self.parent, self
        if not self.tiler.get_option('shallow_resize'):
            parent, child = self._find_like_parent(HorizontalFrame, -1)

        if parent:
            parent.set_right_proportion(child, prop_change)

    def up(self, shallow=False):
        parent, child = self.parent, self
        if not shallow:
            parent, child = self._find_like_parent(VerticalFrame, 0)
        elif parent and not isinstance(parent, VerticalFrame):
            parent, child = parent.parent, parent

        if parent and parent.children[0] != child:
            cs = parent.children
            return cs[cs.index(child) - 1].select(
                where='up',
                x=self.x,
                w=self.w
            )

        return None

    def down(self, shallow=False):
        parent, child = self.parent, self
        if not shallow:
            parent, child = self._find_like_parent(VerticalFrame, -1)
        elif parent and not isinstance(parent, VerticalFrame):
            parent, child = parent.parent, parent

        if parent and parent.children[-1] != child:
            cs = parent.children
            return cs[cs.index(child) + 1].select(
                where='down',
                x=self.x,
                w=self.w
            )

        return None

    def left(self, shallow=False):
        parent, child = self.parent, self
        if not shallow:
            parent, child = self._find_like_parent(HorizontalFrame, 0)
        elif parent and not isinstance(parent, HorizontalFrame):
            parent, child = parent.parent, parent

        if parent and parent.children[0] != child:
            cs = parent.children
            return cs[cs.index(child) - 1].select(
                where='left',
                y=self.y,
                h=self.h
            )

        return None

    def right(self, shallow=False):
        parent, child = self.parent, self
        if not shallow:
            parent, child = self._find_like_parent(HorizontalFrame, -1)
        elif parent and not isinstance(parent, HorizontalFrame):
            parent, child = parent.parent, parent

        if parent and parent.children[-1] != child:
            cs = parent.children
            return cs[cs.index(child) + 1].select(
                where='right',
                y=self.y,
                h=self.h
            )

        return None

    def hsplit(self, cont):
        assert isinstance(cont, Container)

        # No parent for now
        leaf = LeafFrame(self.tiler, None, cont)

        if isinstance(self.parent, HorizontalFrame):
            leaf.proportion = 1.0 / len(self.parent.children)

            if self == self.parent.children[-1]:
                self.parent.add_child(leaf)
            else:
                self.parent.add_child(leaf, self.parent.children.index(self) + 1)

            clen = float(len(self.parent.children))
            factor = (clen - 1) / clen

            for child in self.parent.children:
                child.proportion *= factor
        else:
            self.parent = HorizontalFrame(self.tiler, self.parent)
            self.parent.proportion = self.proportion

            self.proportion = 0.5
            leaf.proportion = 0.5

            self.parent.add_child(self)
            self.parent.add_child(leaf)

            if not self.parent.parent:
                self.tiler.root = self.parent
            else:
                self.parent.parent.replace_child(self, self.parent)

        leaf.parent = self.parent

    def vsplit(self, cont):
        assert isinstance(cont, Container)

        # No parent for now
        leaf = LeafFrame(self.tiler, None, cont)

        if isinstance(self.parent, VerticalFrame):
            leaf.proportion = 1.0 / len(self.parent.children)

            if self == self.parent.children[-1]:
                self.parent.add_child(leaf)
            else:
                self.parent.add_child(leaf, self.parent.children.index(self) + 1)

            clen = float(len(self.parent.children))
            factor = (clen - 1) / clen

            for child in self.parent.children:
                child.proportion *= factor
        else:
            self.parent = VerticalFrame(self.tiler, self.parent)
            self.parent.proportion = self.proportion

            self.proportion = 0.5
            leaf.proportion = 0.5

            self.parent.add_child(self)
            self.parent.add_child(leaf)

            if not self.parent.parent:
                self.tiler.root = self.parent
            else:
                self.parent.parent.replace_child(self, self.parent)

        leaf.parent = self.parent

    def __str__(self):
        return self.cont.__str__()

class HorizontalFrame(Frame):
    def select(self, where, x=None, y=None, w=None, h=None):
        if where == 'left':
            return self.children[-1].select(
                where=where, x=x, y=y, w=w, h=h
            )
        elif where == 'right':
            return self.children[0].select(
                where=where, x=x, y=y, w=w, h=h
            )
        elif where in ('up', 'down'):
            if x is not None and w is not None:
                # Find the frame with the most overlap...
                overlap = []
                for c in self.children:
                    overlap.append(intoverlap(
                        x, x + w,
                        c.x, c.x + c.w
                    ))

                mi = overlap.index(max(overlap))
                return self.children[mi].select(
                    where=where, x=x, y=y, w=w, h=h
                )
            else:
                return self.children[0].select(
                    where=where, x=x, y=y, w=w, h=h
                )

        return None

    def set_up_proportion(self, child, prop_change):
        assert child in self.children

        if self.parent:
            self.parent.set_up_proportion(self, prop_change)

    def set_down_proportion(self, child, prop_change):
        assert child in self.children

        if self.parent:
            self.parent.set_down_proportion(self, prop_change)

    def set_left_proportion(self, child, prop_change):
        assert child in self.children

        left = self.children[:self.children.index(child)]

        if left:
            add_to = -prop_change / len(left)
            for c in left:
                c.proportion += add_to
            child.proportion += prop_change

    def set_right_proportion(self, child, prop_change):
        assert child in self.children

        right = self.children[self.children.index(child) + 1:]

        if right:
            add_to = -prop_change / len(right)
            for c in right:
                c.proportion += add_to
            child.proportion += prop_change

    def _moveresize(self, x, y, w, h):
        Frame._moveresize(self, x, y, w, h)

        s_x = x

        for child in self.children:
            width = int(w * child.proportion)
            child._moveresize(s_x, y, width, h)
            s_x += width

class VerticalFrame(Frame):
    def select(self, where, x=None, y=None, w=None, h=None):
        if where == 'up':
            return self.children[-1].select(
                where=where, x=x, y=y, w=w, h=h
            )
        elif where == 'down':
            return self.children[0].select(
                where=where, x=x, y=y, w=w, h=h
            )
        elif where in ('left', 'right'):
            if y is not None and h is not None:
                # Find the frame with the most overlap...
                overlap = []
                for c in self.children:
                    overlap.append(intoverlap(
                        y, y + h,
                        c.y, c.y + c.h
                    ))

                mi = overlap.index(max(overlap))
                return self.children[mi].select(
                    where=where, x=x, y=y, w=w, h=h
                )
            else:
                return self.children[0].select(
                    where=where, x=x, y=y, w=w, h=h
                )

        return None

    def set_up_proportion(self, child, prop_change):
        assert child in self.children

        up = self.children[:self.children.index(child)]

        if up:
            add_to = -prop_change / len(up)
            for c in up:
                c.proportion += add_to
            child.proportion += prop_change

    def set_down_proportion(self, child, prop_change):
        assert child in self.children

        down = self.children[self.children.index(child) + 1:]

        if down:
            add_to = -prop_change / len(down)
            for c in down:
                c.proportion += add_to
            child.proportion += prop_change

    def set_left_proportion(self, child, prop_change):
        assert child in self.children

        if self.parent:
            self.parent.set_left_proportion(self, prop_change)

    def set_right_proportion(self, child, prop_change):
        assert child in self.children

        if self.parent:
            self.parent.set_right_proportion(self, prop_change)

    def _moveresize(self, x, y, w, h):
        Frame._moveresize(self, x, y, w, h)

        s_y = y

        for child in self.children:
            height = int(h * child.proportion)
            child._moveresize(x, s_y, w, height)
            s_y += height

def intoverlap(s1, e1, s2, e2):
    assert e1 > s1 and e2 > s2

    L1, L2 = e1 - s1, e2 - s2

    if s2 <= s1 and e2 >= e1:
        return L1
    elif e2 < s1 or s2 > e1:
        return 0
    elif s2 >= s1 and e2 <= e1:
        return L2
    elif s2 < s1:
        return e2 - s1
    elif s2 < e1:
        return e1 - s2

    return None
