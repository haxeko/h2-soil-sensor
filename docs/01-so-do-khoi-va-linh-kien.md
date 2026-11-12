# 1. Sơ đồ khối và lựa chọn linh kiện

Phiên bản 2 tách thiết bị làm hai phần: **bo mạch tự thiết kế** (ESP32-H2 + nguồn pin + cổng cắm) và **các module cảm
biến phổ biến mua sẵn** nối bằng cáp. Bo không còn đầu dò in trên PCB, không có cảm biến hay đế pin hàn trên bo.

## 1.1 Sơ đồ khối

```
 ═══ Trên PCB 36 × 60 mm ════════════════════════════════════════════════════════════════════════════

  CR123A ──dây──► J2 JST-PH 2P ─┐
  (hộp pin)       J3 2 pad hàn ─┴─► Q1 AO3415A ──VBAT──► R10 0 Ω ──► U1 TPS63900 ──+3V3──► U2 ESP32-H2-WROOM-02C
                                    chống ngược cực │    cầu đo dòng  buck-boost 3.3 V      RISC-V 96 MHz
                                                    │                 Iq 75 nA              802.15.4 + BLE 5 ···))) Thread
                                                    │                                       (SED/ICD, anten nhô khỏi bo)
                                                    └──► Q2/Q3 + R7/R8: VBAT/2 ──► IO2 (VBAT_ADC), bật bởi IO11

                                       +3V3 ──► Q4 công tắc tải P-FET ◄── IO10 (SENS_PWR_EN_N, mức thấp = bật)
                                                 │
                                                 │ VSENS: chỉ có điện khi đo (~1.5 s mỗi 15 phút)
                    ┌────────────────────────────┼─────────────────────────────────┐
                    ▼                            ▼                                 ▼
          J4 JST-PH 3P: GND VCC AOUT    J7 JST-PH 2P: NTC GND          J6 1×4 2.54 mm: VCC GND SCL SDA
          AOUT ─ R12 1 kΩ ─► IO1        R18 10 kΩ từ VSENS ─► IO3      SDA/SCL ◄─► IO12/IO22 (pull-up 10 kΩ)
          U3 SRV05-4: TVS 4 kênh cho AOUT, NTC, SDA, SCL (các đường đi ra khỏi hộp)
          SW1 BOOT/USER (IO9) · LED đỏ (IO0) · J1 PROG: 3V3 GND TX RX EN IO9 D− D+

 ═══ Ngoài PCB, nối bằng cáp ════════════════════════════════════════════════════════════════════════
                    │                            │                                 │
          module độ ẩm đất điện dung    đầu dò NTC 10 kΩ B3950         module nhiệt/ẩm không khí I²C
          v1.2/v2.0 (TLC555)            chống nước – tuỳ chọn          SHT4x / SHT3x / AHT20 – tuỳ chọn
          AOUT 0–3 V, cắm trong đất     nhiệt độ đất                   đặt sau lỗ thở / tấm che bức xạ
```

Bản vẽ khối trong KiCad nằm ở sheet gốc `hardware/h2-soil-sensor.kicad_sch` (trang 1 của
[`hardware/docs/schematic.pdf`](../hardware/docs/schematic.pdf)).

### Hình dạng vật lý

![Bo mạch v2, mặt trên và mặt dưới (ảnh minh hoạ)](../hardware/docs/render_v2.png)

```
                 ┌─ anten PCB ─────┐  ← nhô ra ngoài mép bo 6 mm:
                 │  (không đồng)   │    không kim loại, không cáp ở gần
   ╭─────────────┴─────────────────┴──────────╮  y = 0
   │ C8 C9      U2 ESP32-H2-WROOM-02C     LED │
   │ R11        (18 × 20 mm)                  │
   │                                          │  y ≈ 14
   │ nguồn TPS63900   đo pin Q2/Q3       J1   │  y ≈ 20…32
   │ C1 R10 U1 L1     VSENS Q4/R9/C7     PROG │
   │ C2…C5 R2…R4                         1×8  │
   │ SW1 BOOT    TP1…TP4                      │  y ≈ 34…38
   │ BAT: J2 (PH 2P)   Q1 R1             ◯ H2 │  y ≈ 41…46
   │ − J3 +    U3 SRV05-4, R12 C13, R18…R20   │  y ≈ 44…51
   │ ◯ H1  J4 SOIL   J7 NTC   J6 I²C (1×4)    │  y ≈ 56…58
   ╰──────────────────────────────────────────╯  y = 60
         GND VCC AOUT  NTC GND  VCC GND SCL SDA
```

