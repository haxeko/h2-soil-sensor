# 5. Dòng tiêu thụ và tuổi thọ pin

Mô hình tính toán có thể chỉnh tham số: [`docs/power_budget.py`](power_budget.py) (`python3 docs/power_budget.py`).
Số liệu nguồn: datasheet ESP32-H2 (bảng 5-7, 5-9), đo dạng sóng ICD của Espressif trên ESP32-H2 (`esp-matter/examples/icd_app`),
datasheet TPS63900, thông số module độ ẩm đất DFRobot SEN0193 (5 mA), trình tự đo trong `firmware/main/sensors.c`.

## 5.1 Dòng tiêu thụ theo trạng thái (tại rail 3.3 V)

| Trạng thái | Dòng | Thời gian / tần suất | Ghi chú |
|---|---|---|---|
| **Light-sleep (ICD idle)** | **25 µA** (ESP32-H2) + ~0.3 µA rò bo | phần lớn thời gian | CPU, radio, miền TOP tắt; RAM giữ; flash tắt (`CONFIG_ESP_SLEEP_POWER_DOWN_FLASH`). Espressif đo ~27 µA trên DevKit |
| TPS63900 Iq | 75 nA (phía pin) | liên tục | hiệu suất ~88 % ở 30 µA, ~90 % ở mA |
| Module cảm biến, cầu chia pin, NTC, pull-up I²C | **0** (VSENS và cầu chia tắt bằng MOSFET) | – | chỉ rò I<sub>DSS</sub> (nA) |
| Thread data poll (SED/ICD slow-poll) | xung RX 25 mA / TX 36–140 mA | 1 lần mỗi 15 s (SIT) hoặc 60 s (LIT) | ≈ **0.25 mAs/poll** ở +10 dBm, 0.31 mAs ở +20 dBm (đo của Espressif: 0.31 mC/poll tại +20 dBm) |
| **Đo cảm biến** | VSENS: module đất ~5 mA + module I²C ≤ 1 mA + NTC 0.17 mA; MCU ~7 mA khi thức | VSENS bật ~1.55 s, MCU thức ~0.12 s, mỗi 15 phút | ≈ **10.4 mAs/lần** (chi tiết 5.2) |
| Báo cáo (subscription report) | ICD active mode 1 s, fast-poll 500 ms, TX/RX + MRP ACK + mã hoá | ~72 lần/ngày | ≈ 1.5 mAs/lần (ước tính) |
| LED | 1.5 mA | 60 ms khi nhấn nút | không đáng kể |
| TX 802.15.4 +20 / +9 / 0 dBm | 140 / 60 / 36 mA | vài trăm µs mỗi khung | mặc định firmware đặt **+10 dBm** |
| BLE commissioning (một lần) | ~3–6 mA trung bình | ≤ 15 phút | ≈ 1–1.5 mAh mỗi lần ghép nối |
| OTA firmware (~1.7 MB qua Thread) | ~15–20 mA | 10–20 phút | ≈ 3–6 mAh mỗi lần cập nhật |
| Deep-sleep (pin cạn, khoá máy) | 7 µA | – | khi VBAT < 2.05 V, chờ nhấn nút |

Quy đổi về dòng pin: I<sub>pin</sub> = I<sub>3V3</sub> × 3.3 V / (V<sub>pin</sub> × η) ≈ I<sub>3V3</sub> × 1.22–1.25.

## 5.2 Năng lượng một lần đo

Trình tự (xem [06](06-firmware.md)): bật VSENS (soft-start 1 ms) → chờ 45 ms → đọc module I²C → **light-sleep** tới 1500 ms
(`CONFIG_SOIL_SETTLE_MS`, chân IO10/IO11 được giữ bằng `gpio_hold`) → bật cầu chia pin 3 ms → ADC → tắt tất cả.

| Thành phần | Dòng (3.3 V) | Thời gian | Điện tích |
|---|---|---|---|
| Module độ ẩm đất (VSENS) | 5 mA | 1.55 s | 7.75 mAs |
| Module I²C (cận trên 0.3–1 mA, không có LED nguồn) | 1 mA | 1.55 s | 1.55 mAs |
| Cầu chia NTC (3.3 V / 20 kΩ ở 25 °C) | 0.165 mA | 1.55 s | 0.26 mAs |
| MCU thức: soft-start, đọc I²C (AHT20 80 ms là trường hợp dài nhất), ADC | ~7 mA | ~0.12 s | 0.84 mAs |
| Cầu chia pin (VBAT / 200 kΩ) | 15 µA | ~10 ms | ≈ 0 |
| **Tổng** | | | **10.40 mAs** (chỉ có module đất: 8.59 mAs) |

So với v1 (đầu dò in trên PCB, ~80 ms thức, 0.65 mAs/lần), một lần đo đắt hơn ~16 lần vì module mua sẵn cần ~1 s để ổn định.
Nhờ CPU light-sleep trong lúc chờ, phần MCU chỉ còn 0.84 mAs; nếu CPU thức suốt 1.5 s (~7 mA) thì sẽ tốn thêm ~10 mAs mỗi lần.

## 5.3 Ngân sách năng lượng một ngày

Kết quả `power_budget.py` (pin CR123A 1500 mAh, dùng được 85 %, tự xả 1 %/năm, V<sub>pin</sub> trung bình 3.0 V; số báo cáo/ngày
= 50 % số lần đo + 1 heartbeat/giờ):

