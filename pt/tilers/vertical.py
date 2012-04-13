import math

from pt.tile_auto import AutoTile

class Vertical(AutoTile):
    def __init__(self, monitor):
        AutoTile.__init__(self, monitor)

        self.hsplit = self.get_option('width_factor')

    #
    # Helper methods
    #

    def decrement_hsplit(self):
        self.hsplit -= self.get_option('step_size')

    def increment_hsplit(self):
        self.hsplit += self.get_option('step_size')

    #
    # Commands
    #

    def cmd_tile(self):
        AutoTile.cmd_tile(self)

        m_size = len(self.store.masters)
        s_size = len(self.store.slaves)

        if not m_size and not s_size:
            return

        m_width = int(self.monitor.wa_width * self.hsplit)
        s_width = self.monitor.wa_width - m_width

        m_x = self.monitor.wa_x
        s_x = m_x + m_width

        if (
            m_width <= 0 or m_width > self.monitor.wa_width or
            s_width <= 0 or s_width > self.monitor.wa_width
        ):
            self.error_exec_callbacks()
            return

        if m_size:
            m_height = self.monitor.wa_height / m_size

            if not s_size:
                m_width = self.monitor.wa_width

            for i, cont in enumerate(self.store.masters):
                cont.moveresize(
                    m_x,
                    self.monitor.wa_y + i * m_height,
                    m_width,
                    m_height
                )

        if s_size:
            s_height = self.monitor.wa_height / s_size

            if not m_size:
                s_width = self.monitor.wa_width
                s_x = self.monitor.wa_x

            for i, cont in enumerate(self.store.slaves):
                cont.moveresize(
                    s_x,
                    self.monitor.wa_y + i * s_height,
                    s_width,
                    s_height
                )

        # If we've made it this far, then we've supposedly tiled correctly
        self.error_clear()

    def cmd_decrease_master(self):
        self.decrement_hsplit()

        self.error_register_callback(self.increment_hsplit)
        self.enqueue()

    def cmd_increase_master(self):
        self.increment_hsplit()

        self.error_register_callback(self.decrement_hsplit)
        self.enqueue()

class VerticalRows(Vertical):
    def __init__(self, monitor):
        Vertical.__init__(self, monitor)

        self.rows = self.get_option('rows')

    #
    # Commands
    #

    def cmd_tile(self):
        AutoTile.cmd_tile(self)

        m_size = len(self.store.masters)
        s_size = len(self.store.slaves)

        if not m_size and not s_size:
            return

        columns = int(math.ceil(float(s_size) / float(self.rows)))
        lastcolumn_rows = s_size % self.rows or self.rows

        m_width = int(self.monitor.wa_width * self.hsplit)

        if not columns:
            s_width = 1
        else:
            s_width = (self.monitor.wa_width - m_width) / columns

        m_x = self.monitor.wa_x
        s_x = m_x + m_width

        if (
            m_width <= 0 or m_width > self.monitor.wa_width or
            s_width <= 0 or s_width > self.monitor.wa_width
        ):
            self.error_exec_callbacks()
            return

        if m_size:
            m_height = self.monitor.wa_height / m_size

            if not s_size:
                m_width = self.monitor.wa_width

            for i, cont in enumerate(self.store.masters):
                cont.moveresize(
                    m_x,
                    self.monitor.wa_y + i * m_height,
                    m_width,
                    m_height
                )

        if s_size:
            s_height = self.monitor.wa_height / self.rows

            if not m_size:
                s_width = self.monitor.wa_width / columns
                s_x = self.monitor.wa_x

            column = 0
            for i, cont in enumerate(self.store.slaves):
                if column == columns - 1:
                    s_height = self.monitor.wa_height / lastcolumn_rows

                cont.moveresize(
                    s_x + column * s_width,
                    self.monitor.wa_y + (i % self.rows) * s_height,
                    s_width,
                    s_height
                )

                if not (i + 1) % self.rows:
                    column += 1

        # If we've made it this far, then we've supposedly tiled correctly
        self.error_clear()
