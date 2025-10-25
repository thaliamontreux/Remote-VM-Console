import json
import os
import threading
from pathlib import Path


class ConfigManager:
    def __init__(self):
        self._lock = threading.RLock()
        self.appdata = os.path.join(os.environ.get('APPDATA', str(Path.home())), 'PentaStarVMBar')
        self.config_path = os.path.join(self.appdata, 'config.json')
        self.themes_dir = os.path.join(self.appdata, 'themes')
        self.icons_dir = os.path.join(self.appdata, 'icons')
        self._ensure_dirs()
        self.config = self._load_or_create()

    def _ensure_dirs(self):
        os.makedirs(self.appdata, exist_ok=True)
        os.makedirs(self.themes_dir, exist_ok=True)
        os.makedirs(self.icons_dir, exist_ok=True)

    def _defaults(self):
        return {
            'servers': [],
            'themes': {
                'default_dark': {
                    'name': 'Default Dark',
                    'description': 'Neutral dark with subtle gradient and green status LED.',
                    'transparent': False,
                    'bg_gradient_start': '#1E1E2A',
                    'bg_gradient_end': '#2A2A3A',
                    'cards_background': '#1B1B26',
                    'text_primary': '#FFFFFF',
                    'text_secondary': '#AAAAAA',
                    'button_bg': '#2F2F45',
                    'button_radius_px': 10,
                    'button_shadow': '#000000',
                    'cluster_header_bg': '#2A2A3A',
                    'cluster_header_text': '#FFFFFF',
                    'vm_led_on': '#4CAF50',
                    'vm_name_text': '#FFFFFF',
                    'vm_server_text': '#AAAAAA',
                    'vm_host_dot': '#888888',
                    'panel_text': '#FFFFFF',
                    'gear_button_bg': '#2F2F45',
                    'gear_button_text': '#FFFFFF',
                    'status_ok': '#4CAF50',
                    'status_warn': '#FFC107',
                    'status_err': '#F44336',
                    'cluster_header_height_px': 10,
                    'cluster_header_width_px': 200
                },
                'Tan_99': {
                    'name': 'Tan_99',
                    'description': 'Warm tan gradient with blue accents and magenta labels.',
                    'bg_gradient_start': '#60270C',
                    'bg_gradient_end': '#944D2B',
                    'transparent': False,
                    'cards_background': '#1B1B26',
                    'text_primary': '#FFFFFF',
                    'text_secondary': '#AAAAAA',
                    'button_bg': '#19518B',
                    'button_radius_px': 5,
                    'button_shadow': '#000000',
                    'cluster_header_bg': '#FFAAFF',
                    'cluster_header_text': '#B92F17',
                    'vm_host_dot': '#000000',
                    'vm_name_text': '#FFFFFF',
                    'vm_server_text': '#FF00FF',
                    'vm_led_on': '#10EE22',
                    'panel_text': '#FFFFFF',
                    'gear_button_bg': '#B0042C',
                    'gear_button_text': '#FFFFFF',
                    'status_ok': '#4CAF50',
                    'status_warn': '#FFC107',
                    'status_err': '#F44336',
                    'cluster_header_height_px': 10,
                    'cluster_header_width_px': 200
                },
                'Neon_Nights': {
                    'name': 'Neon Nights',
                    'description': 'Vibrant purple-to-blue neon glow with cyan accents.',
                    'transparent': False,
                    'bg_gradient_start': '#1F1147',
                    'bg_gradient_end': '#0D1F4A',
                    'cards_background': '#151532',
                    'text_primary': '#E6E6FF',
                    'text_secondary': '#9AA3B2',
                    'button_bg': '#1E88E5',
                    'button_radius_px': 8,
                    'button_shadow': '#000000',
                    'cluster_header_bg': '#2B2B5E',
                    'cluster_header_text': '#E6E6FF',
                    'vm_led_on': '#00E5FF',
                    'vm_name_text': '#FFFFFF',
                    'vm_server_text': '#B3C1D1',
                    'vm_host_dot': '#00E5FF',
                    'panel_text': '#E6E6FF',
                    'gear_button_bg': '#2B2B5E',
                    'gear_button_text': '#E6E6FF',
                    'status_ok': '#00E676',
                    'status_warn': '#FFD54F',
                    'status_err': '#FF5252',
                    'cluster_header_height_px': 10,
                    'cluster_header_width_px': 200
                },
                'Oceanic': {
                    'name': 'Oceanic',
                    'description': 'Cool teal-to-navy ocean palette with crisp white text.',
                    'transparent': False,
                    'bg_gradient_start': '#013A63',
                    'bg_gradient_end': '#011E3C',
                    'cards_background': '#0A2A43',
                    'text_primary': '#E0F7FA',
                    'text_secondary': '#A7C8D1',
                    'button_bg': '#0277BD',
                    'button_radius_px': 10,
                    'button_shadow': '#000000',
                    'cluster_header_bg': '#014F86',
                    'cluster_header_text': '#E0F7FA',
                    'vm_led_on': '#00BFA5',
                    'vm_name_text': '#FFFFFF',
                    'vm_server_text': '#B2EBF2',
                    'vm_host_dot': '#00BFA5',
                    'panel_text': '#E0F7FA',
                    'gear_button_bg': '#014F86',
                    'gear_button_text': '#E0F7FA',
                    'status_ok': '#26A69A',
                    'status_warn': '#FFD54F',
                    'status_err': '#EF5350',
                    'cluster_header_height_px': 10,
                    'cluster_header_width_px': 200
                },
                'Solar_Flare': {
                    'name': 'Solar Flare',
                    'description': 'Radiant orange-to-crimson gradient with bold accents.',
                    'transparent': False,
                    'bg_gradient_start': '#FF8C00',
                    'bg_gradient_end': '#B71C1C',
                    'cards_background': '#3A1E1E',
                    'text_primary': '#FFF3E0',
                    'text_secondary': '#FFCCBC',
                    'button_bg': '#D84315',
                    'button_radius_px': 8,
                    'button_shadow': '#000000',
                    'cluster_header_bg': '#6D2323',
                    'cluster_header_text': '#FFE0B2',
                    'vm_led_on': '#FFCA28',
                    'vm_name_text': '#FFFFFF',
                    'vm_server_text': '#FFE0B2',
                    'vm_host_dot': '#FFCA28',
                    'panel_text': '#FFE0B2',
                    'gear_button_bg': '#6D2323',
                    'gear_button_text': '#FFE0B2',
                    'status_ok': '#81C784',
                    'status_warn': '#FFB74D',
                    'status_err': '#E57373',
                    'cluster_header_height_px': 10,
                    'cluster_header_width_px': 200
                },
                'Forest_Mist': {
                    'name': 'Forest Mist',
                    'description': 'Lush green gradient with misty overlays and soft whites.',
                    'transparent': False,
                    'bg_gradient_start': '#1B5E20',
                    'bg_gradient_end': '#0D3B14',
                    'cards_background': '#102918',
                    'text_primary': '#E8F5E9',
                    'text_secondary': '#B7D7B7',
                    'button_bg': '#2E7D32',
                    'button_radius_px': 10,
                    'button_shadow': '#000000',
                    'cluster_header_bg': '#1B5E20',
                    'cluster_header_text': '#E8F5E9',
                    'vm_led_on': '#A5D6A7',
                    'vm_name_text': '#FFFFFF',
                    'vm_server_text': '#C8E6C9',
                    'vm_host_dot': '#A5D6A7',
                    'panel_text': '#E8F5E9',
                    'gear_button_bg': '#1B5E20',
                    'gear_button_text': '#E8F5E9',
                    'status_ok': '#81C784',
                    'status_warn': '#FFD54F',
                    'status_err': '#E57373',
                    'cluster_header_height_px': 10,
                    'cluster_header_width_px': 200
                },
                'Midnight_Purple': {
                    'name': 'Midnight Purple',
                    'description': 'Deep purple gradient with fuchsia highlights and silver text.',
                    'transparent': False,
                    'bg_gradient_start': '#2D0A31',
                    'bg_gradient_end': '#1B0033',
                    'cards_background': '#1A0820',
                    'text_primary': '#F3E5F5',
                    'text_secondary': '#C5B3CC',
                    'button_bg': '#6A1B9A',
                    'button_radius_px': 12,
                    'button_shadow': '#000000',
                    'cluster_header_bg': '#4A115A',
                    'cluster_header_text': '#F3E5F5',
                    'vm_led_on': '#EC407A',
                    'vm_name_text': '#FFFFFF',
                    'vm_server_text': '#E1BEE7',
                    'vm_host_dot': '#EC407A',
                    'panel_text': '#F3E5F5',
                    'gear_button_bg': '#4A115A',
                    'gear_button_text': '#F3E5F5',
                    'status_ok': '#66BB6A',
                    'status_warn': '#FFCA28',
                    'status_err': '#EF5350',
                    'cluster_header_height_px': 10,
                    'cluster_header_width_px': 200
                },
                'Carbon_Red': {
                    'name': 'Carbon Red',
                    'description': 'Carbon fiber dark with red accents and bold highlights.',
                    'transparent': False,
                    'bg_gradient_start': '#202124',
                    'bg_gradient_end': '#111213',
                    'cards_background': '#1A1B1E',
                    'text_primary': '#ECEFF1',
                    'text_secondary': '#B0BEC5',
                    'button_bg': '#C62828',
                    'button_radius_px': 6,
                    'button_shadow': '#000000',
                    'cluster_header_bg': '#2B2C2F',
                    'cluster_header_text': '#ECEFF1',
                    'vm_led_on': '#FF5252',
                    'vm_name_text': '#FFFFFF',
                    'vm_server_text': '#CFD8DC',
                    'vm_host_dot': '#FF5252',
                    'panel_text': '#ECEFF1',
                    'gear_button_bg': '#2B2C2F',
                    'gear_button_text': '#ECEFF1',
                    'status_ok': '#66BB6A',
                    'status_warn': '#FFA726',
                    'status_err': '#EF5350',
                    'cluster_header_height_px': 10,
                    'cluster_header_width_px': 200
                }
            },
            'active_theme': 'default_dark',
            'cluster_header_height_px': 10,
            'cluster_header_width_px': 200,
            'dock_position': 'top',
            'monitor_index': 0,
            'auto_refresh_on_hover': False,
            'show_running_only': True,
            'debug_logging': True,
            'button_width': 160,
            'button_height': 48,
            'vmrc_path': '',
            'disable_appbar': False,
            'skip_inventory_on_startup': False,
            'side_panel_width': 50,
            'metrics_panel_width': 180
        }

    def _load_or_create(self):
        if not os.path.exists(self.config_path):
            cfg = self._defaults()
            self._save(cfg)
            return cfg
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
        except Exception:
            cfg = self._defaults()
        d = self._defaults()
        for k, v in d.items():
            if k not in cfg:
                cfg[k] = v
        if 'themes' in d:
            for name, theme in d['themes'].items():
                if name not in cfg['themes']:
                    cfg['themes'][name] = theme
        self._save(cfg)
        return cfg

    def _save(self, cfg=None):
        with self._lock:
            data = cfg if cfg is not None else self.config
            tmp = self.config_path + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, self.config_path)

    def save(self):
        self._save()

    def get_servers(self):
        return list(self.config.get('servers', []))

    def set_servers(self, servers):
        self.config['servers'] = servers
        self._save()

    def get_active_theme_name(self):
        return self.config.get('active_theme', 'default_dark')

    def get_theme(self, name=None):
        name = name or self.get_active_theme_name()
        themes = self.config.get('themes', {})
        t = themes.get(name)
        if not t:
            t = list(themes.values())[0] if themes else self._defaults()['themes']['default_dark']
        return t

    def set_theme(self, name, data):
        self.config.setdefault('themes', {})[name] = data
        self._save()

    def set_active_theme(self, name):
        self.config['active_theme'] = name
        self._save()

    def import_theme(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            name = data.get('name') or Path(path).stem
            data.setdefault('name', name)
            data.setdefault('description', '')
            self.set_theme(name, data)
            return name
        except Exception:
            return None

    def export_theme(self, name, path):
        data = self.get_theme(name)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def get_layout(self):
        return {
            'button_width': self.config.get('button_width', 160),
            'button_height': self.config.get('button_height', 48),
            'cluster_header_height_px': self.config.get('cluster_header_height_px', 10),
            'cluster_header_width_px': self.config.get('cluster_header_width_px', 200),
            'dock_position': self.config.get('dock_position', 'top'),
            'monitor_index': self.config.get('monitor_index', 0),
            'metrics_panel_width': self.config.get('metrics_panel_width', 200)
        }

    def set_layout(self, layout):
        self.config.update({
            'button_width': layout.get('button_width', 160),
            'button_height': layout.get('button_height', 48),
            'cluster_header_height_px': layout.get('cluster_header_height_px', 10),
            'cluster_header_width_px': layout.get('cluster_header_width_px', 200),
            'dock_position': layout.get('dock_position', 'top'),
            'monitor_index': layout.get('monitor_index', 0),
            'side_panel_width': layout.get('side_panel_width', self.config.get('side_panel_width', 50)),
            'metrics_panel_width': layout.get('metrics_panel_width', self.config.get('metrics_panel_width', 200))
        })
        self._save()

    def set_docking(self, dock_position, monitor_index):
        self.config['dock_position'] = dock_position
        self.config['monitor_index'] = monitor_index
        self._save()

    def get_bool(self, key, default=False):
        return bool(self.config.get(key, default))

    def set_bool(self, key, value):
        self.config[key] = bool(value)
        self._save()

    def get_vmrc_path(self):
        return self.config.get('vmrc_path', '')

    def set_vmrc_path(self, path):
        self.config['vmrc_path'] = path
        self._save()
