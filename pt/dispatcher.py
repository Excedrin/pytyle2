import time

import config
import ptxcb
import state
import tilers

from command import Command
from window import Window
from tile import Tile

class Dispatcher(object):
    def __init__(self, event_data):
        self._event_data = event_data
        self._stop = False

        assert 'event' in self._event_data

        if hasattr(self, self._event_data['event']):
            getattr(self, self._event_data['event'])()
        else:
            print 'Unrecognized event: %s' % self._event_data['event']
            return

        ptxcb.Window.exec_queue()
        Tile.exec_queue()

        ptxcb.connection.push()

    def stop(self):
        return self._stop

    def KeyPressEvent(self):
        cmd = Command.lookup(self._event_data['keycode'], self._event_data['modifiers'])

        if not cmd:
            return

        x = cmd.get_global_command()

        if x == 'quit':
            for tiler in state.iter_tilers():
                tiler.cmd_untile()

            self._stop = True
        elif x == 'debug':
            state.print_hierarchy(*state.get_active_wsid_and_mid())
        elif x == 'refresh_workarea':
            state.update_property('_NET_WORKAREA')
        elif x == 'reload_configuration':
            config.load_config_file()
            state.update_NET_DESKTOP_GEOMETRY(True)
            state.apply_config()
        else:
            Tile.dispatch(state.get_active_monitor(), cmd)

    def ConfigureNotifyEvent(self):
        win = Window.deep_lookup(self._event_data['window'].wid)

        mt_off = config.get_option(
            'movetime_offset',
            *state.get_active_wsid_and_mid()
        )
        if (
            win and win.lives() and not win.floating and
            (time.time() - win.pytyle_moved_time) > mt_off
        ):
            if (
                state.pointer_grab and
                win.width == self._event_data['width'] and
                win.height == self._event_data['height']
            ):
                pointer = ptxcb.XROOT.query_pointer()

                if ptxcb.XROOT.button_pressed():
                    state.moving = win
                    state.moving.moving = True

            win.set_geometry(
                self._event_data['x'],
                self._event_data['y'],
                self._event_data['width'],
                self._event_data['height']
            )

    def PropertyNotifyEvent(self):
        a = self._event_data['atom']

        state.update_property(a)

        if self._event_data['window']:
            win = Window.lookup(self._event_data['window'].wid)

            if win and win.lives():
                win.update_property(a)

    def FocusInEvent(self):
        if self._event_data['mode'] == 'Ungrab':
            state.pointer_grab = False

            if state.moving:
                win = state.moving
                pointer = ptxcb.XROOT.query_pointer()

                tiler = win.get_tiler()
                if tiler:
                    if tiler.tiling:
                        tiler.mouse_switch(
                            win.container,
                            pointer.root_x,
                            pointer.root_y
                        )
                    tiler.enqueue()

                state.moving.moving = False
                state.moving = False

    def FocusOutEvent(self):
        if self._event_data['mode'] == 'Grab':
            state.pointer_grab = True
