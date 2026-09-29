from aliali.ui.network import (
    network_dashboard_text,
    network_input_text,
    network_keyboard,
    network_text,
)


def test_network_keyboard_exposes_stable_actions():
    callbacks = {
        button.callback_data
        for row in network_keyboard().inline_keyboard
        for button in row
        if button.callback_data
    }

    expected = {
        "network:discover",
        "network:identity",
        "network:correlate",
        "network:geolocation",
        "network:device",
        "network:services",
        "network:iot",
        "network:exposure",
        "network:topology",
        "network:changes",
        "network:evidence",
        "network:dashboard",
        "home",
    }

    assert callbacks == expected


def test_network_text_does_not_present_real_metrics_without_data():
    assert "الأصول: —" in network_dashboard_text()
    assert "لا يتم عرض أرقام غير موجودة في البيانات." in network_dashboard_text()
    assert "تقديري" in network_text()
    assert "IP أو IPv6 أو عنوان MAC" in network_input_text()
