import xcb.xproto

import ptxcb
import config

class Command:
    _cmds = {}
    _mods = {
        'alt': xcb.xproto.ModMask._1,
        'ctrl': xcb.xproto.ModMask.Control,
        'shift': xcb.xproto.ModMask.Shift,
        'super': xcb.xproto.ModMask._4,
        'menu': xcb.xproto.ModMask._3
    }

    def __init__(self, keys, glbl=None, auto=None, manual=None):
        self._original_keybinding = keys
        self._mod_mask = 0
        self._keycode = 0
        self._glbl = glbl
        self._auto = auto
        self._manual = manual
        self._keys = keys

        for part in keys.split('-'):
            part = part.lower()

            if part in Command._mods:
                self._mod_mask |= Command._mods[part]
            elif part.capitalize() in ptxcb.keysyms:
                self._keycode = ptxcb.connection.get_keycode(ptxcb.keysyms[part.capitalize()])
            elif part in ptxcb.keysyms:
                self._keycode = ptxcb.connection.get_keycode(ptxcb.keysyms[part])
            else:
                raise Exception('Bad command syntax')

        if not self._mod_mask or not self._keycode:
            raise Exception('Commands must have a modifier and a key')

        if not ptxcb.XROOT.grab_key(self._keycode, self._mod_mask):
            print 'Could not grab key:', keys

    def get_original_keybinding(self):
        return self._original_keybinding

    def get_index(self):
        return (self._keycode, self._mod_mask)

    # This is for when we don't care if it's auto/manual
    def get_global_command(self):
        return self._glbl

    def get_auto_command(self):
        if not self._auto:
            return self._glbl
        return self._auto

    def get_manual_command(self):
        if not self._manual:
            return self._glbl
        return self._manual

    def unbind(self):
        ptxcb.XROOT.ungrab_key(self._keycode, self._mod_mask)
        del Command._cmds[self.get_index()]

    @staticmethod
    def init():
        Command.unbind_all()

        keybindings = config.get_keybindings()
        for k in keybindings:
            cmd = Command(
                k,
                glbl=keybindings[k]['global'],
                auto=keybindings[k]['auto'],
                manual=keybindings[k]['manual']
            )
            Command._cmds[cmd.get_index()] = cmd

    @staticmethod
    def unbind_all():
        for k in Command._cmds.keys():
            Command._cmds[k].unbind()

    @staticmethod
    def lookup(keycode, mask):
        vmask = 0

        for mod in Command._mods:
            if Command._mods[mod] & mask:
                vmask |= Command._mods[mod]

        if (keycode, vmask) not in Command._cmds:
            return None

        return Command._cmds[(keycode, vmask)]
