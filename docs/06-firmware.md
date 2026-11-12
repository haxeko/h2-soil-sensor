# 6. Firmware (ESP-IDF + esp-matter)

Đã build thành công với **ESP-IDF v6.0.2 + esp-matter `main` (11/2026, connectedhomeip `99a81bd`, Matter 1.5)**,
target `esp32h2`: `h2_soil_sensor.bin` = 0x1948F0 B ≈ 1.66 MB, còn trống 16 % phân vùng OTA 1.875 MB (0x1E0000); không có
cảnh báo trong mã ứng dụng. Firmware v3 chỉ phục vụ **một module độ ẩm đất điện dung** trên J4.

## 6.1 Cấu trúc project

```
firmware/
├── CMakeLists.txt              # project, kéo esp-matter + connectedhomeip components
├── partitions.csv              # 4 MB: nvs, 2 × OTA 1.875 MB, fctry, esp_secure_cert
├── sdkconfig.defaults          # ESP32-H2, Thread MTD, BLE commissioning, PM/light-sleep, ICD SIT
├── sdkconfig.defaults.lit      # tuỳ chọn: LIT ICD (slow-poll 60 s, Check-In)
└── main/
    ├── Kconfig.projbuild       # menu "H2 Soil Sensor": chu kỳ đo, ngưỡng, thời gian ổn định, hiệu chuẩn, GPIO…
    ├── idf_component.yml       # espressif/button ^4
    ├── app_main.cpp            # khởi động: NVS, PM, GPIO, đo pin TRƯỚC khi bật radio, Matter, task
    ├── app_matter.{h,cpp}      # node + endpoint Matter, Power Source, cập nhật có ngưỡng, commissioning, ICD
    ├── app_openthread_config.h # cấu hình radio 802.15.4 native
    ├── sensor_task.{h,cpp}     # task đo định kỳ, hiệu chuẩn, khoá máy khi pin cạn
    ├── sensors.{h,c}           # chuỗi đo: VSENS → chờ module (light-sleep) → cầu chia pin → ADC → %
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
#   menuconfig → "H2 Soil Sensor" để đổi chu kỳ đo, ngưỡng, chân, TX power...

# 4. Nạp qua USB Serial/JTAG: pad J1-8 (D+), J1-7 (D−), J1-2 (GND), pin đã lắp
idf.py -p /dev/ttyACM0 flash monitor
```

> Pad nạp J1 (2 × 4, bước 2.54 mm): hàng sát mép bo 1 = 3V3, 3 = TX, 5 = EN, 7 = D−; hàng trong 2 = GND, 4 = RX, 6 = IO9,
> 8 = D+. Dùng kẹp/đồ gá pogo hoặc hàn dây tạm. Nạp qua UART: TX/RX/GND (+ EN/IO9 nếu adapter tự vào chế độ nạp), xem [02](02-schematic.md).

> Lưu ý môi trường: `install.sh` của esp-matter có thể lỗi phụ thuộc pip (`idf-component-manager~=2.2`) với Python 3.13;
> firmware vẫn build được nếu cài `pip install -r esp-matter/requirements.txt` vào môi trường Python của ESP-IDF.

## 6.3 Cấu hình Kconfig (`idf.py menuconfig` → *H2 Soil Sensor*)

