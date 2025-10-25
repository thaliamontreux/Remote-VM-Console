import json
import logging

from PySide6.QtCore import Signal
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QDialog, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTableWidget,
    QTableWidgetItem, QLineEdit, QMessageBox, QCheckBox, QSpinBox, QComboBox, QFileDialog
)
from PySide6.QtGui import QGuiApplication

from .widgets.color_field import ColorField
from .widgets.toggle_switch import ToggleSwitch
from ..logging_utils import set_debug_enabled


_COLOR_KEYS = [
    'bg_gradient_start', 'bg_gradient_end', 'cards_background', 'text_primary', 'text_secondary',
    'button_bg', 'button_shadow', 'cluster_header_bg', 'cluster_header_text', 'vm_led_on',
    'vm_name_text', 'vm_server_text', 'panel_text', 'gear_button_bg', 'gear_button_text',
    'status_ok', 'status_warn', 'status_err', 'vm_host_dot',
    'metrics_bg_gradient_start', 'metrics_bg_gradient_end', 'metrics_text',
    'metrics_gauge_track', 'metrics_gauge_text', 'metrics_gauge_ok', 'metrics_gauge_warn', 'metrics_gauge_err'
]


class ControlPanelDialog(QDialog):
    serversChanged = Signal()
    layoutChanged = Signal()
    themeChanged = Signal()

    def __init__(self, config_manager, theme_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle('PentaVMControl — Control Panel')
        self.cm = config_manager
        self.tm = theme_manager
        self.tabs = QTabWidget(self)
        self._build_servers_tab()
        self._build_layout_tab()
        self._build_theme_tab()
        self._build_about_tab()
        btns = QHBoxLayout()
        btn_close = QPushButton('Close')
        btn_close.clicked.connect(self.accept)
        btns.addStretch(1)
        btns.addWidget(btn_close)
        root = QVBoxLayout(self)
        root.addWidget(self.tabs)
        root.addLayout(btns)

    def _build_servers_tab(self):
        tab = QWidget()
        v = QVBoxLayout(tab)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(['Name', 'Host', 'Username', 'Password', 'Thumbprint', 'Color'])
        v.addWidget(self.table)
        h = QHBoxLayout()
        btn_add = QPushButton('Add')
        btn_edit = QPushButton('Edit')
        btn_del = QPushButton('Remove')
        h.addWidget(btn_add)
        h.addWidget(btn_edit)
        h.addWidget(btn_del)
        h.addStretch(1)
        v.addLayout(h)
        self.cb_running = QCheckBox('Show running only')
        self.cb_running.setChecked(self.cm.get_bool('show_running_only', True))
        self.cb_running.toggled.connect(self._save_running_only)
        v.addWidget(self.cb_running)
        # Debug logging toggle (green ON / red OFF)
        dbg_row = QHBoxLayout()
        dbg_row.addWidget(QLabel('Debug Logging'))
        self.tgl_debug = ToggleSwitch()
        self.tgl_debug.setChecked(self.cm.get_bool('debug_logging', True))
        self.tgl_debug.toggled.connect(self._toggle_debug)
        dbg_row.addWidget(self.tgl_debug)
        dbg_row.addStretch(1)
        v.addLayout(dbg_row)
        btn_add.clicked.connect(self._add_server)
        btn_edit.clicked.connect(self._edit_server)
        btn_del.clicked.connect(self._remove_server)
        self.tabs.addTab(tab, 'Servers & VMs')
        self._load_servers()

    def _build_layout_tab(self):
        tab = QWidget()
        v = QVBoxLayout(tab)
        current = self.cm.get_layout()
        self.spin_bw = QSpinBox()
        self.spin_bw.setRange(20, 200)
        self.spin_bw.setValue(current['button_width'])
        self.spin_bh = QSpinBox()
        self.spin_bh.setRange(20, 200)
        self.spin_bh.setValue(current['button_height'])
        self.spin_ch = QSpinBox()
        self.spin_ch.setRange(6, 60)
        self.spin_ch.setValue(current['cluster_header_height_px'])
        self.spin_cw = QSpinBox()
        self.spin_cw.setRange(50, 1000)
        self.spin_cw.setValue(current['cluster_header_width_px'])
        self.spin_side = QSpinBox()
        self.spin_side.setRange(32, 50)
        self.spin_side.setValue(self.cm.config.get('side_panel_width', 50))
        self.spin_metrics = QSpinBox()
        self.spin_metrics.setRange(120, 600)
        self.spin_metrics.setValue(current.get('metrics_panel_width', 180))
        self.combo_dock = QComboBox()
        self.combo_dock.addItems(['top', 'left', 'right'])
        self.combo_dock.setCurrentText(current['dock_position'])
        self.combo_mon = QComboBox()
        screens = QGuiApplication.screens()
        for i, s in enumerate(screens):
            g = s.geometry()
            self.combo_mon.addItem(f'{i}: {g.width()}x{g.height()} @ ({g.x()},{g.y()})', i)
        self.combo_mon.setCurrentIndex(min(current['monitor_index'], self.combo_mon.count()-1))
        grid = QVBoxLayout()
        def row(lbl, w):
            h = QHBoxLayout()
            h.addWidget(QLabel(lbl))
            h.addWidget(w, 1)
            grid.addLayout(h)
        row('Button Width', self.spin_bw)
        row('Button Height', self.spin_bh)
        row('Cluster Header Height', self.spin_ch)
        row('Cluster Header Width', self.spin_cw)
        row('Right Rail Width (px)', self.spin_side)
        row('Metrics Panel Width (px)', self.spin_metrics)
        row('Dock Position', self.combo_dock)
        row('Monitor', self.combo_mon)
        v.addLayout(grid)
        btn_apply = QPushButton('Apply Layout')
        btn_apply.clicked.connect(self._apply_layout)
        v.addWidget(btn_apply)
        v.addStretch(1)
        self.tabs.addTab(tab, 'Layout / Sizing')

    def _build_theme_tab(self):
        tab = QWidget()
        v = QVBoxLayout(tab)
        # Theme picker and actions
        top = QHBoxLayout()
        top.addWidget(QLabel('Theme'))
        self.combo_theme = QComboBox()
        self._reload_theme_list()
        self.combo_theme.currentTextChanged.connect(self._on_theme_selected)
        top.addWidget(self.combo_theme, 1)
        btn_new = QPushButton('New')
        btn_dup = QPushButton('Duplicate')
        btn_del = QPushButton('Delete')
        btn_set = QPushButton('Set Active')
        btn_new.clicked.connect(self._new_theme)
        btn_dup.clicked.connect(self._duplicate_theme)
        btn_del.clicked.connect(self._delete_theme)
        btn_set.clicked.connect(self._set_active_selected)
        top.addWidget(btn_new)
        top.addWidget(btn_dup)
        top.addWidget(btn_del)
        top.addWidget(btn_set)
        v.addLayout(top)

        meta = QHBoxLayout()
        self.e_theme_name = QLineEdit()
        self.e_theme_desc = QLineEdit()
        meta.addWidget(QLabel('Name'))
        meta.addWidget(self.e_theme_name, 1)
        meta.addWidget(QLabel('Description'))
        meta.addWidget(self.e_theme_desc, 2)
        btn_save_meta = QPushButton('Save Theme')
        btn_save_meta.clicked.connect(self._save_theme_meta)
        meta.addWidget(btn_save_meta)
        v.addLayout(meta)

        t = self.cm.get_theme(self.cm.get_active_theme_name())
        self.cb_transparent = QCheckBox('Transparent Background')
        self.cb_transparent.setChecked(bool(t.get('transparent', False)))
        self.cb_transparent.toggled.connect(lambda on: self._theme_change('transparent', bool(on)))
        v.addWidget(self.cb_transparent)
        self.fields = {}
        for key in _COLOR_KEYS:
            cf = ColorField(self._initial_theme_value(key, t))
            cf.changed.connect(lambda val, k=key: self._theme_change(k, val))
            h = QHBoxLayout()
            h.addWidget(QLabel(key))
            h.addWidget(cf, 1)
            v.addLayout(h)
            self.fields[key] = cf
        hbtn = QHBoxLayout()
        btn_import = QPushButton('Import .theme')
        btn_export = QPushButton('Export .theme')
        btn_import.clicked.connect(self._import_theme)
        btn_export.clicked.connect(self._export_selected_theme)
        hbtn.addWidget(btn_import)
        hbtn.addWidget(btn_export)
        hbtn.addStretch(1)
        v.addLayout(hbtn)
        v.addStretch(1)
        self.tabs.addTab(tab, 'Theme')
        self._on_theme_selected(self.cm.get_active_theme_name())

    def _build_about_tab(self):
        tab = QWidget()
        v = QVBoxLayout(tab)
        info = QLabel()
        info.setWordWrap(True)
        info.setOpenExternalLinks(True)
        html = (
            "<h2>Remote VMWARE Console</h2>"
            "<h3>Developed by Thalia Montreux</h3>"
            "<div>PentaStar Studios</div>"
            "<div>New Bloomfield Missouri</div>"
            "<p><b>GitHub:</b> <a href=\"https://github.com/thaliamontreux/\">https://github.com/thaliamontreux/</a></p>"
            "<p><b>Email:</b> <a href=\"mailto:montreuxthalia@gmail.com\">montreuxthalia@gmail.com</a></p>"
            "<hr/>"
            "<h4>License</h4>"
            "<p>You may use, modify, and distribute this software, provided that all copies and derivative works retain clear attribution to the original developer: <b>Thalia Montreux</b> (PentaStar Studios). Removal or alteration of this attribution in future releases is prohibited.</p>"
        )
        info.setText(html)
        v.addWidget(info)
        v.addStretch(1)
        self.tabs.addTab(tab, 'About')

    def _load_servers(self):
        servers = self.cm.get_servers()
        self.table.setRowCount(0)
        for s in servers:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(s.get('name','')))
            self.table.setItem(r, 1, QTableWidgetItem(s.get('host','')))
            self.table.setItem(r, 2, QTableWidgetItem(s.get('username','')))
            masked = '•' * len(s.get('password',''))
            self.table.setItem(r, 3, QTableWidgetItem(masked))
            self.table.setItem(r, 4, QTableWidgetItem(s.get('thumbprint','')))
            self.table.setItem(r, 5, QTableWidgetItem(s.get('color','')))

    def _save_running_only(self, on):
        self.cm.set_bool('show_running_only', on)
        self.serversChanged.emit()

    def _toggle_debug(self, on):
        self.cm.set_bool('debug_logging', bool(on))
        try:
            set_debug_enabled(bool(on))
        except Exception:
            pass

    def _add_server(self):
        dlg = _ServerEditDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            host, user, pwd, thumb, name, color = dlg.values()
            servers = self.cm.get_servers()
            entry = {'host': host, 'username': user, 'password': pwd, 'thumbprint': thumb}
            if name:
                entry['name'] = name
            if color:
                entry['color'] = color
            servers.append(entry)
            self.cm.set_servers(servers)
            self._load_servers()
            self.serversChanged.emit()

    def _edit_server(self):
        row = self.table.currentRow()
        if row < 0:
            return
        servers = self.cm.get_servers()
        s = servers[row]
        dlg = _ServerEditDialog(s.get('host',''), s.get('username',''), s.get('password',''), s.get('thumbprint',''), s.get('name',''), s.get('color',''), self)
        if dlg.exec() == QDialog.Accepted:
            host, user, pwd, thumb, name, color = dlg.values()
            entry = {'host': host, 'username': user, 'password': pwd, 'thumbprint': thumb}
            if name:
                entry['name'] = name
            else:
                entry.pop('name', None)
            if color:
                entry['color'] = color
            else:
                entry.pop('color', None)
            servers[row] = entry
            self.cm.set_servers(servers)
            self._load_servers()
            self.serversChanged.emit()

    def _remove_server(self):
        row = self.table.currentRow()
        if row < 0:
            return
        servers = self.cm.get_servers()
        if row < len(servers):
            del servers[row]
            self.cm.set_servers(servers)
            self._load_servers()
            self.serversChanged.emit()

    def _apply_layout(self):
        self.cm.set_layout({
            'button_width': self.spin_bw.value(),
            'button_height': self.spin_bh.value(),
            'cluster_header_height_px': self.spin_ch.value(),
            'cluster_header_width_px': self.spin_cw.value(),
            'dock_position': self.combo_dock.currentText(),
            'monitor_index': self.combo_mon.currentData() or 0,
            'side_panel_width': self.spin_side.value(),
            'metrics_panel_width': self.spin_metrics.value()
        })
        self.layoutChanged.emit()

    def _reload_theme_list(self):
        self.combo_theme.clear()
        names = list(self.cm.config.get('themes', {}).keys())
        for n in names:
            self.combo_theme.addItem(n)
        active = self.cm.get_active_theme_name()
        self.combo_theme.setCurrentText(active)

    def _on_theme_selected(self, name):
        t = self.cm.get_theme(name)
        self.e_theme_name.setText(t.get('name', name))
        self.e_theme_desc.setText(t.get('description', ''))
        self.cb_transparent.setChecked(bool(t.get('transparent', False)))
        for k, cf in self.fields.items():
            cf.setValue(self._initial_theme_value(k, t))

    def _theme_change(self, key, value):
        name = self.combo_theme.currentText() or self.cm.get_active_theme_name()
        t = dict(self.cm.get_theme(name))
        t[key] = value
        self.cm.set_theme(name, t)
        if name == self.cm.get_active_theme_name():
            self.themeChanged.emit()

    def _initial_theme_value(self, key: str, t: dict) -> str:
        # Provide meaningful defaults for metrics-specific keys
        if key == 'metrics_bg_gradient_start':
            return t.get('metrics_bg_gradient_start', t.get('bg_gradient_start', '#1E1E2A'))
        if key == 'metrics_bg_gradient_end':
            return t.get('metrics_bg_gradient_end', t.get('bg_gradient_end', '#2A2A3A'))
        if key == 'metrics_text':
            return t.get('metrics_text', t.get('panel_text', '#FFFFFF'))
        if key == 'metrics_gauge_track':
            return t.get('metrics_gauge_track', '#444444')
        if key == 'metrics_gauge_text':
            return t.get('metrics_gauge_text', t.get('text_primary', '#FFFFFF'))
        if key == 'metrics_gauge_ok':
            return t.get('metrics_gauge_ok', t.get('status_ok', '#4CAF50'))
        if key == 'metrics_gauge_warn':
            return t.get('metrics_gauge_warn', t.get('status_warn', '#FFC107'))
        if key == 'metrics_gauge_err':
            return t.get('metrics_gauge_err', t.get('status_err', '#F44336'))
        return t.get(key, '#000000')

    def _set_active_selected(self):
        name = self.combo_theme.currentText()
        if not name:
            return
        self.cm.set_active_theme(name)
        self.themeChanged.emit()

    def _new_theme(self):
        base_name = self.combo_theme.currentText() or self.cm.get_active_theme_name()
        base = dict(self.cm.get_theme(base_name))
        i = 1
        while True:
            new_name = f'NewTheme_{i}'
            if new_name not in self.cm.config.get('themes', {}):
                break
            i += 1
        base.setdefault('name', new_name)
        base.setdefault('description', '')
        self.cm.set_theme(new_name, base)
        self._reload_theme_list()
        self.combo_theme.setCurrentText(new_name)
        self._on_theme_selected(new_name)

    def _duplicate_theme(self):
        src = self.combo_theme.currentText() or self.cm.get_active_theme_name()
        t = dict(self.cm.get_theme(src))
        i = 1
        while True:
            new_name = f'{src}_Copy{i}'
            if new_name not in self.cm.config.get('themes', {}):
                break
            i += 1
        t['name'] = new_name
        self.cm.set_theme(new_name, t)
        self._reload_theme_list()
        self.combo_theme.setCurrentText(new_name)
        self._on_theme_selected(new_name)

    def _delete_theme(self):
        name = self.combo_theme.currentText()
        if not name:
            return
        if name == self.cm.get_active_theme_name():
            QMessageBox.warning(self, 'Theme', 'Cannot delete the active theme. Set a different active theme first.')
            return
        themes = self.cm.config.get('themes', {})
        if len(themes) <= 1:
            QMessageBox.warning(self, 'Theme', 'At least one theme must exist.')
            return
        if QMessageBox.question(self, 'Theme', f"Delete theme '{name}'?") != QMessageBox.Yes:
            return
        try:
            del themes[name]
            self.cm.save()
            self._reload_theme_list()
            self._on_theme_selected(self.cm.get_active_theme_name())
        except Exception:
            pass

    def _save_theme_meta(self):
        old_name = self.combo_theme.currentText()
        if not old_name:
            return
        new_name = (self.e_theme_name.text().strip() or old_name)
        desc = self.e_theme_desc.text().strip()
        t = dict(self.cm.get_theme(old_name))
        t['name'] = new_name
        t['description'] = desc
        if new_name != old_name:
            themes = self.cm.config.get('themes', {})
            themes[new_name] = t
            try:
                del themes[old_name]
            except Exception:
                pass
            # Update active if it was old_name
            if self.cm.get_active_theme_name() == old_name:
                self.cm.set_active_theme(new_name)
            else:
                self.cm.save()
            self._reload_theme_list()
            self.combo_theme.setCurrentText(new_name)
        else:
            self.cm.set_theme(new_name, t)
        self._on_theme_selected(new_name)
        self.themeChanged.emit()

    def _import_theme(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Import Theme', '', 'Theme (*.theme *.json);;All Files (*)')
        if not path:
            return
        name = self.tm.import_theme(path)
        if name:
            self._reload_theme_list()
            self.combo_theme.setCurrentText(name)
            self._on_theme_selected(name)
            self.themeChanged.emit()

    def _export_selected_theme(self):
        path, _ = QFileDialog.getSaveFileName(self, 'Export Theme', 'theme.theme', 'Theme (*.theme *.json);;All Files (*)')
        if not path:
            return
        name = self.combo_theme.currentText() or self.cm.get_active_theme_name()
        self.tm.export_theme(name, path)


class _ServerEditDialog(QDialog):
    def __init__(self, host='', username='', password='', thumbprint='', name='', color='', parent=None):
        super().__init__(parent)
        self.setWindowTitle('Server')
        v = QVBoxLayout(self)
        self.e_host = QLineEdit(host)
        self.e_user = QLineEdit(username)
        self.e_pwd = QLineEdit(password)
        self.e_pwd.setEchoMode(QLineEdit.Password)
        self.e_thumb = QLineEdit(thumbprint)
        self.e_thumb.setPlaceholderText('SHA1 fingerprint, e.g. AA:BB:CC:...')
        self.e_name = QLineEdit(name)
        self.e_name.setPlaceholderText('Friendly name (optional)')
        self.e_color = QLineEdit(color)
        self.e_color.setPlaceholderText('#RRGGBB (optional)')
        def row(lbl, w):
            h = QHBoxLayout()
            h.addWidget(QLabel(lbl))
            h.addWidget(w, 1)
            v.addLayout(h)
        row('Name', self.e_name)
        row('Host', self.e_host)
        row('Username', self.e_user)
        row('Password', self.e_pwd)
        row('Thumbprint', self.e_thumb)
        row('Color', self.e_color)
        h = QHBoxLayout()
        ok = QPushButton('OK')
        cancel = QPushButton('Cancel')
        ok.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        h.addStretch(1)
        h.addWidget(ok)
        h.addWidget(cancel)
        v.addLayout(h)

    def values(self):
        return (
            self.e_host.text().strip(),
            self.e_user.text().strip(),
            self.e_pwd.text(),
            self.e_thumb.text().strip(),
            self.e_name.text().strip(),
            self.e_color.text().strip().upper()
        )
