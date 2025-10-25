import logging

from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QMessageBox, QApplication, QScrollArea
)
from PySide6.QtGui import QGuiApplication

from ..config import ConfigManager
from ..theme import ThemeManager
from ..appbar import AppBarManager
from ..esxi import ESXiClient
from .control_panel import ControlPanelDialog
from .widgets.wrap_panel import WrapPanel
from .widgets.vm_card import VMCard
from .widgets.host_metrics_card import HostMetricsCard
from ..logging_utils import save_diagnostics, set_debug_enabled, get_debug_enabled


class PentaVMControlMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('PentaVMControl')
        self.cm = ConfigManager()
        self.tm = ThemeManager(self.cm)
        self.appbar = AppBarManager()
        self.esxi = ESXiClient(show_running_only=self.cm.get_bool('show_running_only', True))
        self._disable_appbar_session = False
        logging.debug(f"[CFG] Config path: {self.cm.config_path}")
        logging.debug(f"[CFG] Initial layout: {self.cm.get_layout()}")
        logging.debug(f"[CFG] Flags: show_running_only={self.cm.get_bool('show_running_only', True)} disable_appbar={self.cm.get_bool('disable_appbar', False)} skip_inventory_on_startup={self.cm.get_bool('skip_inventory_on_startup', False)}")
        self.timer = QTimer(self)
        self.timer.setInterval(30000)
        self.timer.timeout.connect(self.refresh_inventory)
        self._build_ui()
        self.tm.apply_to_window(self)

    def _build_ui(self):
        logging.debug('[UI] Building main UI...')
        # Left: VM wrap panel (expands)
        self.panel = WrapPanel(margin=8, hspacing=8, vspacing=8)
        logging.debug('[UI] WrapPanel created')

        # Middle-right: fixed-width metrics scroll area (vertical only)
        self.metrics_scroll = QScrollArea()
        self.metrics_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.metrics_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.metrics_scroll.setWidgetResizable(True)
        self.metrics_body = QWidget()
        self.metrics_v = QVBoxLayout(self.metrics_body)
        self.metrics_v.setContentsMargins(6, 6, 6, 6)
        self.metrics_v.setSpacing(8)
        self.metrics_scroll.setWidget(self.metrics_body)
        self._apply_metrics_width()
        self._apply_metrics_background()

        # Far-right: fixed-width side panel for controls/title
        self.side = QWidget()
        side_l = QVBoxLayout(self.side)
        side_l.setContentsMargins(4, 4, 4, 4)
        side_l.setSpacing(8)
        self.btn_refresh = QPushButton('⟳')
        self.btn_refresh.setToolTip('Refresh')
        self.btn_refresh.clicked.connect(self.refresh_inventory)
        self.btn_gear = QPushButton('⚙')
        self.btn_gear.setToolTip('Control Panel')
        self.btn_gear.clicked.connect(self.open_control_panel)
        self.btn_diag = QPushButton('🧾')
        self.btn_diag.setToolTip('Save Diagnostics Bundle')
        self.btn_diag.clicked.connect(self._save_diagnostics_bundle)
        self.btn_debug = QPushButton('🐞')
        self.btn_debug.setToolTip('Toggle Debug Logs')
        self.btn_debug.clicked.connect(self._toggle_debug_logs)
        self.btn_exit = QPushButton('⏻')
        self.btn_exit.setToolTip('Exit Program')
        self.btn_exit.clicked.connect(self._exit_app)
        self.title_lbl = QLabel('RVMC')
        self.title_lbl.setWordWrap(True)
        self.title_lbl.setAlignment(Qt.AlignCenter)
        self.title_lbl.setStyleSheet(f'color: {self.tm.text_primary()}; font-weight: bold; font-size: 10px;')
        # Even spacing: buttons centered with stretch above and below; label pinned at bottom
        side_l.addStretch(1)
        side_l.addWidget(self.btn_refresh, 0, Qt.AlignHCenter)
        side_l.addWidget(self.btn_gear, 0, Qt.AlignHCenter)
        side_l.addWidget(self.btn_diag, 0, Qt.AlignHCenter)
        side_l.addWidget(self.btn_debug, 0, Qt.AlignHCenter)
        side_l.addWidget(self.btn_exit, 0, Qt.AlignHCenter)
        side_l.addStretch(1)
        side_l.addWidget(self.title_lbl, 0)
        side_w = int(self.cm.config.get('side_panel_width', 50))
        self.side.setFixedWidth(max(32, min(50, side_w)))
        # Apply consistent sizing/style now
        self._apply_side_width()
        self._apply_debug_button_style()

        # Root: horizontal split: [panel][metrics][side]
        root = QWidget()
        root_l = QHBoxLayout(root)
        root_l.setContentsMargins(0, 0, 0, 0)
        root_l.setSpacing(0)
        root_l.addWidget(self.panel, 1)
        root_l.addWidget(self.metrics_scroll, 0)
        root_l.addWidget(self.side, 0)
        self.setCentralWidget(root)
        logging.debug('[UI] Central widget set (split: panel | side)')

    def _desired_dims(self, dock):
        # Compute desired dimensions without querying layout size hints
        layout = self.cm.get_layout()
        margin = getattr(self.panel, 'margin', 8)
        bw = layout.get('button_width', 160)
        bh = layout.get('button_height', 48)
        if dock == 'top':
            # margins + one button row
            return QSize(0, margin * 2 + bh)
        else:
            # left/right: width is one button width + margins
            side_w = (self.side.width() if hasattr(self, 'side') else 50)
            metrics_w = (self.metrics_scroll.width() if hasattr(self, 'metrics_scroll') else self.cm.get_layout().get('metrics_panel_width', 180))
            total_w = margin * 2 + bw + side_w + metrics_w
            return QSize(total_w, 0)

    def showEvent(self, event):
        super().showEvent(event)
        logging.debug('[DOCK] showEvent: positioning and docking...')
        self.position_and_dock()
        skip = self.cm.get_bool('skip_inventory_on_startup', False)
        if skip:
            logging.debug('[INV] Startup: skip_inventory_on_startup=True; not refreshing or starting timer')
        else:
            QTimer.singleShot(200, self.refresh_inventory)
            self.timer.start()

    def closeEvent(self, event):
        self.appbar.unregister(self)
        super().closeEvent(event)

    def position_and_dock(self):
        layout = self.cm.get_layout()
        dock = layout.get('dock_position', 'top')
        mon_index = layout.get('monitor_index', 0)
        disable_appbar = self.cm.get_bool('disable_appbar', False) or self._disable_appbar_session
        screens = QGuiApplication.screens()
        if not screens:
            logging.warning('[DOCK] No screens detected; skipping docking')
            return
        screen = screens[min(mon_index, len(screens)-1)]
        g_full = screen.geometry()
        g_av = screen.availableGeometry()
        logging.debug(f"[DOCK] Target screen index={min(mon_index, len(screens)-1)} full=({g_full.x()},{g_full.y()},{g_full.width()}x{g_full.height()}) avail=({g_av.x()},{g_av.y()},{g_av.width()}x{g_av.height()}) dock={dock} disable_appbar={disable_appbar}")
        if disable_appbar:
            # Run as a normal window (no AppBar reservation) for isolation
            if dock == 'top':
                desired = self.sizeHint().height()
                self.setGeometry(g_av.x(), g_av.y(), g_av.width(), desired)
            elif dock == 'left':
                desired = self.sizeHint().width()
                self.setGeometry(g_av.x(), g_av.y(), desired, g_av.height())
            else:
                desired = self.sizeHint().width()
                self.setGeometry(g_av.right() - desired + 1, g_av.y(), desired, g_av.height())
            return
        if dock == 'top':
            self.setMaximumHeight(1000)
            desired_h = self._desired_dims('top').height()
            logging.debug(f"[DOCK] position_and_dock top: desired_h={desired_h}")
            self.resize(g_full.width(), desired_h)
            try:
                self.appbar.register(self, 'top', g_full)
            except Exception as e:
                logging.error(f'[DOCK] AppBar register failed (top): {e}')
        elif dock == 'left':
            self.setMaximumWidth(1000)
            desired_w = self._desired_dims('left').width()
            logging.debug(f"[DOCK] position_and_dock left: desired_w={desired_w}")
            self.resize(desired_w, g_full.height())
            try:
                self.appbar.register(self, 'left', g_full)
            except Exception as e:
                logging.error(f'[DOCK] AppBar register failed (left): {e}')
        else:
            self.setMaximumWidth(1000)
            desired_w = self._desired_dims('right').width()
            logging.debug(f"[DOCK] position_and_dock right: desired_w={desired_w}")
            self.resize(desired_w, g_full.height())
            try:
                self.appbar.register(self, 'right', g_full)
            except Exception as e:
                logging.error(f'[DOCK] AppBar register failed (right): {e}')

    def rebuild_ui(self, vms):
        logging.info('[INV] UI rebuild started.')
        logging.debug(f'[UI] Rebuilding UI with {len(vms)} VM items')
        old = self.panel.count()
        logging.debug(f'[UI] Clearing existing widgets: count={old}')
        self.panel.clear()
        style = self.tm.vm_button_style()
        added = 0
        for vm in vms:
            logging.debug(f"[UI] Add VM card: name={vm.get('name')} server={vm.get('server')} moid={vm.get('moid')} state={vm.get('power_state')}")
            try:
                card = VMCard(self.tm, vm, self._open_console, self._start_vm, self._stop_vm, self._reboot_vm)
                card.setFixedSize(self.cm.get_layout().get('button_width', 160), self.cm.get_layout().get('button_height', 48))
                try:
                    card.setStyleSheet(self.tm.vm_button_style_for(vm.get('server_color')))
                except Exception:
                    card.setStyleSheet(style)
                self.panel.addWidget(card)
                added += 1
            except Exception as e:
                import traceback
                logging.error(f"[UI] VM card build failed for '{vm.get('name')}': {type(e).__name__}: {e}")
                traceback.print_exc()
        try:
            servers = self.cm.get_servers()
            host_metrics = []
            try:
                host_metrics = self.esxi.fetch_hosts_metrics(servers)
            except Exception as e:
                logging.info(f"[MET] fetch error: {type(e).__name__}: {e}")
            self._rebuild_metrics(host_metrics)
        except Exception as e:
            logging.error(f"[MET] rebuild error: {type(e).__name__}: {e}")
        # Avoid central sizeHint calls here; just log item count
        logging.debug(f"[UI] Pre-redock: items={self.panel.count()}")
        logging.debug('[DOCK] Scheduling redock to content on next event loop tick')
        QTimer.singleShot(0, self._redock_to_content)
        logging.debug(f'[UI] UI rebuild completed: added={added} (cleared={old})')
        logging.info('[INV] UI rebuild completed successfully.')

    def _redock_to_content(self):
        layout = self.cm.get_layout()
        dock = layout.get('dock_position', 'top')
        disable_appbar = self.cm.get_bool('disable_appbar', False) or self._disable_appbar_session
        screens = QGuiApplication.screens()
        screen = screens[min(layout.get('monitor_index', 0), len(screens)-1)]
        g_full = screen.geometry()
        g_av = screen.availableGeometry()
        logging.debug(f"[DOCK] Redock to content: dock={dock} disable_appbar={disable_appbar} full=({g_full.x()},{g_full.y()},{g_full.width()}x{g_full.height()}) avail=({g_av.x()},{g_av.y()},{g_av.width()}x{g_av.height()})")
        if disable_appbar:
            if dock == 'top':
                # Dynamic rows based on available width
                try:
                    margin = getattr(self.panel, 'margin', 8)
                    hsp = getattr(self.panel, 'hspacing', 8)
                    vsp = getattr(self.panel, 'vspacing', 8)
                    bw = self.cm.get_layout().get('button_width', 160)
                    bh = self.cm.get_layout().get('button_height', 48)
                    side_w = self.side.width() if hasattr(self, 'side') else 50
                    metrics_w = self.metrics_scroll.width() if hasattr(self, 'metrics_scroll') else self.cm.get_layout().get('metrics_panel_width', 180)
                    avail_w = g_av.width() - side_w - metrics_w - 2 * margin
                    cols = max(1, int((avail_w + hsp) // (bw + hsp)))
                    n = self.panel.count()
                    rows = max(1, (n + cols - 1) // cols)
                    desired = 2 * margin + rows * bh + (rows - 1) * vsp
                    logging.debug(f"[DOCK] Redock(normal) top: avail_w={avail_w} side_w={side_w} metrics_w={metrics_w} cols={cols} rows={rows} desired_h={desired}")
                except Exception as e:
                    logging.error(f"[DOCK] Redock(normal) top math error: {type(e).__name__}: {e}")
                    desired = self._desired_dims('top').height()
                self.setGeometry(g_av.x(), g_av.y(), g_av.width(), desired)
            elif dock == 'left':
                desired = self._desired_dims('left').width()
                logging.debug(f"[DOCK] Redock(normal) left: desired_w={desired}")
                self.setGeometry(g_av.x(), g_av.y(), desired, g_av.height())
            else:
                desired = self._desired_dims('right').width()
                logging.debug(f"[DOCK] Redock(normal) right: desired_w={desired}")
                self.setGeometry(g_av.right() - desired + 1, g_av.y(), desired, g_av.height())
            return
        geom_before = self.geometry()
        logging.debug(f"[DOCK] Pre-redock window geometry=({geom_before.x()},{geom_before.y()},{geom_before.width()}x{geom_before.height()})")
        if dock == 'top':
            # Dynamic rows based on full width when docked as AppBar
            try:
                margin = getattr(self.panel, 'margin', 8)
                hsp = getattr(self.panel, 'hspacing', 8)
                vsp = getattr(self.panel, 'vspacing', 8)
                bw = self.cm.get_layout().get('button_width', 160)
                bh = self.cm.get_layout().get('button_height', 48)
                side_w = self.side.width() if hasattr(self, 'side') else 50
                metrics_w = self.metrics_scroll.width() if hasattr(self, 'metrics_scroll') else self.cm.get_layout().get('metrics_panel_width', 180)
                full_w = g_full.width() - side_w - metrics_w - 2 * margin
                cols = max(1, int((full_w + hsp) // (bw + hsp)))
                n = self.panel.count()
                rows = max(1, (n + cols - 1) // cols)
                desired = 2 * margin + rows * bh + (rows - 1) * vsp
                logging.debug(f"[DOCK] Redock(appbar) top: full_w={full_w} side_w={side_w} metrics_w={metrics_w} cols={cols} rows={rows} desired_h={desired}")
            except Exception as e:
                logging.error(f"[DOCK] Redock(appbar) top math error: {type(e).__name__}: {e}")
                desired = self._desired_dims('top').height()
            self.resize(g_full.width(), desired)
            try:
                if self.appbar.registered:
                    self.appbar.set_pos(self, 'top', g_full)
                else:
                    self.appbar.register(self, 'top', g_full)
            except Exception as e:
                logging.critical(f'[DOCK] AppBar redock failed (top): {e}; disabling AppBar for session.')
                self._disable_appbar_session = True
                self._redock_to_content()
        elif dock == 'left':
            desired = self._desired_dims('left').width()
            logging.debug(f"[DOCK] Redock(appbar) left: desired_w={desired}")
            self.resize(desired, g_full.height())
            try:
                if self.appbar.registered:
                    self.appbar.set_pos(self, 'left', g_full)
                else:
                    self.appbar.register(self, 'left', g_full)
            except Exception as e:
                logging.critical(f'[DOCK] AppBar redock failed (left): {e}; disabling AppBar for session.')
                self._disable_appbar_session = True
                self._redock_to_content()
        else:
            desired = self._desired_dims('right').width()
            logging.debug(f"[DOCK] Redock(appbar) right: desired_w={desired}")
            self.resize(desired, g_full.height())
            try:
                if self.appbar.registered:
                    self.appbar.set_pos(self, 'right', g_full)
                else:
                    self.appbar.register(self, 'right', g_full)
            except Exception as e:
                logging.critical(f'[DOCK] AppBar redock failed (right): {e}; disabling AppBar for session.')
                self._disable_appbar_session = True
                self._redock_to_content()
        geom_after = self.geometry()
        logging.debug(f"[DOCK] Post-redock window geometry=({geom_after.x()},{geom_after.y()},{geom_after.width()}x{geom_after.height()})")

    def refresh_inventory(self):
        servers = self.cm.get_servers()
        self.esxi.show_running_only = self.cm.get_bool('show_running_only', True)
        vms = []
        try:
            logging.debug(f"[INV] Refresh: servers={len(servers)} show_running_only={self.esxi.show_running_only}")
            vms = self.esxi.fetch_inventory(servers)
        except Exception as e:
            logging.info(f'[INV] FATAL CRASH: {type(e).__name__}: {e}')
        try:
            self.rebuild_ui(vms)
        except Exception as e:
            import traceback
            logging.error(f"[INV] UI rebuild exception: {type(e).__name__}: {e}")
            traceback.print_exc()
        finally:
            logging.debug('[INV] Refresh cycle complete')

    def open_control_panel(self):
        logging.debug('[UI] Opening control panel dialog')
        dlg = ControlPanelDialog(self.cm, self.tm, self)
        dlg.serversChanged.connect(self.refresh_inventory)
        dlg.layoutChanged.connect(lambda: (self._apply_side_width(), self._apply_metrics_width(), self.position_and_dock(), self.refresh_inventory()))
        dlg.themeChanged.connect(self._apply_theme_live)
        dlg.exec()

    def _apply_theme_live(self):
        logging.debug('[THEME] Applying live theme updates to window and VM cards')
        self.tm.apply_to_window(self)
        try:
            # Iterate over current widgets in WrapPanel
            for w in self.panel.findChildren(QWidget, options=Qt.FindDirectChildrenOnly):
                if hasattr(w, 'updateTheme'):
                    w.updateTheme()
            for w in self.metrics_body.findChildren(QWidget, options=Qt.FindDirectChildrenOnly):
                if hasattr(w, 'updateTheme'):
                    w.updateTheme()
            self._apply_metrics_background()
        except Exception as e:
            logging.error(f"[THEME] apply live error: {type(e).__name__}: {e}")

    def _open_console(self, vm):
        host = vm.get('server')
        moid = vm.get('moid')
        logging.debug(f"[ACTION] Open console requested: host={host} moid={moid}")
        if not moid:
            QMessageBox.warning(self, 'VMRC', 'VM does not have a MoRef ID (moid).')
            return
        vmrc_path = self.cm.get_vmrc_path()
        creds = self._creds_for(host)
        ok = self.esxi.launch_vmrc(host, moid, vmrc_path, creds)
        if not ok:
            QMessageBox.warning(self, 'VMRC', 'Failed to launch VMRC. Ensure VMware Remote Console is installed or set vmrc_path in config.')

    def _start_vm(self, vm):
        logging.debug(f"[ACTION] Start VM requested: host={vm.get('server')} moid={vm.get('moid')} name={vm.get('name')}")
        if QMessageBox.question(self, 'Start VM', f"Start '{vm.get('name','')}'?") != QMessageBox.Yes:
            return
        creds = self._creds_for(vm.get('server'))
        if not creds:
            QMessageBox.warning(self, 'Start VM', 'No credentials for host.')
            return
        self.esxi.power_on(creds['host'], creds['username'], creds['password'], vm.get('moid'))
        QTimer.singleShot(1000, self.refresh_inventory)

    def _stop_vm(self, vm):
        logging.debug(f"[ACTION] Guest shutdown requested: host={vm.get('server')} moid={vm.get('moid')} name={vm.get('name')}")
        if QMessageBox.question(self, 'Guest Shutdown', f"Shut down guest OS for '{vm.get('name','')}'?") != QMessageBox.Yes:
            return
        creds = self._creds_for(vm.get('server'))
        if not creds:
            QMessageBox.warning(self, 'Guest Shutdown', 'No credentials for host.')
            return
        ok = self.esxi.shutdown_guest(creds['host'], creds['username'], creds['password'], vm.get('moid'))
        if not ok:
            QMessageBox.warning(self, 'Guest Shutdown', 'Guest shutdown failed. Ensure VMware Tools is installed and running in the guest.')
        QTimer.singleShot(1000, self.refresh_inventory)

    def _reboot_vm(self, vm):
        logging.debug(f"[ACTION] Guest reboot requested: host={vm.get('server')} moid={vm.get('moid')} name={vm.get('name')}")
        if QMessageBox.question(self, 'Guest Restart', f"Restart guest OS for '{vm.get('name','')}'?") != QMessageBox.Yes:
            return
        creds = self._creds_for(vm.get('server'))
        if not creds:
            QMessageBox.warning(self, 'Guest Restart', 'No credentials for host.')
            return
        ok = self.esxi.reboot_guest(creds['host'], creds['username'], creds['password'], vm.get('moid'))
        if not ok:
            QMessageBox.warning(self, 'Guest Restart', 'Guest restart failed. Ensure VMware Tools is installed and running in the guest.')
        QTimer.singleShot(1500, self.refresh_inventory)

    def _creds_for(self, host):
        for s in self.cm.get_servers():
            if s.get('host') == host:
                return s
        return None

    def _apply_side_width(self):
        try:
            side_w = int(self.cm.config.get('side_panel_width', 50))
            self.side.setFixedWidth(max(32, min(50, side_w)))
            # Compute uniform button size from available side width (leave margins)
            btn_size = max(28, min(self.side.width() - 8, 46))
            font_px = max(14, int(btn_size * 0.45))
            for b in (self.btn_refresh, self.btn_gear, self.btn_diag, self.btn_debug, self.btn_exit):
                b.setFixedSize(btn_size, btn_size)
            self.btn_refresh.setStyleSheet(f'font-size: {font_px}px;')
            self.btn_gear.setStyleSheet(f'font-size: {font_px}px;')
            self.btn_diag.setStyleSheet(f'font-size: {font_px}px;')
            self.btn_exit.setStyleSheet(f'font-size: {font_px}px;')
            self._apply_debug_button_style(font_px)
            logging.debug(f"[UI] Applied side width: {self.side.width()} px; button size: {btn_size}px; font: {font_px}px")
        except Exception as e:
            logging.error(f"[UI] apply side width error: {type(e).__name__}: {e}")

    def _apply_metrics_width(self):
        try:
            mw = int(self.cm.get_layout().get('metrics_panel_width', 180))
            self.metrics_scroll.setFixedWidth(max(120, min(600, mw)))
            logging.debug(f"[UI] Applied metrics width: {self.metrics_scroll.width()} px")
        except Exception as e:
            logging.error(f"[UI] apply metrics width error: {type(e).__name__}: {e}")

    def _apply_metrics_background(self):
        try:
            grad = self.tm.metrics_gradient_css()
            # Apply on scroll area (frame) and its viewport/body to avoid white backgrounds
            self.metrics_scroll.setStyleSheet(
                f"QScrollArea {{ background: {grad}; border: none; }}"
            )
            try:
                self.metrics_scroll.viewport().setStyleSheet(f"background: {grad}; border: none;")
            except Exception:
                pass
            try:
                self.metrics_body.setStyleSheet(f"background: {grad};")
            except Exception:
                pass
        except Exception as e:
            logging.error(f"[UI] apply metrics background error: {type(e).__name__}: {e}")

    def _rebuild_metrics(self, hosts):
        try:
            while self.metrics_v.count():
                it = self.metrics_v.takeAt(0)
                w = it.widget() if it else None
                if w is not None:
                    w.setParent(None)
                    w.deleteLater()
        except Exception:
            pass
        try:
            for m in hosts:
                card = HostMetricsCard(self.tm, m)
                self.metrics_v.addWidget(card)
            self.metrics_v.addStretch(1)
        except Exception as e:
            logging.error(f"[MET] build cards error: {type(e).__name__}: {e}")

    def _save_diagnostics_bundle(self):
        try:
            path = save_diagnostics(self.cm.appdata)
            QMessageBox.information(self, 'Diagnostics', f'Diagnostics saved to:\n{path}')
            logging.debug(f"[DIAG] Saved diagnostics bundle: {path}")
        except Exception as e:
            logging.error(f"[DIAG] Save failed: {type(e).__name__}: {e}")
            QMessageBox.warning(self, 'Diagnostics', 'Failed to save diagnostics bundle — see console logs.')

    def _toggle_debug_logs(self):
        try:
            on = not get_debug_enabled()
            set_debug_enabled(on)
            self.cm.set_bool('debug_logging', bool(on))
            self._apply_debug_button_style()
        except Exception as e:
            logging.error(f"[DBG] Toggle failed: {type(e).__name__}: {e}")

    def _apply_debug_button_style(self, font_px=None):
        try:
            on = get_debug_enabled()
            bg = '#2ECC71' if on else '#E74C3C'
            fs = '' if font_px is None else f'font-size: {font_px}px;'
            self.btn_debug.setStyleSheet(f'background: {bg}; color: #FFFFFF; border: none; border-radius: 6px; {fs}')
            self.btn_debug.setToolTip('Debug: ON' if on else 'Debug: OFF')
        except Exception:
            pass

    def _exit_app(self):
        try:
            if QMessageBox.question(self, 'Exit', 'Are you sure you want to exit the program?') == QMessageBox.Yes:
                QApplication.instance().quit()
        except Exception as e:
            logging.error(f"[EXIT] Failed to quit: {type(e).__name__}: {e}")
