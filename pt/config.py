import ConfigParser
import distutils.sysconfig
import os
import os.path
import pwd
import re
import shutil
import sys

# This is PyTyle's custom configuration parser. There are two main
# goals accomplished with this sub-class:
#
# 1. It allows retrival of some other types, like lists, booleans, and
#    lists of certain types (namely, floats and ints).
# 2. It automatically parses Monitor/Workspace/Tiler specific configuration
#    sections and loads them into a tuple (wsid, mid, tiler) indexed
#    dictionary.
# 3. Iterfaces with the "option_types" dictionary specified below, allowing
#    for more automatic retrieval of configuration settings.
class PyTyleConfigParser(ConfigParser.SafeConfigParser):
    def getboolean(self, section, option):
        if self.get(section, option).lower() == 'yes':
            return True
        return False

    def gethex(self, section, option):
        return int(self.get(section, option), 16)

    def getlist(self, section, option):
        def clean(s):
            return s.replace('"', '').replace("'", '')

        return map(
            clean,
            self.get(section, option).split()
        )

    def getfloatlist(self, section, option):
        try:
            return map(
                float,
                self.getlist(section, option)
            )
        except ValueError:
            return self.getlist(section, option)

    def getintlist(self, section, option):
        try:
            return map(
                int,
                self.getlist(section, option)
            )
        except ValueError:
            return self.getlist(section, option)

    def get_option(self, section, option):
        assert option in option_types

        return option_types[option]['exec'](self, section, option)

    def get_global_configs(self):
        retval = {}

        if 'Global' in self.sections():
            for option in self.options('Global'):
                retval[option] = self.get_option('Global', option)

        return retval

    def get_global_keybindings(self):
        retval = {}

        if 'GlobalKeybindings' in self.sections():
            for option in self.options('GlobalKeybindings'):
                retval[option] = self.get('GlobalKeybindings', option)

        return retval

    def get_auto_keybindings(self):
        retval = {}

        if 'AutoKeybindings' in self.sections():
            for option in self.options('AutoKeybindings'):
                retval[option] = self.get('AutoKeybindings', option)

        return retval

    def get_manual_keybindings(self):
        retval = {}

        if 'ManualKeybindings' in self.sections():
            for option in self.options('ManualKeybindings'):
                retval[option] = self.get('ManualKeybindings', option)

        return retval

    def get_wmt_configs(self):
        retval = {}

        all_tilers = self.get_option('Global', 'all_tilers')

        for section in self.sections():
            for tiler in all_tilers:
                m = re.match(
                    '^(Workspace([0-9]+)-?|Monitor([0-9]+)-?|' + tiler + '-?){1,3}$',
                    section
                )
                if m:
                    wsid = int(m.group(2)) if m.group(2) else None
                    mid = int(m.group(3)) if m.group(3) else None
                    tiler = tiler if tiler.lower() in section.lower() else None

                    retval[(wsid, mid, tiler)] = {}

                    for option in self.options(m.group(0)):
                        retval[(wsid, mid, tiler)][option] = self.get_option(
                            m.group(0),
                            option
                        )

        return retval

# Find the configuration file
xdg = os.getenv('XDG_CONFIG_HOME')
home = os.getenv('HOME')
logname = os.getenv('LOGNAME')
user_name = pwd.getpwuid(os.getuid())[0]
config_path = None
config_filename = 'config.ini'
default_file = os.path.join(
    distutils.sysconfig.get_python_lib(),
    'pt',
    config_filename
)

if xdg:
    config_path = os.path.join(xdg, 'pytyle2')
elif home:
    config_path = os.path.join(home, '.config', 'pytyle2')
elif logname:
    config_path = os.path.join(logname, '.config', 'pytyle2')
elif user_name:
    config_path = os.path.join(user_name, '.config', 'pytyle2')

# A list of supported options independent of section header.
# Please do not change settings here. The settings specified here
# are the minimal required for PyTyle to function properly.
option_types = {
    'all_tilers': {
        'exec': PyTyleConfigParser.getlist,
        'default': ['Vertical']
    },
    'movetime_offset': {
        'exec': PyTyleConfigParser.getfloat,
        'default': 0.5
    },
    'tilers': {
        'exec': PyTyleConfigParser.getlist,
        'default': ['Vertical']
    },
    'ignore': {
        'exec': PyTyleConfigParser.getlist,
        'default': []
    },
    'decorations': {
        'exec': PyTyleConfigParser.getboolean,
        'default': True
    },
    'borders': {
        'exec': PyTyleConfigParser.getboolean,
        'default': True
    },
    'border_width': {
        'exec': PyTyleConfigParser.getint,
        'default': 2
    },
    'borders_active_color': {
        'exec': PyTyleConfigParser.gethex,
        'default': 0xff0000,
    },
    'borders_inactive_color': {
        'exec': PyTyleConfigParser.gethex,
        'default': 0x008800,
    },
    'borders_catchall_color': {
        'exec': PyTyleConfigParser.gethex,
        'default': 0x3366ff,
    },
    'placeholder_bg_color': {
        'exec': PyTyleConfigParser.gethex,
        'default': 0x000000,
    },
    'margin': {
        'exec': PyTyleConfigParser.getintlist,
        'default': []
    },
    'padding': {
        'exec': PyTyleConfigParser.getintlist,
        'default': []
    },
    'always_monitor_cmd': {
        'exec': PyTyleConfigParser.getboolean,
        'default': False
    },
    'tile_on_startup': {
        'exec': PyTyleConfigParser.getboolean,
        'default': False
    },
    'step_size': {
        'exec': PyTyleConfigParser.getfloat,
        'default': 0.05
    },
    'width_factor': {
        'exec': PyTyleConfigParser.getfloat,
        'default': 0.5
    },
    'height_factor': {
        'exec': PyTyleConfigParser.getfloat,
        'default': 0.5
    },
    'rows': {
        'exec': PyTyleConfigParser.getint,
        'default': 2
    },
    'columns': {
        'exec': PyTyleConfigParser.getint,
        'default': 2
    },
    'push_down': {
        'exec': PyTyleConfigParser.getint,
        'default': 25
    },
    'push_over': {
        'exec': PyTyleConfigParser.getint,
        'default': 0
    },
    'horz_align': {
        'exec': PyTyleConfigParser.get,
        'default': 'left'
    },
    'shallow_resize': {
        'exec': PyTyleConfigParser.getboolean,
        'default': True
    }
}

