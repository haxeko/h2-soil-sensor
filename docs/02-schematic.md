# 2. Schematic chi tiết theo khối

Nguồn KiCad: `hardware/h2-soil-sensor.kicad_sch` (sheet gốc + 4 sheet con, nối bằng global label).
Bản PDF: [`hardware/docs/schematic.pdf`](../hardware/docs/schematic.pdf) — trang 1 sơ đồ khối, 2 Power, 3 MCU,
4 Sensors (cổng module), 5 UI.

Schematic được sinh từ `hardware/tools/design.py` (nguồn sự thật duy nhất: giá trị, mã LCSC/MPN, net, ghi chú) bằng
`gen_schematic.py`, sau đó `check_netlist.py` xuất netlist bằng `kicad-cli` và đối chiếu **từng chân** với thiết kế (thay
cho ERC vì KiCad 7 CLI chưa có ERC): `nets: 41  components checked: 61 – OK` (33 net có tên + 8 chân NC của module;
57 linh kiện + 4 PWR_FLAG).

---

## 2.1 Khối nguồn (sheet *Power*)

```
 (a) Pin vào, chống ngược cực, buck-boost 3.3 V
 J2-1 (BAT+), J3 "+" ── VBAT_RAW ──D┤ Q1 AO3415A ├S── VBAT ──[ R10 0 Ω ]── VIN_BB ──► U1 VIN (10), EN (1)
 J2-2, J3 "−" ── GND                  G ── R1 100 kΩ ── GND
 VBAT   ── C1 47 µF ── GND, TP1
 VIN_BB ── C2 10 µF ‖ C3 100 nF ── GND
 U1 SEL (2) ── GND      CFG1 (3) ── R2 36.5 kΩ ── GND      CFG2 (4) ── R3 0 Ω ── GND      CFG3 (5) ── R4 16.2 kΩ ── GND
 U1 LX1 (9) ── L1 2.2 µH ── LX2 (7)          U1 GND (8), EP ── GND
 U1 VOUT (6) ── +3V3 ── C4 22 µF ‖ C5 22 µF ── GND, TP2

 (b) Đo điện áp pin (không rò khi ngủ)
 VBAT ──┬──────────────── S┤ Q2 AO3401A ├D ── VBAT_SW ── R7 100 kΩ ──┬── VBAT_ADC → IO2
        R5 1 MΩ                G                                     ├── R8 100 kΩ ── GND
        └──── QB_G ────────────┴── D┤ Q3 2N7002 ├S ── GND            └── C6 10 nF ── GND
                                        G ── VBAT_MEAS_EN ← IO11, R6 100 kΩ ── GND

 (c) Công tắc nguồn module cảm biến
 +3V3 ── S┤ Q4 AO3401A ├D ── VSENS ──┬── C7 1 µF ── GND, TP4
             G                       └──► J4-2, J6-1 (VCC module), R18 (NTC), R19/R20 (pull-up I²C), U3 VP, C14, C20
             └── SENS_PWR_EN_N ← IO10, R9 100 kΩ lên +3V3
```

### Cổng pin (J2, J3)
- **J2** JST-PH 2.0 2P: chân 1 = BAT+ (VBAT_RAW), chân 2 = GND. **J3**: 2 pad Ø2.1 mm, lỗ 1.1 mm, bước 4.6 mm (footprint
  KiCad cho dây 0.5 mm²), pad vuông = “+”, silkscreen “+ / −”. J2 và J3 **song song** – chỉ dùng một trong hai, không bao giờ
  nối hai pin cùng lúc.
- Thứ tự cực của cáp/hộp pin có đầu JST không thống nhất giữa các hãng → có Q1; vẫn nên đo cực trước khi cắm.

### Chống ngược cực (Q1, R1)
- P-MOSFET mắc ngược chiều thông thường: **cực D ở phía pin**, S ở phía tải, G về GND qua R1 100 kΩ.
  Khi lắp đúng, diode thân dẫn trước → V<sub>S</sub> ≈ V<sub>pin</sub> − 0.6 V → V<sub>GS</sub> ≈ −V<sub>pin</sub> → kênh dẫn hoàn toàn.
