import time

import ptxcb

import config
from command import Command
from window import Window
from monitor import Monitor
from workspace import Workspace
from container import Container

_ACTIVE = None
pointer_grab = False
moving = False
properties = {}
xinerama = ptxcb.connection.xinerama_get_screens()

def init():
    reset_properties()
    load_properties()

def apply_config():
    Command.init()

    for mon in Workspace.iter_all_monitors():
        if config.get_option('tile_on_startup', mon.workspace.id, mon.id):
            mon.tile(force_tiling=True)

def get_active():
    global _ACTIVE

    return _ACTIVE

def get_active_monitor():
    wsid, mid = get_active_wsid_and_mid()

    return get_monitor(wsid, mid)

def get_active_wsid_and_mid():
    wsid = -1
    mid = -1
    win = get_active()

    if win and win.monitor and win.monitor.workspace:
        wsid = win.monitor.workspace.id
        mid = win.monitor.id
    else:
        wsid, mid = get_pointer_wsid_and_mid()

    return (wsid, mid)

def get_monitor(wsid, mid):
    return Workspace.WORKSPACES[wsid].get_monitor(mid)

def get_pointer_wsid_and_mid():
    wsid = -1
    mid = -1

    px, py = ptxcb.XROOT.get_pointer_position()
    wsid = properties['_NET_CURRENT_DESKTOP']

    for mon in Workspace.WORKSPACES[wsid].iter_monitors():
        if mon.contains(px, py):
            mid = mon.id
            break

    return wsid, mid

def iter_tilers(workspaces=None, monitors=None):
    if isinstance(workspaces, int):
        workspaces = [workspaces]

    if isinstance(monitors, int):
        monitors = [monitors]

    for wsid in Workspace.WORKSPACES:
        if workspaces is None or wsid in workspaces:
            for mon in Workspace.WORKSPACES[wsid].iter_monitors():
                if monitors is None or mon.id in monitors:
                    tiler = mon.get_tiler()

                    if tiler and tiler.tiling:
                        yield tiler

def iter_windows(workspaces=None, monitors=None):
    if isinstance(workspaces, int):
        workspaces = [workspaces]

    if isinstance(monitors, int):
        monitors = [monitors]

    for wsid in Workspace.WORKSPACES:
        if workspaces is None or wsid in workspaces:
            for mon in Workspace.WORKSPACES[wsid].iter_monitors():
                if monitors is None or mon.id in monitors:
                    for win in mon.iter_windows():
                        yield win

def load_properties():
    property_order = [
        '_NET_CURRENT_DESKTOP',
        '_NET_NUMBER_OF_DESKTOPS',
        '_NET_WORKAREA',
        '_NET_CLIENT_LIST',
        '_NET_ACTIVE_WINDOW',
    ]

    for pname in property_order:
        update_property(pname)

def print_hierarchy(workspaces=None, monitors=None):
    if isinstance(workspaces, int):
        workspaces = [workspaces]

    if isinstance(monitors, int):
        monitors = [monitors]

    for wsid in Workspace.WORKSPACES:
        if workspaces is None or wsid in workspaces:
            print Workspace.WORKSPACES[wsid]

            for mon in Workspace.WORKSPACES[wsid].iter_monitors():
                if monitors is None or mon.id in monitors:
                    print '\t%s' % mon

                    for win in mon.windows:
                        print '\t\t%s' % win

def reset_properties():
    global properties

    properties = {
        '_NET_ACTIVE_WINDOW': '',
        '_NET_CLIENT_LIST': set(),
        '_NET_WORKAREA': [],
        '_NET_NUMBER_OF_DESKTOPS': 0,
        '_NET_DESKTOP_GEOMETRY': {},
        '_NET_CURRENT_DESKTOP': -1,
    }

def set_active(wid):
    global _ACTIVE

    if wid in Window.WINDOWS:
        _ACTIVE = Window.WINDOWS[wid]
    else:
        _ACTIVE = None

def update_property(pname):
    mname = 'update%s' % pname
    gs = globals()

    if mname in gs:
        m = gs[mname]
        m()

def update_NET_ACTIVE_WINDOW():
    global properties

    active = ptxcb.XROOT.get_active_window()
    
    if not active:
        return

    set_active(active)

    properties['_NET_ACTIVE_WINDOW'] = get_active()

    active = get_active()
    if active and active.monitor:
        active.monitor.active = active

    Container.manage_focus(active)

def update_NET_CLIENT_LIST():
    global properties

    old = properties['_NET_CLIENT_LIST']
    new = set(ptxcb.XROOT.get_window_ids())

    properties['_NET_CLIENT_LIST'] = new

    if old != new:
        for wid in new.difference(old):
            Window.add(wid)

        for wid in old.difference(new):
            Window.remove(wid)

        # This might be redundant, but it's important to know
        # the new active window if the old one was destroyed
        # as soon as possible
        update_NET_ACTIVE_WINDOW()

def update_NET_CURRENT_DESKTOP():
    global properties

    old = properties['_NET_CURRENT_DESKTOP']
    properties['_NET_CURRENT_DESKTOP'] = ptxcb.XROOT.get_current_desktop()

    if old != properties['_NET_CURRENT_DESKTOP']:
        Container.active = None

        for tiler in iter_tilers(old):
            tiler.callback_hidden()

        for tiler in iter_tilers(properties['_NET_CURRENT_DESKTOP']):
            tiler.callback_visible()

def update_NET_WORKAREA():
    global properties

    properties['_NET_WORKAREA'] = ptxcb.XROOT.get_workarea()

    for mon in Workspace.iter_all_monitors():
        mon.calculate_workarea()

def update_NET_NUMBER_OF_DESKTOPS():
    global properties, xinerama

    old = properties['_NET_NUMBER_OF_DESKTOPS']
    properties['_NET_NUMBER_OF_DESKTOPS'] = ptxcb.XROOT.get_number_of_desktops()

    # Add destops...
    if old < properties['_NET_NUMBER_OF_DESKTOPS']:
        for wsid in xrange(old, properties['_NET_NUMBER_OF_DESKTOPS']):
            Workspace.add(wsid)
            Monitor.add(wsid, xinerama)

    # Remove desktops
    elif old > properties['_NET_NUMBER_OF_DESKTOPS']:
        for wsid in xrange(properties['_NET_NUMBER_OF_DESKTOPS'], old):
            Monitor.remove(wsid)
            Workspace.remove(wsid)

def update_NET_DESKTOP_GEOMETRY(force=False):
    global properties, xinerama

    old_geom = properties['_NET_DESKTOP_GEOMETRY']
    old_xinerama = xinerama

    time.sleep(1)

    properties['_NET_DESKTOP_GEOMETRY'] = ptxcb.XROOT.get_desktop_geometry()
    xinerama = ptxcb.connection.xinerama_get_screens()

    if old_xinerama != xinerama or force:
        if not force and len(old_xinerama) == len(xinerama):
            for mon in Workspace.iter_all_monitors():
                mid = mon.id
                mon.refresh_bounds(
                    xinerama[mid]['x'],
                    xinerama[mid]['y'],
                    xinerama[mid]['width'],
                    xinerama[mid]['height']
                )
                mon.calculate_workarea()
        else:
            for mon in Workspace.iter_all_monitors():
                for tiler in mon.tilers:
                    tiler.destroy()

            for wid in Window.WINDOWS.keys():
                Window.remove(wid)

            for wsid in Workspace.WORKSPACES.keys():
                Monitor.remove(wsid)
                Workspace.remove(wsid)

            reset_properties()
            load_properties()

init()
