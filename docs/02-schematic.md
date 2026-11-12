# 2. Schematic chi tiết theo khối

Nguồn KiCad: `hardware/h2-soil-sensor.kicad_sch` (sheet gốc + 4 sheet con, nối bằng global label).
Bản PDF: [`hardware/docs/schematic.pdf`](../hardware/docs/schematic.pdf) — trang 1 sơ đồ khối, 2 Power, 3 MCU,
4 Sensors (cổng module đất), 5 UI (nút, LED, pad nạp).

Schematic được sinh từ `hardware/tools/design.py` (nguồn sự thật duy nhất: giá trị, mã LCSC/MPN, net, ghi chú) bằng
`gen_schematic.py`, sau đó `check_netlist.py` xuất netlist bằng `kicad-cli` và đối chiếu **từng chân** với thiết kế (thay
cho ERC vì KiCad 7 CLI chưa có ERC): `nets: 41  components checked: 43 – OK` (28 net có tên + 13 chân NC của module;
39 linh kiện + 4 PWR_FLAG).

---

## 2.1 Khối nguồn (sheet *Power*)

```
 (a) Pin vào, chống ngược cực, buck-boost 3.3 V
 J3 pad 1 "+" ── VBAT_RAW ──D┤ Q1 AO3415A ├S── VBAT ──[ R10 0 Ω ]── VIN_BB ──► U1 VIN (10), EN (1)
 J3 pad 2 "−" ── GND           G ── R1 100 kΩ ── GND
 VBAT   ── C1 47 µF ── GND
 VIN_BB ── C2 10 µF ‖ C3 100 nF ── GND
 U1 SEL (2) ── GND      CFG1 (3) ── R2 36.5 kΩ ── GND      CFG2 (4) ── R3 0 Ω ── GND      CFG3 (5) ── R4 16.2 kΩ ── GND
 U1 LX1 (9) ── L1 2.2 µH ── LX2 (7)          U1 GND (8), EP ── GND
 U1 VOUT (6) ── +3V3 ── C4 22 µF ‖ C5 22 µF ── GND;   +3V3 cũng ra pad nạp J1-1

 (b) Đo điện áp pin (không rò khi ngủ)
 VBAT ──┬──────────────── S┤ Q2 AO3401A ├D ── VBAT_SW ── R7 100 kΩ ──┬── VBAT_ADC → IO2
        R5 1 MΩ                G                                     ├── R8 100 kΩ ── GND
        └──── QB_G ────────────┴── D┤ Q3 2N7002 ├S ── GND            └── C6 10 nF ── GND
                                        G ── VBAT_MEAS_EN ← IO11, R6 100 kΩ ── GND

 (c) Công tắc nguồn module độ ẩm đất
 +3V3 ── S┤ Q4 AO3401A ├D ── VSENS ──┬── C7 1 µF ── GND
             G                       └──► J4-2 (VCC module), C14 1 µF
             └── SENS_PWR_EN_N ← IO10, R9 100 kΩ lên +3V3
```

### Cổng pin (J3)
- **J3**: 2 pad xuyên lỗ Ø2.1 mm, lỗ 1.1 mm, bước 4.6 mm (footprint KiCad cho dây 0.5 mm²): **pad 1 vuông = “+”** (VBAT_RAW),
  **pad 2 tròn = “−”** (GND); silkscreen “− BAT +”. Hàn thẳng dây của hộp pin CR123A, không có đế pin hay đầu cắm trên bo.
- Màu dây của hộp pin không phải lúc nào cũng đúng → có Q1; vẫn nên đo cực trước khi hàn.

### Chống ngược cực (Q1, R1)
- P-MOSFET mắc ngược chiều thông thường: **cực D ở phía pin**, S ở phía tải, G về GND qua R1 100 kΩ.
  Khi lắp đúng, diode thân dẫn trước → V<sub>S</sub> ≈ V<sub>pin</sub> − 0.6 V → V<sub>GS</sub> ≈ −V<sub>pin</sub> → kênh dẫn hoàn toàn.
- Lắp ngược: V<sub>GS</sub> = 0, diode thân phân cực ngược → không có dòng. Sụt áp khi dẫn: 0.26 A × 65 mΩ ≈ 17 mV (trường hợp xấu nhất: TX +20 dBm, pin 2.0 V).
- V<sub>GS(max)</sub> ±8 V của AO3415A thỏa với cả pin sạc 4.2 V.
- **C1 47 µF** trên VBAT cấp xung TX khi pin lạnh và bù trở kháng của dây hộp pin.

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
- R10 (0 Ω) là “cầu đo dòng”: tháo ra và gắn PPK2/µCurrent để đo dòng toàn hệ (kể cả module đất).