- Lắp ngược: V<sub>GS</sub> = 0, diode thân phân cực ngược → không có dòng. Sụt áp khi dẫn: 0.26 A × 65 mΩ ≈ 17 mV (trường hợp xấu nhất: TX +20 dBm, pin 2.0 V).
- V<sub>GS(max)</sub> ±8 V của AO3415A thỏa với cả pin sạc 4.2 V.
- **C1 47 µF** trên VBAT cấp xung TX khi pin lạnh; ở v2 càng quan trọng vì dây pin dài làm tăng trở kháng nguồn.

### Buck-boost TPS63900 (U1)
| Chân | Nối | Ý nghĩa |
|---|---|---|
| EN (1) | VIN_BB | luôn bật (UVLO nội 1.75 V lên / 1.65 V xuống) |
| SEL (2) | GND | chọn V<sub>O(1)</sub> = cấu hình CFG3 |
| CFG1 (3) | R2 = 36.5 kΩ 1 % | V<sub>O(2)</sub> = 3.3 V (dự phòng nếu SEL = 1) |
| CFG2 (4) | R3 = 0 Ω | giới hạn dòng vào = **unlimited** (511 Ω → 100 mA, 1.15 kΩ → 50 mA …) |
| CFG3 (5) | R4 = 16.2 kΩ 1 % | **V<sub>O(1)</sub> = 3.3 V** |
| LX1/LX2 | L1 2.2 µH | I<sub>SAT</sub> ≥ 2 A cho chế độ unlimited |
| VIN | C2 10 µF + C3 100 nF (+ C1 47 µF bulk trên VBAT) | |
| VOUT | C4 + C5 = 2 × 22 µF | ≥ 10 µF hiệu dụng sau DC-bias; thêm bulk cho xung TX |

- Điện trở CFG đọc **một lần lúc khởi động** (R2D), yêu cầu sai số tổng ≤ ±3 % → dùng 1 %/100 ppm, **không** đặt tụ
  lên chân CFG (< 10 pF).
- Chọn “unlimited” vì CR123A (Li-MnO<sub>2</sub> cuộn xoắn) chịu xung tốt; nếu dùng pin Li-SOCl<sub>2</sub> (ER14250…) thì đặt
  R3 = 511 Ω (100 mA) hoặc 1.15 kΩ (50 mA) và tăng C4/C5.
- R10 (0 Ω) là “cầu đo dòng”: tháo ra và gắn PPK2/µCurrent để đo dòng toàn hệ (kể cả module cảm biến).

### Đo điện áp pin (Q2, Q3, R5–R8, C6)
- Cầu chia R7/R8 = 100k/100k → V<sub>ADC</sub> = V<sub>BAT</sub>/2 (1.0–1.65 V, ADC ATTEN 6 dB 0–1.9 V, sai số ±12 mV → ±24 mV ở V<sub>BAT</sub>).
- Công tắc high-side Q2 (AO3401A): S ở VBAT, gate kéo lên VBAT bằng R5 1 MΩ → **mặc định OFF**.
  Q3 (2N7002) kéo gate Q2 xuống GND khi `VBAT_MEAS_EN` = 1. R6 100 kΩ giữ Q3 OFF khi MCU ngủ/reset.
- Dùng P-FET + N-FET thay vì cầu chia nối thẳng: với V<sub>BAT</sub> > 3.3 V (pin mới hoặc pin sạc) gate P-FET vẫn tắt
  hoàn toàn vì được kéo về chính V<sub>BAT</sub>, không phụ thuộc mức logic 3.3 V.
- C6 10 nF + 50 kΩ (Thevenin) → τ = 0.5 ms; firmware bật cầu chia ở cuối cửa sổ đo và chờ 3 ms (≈ 6 τ) rồi mới đọc ADC.
- Dòng khi đo: 15 µA × ~10 ms mỗi lần đo → không đáng kể. Khi tắt: chỉ rò I<sub>DSS</sub> (nA).

