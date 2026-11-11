# 5. Dòng tiêu thụ và tuổi thọ pin

Mô hình tính toán có thể chỉnh tham số: [`docs/power_budget.py`](power_budget.py) (`python3 docs/power_budget.py`).
Số liệu nguồn: datasheet ESP32-H2 (bảng 5-7, 5-9), đo dạng sóng ICD của Espressif trên ESP32-H2 (`esp-matter/examples/icd_app`),
datasheet TPS63900, TLC555, SHT40.

## 5.1 Dòng tiêu thụ theo trạng thái (tại rail 3.3 V)

| Trạng thái | Dòng | Thời gian / tần suất | Ghi chú |
|---|---|---|---|
| **Light-sleep (ICD idle)** | **25 µA** (ESP32-H2) + ~0.3 µA rò bo | phần lớn thời gian | CPU, radio, miền TOP tắt; RAM giữ; flash tắt (`CONFIG_ESP_SLEEP_POWER_DOWN_FLASH`). Espressif đo ~27 µA trên DevKit |
| TPS63900 Iq | 75 nA (phía pin) | liên tục | hiệu suất ~88 % ở 30 µA, ~90 % ở mA |
| Cầu chia pin, VSENS, NTC, I²C pull-up | **0** (tắt bằng MOSFET) | – | chỉ rò I<sub>DSS</sub> (nA) |
| Thread data poll (SED/ICD slow-poll) | xung RX 25 mA / TX 36–140 mA | 1 lần mỗi 15 s (SIT) hoặc 60 s (LIT) | ≈ **0.25 mAs/poll** ở +10 dBm, 0.31 mAs ở +20 dBm (đo của Espressif: 0.31 mC/poll tại +20 dBm) |
| Đo cảm biến | ~8 mA (CPU 96 MHz idle + TLC555 0.7 mA + SHT40 0.32 mA + cầu chia 15 µA + NTC 0.17 mA) | ~80 ms mỗi 15 phút | ≈ 0.65 mAs/lần |
| Báo cáo (subscription report) | ICD active mode 1 s, fast-poll 500 ms, TX/RX + MRP ACK + mã hoá | ~72 lần/ngày | ≈ 1.5 mAs/lần (ước tính) |
| LED | 1.5 mA | 60 ms khi nhấn nút | không đáng kể |
| TX 802.15.4 +20 / +9 / 0 dBm | 140 / 60 / 36 mA | vài trăm µs mỗi khung | mặc định firmware đặt **+10 dBm** |
| BLE commissioning (một lần) | ~3–6 mA trung bình | ≤ 15 phút | ≈ 1–1.5 mAh mỗi lần ghép nối |
| OTA firmware (~1.7 MB qua Thread) | ~15–20 mA | 10–20 phút | ≈ 3–6 mAh mỗi lần cập nhật |
| Deep-sleep (pin cạn, khoá máy) | 7 µA | – | khi VBAT < 2.05 V, chờ nhấn nút |

Quy đổi về dòng pin: I<sub>pin</sub> = I<sub>3V3</sub> × 3.3 V / (V<sub>pin</sub> × η) ≈ I<sub>3V3</sub> × 1.22–1.25.

## 5.2 Ngân sách năng lượng một ngày

Kết quả từ `power_budget.py` (pin CR123A 1500 mAh, dùng được 85 %, tự xả 1 %/năm, V<sub>pin</sub> trung bình 3.0 V):

| Kịch bản | Ngủ (mAh/ngày @3V3) | Poll | Đo | Báo cáo | **Pin mAh/ngày** | **I trung bình** | **Tuổi thọ** |
|---|---|---|---|---|---|---|---|
| SIT, slow-poll 15 s, +10 dBm (mặc định) | 0.607 | 0.400 | 0.017 | 0.030 | **1.31** | **54 µA** | **≈ 2.6 năm** |
| SIT, slow-poll 15 s, +20 dBm | 0.607 | 0.496 | 0.017 | 0.030 | 1.42 | 59 µA | ≈ 2.4 năm |
| LIT, slow-poll 60 s, +10 dBm | 0.607 | 0.100 | 0.017 | 0.030 | 0.94 | 39 µA | **≈ 3.6 năm** |
| LIT, slow-poll 120 s, +10 dBm | 0.607 | 0.050 | 0.017 | 0.030 | 0.88 | 37 µA | ≈ 3.8 năm |

Nhận xét:
- **Dòng ngủ light-sleep (~25 µA) chiếm 55–70 % năng lượng** – nó là giới hạn cứng của Matter-over-Thread trên ESP32-H2
  (phải giữ RAM + liên kết Thread). Chu kỳ đo (15 phút) gần như không ảnh hưởng (< 2 %).
- Poll Thread là thành phần lớn thứ hai → giảm bằng **LIT ICD** (`sdkconfig.defaults.lit`, slow-poll 60 s) khi controller hỗ trợ
  Check-In (Matter ≥ 1.3; ví dụ Home Assistant/Apple mới). Nếu controller không đăng ký Check-In, LIT tự hoạt động như SIT.
- Giảm TX từ +20 dBm xuống +10 dBm tiết kiệm ~8 % – kiểm tra RSSI/LQI tại vị trí lắp đặt trước khi giảm thêm.
- Pin lạnh (< 0 °C) mất 10–30 % dung lượng; tuổi thọ thực tế ngoài trời nên tính **~2–3 năm** cho cấu hình mặc định.
- Nếu không cần nhận lệnh từ xa thường xuyên, có thể tăng `CONFIG_ICD_IDLE_MODE_INTERVAL_SEC` để controller đặt
  subscription max-interval dài hơn (ít báo cáo liveness).

### Vì sao không dùng deep-sleep giữa các lần đo?
Deep-sleep (7 µA) sẽ tiết kiệm hơn nhưng làm mất RAM: thiết bị phải **gắn lại mạng Thread** (MLE child update) và controller
phải **thiết lập lại phiên CASE + subscription** mỗi lần thức → tốn hàng chục mAs và làm thiết bị “offline” trong ứng dụng nhà.
Matter ICD được thiết kế cho light-sleep + slow-poll; firmware chỉ dùng deep-sleep khi pin cạn (khóa an toàn).

## 5.3 Cách đo kiểm thực tế

1. Tháo **R10** (0 Ω), hàn hai dây vào hai pad → nối Nordic PPK2 / Joulescope (chế độ ampe kế, nguồn từ pin).
2. Hoặc dùng PPK2 ở chế độ *source* 3.0 V cấp vào giá pin.
3. Kỳ vọng: nền ~30–35 µA (phía pin), xung poll mỗi 15 s, xung đo ~80 ms mỗi 15 phút, trung bình 50–60 µA (SIT).
4. Nếu nền > 50 µA: kiểm tra LED/PM lock (log `esp_pm_dump_locks`), chân I²C có pull-up nội không, R6/R9 lắp đúng, SHT40 bị
   cấp ngược qua I²C.