### Đo điện áp pin (Q2, Q3, R5–R8, C6)
- Cầu chia R7/R8 = 100k/100k → V<sub>ADC</sub> = V<sub>BAT</sub>/2 (1.0–1.65 V, ADC ATTEN 6 dB 0–1.9 V, sai số ±12 mV → ±24 mV ở V<sub>BAT</sub>).
- Công tắc high-side Q2 (AO3401A): S ở VBAT, gate kéo lên VBAT bằng R5 1 MΩ → **mặc định OFF**.
  Q3 (2N7002) kéo gate Q2 xuống GND khi `VBAT_MEAS_EN` = 1. R6 100 kΩ giữ Q3 OFF khi MCU ngủ/reset.
- Dùng P-FET + N-FET thay vì cầu chia nối thẳng: với V<sub>BAT</sub> > 3.3 V (pin mới hoặc pin sạc) gate P-FET vẫn tắt
  hoàn toàn vì được kéo về chính V<sub>BAT</sub>, không phụ thuộc mức logic 3.3 V.
- C6 10 nF + 50 kΩ (Thevenin) → τ = 0.5 ms; firmware bật cầu chia ở cuối cửa sổ đo và chờ 3 ms (≈ 6 τ) rồi mới đọc ADC.
- Dòng khi đo: 15 µA × ~10 ms mỗi lần đo → không đáng kể. Khi tắt: chỉ rò I<sub>DSS</sub> (nA).

### Công tắc VSENS (Q4, R9, C7) và soft-start
- Q4 AO3401A high-side, gate kéo lên +3V3 (R9) → VSENS tắt khi GPIO10 Hi-Z; GPIO10 kéo thấp để bật. VSENS chỉ nuôi module
  độ ẩm đất (~5 mA), bật ~1.5 s mỗi lần đo → sụt trên Q4 không đáng kể.
- Tụ trên VSENS cố ý nhỏ: C7 1 µF + C14 1 µF (cộng tụ trên module). Nếu Q4 đóng cứng, tụ VSENS chia điện tích với tụ +3V3
  (C4 + C5 + C8 + C9 ≈ 54 µF danh định): sụt ≈ 2 / (54 + 2) × 3.3 V ≈ 0.12 V chỉ riêng tụ trên bo.
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
- **EN**: module đã có RC 10 kΩ/1 µF bên trong → không cần tụ ngoài; EN chỉ đưa ra pad nạp J1-5 (không có nút RESET: reset
  bằng cách chạm pad 5 xuống GND hoặc tháo/lắp pin).
- **Strapping**: IO9 kéo lên 10 kΩ (R21, sheet UI) → SPI boot; nhấn SW1 khi reset → download mode.
  IO8 kéo lên 10 kΩ (R11) theo khuyến nghị (cần =1 cho joint download boot). IO25 (strap JTAG) bỏ trống – bị bỏ qua với eFuse mặc định.
- **VBAT (pin 14)** để NC: bên trong module đã nối với 3V3.
- Không có thạch anh 32.768 kHz (IO13/IO14 để trống): đồng hồ ngủ dùng RC nội 136 kHz.
- Các chân LP (IO8–IO14) dùng cho tín hiệu cần giữ mức trong light-sleep (IO10/IO11 được `gpio_hold` trong lúc chờ module
  ổn định); các chân số chỉ dùng khi thức. IO3, IO4, IO5, IO12, IO13, IO14, IO22, IO25 không nối, firmware đặt Hi-Z.

---

## 2.3 Khối cổng module độ ẩm đất (sheet *Sensors*)

```
 J4 (module đất)  1 GND ── GND
                  2 VCC ── VSENS ── C14 1 µF ── GND
                  3 AOUT ── SOIL_AOUT ──┬── R12 1 kΩ ──┬── SOIL_ADC → IO1 (ADC1_CH0, 12 dB)
                                        │              └── C13 10 nF ── GND
                                        └── D3 LESD5Z3.3T1G: K (1) = SOIL_AOUT, A (2) = GND
```

### Cổng J4 và module
- J4 JST-PH 2.0 3P: 1 = GND, 2 = VCC (VSENS), 3 = AOUT – cùng thứ tự GND/VCC/AOUT với cổng PH2.0-3P của module; silkscreen
  “SOIL” + “A V G” (trái → phải, chân 1 GND ở bên phải). Cáp đi kèm module thường là PH2.0 → Dupont cái nên **không cắm được vào J4**: dùng cáp PH2.0-3P hai đầu nối
  thẳng (hoặc bấm lại đầu) và **đo cáp trước khi cắm** (đảo VCC/GND có thể làm hỏng module).
