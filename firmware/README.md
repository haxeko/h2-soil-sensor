# Firmware – H2 Soil Sensor (ESP-IDF + esp-matter)

Xem tài liệu đầy đủ: [`../docs/06-firmware.md`](../docs/06-firmware.md).

```bash
. $IDF_PATH/export.sh && . $ESP_MATTER_PATH/export.sh
idf.py set-target esp32h2
idf.py build                                   # SIT ICD (mặc định)
# idf.py -D SDKCONFIG_DEFAULTS="sdkconfig.defaults;sdkconfig.defaults.lit" build   # LIT ICD
idf.py -p /dev/ttyACM0 flash monitor
```

Đã kiểm chứng build với ESP-IDF v6.0.2 + esp-matter `main` (Matter 1.5, connectedhomeip 99a81bd).
Cấu hình ứng dụng: `idf.py menuconfig` → **H2 Soil Sensor** (chu kỳ đo, ngưỡng báo cáo, hiệu chuẩn mặc định, chân GPIO,
SHT40/NTC, nguồn kích thích đầu dò, TX power, ngưỡng pin cạn).