Không theo tỉ lệ. Bo 36 × 60 mm, FR4 2 lớp 1.6 mm, vát góc, **mọi linh kiện ở mặt trên**. Pin vào ở mép trái,
ba cổng cảm biến xếp dọc mép dưới (mọi cáp ra một phía), header nạp J1 ở mép phải, module ESP32-H2 ở giữa mép trên
với anten nhô ra ngoài. Hai lỗ M3 (H1 góc dưới trái, H2 mép phải). Chi tiết bố trí: [04-layout-pcb.md](04-layout-pcb.md).

## 1.2 Lựa chọn linh kiện trên bo và lý do

| Khối | Linh kiện | Lý do chọn |
|---|---|---|
| MCU / radio | **ESP32-H2-WROOM-02C-H4S** (4 MB flash) | 802.15.4 (Thread) + BLE 5.3 (commissioning), light-sleep 25 µA, deep-sleep 7 µA. Bản 4 MB để có 2 phân vùng OTA cho Matter (ảnh firmware ~1.7 MB). Anten PCB, nhiệt độ −40…105 °C. Module cần VDD 3.0–3.6 V → bắt buộc có bộ ổn áp vì CR123A sụt xuống 2.0 V cuối đời. |
| Nguồn | **TPS63900DSKR** (buck-boost) | Iq 75 nA, hiệu suất > 90 % ở 10 µA, Vin 1.8–5.5 V nên giữ 3.3 V ổn định từ pin mới (3.2–3.3 V) tới pin gần cạn (2.0 V), dòng ra > 400 mA đủ cho xung TX 140 mA (+20 dBm). Cấu hình bằng điện trở (R2D), không cần cầu chia hồi tiếp (không tốn dòng tĩnh). UVLO 1.75 V. Tương thích cả pin sạc RCR123A/16340 (3.0–4.2 V). |
| Cuộn cảm | TDK TFM252012ALMA2R2MTAA 2.2 µH | Giá trị TI khuyến nghị; Isat 2.6 A > 2 A (cấu hình “unlimited” input current), DCR 75 mΩ, 2520 (1008). |
| Chống ngược cực | **AO3415A** P-MOSFET | Mắc kiểu “ideal diode” (D→pin, S→tải, G→GND): không sụt áp như diode Schottky (~0.3 V là quá lớn với pin 3 V); Vgs(th) ≤ 1 V, Rds(on) ~ 50–65 mΩ ở Vgs = −1.8…−2.5 V → sụt < 20 mV ở 260 mA. Ở v2 càng cần vì pin nối bằng dây/JST: **thứ tự cực của cáp JST-PH không thống nhất giữa các hãng**. |
| Cổng pin | **J2** JST-PH 2.0 2P (B2B-PH-K-S) + **J3** 2 pad hàn dây (song song) | Đúng yêu cầu “PCB có 2 cực để đấu pin”: không kéo dài bo để hàn đế pin → bo gọn 36 × 60 mm; hộp pin có dây đặt tuỳ ý trong vỏ. JST để tháo lắp nhanh; 2 pad (lỗ 1.1 mm, bước 4.6 mm, cho dây 0.5 mm²) để hàn chết khi cần chống rung/oxy hoá tiếp điểm. |
| Đo điện áp pin | AO3401A + 2N7002 + cầu 100k/100k | Cầu chia nối thẳng vào pin sẽ tốn 15 µA liên tục (~0.36 mAh/ngày). Công tắc high-side P-FET (gate kéo lên VBAT bằng 1 MΩ) + N-FET dịch mức; R6 kéo gate N-FET xuống khi MCU ngủ → dòng rò chỉ còn cỡ nA. |
| Công tắc nguồn module | AO3401A (Q4) + R9 100k, soft-start bằng firmware | VSENS nuôi **mọi module bên ngoài** (module đất ~5 mA, module I²C, cầu chia NTC, pull-up I²C). Nếu cấp liên tục, riêng module đất 5 mA = 120 mAh/ngày → hết pin sau ~10 ngày; bật ~1.5 s mỗi lần đo thì chỉ còn ~0.3 mAh/ngày. R9 kéo gate lên 3V3 nên VSENS tắt cả khi GPIO ở Hi-Z (reset, light-sleep, deep-sleep). |
| Cổng module đất | **J4** JST-PH 2.0 3P (B3B-PH-K-S) | Chuẩn cổng của module độ ẩm đất điện dung (PH2.0-3P: GND, VCC, AOUT) → cắm thẳng cáp đi kèm module. |
| Cổng NTC | **J7** JST-PH 2.0 2P | NTC không phân cực; bấm đầu PH 2.0 cho dây đầu dò. |
| Cổng I²C | **J6** header 1×4 2.54 mm | Module I²C phổ biến dùng header 2.54 mm; thứ tự VCC GND SCL SDA giống GY-SHT31-D / module AHT20 (VIN GND SCL SDA) → dây Dupont thẳng. **Module khác (ví dụ của Adafruit) có thể khác thứ tự – kiểm tra trước khi nối.** |
| Bảo vệ ESD | **SRV05-4** (Semtech SRV05-4.TCT, C13612) | 4 kênh TVS cho đúng 4 đường đi ra khỏi hộp (SOIL_AOUT, NTC_ADC, SDA, SCL), SOT-23-6, điện dung thấp (~3 pF theo mô tả LCSC) không ảnh hưởng ADC/I²C 100 kHz. Chân VP nối VSENS → khi tắt nguồn module không có phân cực, không rò. Thay thế cùng chân, rẻ hơn: TECH PUBLIC SRV05-4 (C558418). |
| Front-end analog | R12 1 kΩ + C13 10 nF; R18 10 kΩ 1 % + C19 100 nF | R12 hạn dòng vào IO1 khi có xung/quá áp trên cáp; C13 lọc nhiễu cáp và cấp điện tích cho tụ lấy mẫu ADC. R18 = R25 của NTC → độ nhạy lớn nhất quanh 25 °C. |
| Pull-up I²C | R19, R20 10 kΩ lên **VSENS** | Bus vẫn chạy nếu module không có pull-up; nối VSENS (không phải +3V3) để khi tắt VSENS không có dòng cấp ngược vào module qua SDA/SCL. |
| Tụ VSENS | C7 1 µF + C14 1 µF + C20 100 nF | Cố ý nhỏ để hạn dòng nạp khi Q4 đóng (module đã có tụ riêng). |
| Giao diện | TS-1187A (nút), LED đỏ 0603 + 1 kΩ, header 1×8 2.54 mm | Nút trên IO9 (strapping BOOT + LP GPIO đánh thức), LED chỉ nháy khi cần (~1.5 mA). Header gồm UART0 + USB Serial/JTAG (IO26/IO27) + EN + IO9 để nạp/debug. |
| Thạch anh 32 kHz | YXC X321532768KGD2SI (DNP) | Tùy chọn cho đồng hồ ngủ chính xác (CSL/SSED), mặc định dùng RC nội 136 kHz. |