- Module chạy 3.3–5.5 V, AOUT 0–3.0 V, ~5 mA ([DFRobot SEN0193](https://wiki.dfrobot.com/sen0193/)) → nuôi thẳng từ VSENS 3.3 V,
  AOUT vào ADC ATTEN 12 dB (0–3.3 V) không cần cầu chia.

### Mạch vào analog (R12, C13) và chống ESD (D3)
- **R12 1 kΩ** hạn dòng vào chân ADC khi cáp nhận xung/quá áp (D3 kẹp trước, R12 hạn phần dư). **C13 10 nF** cùng R12 tạo lọc
  RC τ = 10 µs (f<sub>c</sub> ≈ 16 kHz) chống nhiễu cáp và giữ điện tích cho tụ lấy mẫu của ADC.
- **D3 LRC LESD5Z3.3T1G** (SOD-523, C136161): TVS một chiều, cathode ở SOIL_AOUT, anode ở GND. Xung dương bị kẹp (điện áp làm
  việc 3.3 V ≥ AOUT tối đa 3.0 V), xung âm đi qua chiều thuận về GND. Theo mô tả LCSC: 200 W (8/20 µs), kẹp 14.1 V ở 11.2 A,
  105 pF (không ảnh hưởng tín hiệu gần như DC), rò ≤ 1 µA – phần rò này cộng vào tải của AOUT và được hiệu chuẩn cùng module.
  Thay thế: onsemi ESD5Z3.3T1G (C61148, rò 50 nA, tồn kho ít).
- **C14 1 µF** đặt cạnh J4 làm tụ đệm cục bộ cho module; cố ý nhỏ để hạn dòng nạp khi bật VSENS.
- Firmware: chờ `CONFIG_SOIL_SETTLE_MS` = 1500 ms sau khi bật VSENS (module cần ~1 s để mạch dao động + tách đỉnh/RC ổn định),
  đọc 64 mẫu (trimmed mean); AOUT < 200 mV (`CONFIG_SOIL_MODULE_MIN_MV`) = không có module/chập → bỏ qua giá trị.
- Điểm mặc định KHÔ = 2500 mV, ƯỚT = 1200 mV (module v1.2 ở 3.3 V: ~2.2–2.8 V trong không khí, ~1.0–1.4 V trong nước)
  → **phải hiệu chuẩn từng module** (nhấn 2 lần / 3 lần, xem [06](06-firmware.md)).

---

## 2.4 Khối nút nhấn / LED / pad nạp (sheet *UI*)

| Ký hiệu | Chức năng |
|---|---|
| SW1 + R21 10k + C21 100 nF | Nút BOOT/USER trên IO9 (kéo lên ngoài, chống dội RC τ = 1 ms; vẫn lên mức 1 trước khi EN của module lên ~10 ms). |
| D2 + R22 1 kΩ | LED đỏ ~1.5 mA trên IO0, chỉ nháy khi cần. |
| J1 – 8 pad tròn | Pad SMD Ø1.5 mm, lưới 2.54 mm, không phủ kem hàn (phẳng cho kim pogo). Hàng sát mép bo (trái → phải): **1 = 3V3, 3 = TX, 5 = EN, 7 = D−**; hàng trong: **2 = GND, 4 = RX, 6 = IO9, 8 = D+**. Chữ “1” in cạnh pad 1. |

**Nạp firmware** (kẹp/đồ gá pogo 2 × 4 bước 2.54 mm, hoặc hàn dây tạm vào pad):
- *USB Serial/JTAG*: lắp pin, nối USB D+ (pad 8), D− (pad 7), GND (pad 2) tới cổng USB của PC (không nối 5 V/3V3).
  `idf.py -p /dev/ttyACM0 flash monitor`.
- *UART*: TX (pad 3) / RX (pad 4) nối chéo với adapter USB-UART 3.3 V, GND (pad 2). Vào download mode: giữ SW1 (IO9 = 0) rồi
  chạm EN (pad 5) xuống GND; adapter có tín hiệu EN/BOOT (mạch tự động DTR/RTS) thì nối thêm pad 5 và pad 6 (IO9).
  Chỉ cấp 3.3 V từ adapter vào pad 1 khi **đã tháo pin** (không để hai nguồn song song).