| Tuỳ chọn | Mặc định | Ý nghĩa |
|---|---|---|
| `SOIL_MEAS_PERIOD_S` | 900 | Chu kỳ đo (30–86400 s); có thể ghi đè trong NVS (`soil/period_s`) |
| `SOIL_MAX_REPORT_INTERVAL_S` | 3600 | Thời gian tối đa giữa 2 lần cập nhật một giá trị (heartbeat) |
| `SOIL_REPORT_DELTA_PCT` / `VBAT_REPORT_DELTA_MV` | 2 % / 30 mV | Ngưỡng thay đổi để cập nhật |
| `SOIL_SETTLE_MS` | 1500 | Thời gian chờ module ổn định sau khi bật VSENS (module cần ~1 s); chip light-sleep trong lúc chờ |
| `SOIL_MODULE_MIN_MV` | 200 | AOUT thấp hơn = không có module / chập → bỏ qua giá trị |
| `SOIL_ADC_SAMPLES` | 64 | Số mẫu ADC cho AOUT (trimmed mean); VBAT dùng một nửa |
| `SOIL_CAL_DRY_MV_DEFAULT` / `SOIL_CAL_WET_MV_DEFAULT` | 2500 / 1200 mV | Điểm KHÔ/ƯỚT mặc định trước khi hiệu chuẩn (module v1.2 ở 3.3 V: ~2.2–2.8 V trong không khí, ~1.0–1.4 V trong nước) |
| `SOIL_ENABLE_RH_MIRROR` | y | Thêm endpoint Humidity Sensor sao chép độ ẩm đất (tương thích Apple/Google) |
| `VSENS_SOFTSTART_US` | 1000 | Soft-start VSENS (0–20000 µs, 0 = đóng cứng) |
| `VBAT_DIVIDER_RATIO_X1000` | 2000 | Tỉ số cầu chia pin (R7 + R8)/R8 |
| `VBAT_SHUTDOWN_MV` | 2050 | Dưới ngưỡng này thiết bị tắt (deep-sleep) |
| `THREAD_TX_POWER_DBM` | 10 | Công suất phát 802.15.4 (−24…20 dBm) |
| `GPIO_*` | 1, 2, 10, 11, 0, 9 | SOIL_ADC, VBAT_ADC, SENS_PWR_EN_N, VBAT_MEAS_EN, LED, nút |

## 6.4 Mô hình dữ liệu Matter

| Endpoint | Device type | Cluster (server) | Nội dung |
|---|---|---|---|
| 0 | Root Node + **Power Source (0x0011)** | Basic Info, General Commissioning, Network Commissioning (Thread), ICD Management, **Power Source** (Battery + Replaceable) | `BatVoltage` (mV), `BatPercentRemaining` (½ %), `BatChargeLevel` (OK/Warning/Critical), `BatReplacementNeeded`, `BatQuantity=1`, `EndpointList=[0, 1, 2]` |
| 1 | **Soil Sensor (0x0045, Matter 1.5)** | Identify, **Soil Measurement (0x0430)** | `SoilMoistureMeasuredValue` 0–100 %, `SoilMoistureMeasurementLimits` {SoilMoisture, 0–100, ±5 %} |
| 2 | Humidity Sensor (0x0307) | Relative Humidity Measurement | **bản sao độ ẩm đất** (0–100 % → 0–10000) cho Apple Home/Google Home (chưa hiển thị Soil Sensor); tắt bằng `SOIL_ENABLE_RH_MIRROR` |

Trong esp-matter mới, Relative Humidity/Soil Measurement là **cluster “code-driven”** (ServerClusterInterface):
`attribute::update()` sẽ trả `ESP_ERR_NOT_SUPPORTED` cho `MeasuredValue`; phải dùng API tích hợp
`SoilMeasurement::SetSoilMoistureMeasuredValue()` và `RelativeHumidityMeasurement::SetMeasuredValue()` (trong khoá CHIP stack).
Giới hạn Soil Measurement phải được đặt bằng `SoilMeasurement::SetSoilMoistureLimits()` **trước** `esp_matter::start()`
(nếu không, cluster sẽ `VerifyOrDie`).

```cpp
// app_matter.cpp – endpoint Soil Sensor và giới hạn đo
endpoint_t *ep = endpoint::soil_sensor::create(node, &soil_cfg, ENDPOINT_FLAG_NONE, nullptr);
s_ep_soil = endpoint::get_id(ep);
s_soil_ranges[0].rangeMin = 0;  s_soil_ranges[0].rangeMax = 100;
s_soil_ranges[0].fixedMax.SetValue(5);                       // ±5 % sau hiệu chuẩn 2 điểm
limits.measurementType = Globals::MeasurementTypeEnum::kSoilMoisture;
limits.measured = true;  limits.minMeasuredValue = 0;  limits.maxMeasuredValue = 100;
limits.accuracyRanges = DataModel::List<const Globals::Structs::MeasurementAccuracyRangeStruct::Type>(s_soil_ranges, 1);
SoilMeasurement::SetSoilMoistureLimits(s_ep_soil, limits);   // trước esp_matter::start()
endpoint::humidity_sensor::create(node, &mh, ENDPOINT_FLAG_NONE, nullptr);   // EP2: bản sao độ ẩm đất
```

