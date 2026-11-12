# 6. Firmware (ESP-IDF + esp-matter)

Đã build thành công với **ESP-IDF v6.0.2 + esp-matter `main` (11/2026, connectedhomeip `99a81bd`, Matter 1.5)**,
target `esp32h2`: `h2_soil_sensor.bin` ≈ 1.68 MB, còn trống 14 % phân vùng OTA 1.875 MB (0x1E0000).

## 6.1 Cấu trúc project

```
firmware/
├── CMakeLists.txt              # project, kéo esp-matter + connectedhomeip components
├── partitions.csv              # 4 MB: nvs, 2 × OTA 1.875 MB, fctry, esp_secure_cert
├── sdkconfig.defaults          # ESP32-H2, Thread MTD, BLE commissioning, PM/light-sleep, ICD SIT
├── sdkconfig.defaults.lit      # tuỳ chọn: LIT ICD (slow-poll 60 s, Check-In)
├── sdkconfig.defaults.xtal32k  # tuỳ chọn: khi lắp thạch anh 32.768 kHz (Y1)
└── main/
    ├── Kconfig.projbuild       # menu "H2 Soil Sensor": chu kỳ đo, ngưỡng, thời gian ổn định, hiệu chuẩn, module, GPIO…
    ├── idf_component.yml       # espressif/button ^4
    ├── app_main.cpp            # khởi động: NVS, PM, GPIO, đo lần đầu (pin + dò module) TRƯỚC khi bật radio, Matter, task
    ├── app_matter.{h,cpp}      # node + endpoint Matter (theo module có mặt), Power Source, cập nhật có ngưỡng, ICD
    ├── app_openthread_config.h # cấu hình radio 802.15.4 native
    ├── sensor_task.{h,cpp}     # task đo định kỳ, hiệu chuẩn, khoá máy khi pin cạn
    ├── sensors.{h,c}           # chuỗi đo: VSENS → module I²C → chờ module đất (light-sleep) → cầu chia pin → ADC, NTC, %
    ├── air_sensor.{h,c}        # module I²C: tự nhận AHT20/AHT21, SHT4x, SHT3x (driver i2c_master mới, CRC-8)
    ├── calibration.{h,c}       # điểm KHÔ/ƯỚT + chu kỳ đo trong NVS (namespace "soil")
    ├── battery.{h,c}           # đường cong CR123A → %, BatChargeLevel
    ├── board.{h,c}             # chân, công tắc VSENS (soft-start) và cầu chia pin, Hi-Z khi ngủ, gpio_hold khi chờ
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
#   menuconfig → "H2 Soil Sensor" để đổi chu kỳ đo, loại module, ngưỡng, chân, TX power...

# 4. Nạp qua USB Serial/JTAG (J1: D+ D− GND, pin đã lắp)
idf.py -p /dev/ttyACM0 flash monitor
```

> Lưu ý môi trường: `install.sh` của esp-matter có thể lỗi phụ thuộc pip (`idf-component-manager~=2.2`) với Python 3.13;
> firmware vẫn build được nếu cài `pip install -r esp-matter/requirements.txt` vào môi trường Python của ESP-IDF.

## 6.3 Cấu hình Kconfig (`idf.py menuconfig` → *H2 Soil Sensor*)

