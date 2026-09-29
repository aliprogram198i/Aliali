import ipaddress
import re
from dataclasses import dataclass
from enum import StrEnum


class NetworkIdentifierType(StrEnum):
    IP = "ip"
    MAC = "mac"


@dataclass(frozen=True)
class NetworkIdentifier:
    value: str
    identifier_type: NetworkIdentifierType

    @classmethod
    def parse(cls, value: str) -> "NetworkIdentifier":
        raw = value.strip()
        if not raw:
            raise ValueError("network identifier cannot be empty")

        try:
            ip = ipaddress.ip_address(raw)
        except ValueError:
            ip = None

        if ip is not None:
            return cls(str(ip), NetworkIdentifierType.IP)

        normalized = raw.replace("-", ":").lower()
        if re.fullmatch(r"(?:[0-9a-f]{2}:){5}[0-9a-f]{2}", normalized):
            return cls(normalized, NetworkIdentifierType.MAC)

        raise ValueError("unsupported network identifier; expected IPv4, IPv6, or MAC address")


@dataclass(frozen=True)
class AssetIdentity:
    ip: str | None = None
    mac: str | None = None
    hostname: str | None = None
    vendor: str | None = None

    def __post_init__(self) -> None:
        if self.ip is not None:
            normalized_ip = str(ipaddress.ip_address(self.ip.strip()))
            object.__setattr__(self, "ip", normalized_ip)

        if self.mac is not None:
            normalized_mac = self.mac.strip().replace("-", ":").lower()
            if not re.fullmatch(r"(?:[0-9a-f]{2}:){5}[0-9a-f]{2}", normalized_mac):
                raise ValueError("invalid MAC address")
            object.__setattr__(self, "mac", normalized_mac)

        if self.ip is None and self.mac is None:
            raise ValueError("asset identity requires an IP address or MAC address")
