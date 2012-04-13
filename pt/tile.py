import re

import config
from command import Command
from container import Container

class Tile(object):
    queue_tile = set()

    @staticmethod
    def dispatch(monitor, command):
        assert isinstance(command, Command)

        tiler = monitor.get_tiler()

        if tiler:
            if tiler.get_name() == 'ManualTile':
                cmd_nm = command.get_manual_command()
            else:
                cmd_nm = command.get_auto_command()

            if cmd_nm and hasattr(tiler, 'cmd_' + cmd_nm):
                if cmd_nm == 'tile':
                    tiler.enqueue(force_tiling=True)
                elif tiler.tiling:
                    getattr(tiler, 'cmd_' + cmd_nm)()
                elif (tiler.get_option('always_monitor_cmd') and
                      re.match('screen[0-9]_(focus|put)', cmd_nm)):
                    getattr(tiler, 'cmd_' + cmd_nm)()
            elif cmd_nm and cmd_nm.startswith('tile.'):
                tiler.monitor.cycle(tiler_name=cmd_nm[cmd_nm.index('.') + 1:])
            else:
                print 'Invalid command %s' % cmd_nm

    @staticmethod
    def exec_queue():
        for tiler in Tile.queue_tile:
            tiler.cmd_tile()
        Tile.queue_tile = set()

    #
    # Helper methods
    # These are responsible for some utility work common to all
    # tilers. Such as moving windows from one monitor to the next,
    # toggling decorations/borders, and handling high-level functions
    # like callbacks for hiding/showing the tiler, or if an error occurs.
    #

    def __init__(self, monitor):
        self.workspace = monitor.workspace
        self.monitor = monitor
        self.tiling = False
        self.decor = self.get_option('decorations')
        self.borders = self.get_option('borders')
        self.queue_error = set()

    def borders_add(self, do_window=True):
        pass

    def borders_remove(self, do_window=True):
        pass

    def callback_hidden(self):
        if not self.decor:
            self.borders_remove(do_window=False)

    def callback_visible(self):
        if not self.decor:
            self.borders_add(do_window=False)

    def enqueue(self, force_tiling=False):
        if self.tiling or force_tiling:
            Tile.queue_tile.add(self)

    def error_clear(self):
        self.queue_error = set()

    def error_exec_callbacks(self):
        for err in self.queue_error:
            err()
        self.error_clear()

    def error_register_callback(self, exc):
        self.queue_error.add(exc)

    def get_name(self):
        return self.__class__.__name__

    def get_option(self, option):
        return config.get_option(
            option,
            self.workspace.id,
            self.monitor.id,
            self.get_name()
        )

    def mouse_find(self, x, y):
        pass

    def mouse_switch(self, x, y):
        pass

    def screen_focus(self, mid):
        if not self.workspace.has_monitor(mid):
            return
        
        new_tiler = self.workspace.get_monitor(mid).get_tiler()

        if new_tiler.tiling:
            if self != new_tiler:
                if new_tiler:
                    active = new_tiler.get_active_cont()

                if not active:
                    active = self.workspace.get_monitor(mid).get_active()

                if active:
                    active.activate()
        else:
            mon = self.workspace.get_monitor(mid)
            active = mon.get_active()

            if active:
                active.activate()

    def screen_put(self, mid):
        if not self.workspace.has_monitor(mid):
            return

        if self.tiling:
            active = self.get_active_cont()
            new_tiler = self.workspace.get_monitor(mid).get_tiler()

            if new_tiler != self and active and new_tiler.tiling:
                active.win.set_monitor(self.workspace.id, mid)
            elif active and self.monitor.id != mid:
                mon = self.workspace.get_monitor(mid)
                active.win.moveresize(mon.wa_x, mon.wa_y, 
                                      active.w if active.w < mon.wa_width
                                               else mon.wa_width,
                                      active.h if active.h < mon.wa_height
                                               else mon.wa_height)
                active.win.set_monitor(self.workspace.id, mid)
        else:
            active = self.monitor.get_active()
            mon = self.workspace.get_monitor(mid)
            active.moveresize(mon.wa_x, mon.wa_y, 
              active.width if active.width < mon.wa_width else mon.wa_width, 
              active.height if active.height < mon.wa_height else mon.wa_height)
            active.set_monitor(self.workspace.id, mid)


    #
    # Commands
    # Functions called directly by pressing a key.
    #

    def cmd_cycle_tiler(self):
        self.monitor.cycle()

    def cmd_reset(self):
        self.monitor.tile_reset()

    def cmd_screen0_focus(self):
        self.screen_focus(0)

    def cmd_screen1_focus(self):
        self.screen_focus(1)

    def cmd_screen2_focus(self):
        self.screen_focus(2)

    def cmd_screen0_put(self):
        self.screen_put(0)

    def cmd_screen1_put(self):
        self.screen_put(1)

    def cmd_screen2_put(self):
        self.screen_put(2)

    def cmd_tile(self):
        self.tiling = True
        self.monitor.tiler = self

    def cmd_toggle_borders(self):
        self.borders = not self.borders

        if not self.decor:
            if self.borders:
                self.borders_add(do_window=False)
            else:
                self.borders_remove(do_window=False)

    def cmd_toggle_decorations(self):
        self.decor = not self.decor

        if self.decor:
            self.borders_remove()
        else:
            self.borders_add()

        Container.manage_focus(self.monitor.get_active())

    def cmd_untile(self):
        self.tiling = False
        self.monitor.tiler = None
