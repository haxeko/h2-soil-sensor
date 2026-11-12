# 3. BOM (Bill of Materials)

Danh sách linh kiện bo v3 **không bao gồm module ESP32-H2-WROOM-02C** (theo yêu cầu; dùng bản **-H4S, 4 MB flash** để có OTA).
File máy đọc được cho JLCPCB SMT: [`hardware/fab/h2-soil-sensor_BOM_JLCPCB.csv`](../hardware/fab/h2-soil-sensor_BOM_JLCPCB.csv)
và [`hardware/fab/h2-soil-sensor_CPL_JLCPCB.csv`](../hardware/fab/h2-soil-sensor_CPL_JLCPCB.csv); phần không lắp máy liệt kê trong
[`hardware/fab/h2-soil-sensor_not_assembled.csv`](../hardware/fab/h2-soil-sensor_not_assembled.csv) (cả ba sinh bởi
`hardware/tools/make_fab.py` từ các trường `LCSC`/`MPN` trong schematic). Tồn kho, giá và loại thư viện JLC đã kiểm tra qua
API JLCPCB/LCSC tháng 11/2026; đơn giá là giá LCSC ở số lượng 10.

## 3.1 Linh kiện SMT (JLCPCB lắp, mặt trên)

| # | Ký hiệu | SL | Giá trị | Footprint | MPN | Hãng | LCSC | Loại JLC | Đơn giá USD (@10) | Ghi chú |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | C1 | 1 | 47uF 6.3V | C_0805_2012Metric | CL21A476MQYNNNE | Samsung | [C16780](https://www.lcsc.com/product-detail/C16780.html) | Basic | 0.0743 | Bulk VBAT cho xung TX (pin lạnh, dây pin) |
| 2 | C2 | 1 | 10uF 25V | C_0805_2012Metric | CL21A106KAYNNNE | Samsung | [C15850](https://www.lcsc.com/product-detail/C15850.html) | Basic | 0.0314 | CIN TPS63900, sát chân VIN |
| 3 | C3, C9, C21 | 3 | 100nF | C_0603_1608Metric | CC0603KRX7R9BB104 | YAGEO | [C14663](https://www.lcsc.com/product-detail/C14663.html) | Basic | 0.0164 | |
| 4 | C4, C5 | 2 | 22uF 25V | C_0805_2012Metric | CL21A226MAQNNNE | Samsung | [C45783](https://www.lcsc.com/product-detail/C45783.html) | Basic | 0.1055 | COUT TPS63900 |
| 5 | C6, C13 | 2 | 10nF | C_0603_1608Metric | CL10B103KB8NNNC | Samsung | [C1589](https://www.lcsc.com/product-detail/C1589.html) | Extended | 0.0074 | C6 lọc VBAT_ADC; C13 lọc SOIL_ADC |
| 6 | C7, C14 | 2 | 1uF | C_0603_1608Metric | CL10A105KB8NNNC | Samsung | [C15849](https://www.lcsc.com/product-detail/C15849.html) | Basic | 0.0112 | Tụ VSENS, cố ý nhỏ để hạn dòng nạp |
| 7 | C8 | 1 | 10uF 10V | C_0603_1608Metric | CL10A106KP8NNNC | Samsung | [C19702](https://www.lcsc.com/product-detail/C19702.html) | Basic | 0.0233 | Sát chân 3V3 module |
| 8 | D2 | 1 | RED | LED_0603_1608Metric | KT-0603R | Hubei KENTO | [C2286](https://www.lcsc.com/product-detail/C2286.html) | Basic | 0.0077 | LED trạng thái |
| 9 | D3 | 1 | ESD 3.3V | D_SOD-523 | LESD5Z3.3T1G | LRC | [C136161](https://www.lcsc.com/product-detail/C136161.html) | Extended | 0.0160 (0.0194 @1) | TVS cho dây AOUT. Thay thế: onsemi ESD5Z3.3T1G ([C61148](https://www.lcsc.com/product-detail/C61148.html), Extended, tồn kho ít) |
| 10 | L1 | 1 | 2.2uH | L_1008_2520Metric | TFM252012ALMA2R2MTAA | TDK | [C404804](https://www.lcsc.com/product-detail/C404804.html) | Extended | 0.3924 | Thay thế: Murata DFE252012F-2R2M=P2 (C576403) |
| 11 | Q1 | 1 | AO3415A | SOT-23 | AO3415A | AOS | [C133233](https://www.lcsc.com/product-detail/C133233.html) | Extended | 0.0985 | Chống ngược cực. Thay thế: DMG2305UX-7 (C150470) |
| 12 | Q2, Q4 | 2 | AO3401A | SOT-23 | AO3401A | AOS | [C15127](https://www.lcsc.com/product-detail/C15127.html) | Basic | 0.0813 | Công tắc cầu chia pin / VSENS |
| 13 | Q3 | 1 | 2N7002 | SOT-23 | 2N7002 | CJ | [C8545](https://www.lcsc.com/product-detail/C8545.html) | Basic | 0.0154 | Dịch mức gate Q2 |
| 14 | R1, R6, R7, R8, R9 | 5 | 100k | R_0603_1608Metric | 0603WAF1003T5E | UNI-ROYAL | [C25803](https://www.lcsc.com/product-detail/C25803.html) | Basic | 0.0029 | |
| 15 | R2 | 1 | 36.5k | R_0603_1608Metric | 0603WAF3652T5E | UNI-ROYAL | [C23029](https://www.lcsc.com/product-detail/C23029.html) | Extended | 0.0016 | CFG1 → VO(2) = 3.3 V (1 %) |
| 16 | R3, R10 | 2 | 0R | R_0603_1608Metric | 0603WAF0000T5E | UNI-ROYAL | [C21189](https://www.lcsc.com/product-detail/C21189.html) | Basic | 0.0021 | R3 = CFG2 (unlimited); R10 = cầu đo dòng |
| 17 | R4 | 1 | 16.2k | R_0603_1608Metric | 0603WAF1622T5E | UNI-ROYAL | [C22885](https://www.lcsc.com/product-detail/C22885.html) | Extended | 0.0014 | CFG3 → VO(1) = 3.3 V (1 %) |
| 18 | R5 | 1 | 1M | R_0603_1608Metric | 0603WAF1004T5E | UNI-ROYAL | [C22935](https://www.lcsc.com/product-detail/C22935.html) | Basic | 0.0018 | Kéo gate Q2 lên VBAT |
| 19 | R11, R21 | 2 | 10k | R_0603_1608Metric | 0603WAF1002T5E | UNI-ROYAL | [C25804](https://www.lcsc.com/product-detail/C25804.html) | Basic | 0.0022 | Kéo lên strap IO8 / IO9 |
| 20 | R12, R22 | 2 | 1k | R_0603_1608Metric | 0603WAF1001T5E | UNI-ROYAL | [C21190](https://www.lcsc.com/product-detail/C21190.html) | Basic | 0.0017 | R12 hạn dòng AOUT → IO1; R22 LED |
| 21 | SW1 | 1 | BOOT/USER | SW_Push_1P1T_XKB_TS-1187A | TS-1187A-B-A-B | XKB | [C318884](https://www.lcsc.com/product-detail/C318884.html) | Basic | 0.0215 | Nút BOOT/USER |
| 22 | U1 | 1 | TPS63900DSKR | WSON-10-1EP_2.5x2.5mm_P0.5mm_EP1.2x2mm_ThermalVias_0.3mm | TPS63900DSKR | Texas Instruments | [C1518762](https://www.lcsc.com/product-detail/C1518762.html) | Extended | 0.8680 | Buck-boost 75 nA Iq |

**Tổng SMT: 35 linh kiện, 22 mã, ≈ 2.04 USD/bo.** 7 mã là Extended (C1589, C136161, C404804, C133233, C23029, C22885, C1518762).

> “Basic” là linh kiện thư viện cơ bản của JLCPCB (không phí nạp cuộn); “Extended” có phí nạp ~3 USD/mã mỗi đơn.
> Khi đặt hàng, kiểm tra trang xác nhận của JLC: đủ 22 dòng BOM / 35 vị trí trong CPL (kể cả U1) và đúng hướng chân 1 của
> U1, Q1–Q4, D2, D3.

## 3.2 Linh kiện xuyên lỗ (THT) – hàn tay

| # | Ký hiệu | SL | Giá trị | Footprint | MPN | Hãng | LCSC | Loại JLC | Đơn giá USD (@10) | Ghi chú |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | J4 | 1 | JST-PH 3P | JST_PH_B3B-PH-K_1x03_P2.00mm_Vertical | B3B-PH-K-S(LF)(SN) | JST | [C131339](https://www.lcsc.com/product-detail/C131339.html) | Extended | 0.0418 | Module đất: 1 GND, 2 VCC, 3 AOUT |

Không nằm trong file BOM/CPL của JLC (đánh dấu “THT – han tay” trong `not_assembled.csv`); hàn tay hoặc chọn dịch vụ lắp THT.

**Tổng linh kiện trên bo (SMT + J4, không gồm module ESP32-H2, PCB, pin, module cảm biến) ≈ 2.08 USD/bo**
(giá LCSC tham khảo 11/2026, số lượng 10).

## 3.3 Không lắp / không phải linh kiện

| Ký hiệu | Giá trị | Lý do |
|---|---|---|
| U2 | ESP32-H2-WROOM-02C-H4S | Module ESP (không liệt kê theo yêu cầu, mua riêng/consign; EPAD dưới module cần hot-air hoặc bếp gia nhiệt nếu hàn tay) |
| J1 | 8 pad nạp tròn | Không phải linh kiện: pad đồng cho kim pogo hoặc dây hàn tạm |
| J3 | 2 pad dây pin | Không phải linh kiện: hàn thẳng dây hộp pin vào pad “+” (vuông) / “−” (tròn) |

## 3.4 Vật tư ngoài BOM

| Hạng mục | Gợi ý |
|---|---|
| PCB | 26 × 45 mm, FR4 2 lớp 1.6 mm, đồng 1 oz, HASL không chì hoặc ENIG, mask bất kỳ – file `hardware/fab/h2-soil-sensor_gerbers.zip` |
| Module độ ẩm đất | “Capacitive Soil Moisture Sensor v1.2” dùng **TLC555** (DFRobot SEN0193 hoặc tương đương). Nên mua dư để loại module lỗi (thử trong không khí/nước trước) |
| Cáp module | Cáp **PH2.0-3P hai đầu, nối thẳng** (cáp đi kèm module PH2.0 → Dupont cái không vừa J4), hoặc vỏ JST PH 3P (PHR-3) + cos bấm để làm lại đầu |
| Pin | CR123A 3 V Li-MnO<sub>2</sub> (Panasonic CR123A, Energizer EL123AP, Varta…) ~1400–1600 mAh |
| Hộp pin | Hộp/đế CR123A **có dây dẫn**, kẹp chắc; hàn dây vào J3 – kiểm tra cực trước khi hàn |
| Vỏ | Hộp nhựa **IP65** trở lên (ABS/ASA/PC chống UV, màu sáng) có gioăng; bo không có lỗ vít → cố định bằng băng keo xốp 2 mặt, kẹp hoặc keo nến; không có kim loại quanh anten, khe hở ≥ 15 mm |
| Ốc siết cáp | Cable gland theo đường kính cáp module |
| Thông hơi / hút ẩm | Nút thở ePTFE (Gore) cân bằng áp suất; gói silica gel 1–2 g |
| Phủ bảo vệ | Conformal coating acrylic (AR)/polyurethane (UR) cho bo (che pad J1, nút, J4 khi phủ) và **phần linh kiện + mép cắt của module đất**; co nhiệt có keo hoặc epoxy bọc đầu module |
| Dụng cụ nạp | Kẹp/đồ gá pogo 2 × 4 bước 2.54 mm (hoặc dây hàn tạm); cáp USB (D+, D−, GND) hoặc adapter USB-UART 3.3 V |
| Khác | Keo silicone trung tính, dây rút giảm lực kéo cho cáp |