| Tuỳ chọn | Mặc định | Ý nghĩa |
|---|---|---|
| `SOIL_MEAS_PERIOD_S` | 900 | Chu kỳ đo (30–86400 s); có thể ghi đè trong NVS (`soil/period_s`) |
| `SOIL_MAX_REPORT_INTERVAL_S` | 3600 | Thời gian tối đa giữa 2 lần cập nhật một giá trị (heartbeat) |
| `SOIL_REPORT_DELTA_PCT` / `TEMP_REPORT_DELTA_CENTI` / `RH_REPORT_DELTA_CENTI` / `VBAT_REPORT_DELTA_MV` | 2 % / 30 (0.3 °C) / 200 (2 %RH) / 30 mV | Ngưỡng thay đổi để cập nhật |
| `SOIL_SETTLE_MS` | 1500 | Thời gian chờ module đất ổn định sau khi bật VSENS (module cần ~1 s); chip light-sleep trong lúc chờ |
| `SOIL_MODULE_MIN_MV` | 200 | AOUT thấp hơn = không có module / chập → bỏ qua giá trị |
| `SOIL_ADC_SAMPLES` | 64 | Số mẫu ADC (trimmed mean); VBAT và NTC dùng một nửa |
| `SOIL_CAL_DRY_MV_DEFAULT` / `SOIL_CAL_WET_MV_DEFAULT` | 2500 / 1200 mV | Điểm KHÔ/ƯỚT mặc định trước khi hiệu chuẩn (module ở 3.3 V: ~2.4–2.8 V trong không khí, ~1.0–1.4 V trong nước) |
| `SOIL_TEMP_COMP_UV_PER_C` | 0 (tắt) | Bù nhiệt bậc 1 bằng NTC: v − k·(T − 25 °C); đo k cho module của bạn trước khi bật |
| `SOIL_ENABLE_NTC`, `NTC_R25_OHM`, `NTC_BETA` | y, 10000, 3950 | Đầu dò NTC trên J7 |
| `SOIL_AIR_SENSOR` | AUTO | Module I²C trên J6: AUTO (AHT20 0x38, SHT4x 0x44, SHT3x 0x44/0x45) / SHT4X / SHT3X / AHT20 / NONE |
| `SOIL_OPTIONAL_EP_AUTO` | y | Chỉ tạo endpoint NTC / không khí cho cảm biến trả lời ở lần đo lúc khởi động |
| `SOIL_ENABLE_RH_MIRROR` | y | Thêm endpoint Humidity Sensor sao chép độ ẩm đất (tương thích Apple/Google) |
| `VSENS_SOFTSTART_US` | 1000 | Soft-start VSENS (0–20000 µs, 0 = đóng cứng) |
| `VBAT_DIVIDER_RATIO_X1000`, `NTC_SUPPLY_MV` | 2000, 3300 | Tỉ số cầu chia pin; điện áp VSENS dùng cho công thức NTC |
| `VBAT_SHUTDOWN_MV` | 2050 | Dưới ngưỡng này thiết bị tắt (deep-sleep) |
| `THREAD_TX_POWER_DBM` | 10 | Công suất phát 802.15.4 (−24…20 dBm) |
| `GPIO_*` | 1, 2, 3, 10, 11, 12, 22, 0, 9 | SOIL_ADC, VBAT_ADC, NTC_ADC, SENS_PWR_EN_N, VBAT_MEAS_EN, SDA, SCL, LED, nút |

## 6.4 Mô hình dữ liệu Matter

| Endpoint | Device type | Cluster (server) | Nội dung |
|---|---|---|---|
| 0 | Root Node + **Power Source (0x0011)** | Basic Info, General Commissioning, Network Commissioning (Thread), ICD Management, **Power Source** (Battery + Replaceable) | `BatVoltage` (mV), `BatPercentRemaining` (½ %), `BatChargeLevel` (OK/Warning/Critical), `BatReplacementNeeded`, `BatQuantity=1`, `EndpointList` = các endpoint đã tạo |
| 1 | **Soil Sensor (0x0045, Matter 1.5)** | Identify, **Soil Measurement (0x0430)**, Temperature Measurement (chỉ khi có NTC) | `SoilMoistureMeasuredValue` 0–100 %, `SoilMoistureMeasurementLimits` {SoilMoisture, 0–100, ±5 %}; nhiệt độ đất (NTC, −40…85 °C) |
| 2 | Humidity Sensor (0x0307) | Relative Humidity Measurement | **bản sao độ ẩm đất** (0–100 % → 0–10000) cho Apple Home/Google Home (chưa hiển thị Soil Sensor); tắt bằng `SOIL_ENABLE_RH_MIRROR` |
| 3 | Temperature Sensor (0x0302) | Temperature Measurement | nhiệt độ không khí (module I²C) – chỉ khi module trả lời lúc khởi động |
| 4 | Humidity Sensor (0x0307) | Relative Humidity Measurement | độ ẩm không khí (module I²C) – như trên |

- Số endpoint được cấp theo thứ tự tạo: đủ cảm biến và cấu hình mặc định → EP1…EP4; không có module I²C → chỉ EP1, EP2;
  tắt bản sao RH → endpoint không khí thành EP2/EP3.
- **Lần đo đầu tiên chạy trước khi dựng mô hình dữ liệu** (`app_matter_init(&r)`): với `SOIL_OPTIONAL_EP_AUTO = y`, cluster
  nhiệt độ đất chỉ được tạo nếu NTC đọc hợp lệ, EP3/EP4 chỉ được tạo nếu module I²C trả lời → controller không hiện ô trống.
  Hệ quả: **cắm module trước khi lắp pin**; nếu thay đổi bộ cảm biến sau khi đã ghép nối, khởi động lại rồi xoá thiết bị khỏi
  app và ghép lại (factory reset 10 s) để controller đọc lại danh sách endpoint.
