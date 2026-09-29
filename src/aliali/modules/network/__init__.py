from aliali.core.models import ModuleInfo
NETWORK_MODULES = [
    ModuleInfo(
        "network.asset_discovery",
        "🔎 اكتشاف الأصول",
        "حصر الأصول ضمن نطاق مصرح به باستخدام إشارات IP أو MAC.",
        "network",
        metadata={"identifier_types": ["ip", "mac"]},
    ),
    ModuleInfo(
        "network.device_identification",
        "🖥️ تعريف الجهاز",
        "تصنيف الأصل اعتمادا على المورد والأدلة المرصودة.",
        "network",
        metadata={"identifier_types": ["ip", "mac"]},
    ),
    ModuleInfo(
        "network.iot_camera",
        "📷 مؤشرات IoT والكاميرات",
        "تحليل مؤشرات الأجهزة الذكية والكاميرات داخل نطاق مصرح به.",
        "network",
        metadata={"identifier_types": ["ip", "mac"]},
    ),
    ModuleInfo(
        "network.exposure",
        "🚨 التعرض الشبكي",
        "عرض الخدمات والتعرضات المرصودة دون تحويل المنفذ المفتوح تلقائيا إلى ثغرة.",
        "network",
        metadata={"identifier_types": ["ip"]},
    ),
    ModuleInfo(
        "network.topology",
        "🕸️ طوبولوجيا الشبكة",
        "بناء علاقات الشبكة من ملاحظات مصرح بها وأدلة قابلة للتتبع.",
        "network",
        metadata={"identifier_types": ["ip", "mac"]},
    ),
]
