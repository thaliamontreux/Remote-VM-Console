import logging
import os
import ssl
import subprocess
import traceback
from urllib.parse import quote
import hashlib
import platform
try:
    import winreg  # type: ignore
except Exception:
    winreg = None

try:
    from pyVim.connect import SmartConnect, Disconnect
    from pyVmomi import vim
except Exception:
    SmartConnect = None
    Disconnect = None
    vim = None


class ESXiClient:
    def __init__(self, show_running_only=True):
        self.show_running_only = show_running_only

    def fetch_inventory(self, servers):
        vms = []
        logging.info('[INV] refresh_inventory() start')
        if not SmartConnect or not vim:
            logging.info('[INV] pyVmomi not available')
            return vms
        for s in servers:
            host = s.get('host')
            user = s.get('username')
            pwd = s.get('password')
            try:
                logging.info(f'[INV] Connecting to {host} ...')
                ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                si = SmartConnect(host=host, user=user, pwd=pwd, sslContext=ctx)
                content = si.RetrieveContent()
                view = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
                seen = []
                for vm in view.view:
                    try:
                        state = str(vm.runtime.powerState)
                        if self.show_running_only and state.lower() != 'poweredon':
                            continue
                        name = vm.name
                        uuid = getattr(vm.config, 'uuid', '') if getattr(vm, 'config', None) else ''
                        mid = getattr(vm, '_moId', None)
                        if not mid and hasattr(vm, '_GetMoId'):
                            try:
                                mid = vm._GetMoId()
                            except Exception:
                                mid = None
                        # Gather lightweight resource metrics from summary/quickStats
                        cpu_mhz = None
                        mem_mb = None
                        disk_gb = None
                        try:
                            summary = getattr(vm, 'summary', None)
                            if summary is not None:
                                qs = getattr(summary, 'quickStats', None)
                                if qs is not None:
                                    cpu_mhz = getattr(qs, 'overallCpuUsage', None)
                                    # Prefer guestMemoryUsage (MB); fallback to hostMemoryUsage
                                    mem_mb = getattr(qs, 'guestMemoryUsage', None)
                                    if mem_mb in (None, 0):
                                        mem_mb = getattr(qs, 'hostMemoryUsage', None)
                                storage = getattr(summary, 'storage', None)
                                if storage is not None:
                                    committed = getattr(storage, 'committed', None)
                                    if committed is not None:
                                        try:
                                            disk_gb = round(float(committed) / (1024**3), 2)
                                        except Exception:
                                            disk_gb = None
                        except Exception as e:
                            logging.info(f'[INV] metrics parse error: {e}')
                            traceback.print_exc()
                        server_label = s.get('name') or host
                        server_color = s.get('color') or None
                        v = {
                            'server': host,
                            'server_label': server_label,
                            'server_color': server_color,
                            'name': name,
                            'uuid': uuid,
                            'moid': mid,
                            'power_state': state,
                            'res': {
                                'cpu_mhz': cpu_mhz if cpu_mhz is not None else 0,
                                'mem_mb': mem_mb if mem_mb is not None else 0,
                                'disk_gb': disk_gb if disk_gb is not None else 0.0
                            }
                        }
                        seen.append(v)
                    except Exception as e:
                        logging.info(f'[INV] vm parse error: {e}')
                        traceback.print_exc()
                vms.extend(seen)
                view.Destroy()
                Disconnect(si)
                logging.info(f'[INV] {host}: {len(seen)} VM(s) retrieved successfully.')
            except Exception as e:
                logging.info(f'[INV] error {host}: {e}')
                traceback.print_exc()
        logging.info('[INV] All servers processed. Now rebuilding UI elements.')
        return vms

    @staticmethod
    def build_vmrc_url_mks(ra_host: str, websocket: str, mksticket: str, thumbprint: str | None, vmx_path: str) -> str:
        """Build MKS VMRC URL as specified by VMRC: vmrc://<host>/?websocket=...&mksticket=...&thumbprint=...&path=<vmx>"""
        base = f"vmrc://{ra_host}/?websocket={quote(websocket)}&mksticket={quote(mksticket)}"
        if thumbprint:
            base += f"&thumbprint={quote(thumbprint)}"
        base += f"&path={quote(vmx_path)}"
        return base

    def launch_vmrc(self, host, moid, vmrc_path='', creds=None):
        """Follow user's requested flow: AcquireCloneTicket and authority URL.
        Steps:
          1) Connect with pyVmomi
          2) ticket = si.content.sessionManager.AcquireCloneTicket()
          3) vmrc_url = f"vmrc://clone:{ticket}@{host}/?moid={vm_moid}"
          4) Launch VMRC via registry handler or vmrc_path
        """
        if not creds or not SmartConnect:
            logging.error('[VMRC] Missing credentials or pyVmomi not available; cannot acquire clone ticket')
            return False
        username = creds.get('username')
        password = creds.get('password')
        # Ensure we have a valid moid string (try to refresh)
        try:
            moid = self.lookup_vm_moid(host, username or '', password or '', moid)
        except Exception:
            pass
        ticket = None
        try:
            logging.info(f"[VMRC] Connecting to {host} to acquire clone ticket ...")
            ctx = ssl._create_unverified_context()
            si = SmartConnect(host=host, user=username, pwd=password, sslContext=ctx)
            try:
                sm = si.RetrieveContent().sessionManager
                ticket = sm.AcquireCloneTicket()
                logging.info(f"[VMRC] Clone ticket: {ticket}")
            finally:
                try:
                    Disconnect(si)
                except Exception:
                    pass
        except Exception as e:
            logging.error(f"[VMRC] Failed to acquire clone ticket: {e}")
            traceback.print_exc()
            return False

        if not ticket:
            logging.error('[VMRC] Empty clone ticket; aborting')
            return False

        # Build URL per user's instruction (authority form with moid)
        url_to_launch = f"vmrc://clone:{ticket}@{host}/?moid={moid}"
        alt_url = f"vmware-vmrc://clone:{ticket}@{host}/?moid={moid}"
        logging.info(f"[VMRC] Authority URL: {url_to_launch}")
        logging.info(f"[VMRC] Alt URL:       {alt_url}")

        # Launch
        if vmrc_path:
            try:
                subprocess.Popen([vmrc_path, url_to_launch])
                return True
            except Exception:
                pass
        # Try registry protocol handlers
        if self._launch_via_registry(url_to_launch):
            return True
        # Try alt scheme
        if self._launch_via_registry(alt_url):
            return True
        # Fallbacks
        try:
            os.startfile(url_to_launch)
            return True
        except Exception:
            try:
                subprocess.Popen(['cmd', '/c', 'start', '', url_to_launch], shell=True)
                return True
            except Exception:
                return False

    def _launch_via_registry(self, url: str) -> bool:
        if platform.system() != 'Windows' or winreg is None:
            return False
        keys = [r'vmrc\shell\open\command', r'vmware-vmrc\shell\open\command']
        try:
            for subkey in keys:
                try:
                    with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, subkey) as k:
                        cmd, _ = winreg.QueryValueEx(k, None)
                        if not cmd:
                            continue
                        # Replace placeholder and run via shell to honor quoting
                        cmdline = cmd.replace('%1', url).replace('%L', url)
                        logging.info(f"[VMRC] Launch via registry: {cmdline}")
                        subprocess.Popen(cmdline, shell=True)
                        return True
                except Exception:
                    continue
        except Exception as e:
            logging.error(f"[VMRC] Registry launch failed: {e}")
        return False

    @staticmethod
    def get_host_thumbprint(host: str, port: int = 443) -> str:
        """Retrieve ESXi server certificate and compute SHA1 fingerprint in AA:BB:.. format."""
        pem = ssl.get_server_certificate((host, port))
        der = ssl.PEM_cert_to_DER_cert(pem)
        sha1 = hashlib.sha1(der).hexdigest().upper()
        return ':'.join(sha1[i:i+2] for i in range(0, len(sha1), 2))

    def lookup_vm_moid(self, host: str, username: str, password: str, moid_hint: str | None):
        """Fetch latest moid string from ESXi host; prefer exact moRef id if present, otherwise fallback to original hint."""
        if not SmartConnect:
            return moid_hint
        try:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            si = SmartConnect(host=host, user=username, pwd=password, sslContext=ctx)
            try:
                content = si.RetrieveContent()
                view = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
                for vm in view.view:
                    mid = getattr(vm, '_moId', None)
                    if not mid and hasattr(vm, '_GetMoId'):
                        try:
                            mid = vm._GetMoId()
                        except Exception:
                            mid = None
                    if mid and (str(mid) == str(moid_hint) or str(mid).endswith(str(moid_hint))):
                        return str(mid)
                return moid_hint
            finally:
                try:
                    Disconnect(si)
                except Exception:
                    pass
        except Exception:
            return moid_hint

    def shutdown_guest(self, server, username, password, moid) -> bool:
        if not SmartConnect or not vim:
            return False
        try:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            si = SmartConnect(host=server, user=username, pwd=password, sslContext=ctx)
            content = si.RetrieveContent()
            view = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
            target = None
            for vm in view.view:
                mid = getattr(vm, '_moId', None)
                if not mid and hasattr(vm, '_GetMoId'):
                    try:
                        mid = vm._GetMoId()
                    except Exception:
                        mid = None
                if str(mid) == str(moid):
                    target = vm
                    break
            ok = False
            if target:
                try:
                    logging.info(f"[GUEST] ShutdownGuest for moid={moid}")
                    target.ShutdownGuest()
                    ok = True
                except Exception as e:
                    logging.warning(f"[GUEST] ShutdownGuest failed: {type(e).__name__}: {e}")
            view.Destroy()
            Disconnect(si)
            return ok
        except Exception as e:
            logging.error(f"[GUEST] shutdown_guest error: {type(e).__name__}: {e}")
            traceback.print_exc()
            return False

    def reboot_guest(self, server, username, password, moid) -> bool:
        if not SmartConnect or not vim:
            return False
        try:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            si = SmartConnect(host=server, user=username, pwd=password, sslContext=ctx)
            content = si.RetrieveContent()
            view = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
            target = None
            for vm in view.view:
                mid = getattr(vm, '_moId', None)
                if not mid and hasattr(vm, '_GetMoId'):
                    try:
                        mid = vm._GetMoId()
                    except Exception:
                        mid = None
                if str(mid) == str(moid):
                    target = vm
                    break
            ok = False
            if target:
                try:
                    logging.info(f"[GUEST] RebootGuest for moid={moid}")
                    target.RebootGuest()
                    ok = True
                except Exception as e:
                    logging.warning(f"[GUEST] RebootGuest failed: {type(e).__name__}: {e}")
            view.Destroy()
            Disconnect(si)
            return ok
        except Exception as e:
            logging.error(f"[GUEST] reboot_guest error: {type(e).__name__}: {e}")
            traceback.print_exc()
            return False

    def fetch_hosts_metrics(self, servers):
        metrics = []
        if not SmartConnect or not vim:
            return metrics
        for s in servers:
            host = s.get('host')
            user = s.get('username')
            pwd = s.get('password')
            label = s.get('name') or host
            color = s.get('color') or None
            try:
                ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                si = SmartConnect(host=host, user=user, pwd=pwd, sslContext=ctx)
                content = si.RetrieveContent()
                # HostSystem view
                hv = content.viewManager.CreateContainerView(content.rootFolder, [vim.HostSystem], True)
                cpu_pct = None
                mem_pct = None
                disk_free_pct = None
                vms_on = 0
                vms_off = 0
                target_host_id = None
                try:
                    for hs in hv.view:
                        try:
                            summ = getattr(hs, 'summary', None)
                            if summ is None:
                                continue
                            try:
                                target_host_id = getattr(hs, '_moId', None)
                            except Exception:
                                target_host_id = None
                            hw = getattr(summ, 'hardware', None)
                            qs = getattr(summ, 'quickStats', None)
                            # CPU
                            if hw is not None and qs is not None:
                                mhz_per_core = getattr(hw, 'cpuMhz', None)
                                cores = getattr(hw, 'numCpuCores', None)
                                used_mhz = getattr(qs, 'overallCpuUsage', None)
                                if mhz_per_core and cores and used_mhz is not None and mhz_per_core > 0:
                                    cap_mhz = float(mhz_per_core) * float(cores)
                                    cpu_pct = max(0.0, min(100.0, (float(used_mhz) / cap_mhz) * 100.0))
                            # Memory
                            total_mem_b = getattr(hw, 'memorySize', None) if hw is not None else None
                            used_mem_mb = getattr(qs, 'overallMemoryUsage', None) if qs is not None else None
                            if total_mem_b and used_mem_mb is not None and total_mem_b > 0:
                                total_mem_mb = float(total_mem_b) / (1024.0 * 1024.0)
                                mem_pct = max(0.0, min(100.0, (float(used_mem_mb) / total_mem_mb) * 100.0))
                            break
                        except Exception:
                            continue
                finally:
                    try:
                        hv.Destroy()
                    except Exception:
                        pass
                # Count VMs powered on/off (filter to this host if possible)
                vv = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
                try:
                    for vm in vv.view:
                        try:
                            rt = getattr(vm, 'runtime', None)
                            if rt is None:
                                continue
                            if target_host_id is not None:
                                try:
                                    hmor = getattr(rt, 'host', None)
                                    vm_host_id = getattr(hmor, '_moId', None)
                                    if vm_host_id and vm_host_id != target_host_id:
                                        continue
                                except Exception:
                                    pass
                            pwr = getattr(rt, 'powerState', None)
                            if str(pwr).lower() == 'poweredon':
                                vms_on += 1
                            elif str(pwr).lower() == 'poweredoff':
                                vms_off += 1
                        except Exception:
                            continue
                finally:
                    try:
                        vv.Destroy()
                    except Exception:
                        pass
                # Datastore free % across all datastores
                dv = content.viewManager.CreateContainerView(content.rootFolder, [vim.Datastore], True)
                try:
                    total_capacity = 0
                    total_free = 0
                    for ds in dv.view:
                        try:
                            summ = getattr(ds, 'summary', None)
                            if summ is None:
                                continue
                            cap = getattr(summ, 'capacity', None)
                            free = getattr(summ, 'freeSpace', None)
                            if cap and free is not None:
                                total_capacity += int(cap)
                                total_free += int(free)
                        except Exception:
                            continue
                    if total_capacity > 0:
                        disk_free_pct = max(0.0, min(100.0, (float(total_free) / float(total_capacity)) * 100.0))
                finally:
                    try:
                        dv.Destroy()
                    except Exception:
                        pass
                Disconnect(si)
                metrics.append({
                    'host': host,
                    'label': label,
                    'color': color,
                    'cpu_pct': round(cpu_pct if cpu_pct is not None else 0.0, 2),
                    'mem_pct': round(mem_pct if mem_pct is not None else 0.0, 2),
                    'disk_free_pct': round(disk_free_pct if disk_free_pct is not None else 0.0, 2),
                    'vms_on': int(vms_on),
                    'vms_off': int(vms_off)
                })
            except Exception as e:
                logging.info(f'[MET] error {host}: {e}')
                traceback.print_exc()
        return metrics

    def power_on(self, server, username, password, moid):
        if not SmartConnect or not vim:
            return False
        try:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            si = SmartConnect(host=server, user=username, pwd=password, sslContext=ctx)
            content = si.RetrieveContent()
            view = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
            target = None
            for vm in view.view:
                mid = getattr(vm, '_moId', None)
                if not mid and hasattr(vm, '_GetMoId'):
                    try:
                        mid = vm._GetMoId()
                    except Exception:
                        mid = None
                if str(mid) == str(moid):
                    target = vm
                    break
            if target:
                try:
                    target.PowerOnVM_Task()
                except Exception:
                    traceback.print_exc()
            view.Destroy()
            Disconnect(si)
            return target is not None
        except Exception:
            traceback.print_exc()
            return False

    def power_off(self, server, username, password, moid):
        if not SmartConnect or not vim:
            return False
        try:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            si = SmartConnect(host=server, user=username, pwd=password, sslContext=ctx)
            content = si.RetrieveContent()
            view = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
            target = None
            for vm in view.view:
                mid = getattr(vm, '_moId', None)
                if not mid and hasattr(vm, '_GetMoId'):
                    try:
                        mid = vm._GetMoId()
                    except Exception:
                        mid = None
                if str(mid) == str(moid):
                    target = vm
                    break
            if target:
                try:
                    target.PowerOffVM_Task()
                except Exception:
                    traceback.print_exc()
            view.Destroy()
            Disconnect(si)
            return target is not None
        except Exception:
            traceback.print_exc()
            return False
