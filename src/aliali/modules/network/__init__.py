from aliali.core.models import ModuleInfo

NETWORK_MODULES = [
    ModuleInfo(
        "network.asset_discovery",
        "🔎 Asset Discovery",
        "Inventory assets in an authorized scope using IP or MAC identifiers.",
        "network",
        metadata={"identifier_types": ["ip", "mac"]},
    ),
    ModuleInfo(
        "network.device_identification",
        "🖥️ Device Identification",
        "Classify observed devices using vendor and other safe evidence.",
        "network",
        metadata={"identifier_types": ["ip", "mac"]},
    ),
    ModuleInfo(
        "network.iot_camera",
        "📷 IoT / Camera Detection",
        "Identify camera-like/IoT indicators in authorized networks.",
        "network",
        metadata={"identifier_types": ["ip", "mac"]},
    ),
    ModuleInfo(
        "network.exposure",
        "🚨 Exposure Detection",
        "Report exposed services and configuration risks in authorized scopes.",
        "network",
        metadata={"identifier_types": ["ip"]},
    ),
    ModuleInfo(
        "network.topology",
        "🕸️ Network Topology",
        "Build an evidence-based network relationship graph from authorized observations.",
        "network",
        metadata={"identifier_types": ["ip", "mac"]},
    ),
]