```
one measurement at the 3.3 V rail (all modules):
  soil module    7.75 mAs
  I2C module     1.55 mAs
  NTC divider    0.26 mAs
  MCU awake      0.84 mAs
  total         10.40 mAs   (soil module only: 8.59 mAs)
```

| Kịch bản (đủ 3 module trừ khi ghi khác) | Ngủ (mAh/ngày @3V3) | Poll | Đo | Báo cáo | **Pin mAh/ngày** | **I trung bình** | **Tuổi thọ** |
|---|---|---|---|---|---|---|---|
| SIT, slow-poll 15 s, +10 dBm, đo 15 phút (mặc định) | 0.607 | 0.400 | 0.277 | 0.030 | **1.63** | **67.7 µA** | **≈ 2.1 năm** |
| SIT, slow-poll 15 s, +20 dBm | 0.607 | 0.496 | 0.277 | 0.030 | 1.74 | 72.6 µA | ≈ 2.0 năm |
| LIT, slow-poll 60 s, +10 dBm | 0.607 | 0.100 | 0.277 | 0.030 | 1.26 | 52.4 µA | **≈ 2.7 năm** |
| LIT, slow-poll 120 s, +10 dBm | 0.607 | 0.050 | 0.277 | 0.030 | 1.20 | 49.9 µA | ≈ 2.8 năm |
| SIT 15 s, đo mỗi 30 phút | 0.607 | 0.400 | 0.139 | 0.020 | 1.44 | 60.1 µA | ≈ 2.4 năm |
| SIT 15 s, chỉ module đất (không I²C, không NTC) | 0.607 | 0.400 | 0.229 | 0.030 | 1.57 | 65.3 µA | ≈ 2.2 năm |
| LIT 60 s, đo mỗi 30 phút | 0.607 | 0.100 | 0.139 | 0.020 | 1.08 | 44.9 µA | ≈ 3.1 năm |

Nhận xét:
- **Dòng ngủ light-sleep (~25 µA) vẫn chiếm phần lớn nhất: ~47 % (SIT) đến ~60 % (LIT)** – giới hạn cứng của Matter-over-Thread
  trên ESP32-H2 (phải giữ RAM + liên kết Thread).
- **Đo cảm biến nay chiếm ~21 % (SIT) / ~27 % (LIT)** năng lượng (v1: < 2 %), chủ yếu là 5 mA của module đất trong 1.5 s. Các núm
  vặn: tăng `CONFIG_SOIL_MEAS_PERIOD_S` (độ ẩm đất thay đổi chậm, 30 phút thường đủ), giảm `CONFIG_SOIL_SETTLE_MS` nếu đo bằng
  oscilloscope thấy AOUT của module ổn định sớm hơn (năng lượng đo gần tỉ lệ thuận với thời gian VSENS bật), không cắm module
  không dùng, gỡ LED nguồn trên module I²C.
- Poll Thread là thành phần lớn thứ hai ở SIT (~30 %) → giảm bằng **LIT ICD** (`sdkconfig.defaults.lit`, slow-poll 60 s) khi
  controller hỗ trợ Check-In (Matter ≥ 1.3; ví dụ Home Assistant/Apple mới). Nếu controller không đăng ký Check-In, LIT tự hoạt
  động như SIT.
- Giảm TX từ +20 dBm xuống +10 dBm tiết kiệm ~6 % – kiểm tra RSSI/LQI tại vị trí lắp đặt trước khi giảm thêm.
- Pin lạnh (< 0 °C) mất 10–30 % dung lượng; tuổi thọ thực tế ngoài trời nên tính **~1.5–2 năm** cho cấu hình mặc định,
  **~2–3 năm** với LIT + đo 30 phút.
- Nếu không cần nhận lệnh từ xa thường xuyên, có thể tăng `CONFIG_ICD_IDLE_MODE_INTERVAL_SEC` để controller đặt
  subscription max-interval dài hơn (ít báo cáo liveness).

### Vì sao không dùng deep-sleep giữa các lần đo?
Deep-sleep (7 µA) sẽ tiết kiệm hơn nhưng làm mất RAM: thiết bị phải **gắn lại mạng Thread** (MLE child update) và controller
phải **thiết lập lại phiên CASE + subscription** mỗi lần thức → tốn hàng chục mAs và làm thiết bị “offline” trong ứng dụng nhà.
Matter ICD được thiết kế cho light-sleep + slow-poll; firmware chỉ dùng deep-sleep khi pin cạn (khóa an toàn).

## 5.4 Cách đo kiểm thực tế

1. Tháo **R10** (0 Ω), hàn hai dây vào hai pad → nối Nordic PPK2 / Joulescope (chế độ ampe kế, nguồn từ pin).
2. Hoặc dùng PPK2 ở chế độ *source* 3.0 V cấp vào J2/J3 (thay cho pin).
3. Kỳ vọng (SIT, đủ module): nền ~30–35 µA (phía pin), xung poll mỗi 15 s, mỗi 15 phút một “bậc” ~7–8 mA (phía pin) kéo dài
   ~1.5 s khi VSENS bật, trung bình ~65–70 µA.
4. Nếu nền > 50 µA: kiểm tra VSENS có tắt hẳn không (TP4 = 0 V), LED/PM lock (log `esp_pm_dump_locks`), chân I²C còn pull-up
   nội không, R6/R9 lắp đúng, module bị cấp ngược qua SDA/SCL hoặc AOUT.
