# PentaVMControl

Windows-native dockable VM management bar for VMware ESXi.

## Features (Rev 13B)
- Dockable AppBar on top/left/right monitors
- ESXi 7.0.3u+ via pyVmomi
- One-click VMRC launch (vmrc:// URL)
- Servers, Layout, Theme control panel
- Persistent config at %APPDATA%\PentaStarVMBar\config.json
- Live theme system with import/export
- Diagnostics printed to stdout

## Requirements
- Windows 10/11 x64
- Python 3.10+

## Install
```powershell
py -3.10 -m venv .venv
. .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run
```powershell
python app.py
```

On first run, a default config will be created at:
```
%APPDATA%\PentaStarVMBar\config.json
```
Add your ESXi hosts in the Control Panel (gear icon) or edit the config.

## VMRC Launch
- If VMware Remote Console is installed with vmrc:// protocol registered, the app will open the URL directly.
- Optionally set `vmrc_path` in config to the full path to VMRC.exe.

## Build EXE (optional)
```powershell
pip install pyinstaller
pyinstaller --noconfirm --windowed --name PentaVMControl app.py
```

## Notes
- AppBar docking requires pywin32/ctypes. If unavailable, the app runs as a normal window.
- ESXi operations require valid host credentials. SSL verification is disabled by default for direct-host connects.
