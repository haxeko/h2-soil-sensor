# 3. BOM (Bill of Materials)

Danh sách lắp ráp **không bao gồm module ESP32-H2-WROOM-02C** (theo yêu cầu; dùng bản **-H4S, 4 MB flash** để có OTA).
File máy đọc được cho JLCPCB SMT: [`hardware/fab/h2-soil-sensor_BOM_JLCPCB.csv`](../hardware/fab/h2-soil-sensor_BOM_JLCPCB.csv)
và [`hardware/fab/h2-soil-sensor_CPL_JLCPCB.csv`](../hardware/fab/h2-soil-sensor_CPL_JLCPCB.csv) (sinh bởi `hardware/tools/make_fab.py`
từ chính các trường `LCSC`/`MPN` trong schematic). Tồn kho và giá đã kiểm tra qua API JLCPCB/LCSC ngày 11/2026.

## 3.1 Linh kiện lắp ráp

| # | Ký hiệu | SL | Giá trị | Footprint | MPN | Hãng | LCSC | Loại JLC | Đơn giá USD (@10) | Ghi chú |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | BT1 | 1 | CR123A 3V Li-MnO2 | BatteryHolder_MYOUNG_BH-123A-A1CJ002 | BH-123A-A1CJ002 | MYOUNG | [C5290177](https://www.lcsc.com/product-detail/C5290177.html) | Extended | 0.5901 | Giá THT, hàn tay. Môi trường ẩm: bản mạ vàng BH-123A-B5BA003 (C19184081) |
| 2 | C1 | 1 | 47uF 6.3V | C_0805_2012Metric | CL21A476MQYNNNE | Samsung | [C16780](https://www.lcsc.com/product-detail/C16780.html) | Basic | 0.0743 | Bulk VBAT cho xung TX khi pin lạnh |
| 3 | C2 | 1 | 10uF 25V | C_0805_2012Metric | CL21A106KAYNNNE | Samsung | [C15850](https://www.lcsc.com/product-detail/C15850.html) | Basic | 0.0314 | CIN TPS63900, sát chân VIN |
| 4 | C3, C9, C15, C19, C20, C21 | 6 | 100nF | C_0603_1608Metric | CC0603KRX7R9BB104 | YAGEO | [C14663](https://www.lcsc.com/product-detail/C14663.html) | Basic | 0.0164 |  |
| 5 | C4, C5 | 2 | 22uF 25V | C_0805_2012Metric | CL21A226MAQNNNE | Samsung | [C45783](https://www.lcsc.com/product-detail/C45783.html) | Basic | 0.1055 | COUT TPS63900 |
| 6 | C6, C13, C17, C18 | 4 | 10nF | C_0603_1608Metric | CL10B103KB8NNNC | Samsung | [C1589](https://www.lcsc.com/product-detail/C1589.html) | Extended | 0.0074 |  |
| 7 | C7 | 1 | 1uF | C_0603_1608Metric | CL10A105KB8NNNC | Samsung | [C15849](https://www.lcsc.com/product-detail/C15849.html) | Basic | 0.0112 |  |
| 8 | C8 | 1 | 10uF 10V | C_0603_1608Metric | CL10A106KP8NNNC | Samsung | [C19702](https://www.lcsc.com/product-detail/C19702.html) | Basic | 0.0233 |  |
| 9 | C14 | 1 | 100pF C0G | C_0603_1608Metric | CL10C101JB8NNNC | Samsung | [C14858](https://www.lcsc.com/product-detail/C14858.html) | Basic | 0.0082 | Tụ định thời 555 – bắt buộc C0G |
| 10 | D1 | 1 | 1N4148WS | D_SOD-323 | 1N4148WS | Changjiang | [C2128](https://www.lcsc.com/product-detail/C2128.html) | Basic | 0.0110 | Tách đỉnh, rò ngược thấp |
| 11 | D2 | 1 | RED | LED_0603_1608Metric | KT-0603R | Hubei KENTO | [C2286](https://www.lcsc.com/product-detail/C2286.html) | Basic | 0.0077 | LED trạng thái |
| 12 | J1 | 1 | PROG | PinHeader_1x08_P2.54mm_Vertical | PZ254V-11-08P | XFCN | [C492407](https://www.lcsc.com/product-detail/C492407.html) | Extended | 0.0510 | Header nạp (có thể để trống lỗ) |
| 13 | L1 | 1 | 2.2uH | L_1008_2520Metric | TFM252012ALMA2R2MTAA | TDK | [C404804](https://www.lcsc.com/product-detail/C404804.html) | Extended | 0.3924 | Thay thế: Murata DFE252012F-2R2M=P2 (C576403) |
| 14 | Q1 | 1 | AO3415A | SOT-23 | AO3415A | AOS | [C133233](https://www.lcsc.com/product-detail/C133233.html) | Extended | 0.0985 | Chống ngược cực. Thay thế: DMG2305UX-7 (C150470) |
| 15 | Q2, Q4 | 2 | AO3401A | SOT-23 | AO3401A | AOS | [C15127](https://www.lcsc.com/product-detail/C15127.html) | Basic | 0.0813 | Công tắc cầu chia pin / VSENS |
| 16 | Q3 | 1 | 2N7002 | SOT-23 | 2N7002 | CJ | [C8545](https://www.lcsc.com/product-detail/C8545.html) | Basic | 0.0154 | Dịch mức gate Q2 |
| 17 | R1, R6, R7, R8, R9 | 5 | 100k | R_0603_1608Metric | 0603WAF1003T5E | UNI-ROYAL | [C25803](https://www.lcsc.com/product-detail/C25803.html) | Basic | 0.0029 |  |
| 18 | R2 | 1 | 36.5k | R_0603_1608Metric | 0603WAF3652T5E | UNI-ROYAL | [C23029](https://www.lcsc.com/product-detail/C23029.html) | Extended | 0.0016 | CFG1 → VO(2)=3.3 V (1 %) |
| 19 | R3, R10, R13 | 3 | 0R | R_0603_1608Metric | 0603WAF0000T5E | UNI-ROYAL | [C21189](https://www.lcsc.com/product-detail/C21189.html) | Basic | 0.0021 | R3 = CFG2 (unlimited); R10 = cầu đo dòng; R13 = chọn kích thích 555 |
| 20 | R4 | 1 | 16.2k | R_0603_1608Metric | 0603WAF1622T5E | UNI-ROYAL | [C22885](https://www.lcsc.com/product-detail/C22885.html) | Extended | 0.0014 | CFG3 → VO(1)=3.3 V (1 %) |
| 21 | R5 | 1 | 1M | R_0603_1608Metric | 0603WAF1004T5E | UNI-ROYAL | [C22935](https://www.lcsc.com/product-detail/C22935.html) | Basic | 0.0018 |  |
| 22 | R11, R12, R15, R18, R19, R20, R21 | 7 | 10k | R_0603_1608Metric | 0603WAF1002T5E | UNI-ROYAL | [C25804](https://www.lcsc.com/product-detail/C25804.html) | Basic | 0.0022 |  |
| 23 | R16, R17 | 2 | 470k | R_0603_1608Metric | 0603WAF4703T5E | UNI-ROYAL | [C23178](https://www.lcsc.com/product-detail/C23178.html) | Basic | 0.0030 |  |
| 24 | R22 | 1 | 1k | R_0603_1608Metric | 0603WAF1001T5E | UNI-ROYAL | [C21190](https://www.lcsc.com/product-detail/C21190.html) | Basic | 0.0017 |  |
| 25 | RT1 | 1 | 10k B3380 | R_0603_1608Metric | NCP18XH103F03RB | Murata | [C13564](https://www.lcsc.com/product-detail/C13564.html) | Extended | 0.0466 | NTC 10k B3380 1 %, đặt trên que |
| 26 | SW1 | 1 | BOOT/USER | SW_Push_1P1T_XKB_TS-1187A | TS-1187A-B-A-B | XKB | [C318884](https://www.lcsc.com/product-detail/C318884.html) | Basic | 0.0215 | Nút BOOT/USER |
| 27 | U1 | 1 | TPS63900DSKR | WSON-10-1EP_2.5x2.5mm_P0.5mm_EP1.2x2mm_ThermalVias_0.3mm | TPS63900DSKR | Texas Instruments | [C1518762](https://www.lcsc.com/product-detail/C1518762.html) | Extended | 0.8680 | Buck-boost 75 nA Iq |
| 28 | U3 | 1 | TLC555IDR | SOIC-8_3.9x4.9mm_P1.27mm | TLC555IDR | Texas Instruments | [C6987](https://www.lcsc.com/product-detail/C6987.html) | Extended | 0.3770 | Bản I (−40…85 °C). Thay thế: LMC555CMMX/NOPB (C398924, VSSOP-8 – cần đổi footprint) |
| 29 | U4 | 1 | SHT40-AD1F-R2 | Sensirion_DFN-4_1.5x1.5mm_P0.8mm_SHT4x_NoCentralPad | SHT40-AD1F-R2 | Sensirion | [C7461846](https://www.lcsc.com/product-detail/C7461846.html) | Extended | 2.0645 | Có màng PTFE. Thay thế: SHT40-AD1B-R2 (C2909890) nếu đặt trong buồng có màng thở |

**Tổng linh kiện (không gồm module ESP32-H2, PCB, pin): ≈ 5.24 USD/bo** (giá LCSC tham khảo 11/2026, số lượng 10).

> “Basic” là linh kiện thư viện cơ bản của JLCPCB (không phí nạp cuộn); “Extended” có phí nạp ~3 USD/mã.
> BT1 và J1 là linh kiện xuyên lỗ: CPL chỉ chứa linh kiện SMD, hai linh kiện này hàn tay (hoặc chọn dịch vụ THT).

## 3.2 Linh kiện không lắp (DNP) / không thuộc BOM

| Ký hiệu | Giá trị | LCSC | Lý do |
|---|---|---|---|
| U2 | ESP32-H2-WROOM-02C-H4S | – | Module ESP (không liệt kê theo yêu cầu, mua riêng/consign) |
| Y1 | 32.768 kHz 12.5 pF (X321532768KGD2SI) | C620155 | Tùy chọn: thạch anh RTC cho CSL/SSED |
| C10, C11 | 18 pF C0G (CL10C180JB8NNNC) | C1647 | Tải cho Y1 |
| C12 | 100 nF | C14663 | Tùy chọn: thêm trễ EN (module đã có RC) |
| R14 | 0 Ω | C21189 | Lắp khi dùng kích thích LEDC từ GPIO4 (khi đó bỏ R13 + U3) |
| SW2 | TS-1187A (nút RESET) | C318884 | Tùy chọn |
| PRB1 | Điện cực đầu dò | – | Là đồng trên PCB |
| TP1–TP6, H1, H2 | test point, lỗ M2 | – | Không phải linh kiện |

## 3.3 Vật tư ngoài BOM điện tử

| Hạng mục | Gợi ý |
|---|---|
| PCB | 26 × 212 mm, FR4 2 lớp **1.6 mm** (cứng để cắm đất), mask xanh/đen, HASL không chì hoặc ENIG, *via tented* (bắt buộc ở vùng đầu dò) |
| Pin | CR123A 3 V Li-MnO<sub>2</sub> (Panasonic CR123A, Energizer EL123AP, Varta…) ~1400–1600 mAh |
| Phủ bảo vệ | Conformal coating acrylic (AR) hoặc polyurethane (UR) cho phần đầu dò; tốt nhất 2 lớp, 50–100 µm; hoặc epoxy / cao su lỏng cho mép que |
| Vỏ | Hộp ABS/ASA chống UV hoặc ống PVC Ø32 mm có nắp ren + gioăng; lỗ thở Gore/ePTFE; keo epoxy/silicone trung tính tại khe que đi ra |
| Hút ẩm | Gói silica gel 1–2 g trong hộp |
