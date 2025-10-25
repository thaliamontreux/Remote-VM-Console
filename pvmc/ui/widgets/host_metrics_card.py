from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QHBoxLayout, QVBoxLayout

from .mini_gauge import MiniGauge


class HostMetricsCard(QFrame):
    def __init__(self, theme, metrics: dict, parent=None):
        super().__init__(parent)
        self.setObjectName('hostmetricard')
        self.theme = theme
        self.metrics = metrics or {}
        t = self.theme.active_theme()
        txt = self.theme.metrics_text_color()
        # Pastel background derived from server color
        pastel_bg = None
        try:
            col = self.metrics.get('color')
            light = self.theme.lighten_color(col, 0.6)
            # hex to rgb
            r = int(light[1:3], 16)
            g = int(light[3:5], 16)
            b = int(light[5:7], 16)
            pastel_bg = f'rgba({r},{g},{b},80)'
        except Exception:
            pastel_bg = 'rgba(255,255,255,36)'
        self.setStyleSheet(
            f"QFrame#hostmetricard {{ background: transparent; border: 1px solid rgba(255,255,255,0.18); border-radius: 6px; }}"
            f" QLabel {{ color: {txt}; font-size: 10px; }}"
        )

        # Header with server label
        hdr = QFrame(self)
        hdr.setObjectName('hostmetrictitle')
        hdr.setStyleSheet(f"QFrame#hostmetrictitle {{ background: {pastel_bg}; border-top-left-radius: 6px; border-top-right-radius: 6px; }}")
        lbl = QLabel(self.metrics.get('label') or self.metrics.get('host') or '')
        lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(8, 4, 8, 4)
        hl.addWidget(lbl, 1)
        # Counts label (On/Off)
        self.counts = QLabel(self._counts_html())
        self.counts.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        hl.addWidget(self.counts, 0, Qt.AlignRight)

        # Determine colors using theme thresholds
        ok = self.theme.gauge_ok_color()
        warn = self.theme.gauge_warn_color()
        err = self.theme.gauge_err_color()

        cpu = float(self.metrics.get('cpu_pct') or 0.0)
        mem = float(self.metrics.get('mem_pct') or 0.0)
        dfree = float(self.metrics.get('disk_free_pct') or 0.0)

        def col_cpu(v):
            return err if v >= 90.0 else (warn if v >= 80.0 else ok)

        def col_mem(v):
            return err if v >= 90.0 else (warn if v >= 80.0 else ok)

        def col_dfree(v):
            return err if v <= 10.0 else (warn if v <= 20.0 else ok)

        # CPU gauge (usage)
        self.g_cpu = MiniGauge(cpu, col_cpu(cpu))
        self.g_cpu.setTrack(self.theme.gauge_track_color())
        self.g_cpu.setTextColor(self.theme.gauge_text_color())
        self.l_cpu = QLabel('CPU')
        self.l_cpu.setAlignment(Qt.AlignHCenter)
        v_cpu = QVBoxLayout()
        v_cpu.setContentsMargins(0, 0, 0, 0)
        v_cpu.setSpacing(2)
        v_cpu.addWidget(self.g_cpu, 0, Qt.AlignHCenter)
        v_cpu.addWidget(self.l_cpu, 0, Qt.AlignHCenter)

        # MEM gauge (usage)
        self.g_mem = MiniGauge(mem, col_mem(mem))
        self.g_mem.setTrack(self.theme.gauge_track_color())
        self.g_mem.setTextColor(self.theme.gauge_text_color())
        self.l_mem = QLabel('MEM')
        self.l_mem.setAlignment(Qt.AlignHCenter)
        v_mem = QVBoxLayout()
        v_mem.setContentsMargins(0, 0, 0, 0)
        v_mem.setSpacing(2)
        v_mem.addWidget(self.g_mem, 0, Qt.AlignHCenter)
        v_mem.addWidget(self.l_mem, 0, Qt.AlignHCenter)

        # DISK gauge (free %)
        self.g_dsk = MiniGauge(dfree, col_dfree(dfree))
        self.g_dsk.setTrack(self.theme.gauge_track_color())
        self.g_dsk.setTextColor(self.theme.gauge_text_color())
        self.l_dsk = QLabel('DSK')
        self.l_dsk.setAlignment(Qt.AlignHCenter)
        v_dsk = QVBoxLayout()
        v_dsk.setContentsMargins(0, 0, 0, 0)
        v_dsk.setSpacing(2)
        v_dsk.addWidget(self.g_dsk, 0, Qt.AlignHCenter)
        v_dsk.addWidget(self.l_dsk, 0, Qt.AlignHCenter)

        # Gauge row centered
        row = QHBoxLayout()
        row.setContentsMargins(8, 6, 8, 6)
        row.setSpacing(6)
        row.addStretch(1)
        row.addLayout(v_cpu)
        row.addLayout(v_mem)
        row.addLayout(v_dsk)
        row.addStretch(1)

        # Root layout
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(hdr, 0)
        root.addLayout(row, 0)

        # Set tooltip with precise values
        self.setToolTip(f"CPU {cpu:.0f}% • MEM {mem:.0f}% • DISK Free {dfree:.0f}%")

    def updateTheme(self):
        t = self.theme.active_theme()
        txt = t.get('panel_text', '#FFFFFF')
        pastel_bg = None
        try:
            col = self.metrics.get('color')
            light = self.theme.lighten_color(col, 0.6)
            r = int(light[1:3], 16)
            g = int(light[3:5], 16)
            b = int(light[5:7], 16)
            pastel_bg = f'rgba({r},{g},{b},80)'
        except Exception:
            pastel_bg = 'rgba(255,255,255,36)'
        self.setStyleSheet(
            f"QFrame#hostmetricard {{ background: transparent; border: 1px solid rgba(255,255,255,0.18); border-radius: 6px; }}"
            f" QFrame#hostmetrictitle {{ background: {pastel_bg}; border-top-left-radius: 6px; border-top-right-radius: 6px; }}"
            f" QLabel {{ color: {txt}; font-size: 10px; }}"
        )
        try:
            self.counts.setText(self._counts_html())
        except Exception:
            pass
        # Refresh gauge colors according to theme
        ok = self.theme.gauge_ok_color()
        warn = self.theme.gauge_warn_color()
        err = self.theme.gauge_err_color()
        cpu = float(self.metrics.get('cpu_pct') or 0.0)
        mem = float(self.metrics.get('mem_pct') or 0.0)
        dfree = float(self.metrics.get('disk_free_pct') or 0.0)
        def col_cpu(v):
            return err if v >= 90.0 else (warn if v >= 80.0 else ok)
        def col_mem(v):
            return err if v >= 90.0 else (warn if v >= 80.0 else ok)
        def col_dfree(v):
            return err if v <= 10.0 else (warn if v <= 20.0 else ok)
        try:
            self.g_cpu.setColor(col_cpu(cpu))
            self.g_cpu.setTrack(self.theme.gauge_track_color())
            self.g_cpu.setTextColor(self.theme.gauge_text_color())
            self.g_mem.setColor(col_mem(mem))
            self.g_mem.setTrack(self.theme.gauge_track_color())
            self.g_mem.setTextColor(self.theme.gauge_text_color())
            self.g_dsk.setColor(col_dfree(dfree))
            self.g_dsk.setTrack(self.theme.gauge_track_color())
            self.g_dsk.setTextColor(self.theme.gauge_text_color())
        except Exception:
            pass

    def _counts_html(self) -> str:
        try:
            on = int(self.metrics.get('vms_on') or 0)
            off = int(self.metrics.get('vms_off') or 0)
        except Exception:
            on, off = 0, 0
        ok = self.theme.gauge_ok_color()
        err = self.theme.gauge_err_color()
        return f"<span style='color:{ok}'>On {on}</span> • <span style='color:{err}'>Off {off}</span>"