## 1.3 Module cảm biến bên ngoài (không nằm trên PCB)

| Module | Thông số / giao tiếp | Ghi chú chọn mua |
|---|---|---|
| **Độ ẩm đất điện dung v1.2 / v2.0** (DFRobot SEN0193 và các bản tương tự) | Nguồn 3.3–5.5 V DC, dòng 5 mA, ngõ ra analog 0–3.0 V, cổng PH2.0-3P (GND, VCC, AOUT), dài 98 mm ([DFRobot wiki](https://wiki.dfrobot.com/sen0193/), [Core Electronics](https://core-electronics.com.au/capacitive-soil-moisture-sensor-corrosion-resistant.html)). Điện áp ra **cao khi khô, thấp khi ướt**. | Nên chọn module dùng **TLC555** (CMOS, chạy được ở 3.3 V); một số bản rẻ dùng NE555 (không chạy ở 3.3 V) hoặc lỗi lắp ráp → **thử từng module trong không khí và trong nước trước khi lắp đặt**. Chỉ phần đầu dò được phủ; phần linh kiện phía trên và mép cắt PCB phải tự bịt kín (xem [07](07-rui-ro-ngoai-troi.md)). |
| **Nhiệt độ/độ ẩm không khí I²C** (tuỳ chọn) | SHT4x (0x44), SHT3x (0x44/0x45), AHT20/AHT21 (0x38); firmware tự nhận loại, kiểm tra CRC | Module phải chạy được ở 3.3 V; nếu có LED nguồn nên gỡ LED (tốn dòng trong cửa sổ đo). |
| **Đầu dò NTC chống nước** (tuỳ chọn) | 10 kΩ ở 25 °C, B = 3950 (đổi được trong Kconfig) | 2 dây, không phân cực; dùng cho cluster nhiệt độ đất và bù nhiệt tuỳ chọn. |
| **Pin + hộp pin** | 1 × CR123A 3 V Li-MnO<sub>2</sub> ~1500 mAh, hộp pin có dây | Nối J2 (bấm đầu JST-PH 2P) hoặc hàn vào J3; **kiểm tra cực bằng đồng hồ** trước khi cắm. |

## 1.4 Phân bổ chân ESP32-H2-WROOM-02C

| Chân module | GPIO | Chức năng | Ghi chú |
|---|---|---|---|
| 27 | IO1 | SOIL_ADC (ADC1_CH0) | AOUT module đất qua R12; ATTEN 12 dB (0–3.3 V) |
| 26 | IO2 | VBAT_ADC (ADC1_CH1) | VBAT/2, ATTEN 6 dB |
| 25 | IO3 | NTC_ADC (ADC1_CH2) | ATTEN 12 dB (0–3.3 V) |
| 5 | IO10 | SENS_PWR_EN_N | LP GPIO, mức thấp = bật VSENS (R9 giữ tắt) |
| 6 | IO11 | VBAT_MEAS_EN | LP GPIO, mức cao = bật cầu chia pin (R6 giữ tắt) |
| 10 / 15 | IO12 / IO22 | I²C SDA / SCL | 100 kHz, pull-up 10 k lên VSENS, không dùng pull-up nội |
| 8 | IO9 | BOOT/USER button | strapping (kéo lên 10 k), LP GPIO đánh thức light sleep |
| 7 | IO8 | strapping | kéo lên 10 k (R11) |
| 28 | IO0 | LED | active high |
| 11 / 12 | IO13 / IO14 | XTAL_32K_P/N | thạch anh 32 kHz (DNP) |
| 21 / 22 | IO23 / IO24 | UART0 RX / TX | header J1 |
| 23 / 24 | IO26 / IO27 | USB D− / D+ | header J1 |
| 3, 4, 20 | IO4, IO5, IO25 | dự phòng | để trống, firmware đặt Hi-Z (IO25 là strap JTAG – bị bỏ qua với eFuse mặc định) |
| 2 / 1 / 14 | EN / 3V3 / VBAT | | EN ra J1-5 (module có RC sẵn); 3V3 có C8 + C9; VBAT để NC |

Nguyên tắc: các tín hiệu điều khiển công suất đặt trên **LP GPIO (IO8–IO14)** vì đây là các chân duy nhất còn hoạt động/giữ
mức khi light-sleep tắt miền nguồn TOP (`CONFIG_PM_POWER_DOWN_PERIPHERAL_IN_LIGHT_SLEEP`) – firmware dùng `gpio_hold` để giữ
VSENS bật trong lúc chip light-sleep chờ module đất ổn định – và mỗi tín hiệu đều có điện trở ngoài xác định trạng thái
OFF an toàn.