# Specified in the "(Auto|Manual)Keybindings" section
keybindings = {}

# Settings specified in the "Global" section
glbls = {}

# A tuple (wsid, mid, tiler) indexed dictionary that allows for
# Monitor/Workspace/Tiler specific settings. The order or precedence
# (in descending order) is as follows:
#
#   Workspace/Monitor/Tiler
#   Workspace/Monitor
#   Workspace/Tiler
#   Monitor/Tiler
#   Workspace
#   Monitor
#   Tiler
#   Globals
#   Defaults (specified in option_types above)
#
# Options can be specified in section headers. The following are some
# valid examples:
#
# [Workspace0-Monitor1] or [Monitor1-Workspace0]
# Specifies options that only apply to the monitor indexed at 1 on
# the first workspace.
#
# [Horizontal]
# Specifies options that only apply to the Horizontal tiling layout.
#
# [Monitor0-Vertical] or [Vertical-Monitor0]
# Specifies options that only apply to the Vertical tiling layout on the
# monitor indexed at 0.
#
# [Monitor2-Horizontal-Workspace3] or any ordering thereof
# Specifies options that only apply to the Horizontal tiling layout on
# the monitor indexed at 2 and the fourth workspace.
#
# Essentially, any combination of "Workspace#", "Monitor#", or "[Tiling
# layout name]" is valid.
wmt = {}

# Loads the configuration file. This is called automatically when
# this module is imported, but it can also be called again when
# the settings ought to be refreshed.
# If no configuration file exists, create one.
def load_config_file():
    global glbls, keybindings, wmt, paths

    # Find the configuration file... create one if it doesn't exist
    if not config_path:
        config_file = default_file
    else:
        config_file = os.path.join(config_path, config_filename)

        if not os.access(config_file, os.F_OK | os.R_OK):
            if not os.path.exists(config_path):
                os.makedirs(config_path)

            if os.access(default_file, os.F_OK | os.R_OK):
                shutil.copyfile(default_file, config_file)

    # Something went wrong...
    if not os.access(config_file, os.F_OK | os.R_OK):
        config_file = default_file

    if not os.access(config_file, os.F_OK | os.R_OK):
        print '''
            The configuration file could not be loaded. Please check to make
            sure a configuration file exists at ~/.config/pytyle2/config.ini
            or in the Python package directory.
        '''
        sys.exit(0)

    conf = PyTyleConfigParser()
    conf.read(config_file)

    glbls = {}
    keybindings = {}

    k_global = conf.get_global_keybindings()
    k_auto = conf.get_auto_keybindings()
    k_manual = conf.get_manual_keybindings()
    for k in k_global:
        keybindings[k] = {
            'global': k_global[k],
            'auto': None,
            'manual': None
        }
    for k in k_auto:
        if k not in keybindings:
            keybindings[k] = {
                'global': None,
                'auto': None,
                'manual': None
            }
        keybindings[k]['auto'] = k_auto[k]
    for k in k_manual:
        if k not in keybindings:
            keybindings[k] = {
                'global': None,
                'auto': None,
                'manual': None
            }
        keybindings[k]['manual'] = k_manual[k]

    glbls = conf.get_global_configs()
    wmt = conf.get_wmt_configs()

# Just a public accessor to get a list of all the keybindings
def get_keybindings():
    global keybindings

    return keybindings

# A public accessor to obtain a value for an option. It takes
# precedence into account, therefore, this function should
# always be called with the most information available, unless
# otherwise desired.
def get_option(option, wsid=None, mid=None, tiler=None):
    global glbls, wmt, option_types

    # Cascade up... See the comments for the "wmt" variable
    # above for more details.

    # Generate lookup tuples... in order!
    attempts = [
        (wsid, mid, tiler),
        (wsid, mid, None),
        (wsid, None, tiler),
        (None, mid, tiler),
        (wsid, None, None),
        (None, mid, None),
        (None, None, tiler)
    ]

    for lookup in attempts:
        if lookup in wmt and option in wmt[lookup]:
            return wmt[lookup][option]

    if option in glbls:
        return glbls[option]
    else:
        return option_types[option]['default']

    return None

load_config_file()
