from tile import Tile
from container import Container

class AutoTile(Tile):
    def __init__(self, monitor):
        Tile.__init__(self, monitor)
        self.store = None
        self.cycle_index = 0

    #
    # Helper methods
    #

    def add(self, win):
        if (
            win.tilable() and self.tiling and
            win.get_winclass().lower() not in self.get_option('ignore')
        ):
            cont = Container(self, win)
            self.store.add(cont)
            self.enqueue()

    def remove(self, win, reset_window=False):
        if win.container and self.tiling:
            self.store.remove(win.container)
            win.container.remove(reset_window=reset_window)
            self.enqueue()

    def mouse_find(self, x, y):
        if self.store:
            for cont in self.store.all():
                x1, x2 = cont.x, cont.x + cont.w
                y1, y2 = cont.y, cont.y + cont.h

                if (
                    x >= x1 and x <= x2 and
                    y >= y1 and y <= y2
                ):
                    return cont

        return None

    def mouse_switch(self, cont, x, y):
        if self.store:
            switch = self.mouse_find(x, y)
            if switch:
                cont.switch(switch)

    def borders_add(self, do_window=True):
        if self.store:
            for cont in self.store.all():
                cont.decorations(False, do_window)

    def borders_remove(self, do_window=True):
        if self.store:
            for cont in self.store.all():
                cont.decorations(True, do_window)

    def destroy(self):
        self.cmd_untile()

    def detach(self):
        self.tiling = False

        if self.store:
            for cont in self.store.all()[:]:
                cont.remove()

            self.store.reset()

    def get_active(self):
        active = self.monitor.get_active()

        if active:
            if active.container and active.container in self.store.all():
                return active.container
            elif self.store:
                return self.store.all()[0]

        return None

    def get_active_cont(self):
        return self.get_active()

    def get_next(self):
        active = self.get_active()

        if active:
            a = self.store.all()
            m = self.store.masters
            s = self.store.slaves

            if active in m:
                if m.index(active) == 0:
                    return a[(a.index(m[-1]) + 1) % len(a)]
                else:
                    return a[(a.index(active) - 1) % len(a)]
            else:
                if m and s.index(active) == len(s) - 1:
                    return m[-1]
                else:
                    return a[(a.index(active) + 1) % len(a)]

        return None

    def get_previous(self):
        active = self.get_active()

        if active:
            a = self.store.all()
            m = self.store.masters
            s = self.store.slaves

            if active in m:
                if m.index(active) == len(m) - 1:
                    return a[-1]
                else:
                    return a[(a.index(active) + 1) % len(a)]
            else:
                if m and s.index(active) == 0:
                    return m[0]
                else:
                    return a[(a.index(active) - 1) % len(a)]

        return None

    #
    # Commands
    #

    def cmd_cycle(self):
        if self.store.masters and self.store.slaves:
            if self.cycle_index >= len(self.store.slaves):
                self.cycle_index = 0

            master = self.store.masters[0]
            slave = self.store.slaves[self.cycle_index]

            master.switch(slave)
            master.activate()

            self.cycle_index += 1

    def cmd_float(self):
        active = self.monitor.get_active()

        if active and active.monitor.workspace.id == self.workspace.id and active.monitor.id == self.monitor.id:
            if not active.floating:
                active.floating = True
                self.remove(active, reset_window=True)
            else:
                active.floating = False
                self.add(active)

    def cmd_focus_master(self):
        master = self.store.masters[0]

        if master:
            master.activate()

    def cmd_increase_master(self):
        pass

    def cmd_decrease_master(self):
        pass

    def cmd_increment_masters(self):
        self.store.inc_masters()
        self.enqueue()

    def cmd_decrement_masters(self):
        self.store.dec_masters()
        self.enqueue()

    def cmd_make_active_master(self):
        if self.store.masters:
            active = self.get_active()
            master = self.store.masters[0]

            if active != master:
                master.switch(active)

    def cmd_next(self):
        next = self.get_next()

        if next:
            next.activate()

    def cmd_previous(self):
        previous = self.get_previous()

        if previous:
            previous.activate()

    def cmd_switch_next(self):
        active = self.get_active()
        next = self.get_next()

        if active and next:
            active.switch(next)

    def cmd_switch_previous(self):
        active = self.get_active()
        previous = self.get_previous()

        if active and previous:
            active.switch(previous)

    def cmd_tile(self):
        Tile.cmd_tile(self)

        if not self.store:
            self.store = AutoStore()

        if self.store.empty():
            active = self.monitor.get_active()

            if active:
                self.add(active)

            for win in self.monitor.iter_windows():
                if win != active:
                    self.add(win)

    def cmd_untile(self):
        Tile.cmd_untile(self)

        if self.store:
            for cont in self.store.all()[:]:
                cont.remove(reset_window=True)

            self.store.reset()

class AutoStore(object):
    def __init__(self):
        self.masters = []
        self.slaves = []
        self.mcnt = 1
        self.changes = False

    def made_changes(self):
        if self.changes:
            self.changes = False
            return True
        return False

    def add(self, cont, top = False):
        if len(self.masters) < self.mcnt:
            if cont in self.slaves:
                self.slaves.remove(cont)

            if top:
                self.masters.insert(0, cont)
            else:
                self.masters.append(cont)

            self.changes = True
        elif cont not in self.slaves:
            if top:
                self.slaves.insert(0, cont)
            else:
                self.slaves.append(cont)

            self.changes = True

    def empty(self):
        return not self.masters and not self.slaves

    def remove(self, cont):
        if cont in self.masters:
            self.masters.remove(cont)

            if len(self.masters) < self.mcnt and self.slaves:
                self.masters.append(self.slaves.pop(0))

            self.changes = True
        elif cont in self.slaves:
            self.slaves.remove(cont)

            self.changes = True

    def reset(self):
        self.masters = []
        self.slaves = []
        self.changes = False

    def switch(self, cont1, cont2):
        if cont1 in self.masters and cont2 in self.masters:
            i1, i2 = self.masters.index(cont1), self.masters.index(cont2)
            self.masters[i1], self.masters[i2] = self.masters[i2], self.masters[i1]
        elif cont1 in self.slaves and cont2 in self.slaves:
            i1, i2 = self.slaves.index(cont1), self.slaves.index(cont2)
            self.slaves[i1], self.slaves[i2] = self.slaves[i2], self.slaves[i1]
        elif cont1 in self.masters: # and cont2 in self.slaves
            i1, i2 = self.masters.index(cont1), self.slaves.index(cont2)
            self.masters[i1], self.slaves[i2] = self.slaves[i2], self.masters[i1]
        else: # cont1 in self.slaves and cont2 in self.masters
            i1, i2 = self.slaves.index(cont1), self.masters.index(cont2)
            self.slaves[i1], self.masters[i2] = self.masters[i2], self.slaves[i1]

    def inc_masters(self):
        self.mcnt = min(self.mcnt + 1, len(self.all()))

        if len(self.masters) < self.mcnt and self.slaves:
            self.masters.append(self.slaves.pop(0))

    def dec_masters(self):
        if self.mcnt <= 0:
            return
        self.mcnt -= 1

        if len(self.masters) > self.mcnt:
            self.slaves.append(self.masters.pop())

    def all(self):
        return self.masters + self.slaves

    def __str__(self):
        r = 'Masters: %s\n' % [cont.get_name() for cont in self.masters]
        r += 'Slaves: %s\n' % [cont.get_name() for cont in self.slaves]

        return r
