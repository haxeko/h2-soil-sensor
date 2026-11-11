# 2. Schematic chi tiết theo khối

Nguồn KiCad: `hardware/h2-soil-sensor.kicad_sch` (sheet gốc + 4 sheet con, nối bằng global label).
Bản PDF: [`hardware/docs/schematic.pdf`](../hardware/docs/schematic.pdf) — trang 1 sơ đồ khối, 2 Power, 3 MCU, 4 Sensors, 5 UI.

Schematic được sinh từ `hardware/tools/design.py` (nguồn sự thật duy nhất) bằng `gen_schematic.py`, sau đó
`check_netlist.py` xuất netlist bằng `kicad-cli` và đối chiếu **từng chân** với thiết kế (thay cho ERC vì
KiCad 7 CLI chưa có ERC): `47 net, 72 linh kiện – OK`.

---

## 2.1 Khối nguồn (sheet *Power*)

```
            Q1 AO3415A (P-FET, chống ngược cực)            R10 0R (đo dòng)
 BT1 +  ──D┤▼├S───────────●─────────────●──────────────[R10]──● VIN_BB ──●──────────┐
 CR123A     G             │ VBAT        │                      │          │          │
   −        │            C1 47µF       R5 1M                  C2 10µF    C3 100nF   │
   │       R1 100k        │             │  QB_G               │          │       ┌──┴──────────┐
  GND      GND           GND            ├────────┐            GND        GND     │10 VIN  VOUT 6├─● +3V3
                                        │      D┤ Q3 2N7002              EN 1 ───┤ 1 EN         │  │
                         VBAT ──S┤Q2├D──┼──R7 100k──● VBAT_ADC → IO2     SEL 2 ──┤ 2 SEL  LX1 9 ├──L1 2.2µH──┐
                           AO3401A G────┘           │                     GND    │        LX2 7 ├────────────┘
                                                   R8 100k  C6 10nF              │ 3 CFG1 ─R2 36.5k─GND     │
                         VBAT_MEAS_EN (IO11)──┬─G   │        │                   │ 4 CFG2 ─R3 0R────GND     │
                                             R6 100k GND     GND                 │ 5 CFG3 ─R4 16.2k─GND     │
                                              GND                                │ 8,EP GND               C4,C5 22µF
                                                                                 └─────────────┘
   +3V3 ──S┤Q4 AO3401A├D── VSENS (TLC555, NTC, SHT40, pull-up I²C) ── C7 1µF
            G── SENS_PWR_EN_N (IO10), R9 100k kéo lên +3V3
```

### Chống ngược cực (Q1, R1)
- P-MOSFET mắc ngược chiều thông thường: **cực D ở phía pin**, S ở phía tải, G về GND qua R1 100 kΩ.
  Khi lắp đúng, diode thân dẫn trước → V<sub>S</sub> ≈ V<sub>pin</sub> − 0.6 V → V<sub>GS</sub> ≈ −V<sub>pin</sub> → kênh dẫn hoàn toàn.
- Lắp ngược: V<sub>GS</sub> = 0, diode thân phân cực ngược → không có dòng. Sụt áp khi dẫn: 0.26 A × 65 mΩ ≈ 17 mV (trường hợp xấu nhất: TX +20 dBm, pin 2.0 V).
- V<sub>GS(max)</sub> ±8 V của AO3415A thỏa với cả pin sạc 4.2 V.

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
- R10 (0 Ω) là “cầu đo dòng”: tháo ra và gắn PPK2/µCurrent để đo dòng toàn hệ.

### Đo điện áp pin (Q2, Q3, R5–R8, C6)
- Cầu chia R7/R8 = 100k/100k → V<sub>ADC</sub> = V<sub>BAT</sub>/2 (1.0–1.65 V, ADC ATTEN 6 dB 0–1.9 V, sai số ±12 mV → ±24 mV ở V<sub>BAT</sub>).
- Công tắc high-side Q2 (AO3401A): S ở VBAT, gate kéo lên VBAT bằng R5 1 MΩ → **mặc định OFF**.
  Q3 (2N7002) kéo gate Q2 xuống GND khi `VBAT_MEAS_EN` = 1. R6 100 kΩ giữ Q3 OFF khi MCU ngủ/reset.
- Dùng P-FET + N-FET thay vì cầu chia nối thẳng: với V<sub>BAT</sub> > 3.3 V (pin mới hoặc pin sạc) gate P-FET vẫn tắt
  hoàn toàn vì được kéo về chính V<sub>BAT</sub>, không phụ thuộc mức logic 3.3 V.
- C6 10 nF + 50 kΩ (Thevenin) → τ = 0.5 ms; firmware đợi ≥ 60 ms (song song thời gian ổn định đầu dò).
- Dòng khi đo: 15 µA × ~80 ms mỗi 15 phút → không đáng kể. Khi tắt: chỉ rò I<sub>DSS</sub> (nA).

