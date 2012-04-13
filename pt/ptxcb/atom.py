import struct

import xcb.xproto

import connection
from atoms import atoms

class Atom:
    _cache = {}

    @staticmethod
    def build_cache():
        if Atom._cache:
            return

        for atom in atoms:
            Atom._cache[atom] = connection.get_core().InternAtom(
                False,
                len(atom),
                atom
            ).reply().atom

            if (atoms[atom][0] is not None and
                atoms[atom][0] not in Atom._cache):
                Atom._cache[atoms[atom][0]] = connection.get_core().InternAtom(
                    False,
                    len(atoms[atom][0]),
                    atoms[atom][0]
                ).reply().atom

    @staticmethod
    def get_atom(name):
        if not Atom._cache:
            raise Exception('Atom cache has not been built')

        if name not in Atom._cache:
            Atom._cache[name] = connection.get_core().InternAtom(True, len(name), name).reply().atom

        return Atom._cache[name]

    @staticmethod
    def get_atom_name(num):
        return Atom.ords_to_str(connection.get_core().GetAtomName(num).reply().name)

    @staticmethod
    def get_atom_type(name):
        if name not in atoms:
            #raise Exception('Atom %s does not have a stored type' % name)
            return xcb.xproto.Atom.Any

        return Atom.get_atom(atoms[name][0])

    @staticmethod
    def get_atom_length(name):
        if name not in atoms:
            raise Exception('Atom %s does not have a stored length' % name)

        return atoms[name][1]

    @staticmethod
    def get_type_name(atom_name):
        if atom_name not in atoms:
            #raise Exception('Atom %s does not have a stored type' % atom_name)
            return None

        return atoms[atom_name][0]

    @staticmethod
    def ords_to_str(ords):
        return ''.join([chr(i) for i in ords if i < 128])

    @staticmethod
    def null_terminated_to_strarray(ords):
        ret = []
        s = ''

        for o in ords:
            if not o:
                ret.append(s)
                s = ''
            else:
                s += chr(o)

        return ret