## 6.5 Luồng đo (mỗi 15 phút – cấu hình được)

```c
// sensors.c – sensors_measure()
esp_pm_lock_acquire(lock);                 // giữ chip thức ở các đoạn cần CPU
board_sensor_power(true);                  // soft-start: chỉ pull-down nội (~45 kΩ) chống R9 trong 1 ms, rồi IO10 = 0 → VSENS bật
settle_wait(t_on, CONFIG_SOIL_SETTLE_MS);  // module cần ~1 s: gpio_hold giữ IO10/IO11, nhả PM lock → LIGHT-SLEEP tới 1500 ms
board_vbat_divider(true); vTaskDelay(3);   // IO11 = 1 → Q3/Q2 bật cầu chia pin (τ = 0.5 ms)
adc_read_mv(soil, 64); adc_read_mv(vbat, 32);
                                           // oneshot + curve-fitting; SOIL: ATTEN 12 dB, VBAT: 6 dB
                                           // sắp xếp, bỏ 1/8 thấp + 1/8 cao (trimmed mean)
if (soil_mv > CONFIG_SOIL_MODULE_MIN_MV)   // < 200 mV = không có module / chập → bỏ qua
    pct = 100·(dry − v)/(dry − wet), kẹp 0..100        // AOUT cao = khô, thấp = ướt
board_sensor_power(false); board_vbat_divider(false);   // lái OFF rồi trả chân về Hi-Z, R9/R6 giữ OFF
```

| t (ms) | Bước | CPU |
|---|---|---|
| 0 | VSENS bật (soft-start 1 ms) | thức |
| 1 → 1500 | chờ module ổn định | light-sleep |
| 1500 → ~1510 | cầu chia pin 3 ms + ADC (64 + 32 mẫu) | thức |
| ~1510 | tắt VSENS và cầu chia | – |

Giữa các lần đo, `sensor_task` chờ `xTaskNotifyWait(…, period)`; với `CONFIG_PM_ENABLE` + tickless idle chip tự vào
light-sleep, OpenThread vẫn poll parent theo chu kỳ ICD. Lúc khởi động, `board_init()` đặt các chân không dùng
(IO3, IO4, IO5, IO12, IO13, IO14, IO22, IO25) về Hi-Z. Năng lượng mỗi lần đo: xem [05](05-nang-luong-va-tuoi-tho-pin.md).

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
| Độ ẩm đất (EP1 và bản sao EP2) | 2 % (`SOIL_REPORT_DELTA_PCT`) |
| Điện áp pin | 30 mV (`VBAT_REPORT_DELTA_MV`) |
| Thời gian tối đa giữa 2 lần cập nhật | 3600 s (`SOIL_MAX_REPORT_INTERVAL_S`) |

Controller vẫn có subscription riêng (min/max interval); với ICD, max-interval ≥ `IdleModeDuration` (900 s). Khi module bị
rút/hỏng (AOUT < 200 mV) giá trị **không được cập nhật** – controller giữ giá trị cũ.

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
Đồng hồ ngủ dùng RC nội 136 kHz (`CONFIG_RTC_CLK_SRC_EXT_CRYS=n`).

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
1. Bịt kín phần linh kiện của module (xem [07](07-rui-ro-ngoai-troi.md)), cắm module vào J4. Lau khô đầu dò, để trong không
   khí → **nhấn 2 lần** (KHÔ). LED xác nhận sau ~1.5 s (thời gian ổn định của module).
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
