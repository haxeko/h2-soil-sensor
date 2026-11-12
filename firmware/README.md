# Firmware – H2 Soil Sensor (ESP-IDF + esp-matter)

Xem tài liệu đầy đủ: [`../docs/06-firmware.md`](../docs/06-firmware.md).

```bash
. $IDF_PATH/export.sh && . $ESP_MATTER_PATH/export.sh
idf.py set-target esp32h2
idf.py build                                   # SIT ICD (mặc định)
# idf.py -D SDKCONFIG_DEFAULTS="sdkconfig.defaults;sdkconfig.defaults.lit" build   # LIT ICD
idf.py -p /dev/ttyACM0 flash monitor
```

Đã kiểm chứng build với ESP-IDF v6.0.2 + esp-matter `main` (Matter 1.5, connectedhomeip 99a81bd): 1.68 MB, còn 14 % phân vùng OTA.
Cấu hình ứng dụng: `idf.py menuconfig` → **H2 Soil Sensor** (chu kỳ đo, ngưỡng báo cáo, thời gian ổn định module đất,
hiệu chuẩn mặc định, module I²C: tự nhận / SHT4x / SHT3x / AHT20 / không, NTC R25/B, soft-start VSENS, TX power, ngưỡng pin cạn,
chân GPIO).

Phần cứng v2 dùng module cảm biến mua sẵn: module độ ẩm đất điện dung (J4, AOUT → IO1), module nhiệt/ẩm không khí I²C
(J6, IO12/IO22), đầu dò NTC 10k (J7, IO3). Cắm module trước khi lắp pin – endpoint chỉ được tạo cho cảm biến có mặt lúc khởi động.
