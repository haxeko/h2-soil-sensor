# 6. Firmware (ESP-IDF + esp-matter)

Đã build thành công với **ESP-IDF v6.0.2 + esp-matter `main` (11/2026, connectedhomeip `99a81bd`, Matter 1.5)**,
target `esp32h2`: `h2_soil_sensor.bin` = 1.68 MB, còn trống 14 % phân vùng OTA 1.875 MB. Không có cảnh báo trong mã ứng dụng.

## 6.1 Cấu trúc project

```
firmware/
├── CMakeLists.txt              # project, kéo esp-matter + connectedhomeip components
├── partitions.csv              # 4 MB: nvs, 2 × OTA 1.875 MB, fctry, esp_secure_cert
├── sdkconfig.defaults          # ESP32-H2, Thread MTD, BLE commissioning, PM/light-sleep, ICD SIT
├── sdkconfig.defaults.lit      # tuỳ chọn: LIT ICD (slow-poll 60 s, Check-In)
├── sdkconfig.defaults.xtal32k  # tuỳ chọn: khi lắp thạch anh 32.768 kHz (Y1)
└── main/
    ├── Kconfig.projbuild       # chu kỳ đo, ngưỡng báo cáo, hiệu chuẩn mặc định, chân GPIO, TX power…
    ├── idf_component.yml       # espressif/button ^4
    ├── app_main.cpp            # khởi động: NVS, PM, GPIO, đo pin trước khi bật radio, Matter, task
    ├── app_matter.{h,cpp}      # node + endpoint Matter, Power Source, cập nhật có ngưỡng, commissioning, ICD
    ├── app_openthread_config.h # cấu hình radio 802.15.4 native
    ├── sensor_task.{h,cpp}     # task đo định kỳ, hiệu chuẩn, khoá máy khi pin cạn
    ├── sensors.{h,c}           # chuỗi đo: VSENS/cầu chia, ADC oneshot + curve-fitting, NTC, bù nhiệt
    ├── sht40.{h,c}             # driver SHT40 (i2c_master mới, CRC-8)
    ├── calibration.{h,c}       # điểm KHÔ/ƯỚT + chu kỳ đo trong NVS (namespace "soil")
    ├── battery.{h,c}           # đường cong CR123A → %, BatChargeLevel
    ├── board.{h,c}             # chân, công tắc nguồn, trạng thái Hi-Z khi ngủ, kích thích LEDC tuỳ chọn
    ├── status_led.{h,c}        # mẫu nháy LED (esp_timer + PM lock, an toàn đa luồng)
    └── app_button.{h,cpp}      # 1/2/3 lần nhấn, giữ 3 s/10 s
```

## 6.2 Build & nạp

```bash
# 1. Môi trường (một lần)
git clone -b v6.0.2 --recursive https://github.com/espressif/esp-idf.git && ./esp-idf/install.sh esp32h2
git clone --depth 1 https://github.com/espressif/esp-matter.git
cd esp-matter && git submodule update --init --depth 1 connectedhomeip/connectedhomeip
./connectedhomeip/connectedhomeip/scripts/checkout_submodules.py --platform esp32 linux --shallow
. ../esp-idf/export.sh && ./install.sh --no-host-tool && cd ..

# 2. Mỗi phiên làm việc
. esp-idf/export.sh && . esp-matter/export.sh

# 3. Build (SIT mặc định)
cd h2-soil-sensor/firmware
idf.py set-target esp32h2 && idf.py build
#   LIT ICD:   idf.py -D SDKCONFIG_DEFAULTS="sdkconfig.defaults;sdkconfig.defaults.lit" build
#   menuconfig → "H2 Soil Sensor" để đổi chu kỳ đo, ngưỡng, chân, TX power...

# 4. Nạp qua USB Serial/JTAG (J1: D+ D− GND, pin đã lắp)
idf.py -p /dev/ttyACM0 flash monitor
```

