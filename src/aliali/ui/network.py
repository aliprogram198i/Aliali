from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def network_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("اكتشاف الأصول", callback_data="network:discover")],
        [InlineKeyboardButton("هوية الأصل", callback_data="network:identity")],
        [InlineKeyboardButton("ربط IP و MAC", callback_data="network:correlate")],
        [InlineKeyboardButton("الموقع الشبكي", callback_data="network:geolocation")],
        [InlineKeyboardButton("المورد ونوع الجهاز", callback_data="network:device")],
        [InlineKeyboardButton("الخدمات والبروتوكولات", callback_data="network:services")],
        [InlineKeyboardButton("مؤشرات أجهزة IoT", callback_data="network:iot")],
        [InlineKeyboardButton("التعرض الشبكي", callback_data="network:exposure")],
        [InlineKeyboardButton("طوبولوجيا الشبكة", callback_data="network:topology")],
        [InlineKeyboardButton("تغييرات الأصول", callback_data="network:changes")],
        [InlineKeyboardButton("الأدلة", callback_data="network:evidence")],
        [InlineKeyboardButton("لوحة ذكاء الشبكة", callback_data="network:dashboard")],
        [InlineKeyboardButton("الرئيسية", callback_data="home")],
    ])


def network_text() -> str:
    return (
        "أمن الشبكة — Network Asset Intelligence\n\n"
        "محرك موحد لبناء صورة الأصل الشبكي من العنوان والشبكة "
        "والخدمات والموقع والأدلة والتاريخ.\n\n"
        "العمليات النشطة تتطلب نطاقا مصرحا به.\n"
        "الموقع الجغرافي المعتمد على العنوان تقديري."
    )


def network_input_text() -> str:
    return (
        "مدخل الأصل الشبكي\n\n"
        "أرسل عنوان IP أو IPv6 أو عنوان MAC.\n"
        "مثال IP: 192.168.1.10\n"
        "مثال MAC: AA:BB:CC:DD:EE:FF\n\n"
        "سيتم التعامل مع القيمة كإشارة هوية فقط إلى أن تتوفر أدلة أخرى."
    )


def network_dashboard_text() -> str:
    return (
        "لوحة ذكاء الشبكة\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "الأصول: —\n"
        "النشطة: —\n"
        "الجديدة: —\n"
        "المتغيرة: —\n"
        "مؤشرات IoT: —\n"
        "عناصر تحتاج مراجعة: —\n\n"
        "جودة الهوية\n"
        "عالية: — | متوسطة: — | منخفضة: —\n\n"
        "الموقع الشبكي\n"
        "الدول: — | ASN: — | مزودو الخدمة: —\n\n"
        "لا يتم عرض أرقام غير موجودة في البيانات."
    )