- Trong esp-matter mới, Temperature/Relative Humidity/Soil Measurement là **cluster “code-driven”** (ServerClusterInterface):
  `attribute::update()` sẽ trả `ESP_ERR_NOT_SUPPORTED` cho `MeasuredValue`; phải dùng API tích hợp
  `SoilMeasurement::SetSoilMoistureMeasuredValue()`, `TemperatureMeasurement::SetMeasuredValue()`,
  `RelativeHumidityMeasurement::SetMeasuredValue()` (trong khoá CHIP stack). Giới hạn Soil Measurement phải được đặt bằng
  `SoilMeasurement::SetSoilMoistureLimits()` **trước** `esp_matter::start()` (nếu không, cluster sẽ `VerifyOrDie`).

```cpp
// app_matter.cpp – endpoint Soil Sensor, giới hạn đo, cluster nhiệt độ đất tuỳ chọn
endpoint_t *ep = endpoint::soil_sensor::create(node, &soil_cfg, ENDPOINT_FLAG_NONE, nullptr);
s_ep_soil = endpoint::get_id(ep);
s_soil_ranges[0].rangeMin = 0;  s_soil_ranges[0].rangeMax = 100;
s_soil_ranges[0].fixedMax.SetValue(5);                       // ±5 % sau hiệu chuẩn 2 điểm
limits.measurementType = Globals::MeasurementTypeEnum::kSoilMoisture;
limits.measured = true;  limits.minMeasuredValue = 0;  limits.maxMeasuredValue = 100;
limits.accuracyRanges = DataModel::List<const Globals::Structs::MeasurementAccuracyRangeStruct::Type>(s_soil_ranges, 1);
SoilMeasurement::SetSoilMoistureLimits(s_ep_soil, limits);   // trước esp_matter::start()
if (s_has_ntc)                                                // NTC đọc được ở lần đo lúc khởi động
    cluster::temperature_measurement::create(ep, &st, CLUSTER_FLAG_SERVER);
```

## 6.5 Luồng đo (mỗi 15 phút – cấu hình được)

```c
// sensors.c – sensors_measure()
esp_pm_lock_acquire(lock);                 // giữ chip thức ở các đoạn cần CPU
board_sensor_power(true);                  // soft-start: chỉ pull-down nội (~45 kΩ) chống R9 trong 1 ms, rồi IO10 = 0 → VSENS bật
settle_wait(t_on, 45);                     // AHT20 cần 40 ms sau cấp nguồn (SHT3x/SHT4x 1–2 ms) – light-sleep
air_sensor_measure(SDA, SCL, &t, &rh);     // lần đầu dò AHT20 0x38 → SHT4x 0x44 → SHT3x 0x44/0x45, sau đó nhớ loại; CRC-8
board_i2c_release();                       // SDA/SCL input, KHÔNG pull-up (tránh cấp ngược VSENS khi tắt)
settle_wait(t_on, CONFIG_SOIL_SETTLE_MS);  // module đất cần ~1 s: gpio_hold giữ IO10/IO11, nhả PM lock → LIGHT-SLEEP tới 1500 ms
board_vbat_divider(true); vTaskDelay(3);   // IO11 = 1 → Q3/Q2 bật cầu chia pin (τ = 0.5 ms)
adc_read_mv(soil, 64); adc_read_mv(vbat, 32); adc_read_mv(ntc, 32);
                                           // oneshot + curve-fitting; SOIL & NTC: ATTEN 12 dB, VBAT: 6 dB
                                           // sắp xếp, bỏ 1/8 thấp + 1/8 cao (trimmed mean)
if (soil_mv > CONFIG_SOIL_MODULE_MIN_MV)   // < 200 mV = không có module / chập → bỏ qua
    soil_mv_comp = soil_mv - k·(T_NTC − 25 °C);       // k = SOIL_TEMP_COMP_UV_PER_C (mặc định 0 = tắt)
pct = 100·(dry − v)/(dry − wet), kẹp 0..100            // AOUT cao = khô, thấp = ướt
board_sensor_power(false); board_vbat_divider(false);   // lái OFF rồi trả chân về Hi-Z, R9/R6 giữ OFF
```

| t (ms) | Bước | CPU |
|---|---|---|
| 0 | VSENS bật (soft-start 1 ms) | thức |
| 1–45 | chờ module I²C khởi động | light-sleep |
| 45 → ~55…140 | đọc I²C (SHT4x ~10 ms, SHT3x ~16 ms, AHT20 ~80 ms) | thức (idle) |
| → 1500 | chờ module đất ổn định | light-sleep |
| 1500 → ~1510 | cầu chia pin 3 ms + ADC (64 + 32 + 32 mẫu) | thức |
| ~1510 | tắt VSENS và cầu chia | – |

