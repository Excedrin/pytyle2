import struct

import xcb.xproto, xcb.xcb, xcb.xinerama, xcb.randr

conn = None
setup = None

syms_to_codes = {}
codes_to_syms = {}

def init():
    global conn, setup

    conn = xcb.xcb.connect()
    setup = conn.get_setup()

    init_keymap()

def init_keymap():
    global setup, syms_to_codes, codes_to_syms

    q = get_core().GetKeyboardMapping(
        setup.min_keycode,
        setup.max_keycode - setup.min_keycode + 1
    ).reply()

    kpc = q.keysyms_per_keycode

    for i, v in enumerate(q.keysyms):
        keycode = (i / kpc) + setup.min_keycode

        if v not in syms_to_codes:
            syms_to_codes[v] = keycode

        if keycode not in codes_to_syms:
            codes_to_syms[keycode] = []
        codes_to_syms[keycode].append(v)

def disconnect():
    global conn

    conn.disconnect()

def flush():
    global conn

    conn.flush()

def get_core():
    global conn

    return conn.core

def get_extensions():
    ret = []
    exts = get_core().ListExtensions().reply()
    for name in exts.names:
        ret.append(''.join([chr(i) for i in name.name]).lower())

    return ret

def get_keycode(keysym):
    global syms_to_codes

    return syms_to_codes[keysym]

def get_keysym(keycode):
    global codes_to_syms

    return codes_to_syms[keycode][0]

def push():
    flush()
    xsync()

def xinerama_get_screens():
    global conn, setup

    ret = []

    xinerama = conn(xcb.xinerama.key)
    screens = xinerama.QueryScreens().reply().screen_info

    for screen in screens:
        ret.append({
            'x': screen.x_org,
            'y': screen.y_org,
            'width': screen.width,
            'height': screen.height
        })

    # For the RandR extension...
    # I'm using nVidia TwinView... need to test this
    #randr = conn(xcb.randr.key)
    #r_screens = randr.GetScreenResources(setup.roots[0].root).reply()
    #for icrt in r_screens.crtcs:
        #crt = randr.GetCrtcInfo(icrt, xcb.xcb.CurrentTime).reply()
        #crt.x, crt.y, crt.width, crt.height

    return ret

def xsync():
    try:
        get_core().GetInputFocus().reply()
    except:
        return

init()