### Công tắc VSENS (Q4, R9, C7) và soft-start
- Q4 AO3401A high-side, gate kéo lên +3V3 (R9) → VSENS tắt khi GPIO10 Hi-Z; GPIO10 kéo thấp để bật. VSENS nuôi **mọi module
  bên ngoài**, chỉ bật ~1.5 s mỗi lần đo; dòng khi đo ~5–7 mA (module đất ~5 mA + module I²C + NTC 0.17 mA) → sụt trên Q4 không đáng kể.
- Tụ trên VSENS cố ý nhỏ: C7 1 µF + C14 1 µF + C20 100 nF ≈ 2.1 µF (cộng tụ trên module, không biết trước). Nếu Q4 đóng cứng,
  tụ VSENS chia điện tích với tụ +3V3 (C4 + C5 + C8 + C9 ≈ 54 µF danh định): sụt ≈ 2.1 / (54 + 2.1) × 3.3 V ≈ 0.12 V chỉ riêng
  tụ trên bo, nhiều hơn nếu module có tụ lớn.
- Vì vậy firmware **soft-start**: `board_sensor_power(true)` trước hết chỉ bật pull-down nội yếu (~45 kΩ) của IO10 chống lại
  R9 100 kΩ → gate Q4 bị kéo xuống qua trở kháng cao (R9 ‖ R<sub>pd</sub> ≈ 31 kΩ) nên Q4 mở từ từ, dòng nạp được trải ra; sau
  `CONFIG_VSENS_SOFTSTART_US` (mặc định 1000 µs, 0 = tắt) IO10 mới bị lái xuống 0 V cứng.

### PWR_FLAG
GND, VBAT, VSENS, VIN_BB có PWR_FLAG để ERC trong KiCad không báo “power input not driven”.

---

## 2.2 Khối MCU (sheet *MCU*)

- **U2 ESP32-H2-WROOM-02C** (18 × 20 mm): footprint riêng `h2soil:ESP32-H2-WROOM-02C` theo land pattern datasheet v1.2
  (pad 1.5 × 0.9 mm, bước 1.5 mm, EPAD chia 2 phần 2.8 × 0.55 + 2.8 × 1.6 mm với 9 via nhiệt).
- Tụ nguồn: **C8 10 µF + C9 100 nF** sát chân 3V3 (pin 1).
- **EN**: module đã có RC 10 kΩ/1 µF bên trong → C12 để DNP; EN chỉ đưa ra header J1-5 (v2 không có nút RESET: reset bằng
  cách chạm J1-5 xuống GND hoặc tháo/lắp pin).
- **Strapping**: IO9 kéo lên 10 kΩ (R21, sheet UI) → SPI boot; nhấn SW1 khi reset → download mode.
  IO8 kéo lên 10 kΩ (R11) theo khuyến nghị (cần =1 cho joint download boot). IO25 (strap JTAG) bỏ trống – bị bỏ qua với eFuse mặc định.
- **VBAT (pin 14)** để NC: bên trong module đã nối với 3V3.
- **Thạch anh 32.768 kHz (Y1, C10, C11 – DNP)** trên IO13/IO14: lắp khi cần đồng hồ ngủ chính xác (CSL/SSED), bật
  `CONFIG_RTC_CLK_SRC_EXT_CRYS` (file `sdkconfig.defaults.xtal32k`). C10/C11 = 18 pF cho C<sub>L</sub> 12.5 pF (hiệu chỉnh theo bo thực).
- Các chân LP (IO8–IO14) dùng cho tín hiệu cần giữ mức trong light-sleep (IO10/IO11 được `gpio_hold` trong lúc chờ module
  ổn định); các chân số (IO0–5, IO22–27) chỉ dùng khi thức. IO4, IO5, IO25 để trống.

---

## 2.3 Khối cổng cảm biến (sheet *Sensors*)

