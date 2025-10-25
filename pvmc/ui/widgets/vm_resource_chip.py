from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QHBoxLayout, QVBoxLayout


class VMResourceChip(QFrame):
    def __init__(self, theme, vm, parent=None):
        super().__init__(parent)
        self.setObjectName('vmreschip')
        self.theme = theme
        self.vm = vm
        t = self.theme.active_theme()
        txt = t.get('panel_text', '#FFFFFF')
        self.setStyleSheet(f"QFrame#vmreschip {{ background: transparent; }} QLabel {{ color: {txt}; font-size: 10px; }}")
        name = vm.get('name', '')
        res = vm.get('res') or {}
        cpu = res.get('cpu_mhz', 0)
        mem = res.get('mem_mb', 0)
        disk = res.get('disk_gb', 0.0)
        self.lbl_name = QLabel(name)
        self.lbl_cpu = QLabel(f"CPU {cpu} MHz")
        self.lbl_mem = QLabel(f"MEM {mem} MB")
        self.lbl_disk = QLabel(f"DISK {disk} GB")
        # Compact layout
        h = QHBoxLayout(self)
        h.setContentsMargins(6, 4, 6, 4)
        h.setSpacing(8)
        h.addWidget(self.lbl_name, 0, Qt.AlignVCenter)
        h.addWidget(self.lbl_cpu, 0, Qt.AlignVCenter)
        h.addWidget(self.lbl_mem, 0, Qt.AlignVCenter)
        h.addWidget(self.lbl_disk, 0, Qt.AlignVCenter)

    def updateTheme(self):
        t = self.theme.active_theme()
        txt = t.get('panel_text', '#FFFFFF')
        self.setStyleSheet(f"QFrame#vmreschip {{ background: transparent; }} QLabel {{ color: {txt}; font-size: 10px; }}")
