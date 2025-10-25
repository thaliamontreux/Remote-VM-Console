from PySide6.QtCore import Qt


class ThemeManager:
    def __init__(self, config_manager):
        self.cm = config_manager

    def active_theme(self):
        return self.cm.get_theme()

    def apply_to_window(self, window):
        t = self.active_theme()
        if t.get('transparent', False):
            window.setAttribute(Qt.WA_TranslucentBackground, True)
            window.setStyleSheet('background: transparent;')
        else:
            bg0 = t.get('bg_gradient_start', '#1e1e2a')
            bg1 = t.get('bg_gradient_end', '#2a2a3a')
            window.setAttribute(Qt.WA_TranslucentBackground, False)
            window.setStyleSheet(f'QMainWindow {{ background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 {bg0}, stop:1 {bg1}); }}')

    def gradient_css(self):
        t = self.active_theme()
        bg0 = t.get('bg_gradient_start', '#1e1e2a')
        bg1 = t.get('bg_gradient_end', '#2a2a3a')
        return f"qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 {bg0}, stop:1 {bg1})"

    def metrics_gradient_css(self):
        t = self.active_theme()
        bg0 = t.get('metrics_bg_gradient_start', t.get('bg_gradient_start', '#1e1e2a'))
        bg1 = t.get('metrics_bg_gradient_end', t.get('bg_gradient_end', '#2a2a3a'))
        return f"qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 {bg0}, stop:1 {bg1})"

    def metrics_text_color(self):
        t = self.active_theme()
        return t.get('metrics_text', t.get('panel_text', '#FFFFFF'))

    def gauge_track_color(self):
        t = self.active_theme()
        return t.get('metrics_gauge_track', '#444444')

    def gauge_text_color(self):
        t = self.active_theme()
        return t.get('metrics_gauge_text', t.get('text_primary', '#FFFFFF'))

    def gauge_ok_color(self):
        t = self.active_theme()
        return t.get('metrics_gauge_ok', t.get('status_ok', '#4CAF50'))

    def gauge_warn_color(self):
        t = self.active_theme()
        return t.get('metrics_gauge_warn', t.get('status_warn', '#FFC107'))

    def gauge_err_color(self):
        t = self.active_theme()
        return t.get('metrics_gauge_err', t.get('status_err', '#F44336'))

    def vm_button_style(self):
        return self.vm_button_style_for()

    def vm_button_style_for(self, bg_override=None):
        t = self.active_theme()
        bg = bg_override or t.get('button_bg', '#2f2f45')
        txt = t.get('vm_name_text', '#FFFFFF')
        radius = int(t.get('button_radius_px', 10))
        return f'QFrame#vmcard {{ background: {bg}; border-radius: {radius}px; }} QLabel {{ color: {txt}; }}'

    def led_color_on(self):
        t = self.active_theme()
        return t.get('vm_led_on', '#4CAF50')

    def text_primary(self):
        t = self.active_theme()
        return t.get('text_primary', '#FFFFFF')

    def lighten_color(self, hex_color, factor=0.2):
        try:
            s = (hex_color or '').strip()
            if not s:
                s = self.active_theme().get('button_bg', '#2f2f45')
            if not s.startswith('#'):
                s = '#' + s
            s = s[:7]
            r = int(s[1:3], 16)
            g = int(s[3:5], 16)
            b = int(s[5:7], 16)
            r = min(255, int(r + (255 - r) * float(factor)))
            g = min(255, int(g + (255 - g) * float(factor)))
            b = min(255, int(b + (255 - b) * float(factor)))
            return f"#{r:02X}{g:02X}{b:02X}"
        except Exception:
            t = self.active_theme()
            return t.get('button_bg', '#2F2F45')

    def update_theme_value(self, key, value):
        name = self.cm.get_active_theme_name()
        t = self.cm.get_theme(name)
        t[key] = value
        self.cm.set_theme(name, t)

    def import_theme(self, path):
        return self.cm.import_theme(path)

    def export_theme(self, name, path):
        self.cm.export_theme(name, path)