> Lưu ý môi trường: `install.sh` của esp-matter có thể lỗi phụ thuộc pip (`idf-component-manager~=2.2`) với Python 3.13;
> firmware vẫn build được nếu cài `pip install -r esp-matter/requirements.txt` vào môi trường Python của ESP-IDF.

## 6.3 Mô hình dữ liệu Matter

| Endpoint | Device type | Cluster (server) | Nội dung |
|---|---|---|---|
| 0 | Root Node + **Power Source (0x0011)** | Basic Info, General Commissioning, Network Commissioning (Thread), ICD Management, **Power Source** (Battery + Replaceable) | `BatVoltage` (mV), `BatPercentRemaining` (½ %), `BatChargeLevel` (OK/Warning/Critical), `BatReplacementNeeded`, `BatQuantity=1`, `EndpointList=[0..4]` |
| 1 | **Soil Sensor (0x0045, Matter 1.5)** | Identify, **Soil Measurement (0x0430)**, Temperature Measurement | `SoilMoistureMeasuredValue` 0–100 %, `SoilMoistureMeasurementLimits` {SoilMoisture, 0–100, ±5 %}; nhiệt độ đất (NTC) |
| 2 | Humidity Sensor (0x0307) | Relative Humidity Measurement | **bản sao độ ẩm đất** (0–100 % → 0–10000) cho Apple Home/Google Home (chưa hiển thị Soil Sensor) |
| 3 | Temperature Sensor (0x0302) | Temperature Measurement | nhiệt độ không khí (SHT40) – tuỳ chọn |
| 4 | Humidity Sensor (0x0307) | Relative Humidity Measurement | độ ẩm không khí (SHT40) – tuỳ chọn |

Trong esp-matter mới, Temperature/Relative Humidity/Soil Measurement là **cluster “code-driven”** (ServerClusterInterface):
`attribute::update()` sẽ trả `ESP_ERR_NOT_SUPPORTED` cho `MeasuredValue`; phải dùng API tích hợp
`SoilMeasurement::SetSoilMoistureMeasuredValue()`, `TemperatureMeasurement::SetMeasuredValue()`,
`RelativeHumidityMeasurement::SetMeasuredValue()` (trong khoá CHIP stack). Giới hạn Soil Measurement phải được đặt bằng
`SoilMeasurement::SetSoilMoistureLimits()` **trước** `esp_matter::start()` (nếu không, cluster sẽ `VerifyOrDie`).

```cpp
// app_matter.cpp – tạo endpoint Soil Sensor và giới hạn đo
endpoint::soil_sensor::config_t soil_cfg;
endpoint_t *ep = endpoint::soil_sensor::create(node, &soil_cfg, ENDPOINT_FLAG_NONE, nullptr);
s_ep_soil = endpoint::get_id(ep);
s_soil_ranges[0].rangeMin = 0;  s_soil_ranges[0].rangeMax = 100;
s_soil_ranges[0].fixedMax.SetValue(5);                       // ±5 % sau hiệu chuẩn 2 điểm
Globals::Structs::MeasurementAccuracyStruct::Type limits;
limits.measurementType = Globals::MeasurementTypeEnum::kSoilMoisture;
limits.measured = true;  limits.minMeasuredValue = 0;  limits.maxMeasuredValue = 100;
limits.accuracyRanges = DataModel::List<const Globals::Structs::MeasurementAccuracyRangeStruct::Type>(s_soil_ranges, 1);
SoilMeasurement::SetSoilMoistureLimits(s_ep_soil, limits);   // trước esp_matter::start()
cluster::temperature_measurement::create(ep, &st, CLUSTER_FLAG_SERVER);   // nhiệt độ đất (NTC)
```

## 6.4 Luồng đo (mỗi 15 phút – cấu hình được)

