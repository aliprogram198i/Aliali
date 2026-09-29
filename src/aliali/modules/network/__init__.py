from aliali.core.models import ModuleInfo

NETWORK_MODULES = [
    ModuleInfo("network.asset_discovery", "🔎 Asset Discovery", "Inventory assets in an authorized scope.", "network"),
    ModuleInfo("network.device_identification", "🖥️ Device Identification", "Classify observed devices using safe evidence.", "network"),
    ModuleInfo("network.iot_camera", "📷 IoT / Camera Detection", "Identify camera-like/IoT indicators in authorized networks.", "network"),
    ModuleInfo("network.exposure", "🚨 Exposure Detection", "Report exposed services and configuration risks.", "network"),
    ModuleInfo("network.topology", "🕸️ Network Topology", "Build an evidence-based network relationship graph.", "network"),
]
