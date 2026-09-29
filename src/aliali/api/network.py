import ipaddress
import re
import socket
from dataclasses import dataclass


_MAC_RE = re.compile(r"^(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$")


@dataclass(frozen=True)
class NetworkTarget:
    kind: str
    value: str


def normalize_target(*, ip: str | None, mac: str | None) -> NetworkTarget:
    if bool(ip) == bool(mac):
        raise ValueError("Provide exactly one of ip or mac")

    if ip:
        try:
            address = ipaddress.ip_address(ip.strip())
        except ValueError as exc:
            raise ValueError("Invalid IP address") from exc
        return NetworkTarget("ip", str(address))

    value = mac.strip().upper().replace("-", ":")
    if not _MAC_RE.fullmatch(value):
        raise ValueError("Invalid MAC address")
    return NetworkTarget("mac", value)


def reverse_dns(ip: str) -> str | None:
    try:
        hostname, _, _ = socket.gethostbyaddr(ip)
    except (OSError, socket.herror, socket.gaierror):
        return None
    return hostname


def tcp_connectivity(ip: str, port: int, timeout_seconds: float = 2.0) -> bool:
    if not 1 <= port <= 65535:
        raise ValueError("Port must be between 1 and 65535")
    try:
        with socket.create_connection((ip, port), timeout=timeout_seconds):
            return True
    except OSError:
        return False