```cpp
// sensors.c – sensors_measure(): ~80 ms thức, giữ PM lock
board_vbat_divider(true);          // IO11 = 1 → Q3/Q2 bật cầu chia pin
board_sensor_power(true);          // IO10 = 0 → Q4 bật VSENS (TLC555, NTC, SHT40)
sht40_measure(SDA, SCL, &t, &rh);  // sau 2 ms cấp nguồn; lệnh 0xFD, CRC-8
board_i2c_release();               // SDA/SCL input, KHÔNG pull-up (tránh cấp ngược VSENS)
vTaskDelay(SETTLE_MS - elapsed);   // 60 ms cho bộ tách đỉnh ổn định
adc_oneshot …                      // SOIL & VBAT: ATTEN 6 dB; NTC: 12 dB; curve-fitting calibration
adc_read_mv(…, 64)                 // 64 mẫu, sắp xếp, bỏ 1/8 thấp + 1/8 cao (trimmed mean)
soil_mv_comp = soil_mv - k·(T_đất − 25 °C)      // bù trôi nhiệt diode (1 mV/°C mặc định)
pct = 100·(dry − v)/(dry − wet), kẹp 0..100
board_sensor_power(false); board_vbat_divider(false);   // trả chân về Hi-Z, điện trở ngoài giữ OFF
```

Giữa các lần đo, `sensor_task` chờ `xTaskNotifyWait(…, period)`; với `CONFIG_PM_ENABLE` + tickless idle chip tự vào
light-sleep, OpenThread vẫn poll parent theo chu kỳ ICD.

## 6.5 Chỉ báo cáo khi thay đổi > ngưỡng hoặc quá thời gian tối đa

```cpp
// app_matter.cpp
static int gate(last_t &l, int32_t v, int32_t delta, int64_t now, bool force) {
    if (force || !l.valid || abs(v - l.value) >= delta) { … return changed ? 1 : 2; }   // cập nhật
    if (now - l.t_us >= MAX_INTERVAL) { … return changed ? 1 : 2; }                      // hết thời gian tối đa
    return 0;                                                                              // bỏ qua
}
// 1 → Set…MeasuredValue() (giá trị mới → subscription report)
// 2 → provider.ReportAttributeChanged(path) (giá trị không đổi nhưng vẫn gửi “heartbeat”)
```

| Đại lượng | Ngưỡng mặc định (Kconfig) |
|---|---|
| Độ ẩm đất | 2 % (`SOIL_REPORT_DELTA_PCT`) |
| Nhiệt độ (đất/không khí) | 0.3 °C (`TEMP_REPORT_DELTA_CENTI` = 30) |
| Độ ẩm không khí | 2 %RH |
| Điện áp pin | 30 mV |
| Thời gian tối đa giữa 2 lần cập nhật | 3600 s (`SOIL_MAX_REPORT_INTERVAL_S`) |

Controller vẫn có subscription riêng (min/max interval); với ICD, max-interval ≥ `IdleModeDuration` (900 s).

## 6.6 Cấu hình ICD / Thread SED

| Tham số | SIT (mặc định) | LIT (`sdkconfig.defaults.lit`) |
|---|---|---|
| `CONFIG_ICD_SLOW_POLL_INTERVAL_MS` | 15000 (giới hạn tối đa của SIT) | 60000 |
| `CONFIG_ICD_FAST_POLL_INTERVAL_MS` | 500 | 500 |
| `CONFIG_ICD_IDLE_MODE_INTERVAL_SEC` | 900 | 900 |
| `CONFIG_ICD_ACTIVE_MODE_INTERVAL_MS` | 1000 | 1000 |
| `CONFIG_ICD_ACTIVE_MODE_THRESHOLD_MS` | 1000 | 5000 |
| User Active Mode Trigger | nút SW1 (1 lần nhấn) | nút SW1 |

Kèm theo: `CONFIG_OPENTHREAD_MTD`, `CONFIG_PM_ENABLE`, `CONFIG_PM_POWER_DOWN_PERIPHERAL_IN_LIGHT_SLEEP`,
`CONFIG_FREERTOS_USE_TICKLESS_IDLE`, `CONFIG_IEEE802154_SLEEP_ENABLE`, `CONFIG_ESP_SLEEP_POWER_DOWN_FLASH`,
`CONFIG_ESP_PHY_MAC_BB_PD`, `CONFIG_USE_BLE_ONLY_FOR_COMMISSIONING` (giải phóng BLE sau khi ghép).
TX power đặt bằng `otPlatRadioSetTransmitPower()` khi Thread khởi động (`CONFIG_THREAD_TX_POWER_DBM`, mặc định +10 dBm).