```
 J4 (module đất)  1 GND ── GND
                  2 VCC ── VSENS
                  3 AOUT ── SOIL_AOUT ──┬── R12 1 kΩ ──┬── SOIL_ADC → IO1 (ADC1_CH0, 12 dB)
                                        └── U3 kênh 1  └── C13 10 nF ── GND

 VSENS ── R18 10 kΩ 1 % ──┬── NTC_ADC → IO3 (ADC1_CH2, 12 dB)
                          ├── C19 100 nF ── GND
                          ├── U3 kênh 3
                          └── J7-1 ── [NTC 10 kΩ B3950, ngoài bo] ── J7-2 ── GND

 J6 (module I²C)  1 VCC ── VSENS          R19 10 kΩ: VSENS ── I2C_SDA       U3 kênh 4: I2C_SDA
                  2 GND ── GND            R20 10 kΩ: VSENS ── I2C_SCL       U3 kênh 6: I2C_SCL
                  3 SCL ── I2C_SCL → IO22
                  4 SDA ── I2C_SDA → IO12

 VSENS ── C14 1 µF ‖ C20 100 nF ── GND          U3 SRV05-4: VP (5) = VSENS, VN (2) = GND
```

### Module độ ẩm đất (J4, R12, C13)
- J4: 1 = GND, 2 = VCC (VSENS), 3 = AOUT – cùng thứ tự GND/VCC/AOUT với cổng PH2.0-3P của module. Cáp PH 2.0 bán sẵn có loại
  nối thẳng và loại đảo chiều → **đo cáp trước khi cắm** (đảo VCC/GND có thể làm hỏng module).
