# Firmware – H2 Soil Sensor (ESP-IDF + esp-matter)

Xem tài liệu đầy đủ: [`../docs/06-firmware.md`](../docs/06-firmware.md).

```bash
. $IDF_PATH/export.sh && . $ESP_MATTER_PATH/export.sh
idf.py set-target esp32h2
idf.py build                                   # SIT ICD (mặc định)
# idf.py -D SDKCONFIG_DEFAULTS="sdkconfig.defaults;sdkconfig.defaults.lit" build   # LIT ICD
idf.py -p /dev/ttyACM0 flash monitor           # USB Serial/JTAG qua pad J1: D+ (8), D− (7), GND (2), pin đã lắp
```

Đã kiểm chứng build với ESP-IDF v6.0.2 + esp-matter `main` (Matter 1.5, connectedhomeip 99a81bd): 1.66 MB, còn 16 % phân vùng OTA.
Cấu hình ứng dụng: `idf.py menuconfig` → **H2 Soil Sensor** (chu kỳ đo, ngưỡng báo cáo, thời gian ổn định module, hiệu chuẩn
mặc định, bản sao Humidity Sensor, soft-start VSENS, TX power, ngưỡng pin cạn, chân GPIO).

Phần cứng v3 chỉ có một cảm biến: module độ ẩm đất điện dung “Capacitive Soil Moisture Sensor v1.2” trên J4 (AOUT → IO1).