### Công tắc VSENS (Q4, R9, C7)
- Q4 AO3401A high-side, gate kéo lên +3V3 (R9) → VSENS tắt khi GPIO10 Hi-Z; GPIO10 kéo thấp để bật.
- C7 1 µF + C15/C20 100 nF tại tải. Dòng nạp tức thời khi bật làm +3V3 sụt ~ (1.2 µF / 54 µF) × 3.3 V ≈ 70 mV – chấp nhận được (module chịu 3.0–3.6 V).

### PWR_FLAG
GND, VBAT, VSENS, VIN_BB có PWR_FLAG để ERC trong KiCad không báo “power input not driven”.

---

## 2.2 Khối MCU (sheet *MCU*)

- **U2 ESP32-H2-WROOM-02C**: footprint riêng `h2soil:ESP32-H2-WROOM-02C` theo land pattern datasheet v1.2 (pad 1.5 × 0.9 mm,
  bước 1.5 mm, EPAD chia 2 phần 2.8 × 0.55 + 2.8 × 1.6 mm với 9 via nhiệt).
- Tụ nguồn: **C8 10 µF + C9 100 nF** sát chân 3V3 (pin 1).
- **EN**: module đã có RC 10 kΩ/1 µF bên trong → C12 để DNP; EN đưa ra header J1 và nút SW2 (DNP).
- **Strapping**: IO9 kéo lên 10 kΩ (R21, sheet UI) → SPI boot; nhấn SW1 khi reset → download mode.
  IO8 kéo lên 10 kΩ (R11) theo khuyến nghị (cần =1 cho joint download boot). IO25 (strap JTAG) bỏ trống – bị bỏ qua với eFuse mặc định.
- **VBAT (pin 14)** để NC: bên trong module đã nối với 3V3.
- **Thạch anh 32.768 kHz (Y1, C10, C11 – DNP)** trên IO13/IO14: lắp khi cần đồng hồ ngủ chính xác (CSL/SSED), bật
  `CONFIG_RTC_CLK_SRC_EXT_CRYS` (file `sdkconfig.defaults.xtal32k`). C10/C11 = 18 pF cho C<sub>L</sub> 12.5 pF (hiệu chỉnh theo bo thực).
- Các chân LP (IO8–IO14) dùng cho tín hiệu cần giữ mức trong light-sleep; các chân số (IO0–5, IO22–27) chỉ dùng khi thức.

---

## 2.3 Khối cảm biến (sheet *Sensors*)

### Bộ dao động TLC555 (U3, R12, C14, C13, C15)
```
 VSENS ─┬─ 8 VCC   4 RESET ─ VSENS
        │  TLC555I
       C15         3 OUT ─┬─ R12 10k ─┬─ 2 TR / 6 THR
       100n               │           C14 100pF C0G
                          │           GND
                          └─ R13 0R ─ PROBE_EXC ─ R15 10k ─ PROBE_SENSE ─ điện cực
        5 CV ─ C13 10nF                                            │
        7 DIS ─ NC                                               D1 1N4148WS
                                                                   │ PROBE_DET
                                                         C17 10nF ─┤
                                                                  R16 470k
                                                                   ├─ SOIL_ADC (IO1) ── C18 10nF
                                                                  R17 470k
                                                                  GND
```
- Cấu hình duty 50 % bằng hồi tiếp từ OUT: f ≈ 1 / (2·ln2·R12·C14) = 1/(1.386 × 10 kΩ × 100 pF) ≈ **720 kHz** lý thuyết;
  trễ lan truyền của TLC555 ở 3.3 V (~150–250 ns mỗi cạnh) đưa tần số thực về khoảng **0.5–0.65 MHz**. Không dùng chân DIS
  nên không có dòng xả liên tục (cấu hình RA/RB cổ điển sẽ tốn ~1.6 mA).
- Dòng TLC555 ≈ 250 µA tĩnh + V·f·(C<sub>PD</sub>+C<sub>L</sub>) ≈ 0.4 mA → ~0.7 mA khi chạy, chỉ trong ~80 ms mỗi lần đo.
- Tụ định thời phải là **C0G/NP0** (ổn định nhiệt). Tần số không cần chính xác (đã hiệu chuẩn) nhưng cần ổn định.

### Mạng đầu dò + tách đỉnh
- Mạch RC: R<sub>S</sub> (R15 10 kΩ) nối tiếp với điện dung điện cực C<sub>P</sub> (SENSE ↔ GND qua đất). Với sóng vuông chu kỳ T,
  biên độ đỉnh tại nút SENSE: V<sub>pk</sub> = V<sub>DD</sub>/2 · (1 + tanh(T / (4 R<sub>S</sub> C<sub>P</sub>))).