Giữa các lần đo, `sensor_task` chờ `xTaskNotifyWait(…, period)`; với `CONFIG_PM_ENABLE` + tickless idle chip tự vào
light-sleep, OpenThread vẫn poll parent theo chu kỳ ICD. Năng lượng mỗi lần đo: xem [05](05-nang-luong-va-tuoi-tho-pin.md).

## 6.6 Chỉ báo cáo khi thay đổi > ngưỡng hoặc quá thời gian tối đa

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
| Độ ẩm không khí | 2 %RH (`RH_REPORT_DELTA_CENTI` = 200) |
| Điện áp pin | 30 mV |
| Thời gian tối đa giữa 2 lần cập nhật | 3600 s (`SOIL_MAX_REPORT_INTERVAL_S`) |

Controller vẫn có subscription riêng (min/max interval); với ICD, max-interval ≥ `IdleModeDuration` (900 s). Giá trị không
hợp lệ (module đất bị rút, NTC hở, module I²C không trả lời) **không được cập nhật** – controller giữ giá trị cũ.

## 6.7 Cấu hình ICD / Thread SED

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

## 6.8 Nút nhấn & LED

| Thao tác SW1 | Hành động | LED |
|---|---|---|
| Nhấn 1 lần | Đo + báo cáo ngay, ICD active mode (UAT); nếu chưa ghép → mở cửa sổ commissioning BLE 15 phút | 1 chớp |
| Nhấn 2 lần | **Hiệu chuẩn KHÔ**: lưu AOUT hiện tại làm điểm 0 % (module lau khô, để trong không khí) | 2 chớp (lỗi: 6 chớp nhanh) |
| Nhấn 3 lần | **Hiệu chuẩn ƯỚT**: lưu điểm 100 % (đầu dò ngập nước/đất bão hoà, tới vạch giới hạn) | 3 chớp |
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

### Quy trình hiệu chuẩn khuyến nghị (mỗi module một lần)
1. Bịt kín phần linh kiện của module (xem [07](07-rui-ro-ngoai-troi.md)), cắm module vào J4, lắp pin. Lau khô đầu dò, để trong
   không khí → **nhấn 2 lần** (KHÔ). Mỗi lần nhấn, LED xác nhận sau ~1.5 s (thời gian ổn định của module).
2. Nhúng đầu dò vào cốc nước (hoặc đất bão hoà nước của chính vườn đó) **tới vạch giới hạn, phần linh kiện phải khô** → chờ
   10 s → **nhấn 3 lần** (ƯỚT).
3. Hiệu chuẩn theo loại đất cho kết quả “% độ ẩm tương đối” sát thực tế hơn: KHÔ = đất phơi khô, ƯỚT = đất sau tưới đẫm 30 phút.
4. Giá trị lưu trong NVS (`soil/dry_mv`, `soil/wet_mv`), giữ qua factory reset; thứ tự hai bước không quan trọng. Nếu hiệu
   KHÔ − ƯỚT < 50 mV hoặc module không có (AOUT < 200 mV) → 6 chớp nhanh. **Thay module = hiệu chuẩn lại.**

## 6.9 Bảo vệ pin cạn
- Khi khởi động, firmware đo pin **trước** khi bật radio; nếu V<sub>BAT</sub> < 2050 mV → deep-sleep, chỉ thức khi nhấn nút.
- Khi chạy: 2 lần đo liên tiếp < 2050 mV → gửi báo cáo cuối (BatChargeLevel = Critical) rồi deep-sleep (tránh vòng lặp
  brown-out reset làm cạn kiệt pin và rò rỉ).

## 6.10 Commissioning & sản xuất
- Lần đầu khởi động (chưa có fabric): BLE quảng bá 15 phút; quét QR/mã ghép nối in ra UART log (`chip-tool`/app nhà).
- Firmware mặc định dùng **chứng chỉ thử (test DAC, VID 0xFFF1)** của SDK → các hệ sinh thái sẽ cảnh báo “thiết bị chưa
  chứng nhận”. Sản phẩm thật cần VID/PID riêng, DAC/PAI từ PAA và factory partition (dùng `esp-matter-mfg-tool`,
  phân vùng `fctry`/`esp_secure_cert` đã có sẵn trong `partitions.csv`).
- OTA Requestor bật sẵn (`CONFIG_ENABLE_OTA_REQUESTOR`), 2 phân vùng OTA.
