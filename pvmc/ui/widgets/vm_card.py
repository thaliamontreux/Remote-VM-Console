import logging
import math

from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QAction, QFontMetrics, QColor
from PySide6.QtWidgets import QFrame, QLabel, QHBoxLayout, QVBoxLayout, QMenu, QGraphicsDropShadowEffect


class ElideLabel(QLabel):
    def __init__(self, text='', mode=Qt.ElideLeft, parent=None):
        super().__init__(text, parent)
        self._mode = mode
        self._full = text

    def setText(self, text):
        self._full = text
        super().setText(text)

    def resizeEvent(self, event):
        try:
            fm = QFontMetrics(self.font())
            w = max(0, self.width())
            elided = fm.elidedText(self._full, self._mode, w)
            super().setText(elided)
        except Exception as e:
            logging.error(f"[LABEL] Elide error: {type(e).__name__}: {e}")
        super().resizeEvent(event)


class Led(QLabel):
    def __init__(self, color='#4CAF50', parent=None):
        super().__init__('', parent)
        self.setFixedSize(QSize(10, 10))
        self.set_color(color)

    def set_color(self, color):
        self.setStyleSheet(f'background: {color}; border-radius: 5px;')


class VMCard(QFrame):
    def __init__(self, theme, vm, on_console, on_start, on_stop, on_reboot=None, parent=None):
        super().__init__(parent)
        self.setObjectName('vmcard')
        self.theme = theme
        self.vm = vm
        self.on_console = on_console
        self.on_start = on_start
        self.on_stop = on_stop
        self.on_reboot = on_reboot
        name_u = (vm.get('name','') or '').upper()
        self.is_important = ('IMPORTANT' in name_u) or ('(I)' in name_u)
        on_color = self.theme.led_color_on()
        powered_on = (vm.get('power_state','').lower()=="poweredon")
        self.led = Led(on_color if powered_on else '#666666')
        self.name = ElideLabel(vm.get('name',''))
        # Prefer custom server label if present
        self.server = QLabel(vm.get('server_label', vm.get('server','')))
        self.server.setStyleSheet(f'color: {self.theme.active_theme().get("vm_server_text", "#AAAAAA")}; font-size: 10px;')
        v = QVBoxLayout()
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(0)
        v.addWidget(self.name)
        v.addWidget(self.server)
        h = QHBoxLayout(self)
        h.setContentsMargins(8, 6, 8, 6)
        h.setSpacing(8)
        # Stack LEDs vertically: main power LED (no extra flashing LED)
        leds = QVBoxLayout()
        leds.setContentsMargins(0, 0, 0, 0)
        leds.setSpacing(4)
        leds.addWidget(self.led, 0, Qt.AlignTop)
        h.addLayout(leds)
        h.addLayout(v)
        eff = QGraphicsDropShadowEffect(self)
        self._shadow_effect = eff
        self.setGraphicsEffect(self._shadow_effect)
        self.setCursor(Qt.PointingHandCursor)
        try:
            hsize = self.sizeHint()
            logging.debug(f"[CARD] Built VMCard name='{vm.get('name')}' server='{vm.get('server')}' moid='{vm.get('moid')}' sizeHint=({hsize.width()}x{hsize.height()})")
        except Exception as e:
            logging.error(f"[CARD] sizeHint error: {type(e).__name__}: {e}")
        # Apply initial style with optional server color override; lighten if IMPORTANT
        try:
            bg_override = vm.get('server_color')
            if self.is_important:
                bg_override = self.theme.lighten_color(bg_override, 0.25)
            self.setStyleSheet(self.theme.vm_button_style_for(bg_override))
        except Exception:
            self.setStyleSheet(self.theme.vm_button_style())
        # Initialize pulsing state and apply initial glow state
        self._pulse_timer = None
        self._pulse_theta = 0.0
        try:
            self._update_glow_state(powered_on)
        except Exception:
            pass

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if callable(self.on_console):
                self.on_console(self.vm)
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        m = QMenu(self)
        act_console = QAction('Remote Console', self)
        act_console.triggered.connect(lambda: self.on_console(self.vm))
        act_start = QAction('Start VM', self)
        act_start.triggered.connect(lambda: self.on_start(self.vm))
        act_stop = QAction('Guest Shutdown', self)
        act_stop.triggered.connect(lambda: self.on_stop(self.vm))
        act_restart = None
        if callable(getattr(self, 'on_reboot', None)):
            act_restart = QAction('Guest Restart', self)
            act_restart.triggered.connect(lambda: self.on_reboot(self.vm))
        m.addAction(act_console)
        m.addSeparator()
        m.addAction(act_start)
        m.addAction(act_stop)
        if act_restart is not None:
            m.addAction(act_restart)
        m.exec(event.globalPos())

    def updateTheme(self):
        self.server.setStyleSheet(f'color: {self.theme.active_theme().get("vm_server_text", "#AAAAAA")}; font-size: 10px;')
        bg_override = self.vm.get('server_color')
        if self.is_important:
            bg_override = self.theme.lighten_color(bg_override, 0.25)
        self.setStyleSheet(self.theme.vm_button_style_for(bg_override))
        # Reapply glow based on current power state
        try:
            powered_on = (self.vm.get('power_state','').lower()=="poweredon")
            self._update_glow_state(powered_on)
        except Exception:
            pass

    def setPowered(self, on):
        self.led.set_color(self.theme.led_color_on() if on else '#666666')
        # Apply or remove pulsing yellow glow for IMPORTANT
        try:
            self._update_glow_state(on)
        except Exception:
            pass

    def _update_glow_state(self, powered_on=None):
        if powered_on is None:
            powered_on = (self.vm.get('power_state','').lower()=="poweredon")
        if not self.is_important or powered_on:
            self._stop_pulse()
            try:
                self._shadow_effect.setColor(QColor('#000000'))
                self._shadow_effect.setOffset(2, 2)
                self._shadow_effect.setBlurRadius(6)
            except Exception:
                pass
            return
        # IMPORTANT and powered off -> pulsing yellow glow
        self._start_pulse()

    def _start_pulse(self):
        if self._pulse_timer is not None:
            if self._pulse_timer.isActive():
                return
        self._pulse_theta = 0.0
        if self._pulse_timer is None:
            self._pulse_timer = QTimer(self)
            self._pulse_timer.setInterval(50)  # ~20 FPS
            self._pulse_timer.timeout.connect(self._tick_pulse)
        self._pulse_timer.start()

    def _stop_pulse(self):
        try:
            if self._pulse_timer is not None:
                self._pulse_timer.stop()
        except Exception:
            pass

    def _tick_pulse(self):
        try:
            # Smooth pulse 0..1
            self._pulse_theta = (self._pulse_theta + 0.25) % (2 * math.pi)
            k = 0.5 + 0.5 * math.sin(self._pulse_theta)
            # Blur between 12..24, alpha between 90..200
            blur = 12 + int(12 * k)
            alpha = 90 + int(110 * k)
            col = QColor('#FFD700')
            col.setAlpha(alpha)
            self._shadow_effect.setColor(col)
            self._shadow_effect.setOffset(0, 0)
            self._shadow_effect.setBlurRadius(blur)
        except Exception:
            pass