| Môi trường | C<sub>P</sub> (ước tính) | V<sub>pk</sub> (T ≈ 1.8 µs) | SOIL_ADC (sau diode, /2) |
|---|---|---|---|
| Không khí | ~15 pF | 3.29 V | ~1.42 V |
| Đất khô | ~25 pF | 3.21 V | ~1.38 V |
| Đất ẩm vừa | ~50 pF | 2.83 V | ~1.19 V |
| Đất ướt | ~100 pF | 2.35 V | ~0.95 V |
| Nước | ~250 pF | 1.94 V | ~0.75 V |

  Vì vậy giá trị mặc định trong firmware là DRY = 1400 mV, WET = 750 mV; **phải hiệu chuẩn lại trên bo thật** (2 lần nhấn / 3 lần nhấn).
- D1 dùng 1N4148WS (dòng rò ngược ~nA) thay Schottky (µA ở nhiệt độ cao) để tránh trôi khi nắng nóng; V<sub>F</sub> ≈ 0.45 V ở µA
  và hệ số nhiệt ≈ −2 mV/°C → +1 mV/°C ở ADC → firmware bù bằng NTC (`CONFIG_SOIL_TEMP_COMP_UV_PER_C` = 1000 µV/°C).
- C17 10 nF giữ đỉnh; R16/R17 (940 kΩ tổng) vừa xả (τ ≈ 9 ms) vừa chia 1/2 vào dải ATTEN 6 dB; C18 10 nF cấp điện tích cho tụ
  lấy mẫu của ADC (datasheet ESP32-H2 đo ADC với 100 nF ngoài – ở đây nguồn trở kháng 235 kΩ nên 10 nF là đủ cho lấy mẫu chậm).
- **R13/R14**: chọn nguồn kích thích. Mặc định R13 = 0 Ω (TLC555). Tùy chọn: bỏ U3 + R13, lắp R14 → ESP32-H2 tạo sóng vuông
  1–4 MHz bằng LEDC trên IO4 (`CONFIG_SOIL_EXCITATION_LEDC`), tần số ổn định theo thạch anh và cao hơn → ít nhạy độ mặn hơn.
- TP5 (SOIL_ADC), TP6 (PROBE_EXC) để kiểm tra bằng oscilloscope.

### Nhiệt độ đất (RT1, R18, C19)
- VSENS → R18 10 kΩ 1 % → NTC_ADC → RT1 NTC 10 kΩ B3380 → GND; ADC ATTEN 12 dB (0–3.3 V).
- T = 1 / (1/298.15 + ln(R/10k)/3380) − 273.15; R = 10k · V/(3300 − V). Phạm vi 0–60 °C ứng với 2.4–0.85 V.
- RT1 đặt trên que, ở **~5 cm dưới vạch mặt đất**, trong kênh riêng mép phải (đường NTC_ADC được bảo vệ bởi dải GND).

### SHT40 (U4, R19, R20, C20)
- Nuôi từ VSENS, pull-up I²C 10 kΩ **lên VSENS** (không lên +3V3) để khi VSENS tắt không có dòng chạy qua diode ESD của SHT40.
  Hệ quả: firmware phải trả SDA/SCL về **input không pull** trước khi tắt VSENS (`board_i2c_release()`).
- Lệnh đo 0xFD (độ lặp lại cao, ≤ 8.3 ms), kiểm tra CRC-8 (đa thức 0x31).
- Dùng bản **SHT40-AD1F** (màng PTFE). Footprint có vùng cấm đồng dưới tâm cảm biến (theo Sensirion).

---

## 2.4 Khối nút nhấn / LED / nạp (sheet *UI*)

| Ký hiệu | Chức năng |
|---|---|
| SW1 + R21 10k + C21 100 nF | Nút BOOT/USER trên IO9 (kéo lên ngoài, chống dội RC τ = 1 ms; vẫn lên mức 1 trước khi EN của module lên ~10 ms). |
| SW2 (DNP) | Nút RESET trên EN. |
| D2 + R22 1 kΩ | LED đỏ ~1.5 mA trên IO0, chỉ nháy khi cần. |
| J1 1×8 2.54 mm | 1 = 3V3, 2 = GND, 3 = TXD0, 4 = RXD0, 5 = EN, 6 = IO9, 7 = USB_D−, 8 = USB_D+. Có thể chỉ để lỗ (không hàn) cho bản sản xuất. |
| TP1–TP6 | VBAT, 3V3, GND, VSENS, SOIL_ADC, PROBE_EXC. |
| H1, H2 | Lỗ M2 gần vạch mặt đất để kẹp bo vào hộp/đệm kín. |

**Nạp firmware:**
- *USB Serial/JTAG*: lắp pin, nối USB D+ (J1-8), D− (J1-7), GND (J1-2) tới cổng USB của PC (không nối 5 V/3V3). `idf.py -p /dev/ttyACM0 flash monitor`.
- *UART*: **tháo pin**, cấp 3.3 V từ adapter USB-UART 3.3 V vào J1-1, nối TX/RX chéo, giữ SW1 (IO9 = 0) rồi chạm EN xuống GND (J1-5) để vào download mode.
  Không cấp 3V3 ngoài khi pin đang lắp (hai nguồn song song).