- Module chạy 3.3–5.5 V, AOUT 0–3.0 V, ~5 mA ([DFRobot SEN0193](https://wiki.dfrobot.com/sen0193/)) → nuôi thẳng từ VSENS 3.3 V,
  AOUT vào ADC ATTEN 12 dB (0–3.3 V) không cần cầu chia.
- **R12 1 kΩ** hạn dòng vào chân ADC khi cáp nhận xung/quá áp (U3 kẹp trước, R12 hạn phần dư). **C13 10 nF** cùng R12 tạo lọc
  RC τ = 10 µs (f<sub>c</sub> ≈ 16 kHz) chống nhiễu cáp và giữ điện tích cho tụ lấy mẫu của ADC.
- Firmware: chờ `CONFIG_SOIL_SETTLE_MS` = 1500 ms sau khi bật VSENS (module cần ~1 s để mạch dao động + tách đỉnh/RC ổn định),
  đọc 64 mẫu (trimmed mean); AOUT < 200 mV (`CONFIG_SOIL_MODULE_MIN_MV`) = không có module/chập → bỏ qua giá trị.
- Điểm mặc định KHÔ = 2500 mV, ƯỚT = 1200 mV (module điển hình ở 3.3 V: ~2.4–2.8 V trong không khí, ~1.0–1.4 V trong nước)
  → **phải hiệu chuẩn từng module** (nhấn 2 lần / 3 lần, xem [06](06-firmware.md)).

### Đầu dò NTC (J7, R18, C19)
- VSENS → R18 10 kΩ 1 % → NTC_ADC → J7-1 → NTC → J7-2 → GND; ADC ATTEN 12 dB.
- R = 10k · V / (V<sub>S</sub> − V), V<sub>S</sub> = `CONFIG_NTC_SUPPLY_MV` (3300); T = 1 / (1/298.15 + ln(R/R<sub>25</sub>)/B) − 273.15 với
  R<sub>25</sub> = 10 kΩ, B = 3950 (`CONFIG_NTC_R25_OHM`, `CONFIG_NTC_BETA`).

| T | 0 °C | 25 °C | 40 °C | 60 °C |
|---|---|---|---|---|
| NTC_ADC (B3950, V<sub>S</sub> = 3.3 V) | 2.54 V | 1.65 V | 1.14 V | 0.66 V |

- V < 30 mV (chập) hoặc > V<sub>S</sub> − 30 mV (hở/không cắm) hoặc T ngoài −40…90 °C → không hợp lệ.
- C19 100 nF lọc nhiễu cáp; τ = (10k ‖ 10k) × 100 nF = 0.5 ms, rất nhỏ so với 1.5 s chờ. Dòng 3.3 V / 20 kΩ ≈ 0.17 mA ở 25 °C, chỉ khi đo.
- Phép đo dùng mV tuyệt đối: nếu +3V3 thực tế (đo ở TP2) lệch 3.3 V, đặt `CONFIG_NTC_SUPPLY_MV` theo giá trị đo.

### Module I²C (J6, R19, R20)
- J6: 1 = VCC (VSENS), 2 = GND, 3 = SCL (IO22), 4 = SDA (IO12) – thứ tự VIN GND SCL SDA của GY-SHT31-D / module AHT20.
  Board khác (ví dụ Adafruit) có thứ tự/số chân khác → nối dây theo **tên chân**, không theo vị trí.
- **R19/R20 10 kΩ** lên VSENS; module thường đã có pull-up 10 kΩ → song song ~5 kΩ, vẫn ổn ở 100 kHz. Pull-up nội của ESP32-H2 tắt.
- Sau khi đọc, `board_i2c_release()` đặt SDA/SCL thành input không pull → khi VSENS tắt không có dòng cấp ngược vào module.
- Hỗ trợ: SHT4x 0x44 (lệnh 0xFD, chờ 10 ms), SHT3x 0x44/0x45 (single-shot 0x2400, 16 ms), AHT20/AHT21 0x38 (khởi tạo 0xBE nếu
  chưa hiệu chuẩn, đo 0xAC, 80 ms); kiểm tra CRC-8 (đa thức 0x31) cho cả ba. Firmware chờ 45 ms sau khi bật VSENS (AHT20 cần 40 ms).

### Tụ VSENS (C14, C20) và chống ESD (U3)
- **C14 1 µF + C20 100 nF** đặt cạnh các cổng làm tụ đệm cục bộ; cố ý nhỏ để hạn dòng nạp khi bật VSENS (module có tụ riêng).
- **U3 SRV05-4** (SOT-23-6): kênh 1 SOIL_AOUT, 3 NTC_ADC, 4 SDA, 6 SCL; VP (5) = VSENS, VN (2) = GND. Mỗi đường có diode dẫn
  về VSENS và GND + TVS giữa VP–VN → xung ESD trên cáp được dẫn đi trước khi tới ESP32-H2. VP nối VSENS nên khi ngủ
  (VSENS = 0 V, các chân Hi-Z) mảng diode không phân cực → không rò. Theo mô tả LCSC: điện áp làm việc 5 V, ~3 pF, rò ≤ 5 µA ở 5 V.
- Thay thế cùng chân, rẻ hơn: TECH PUBLIC SRV05-4 (C558418) – theo mô tả LCSC chịu xung 60 W (Semtech: 300 W).

---

## 2.4 Khối nút nhấn / LED / nạp (sheet *UI*)

| Ký hiệu | Chức năng |
|---|---|
| SW1 + R21 10k + C21 100 nF | Nút BOOT/USER trên IO9 (kéo lên ngoài, chống dội RC τ = 1 ms; vẫn lên mức 1 trước khi EN của module lên ~10 ms). |
| D2 + R22 1 kΩ | LED đỏ ~1.5 mA trên IO0, chỉ nháy khi cần. |
| J1 1×8 2.54 mm | 1 = 3V3, 2 = GND, 3 = TXD0, 4 = RXD0, 5 = EN, 6 = IO9, 7 = USB_D−, 8 = USB_D+. Có thể chỉ để lỗ (không hàn) cho bản sản xuất. |
| TP1–TP4 | Pad Ø1 mm: VBAT, 3V3, GND, VSENS. |
| H1, H2 | Lỗ M3 (Ø3.2 mm, không mạ) để bắt bo vào hộp; không có đường mạch/via dưới đầu vít. |

**Nạp firmware:**
- *USB Serial/JTAG*: lắp pin, nối USB D+ (J1-8), D− (J1-7), GND (J1-2) tới cổng USB của PC (không nối 5 V/3V3). `idf.py -p /dev/ttyACM0 flash monitor`.
- *UART*: **tháo pin**, cấp 3.3 V từ adapter USB-UART 3.3 V vào J1-1, nối TX/RX chéo, giữ SW1 (IO9 = 0) rồi chạm EN xuống GND (J1-5) để vào download mode.
  Không cấp 3V3 ngoài khi pin đang lắp (hai nguồn song song).