## 6.7 Nút nhấn & LED

| Thao tác SW1 | Hành động | LED |
|---|---|---|
| Nhấn 1 lần | Đo + báo cáo ngay, ICD active mode (UAT); nếu chưa ghép → mở cửa sổ commissioning BLE 15 phút | 1 chớp |
| Nhấn 2 lần | **Hiệu chuẩn KHÔ**: lưu điện áp hiện tại làm điểm 0 % (đầu dò trong không khí/đất khô hoàn toàn) | 2 chớp (lỗi: 6 chớp nhanh) |
| Nhấn 3 lần | **Hiệu chuẩn ƯỚT**: lưu điểm 100 % (đầu dò ngập nước/đất bão hoà, ngập tới vạch) | 3 chớp |
| Giữ ≥ 3 s | Cảnh báo sắp reset (thả tay để huỷ) | sáng liên tục |
| Giữ ≥ 10 s | **Factory reset Matter** (xoá fabric, mạng Thread). Hiệu chuẩn được giữ lại | nháy nhanh rồi khởi động lại |
| Giữ khi cấp nguồn/reset | Vào chế độ nạp ROM (IO9 = 0) | – |

| LED | Ý nghĩa |
|---|---|
| chớp ngắn mỗi 2 s | đang mở cửa sổ commissioning |
| 2 chớp sau ghép nối | commissioning thành công |
| nhấp nháy 1 Hz | Identify từ ứng dụng |
| 3 chớp rất ngắn khi nhấn nút | pin yếu (≤ 5 %) |
| 6 chớp nhanh | lỗi (đo/hiệu chuẩn/commissioning) |

### Quy trình hiệu chuẩn khuyến nghị
1. Sau khi phủ coating và lắp vỏ hoàn chỉnh, lau khô que, để trong không khí → **nhấn 2 lần** (KHÔ).
2. Cắm que vào cốc nước (hoặc đất bão hoà nước của chính vườn đó) **ngập đúng tới vạch SOIL LINE** → chờ 10 s → **nhấn 3 lần** (ƯỚT).
3. Hiệu chuẩn theo loại đất cho kết quả “% độ ẩm tương đối” sát thực tế hơn: KHÔ = đất phơi khô, ƯỚT = đất sau tưới đẫm 30 phút.
4. Giá trị lưu trong NVS (`soil/dry_mv`, `soil/wet_mv`), giữ qua factory reset; thứ tự hai bước không quan trọng.

## 6.8 Bảo vệ pin cạn
- Khi khởi động, firmware đo pin **trước** khi bật radio; nếu V<sub>BAT</sub> < 2050 mV → deep-sleep, chỉ thức khi nhấn nút.
- Khi chạy: 2 lần đo liên tiếp < 2050 mV → gửi báo cáo cuối (BatChargeLevel = Critical) rồi deep-sleep (tránh vòng lặp
  brown-out reset làm cạn kiệt pin và rò rỉ).

## 6.9 Commissioning & sản xuất
- Lần đầu khởi động (chưa có fabric): BLE quảng bá 15 phút; quét QR/mã ghép nối in ra UART log (`chip-tool`/app nhà).
- Firmware mặc định dùng **chứng chỉ thử (test DAC, VID 0xFFF1)** của SDK → các hệ sinh thái sẽ cảnh báo “thiết bị chưa
  chứng nhận”. Sản phẩm thật cần VID/PID riêng, DAC/PAI từ PAA và factory partition (dùng `esp-matter-mfg-tool`,
  phân vùng `fctry`/`esp_secure_cert` đã có sẵn trong `partitions.csv`).
- OTA Requestor bật sẵn (`CONFIG_ENABLE_OTA_REQUESTOR`), 2 phân vùng OTA.
