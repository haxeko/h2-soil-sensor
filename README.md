# H2 Soil Sensor — cảm biến độ ẩm đất Matter over Thread chạy pin

**Phiên bản 3:** bo mạch gọn **26 × 45 mm** chỉ gồm **ESP32-H2-WROOM-02C** + **tầng nguồn pin** (1 × CR123A, buck-boost
**TPS63900**, Iq 75 nA) + **một cổng J4 JST-PH 2.0 3P** cho module phổ biến **“Capacitive Soil Moisture Sensor v1.2”**
(module điện dung, ngõ ra analog AOUT). Pin hàn vào **2 pad J3** (“+” vuông, “−” tròn) bằng dây của hộp pin; nạp firmware qua
**8 pad tròn J1** (kẹp pogo 2.54 mm hoặc hàn dây) thay cho header. Thiết bị kết nối **Matter over Thread** như
**Sleepy End Device / ICD**; module chỉ được cấp nguồn (rail VSENS qua MOSFET) trong ~1.5 s mỗi lần đo.

| | |
|---|---|
| ![Bo mạch v3, mặt trên và mặt dưới](hardware/docs/render.png) | **Phần cứng**: KiCad (schematic phân cấp 5 sheet + PCB 2 lớp 26 × 45 mm, đã đi dây, DRC sạch), Gerber/BOM/CPL cho JLCPCB; linh kiện trên bo ≈ 2.1 USD (không gồm module ESP).<br><br>**Firmware**: ESP-IDF v6.0.2 + esp-matter (Matter 1.5): Soil Sensor (Soil Measurement), Humidity Sensor (bản sao độ ẩm đất, tương thích Apple/Google), Power Source (pin), ICD SIT/LIT, light-sleep, hiệu chuẩn bằng nút nhấn.<br><br>**Tuổi thọ pin ước tính** (đo mỗi 15 phút): ~2.2 năm (SIT, poll 15 s) – ~2.9 năm (LIT, poll 60 s); ~3.3 năm với LIT + đo mỗi 30 phút. |

## Tài liệu (tiếng Việt)

1. [Sơ đồ khối, lựa chọn linh kiện và module cảm biến](docs/01-so-do-khoi-va-linh-kien.md)
2. [Schematic chi tiết theo khối (nguồn, MCU, cổng cảm biến, nút/LED/pad nạp)](docs/02-schematic.md) — PDF: [`hardware/docs/schematic.pdf`](hardware/docs/schematic.pdf)
3. [BOM kèm mã LCSC (không gồm module ESP) và vật tư ngoài BOM](docs/03-bom.md)
4. [Hướng dẫn layout PCB](docs/04-layout-pcb.md)
5. [Dòng tiêu thụ từng trạng thái và tuổi thọ pin](docs/05-nang-luong-va-tuoi-tho-pin.md) — mô hình: [`docs/power_budget.py`](docs/power_budget.py)
6. [Cấu trúc project firmware và code chính](docs/06-firmware.md)
7. [Rủi ro và lưu ý khi dùng ngoài trời](docs/07-rui-ro-ngoai-troi.md)

## Cấu trúc repository

```
hardware/
├── h2-soil-sensor.kicad_pro / .kicad_sch / .kicad_pcb   # project KiCad (mở bằng KiCad ≥ 7)
├── power.kicad_sch, mcu.kicad_sch, sensors.kicad_sch, ui.kicad_sch
├── lib/h2soil.kicad_sym, lib/h2soil.pretty/             # symbol/footprint riêng (module ESP32-H2, pad nạp 2×4, WSON-10 via 0.3 mm)
├── fab/                                                 # Gerber+khoan (zip), BOM & CPL JLCPCB, danh sách không lắp máy
├── docs/                                                # schematic.pdf, pcb_top/bottom, assembly_top.pdf, render*.png, drc_report.txt
└── tools/                                               # script sinh schematic/PCB/fab từ design.py (+ router A*)
firmware/                                                # project ESP-IDF + esp-matter
docs/                                                    # tài liệu thiết kế
```

## Trạng thái kiểm chứng

| Hạng mục | Kết quả |
|---|---|
| Schematic | Netlist xuất bằng `kicad-cli` khớp 100 % với `design.py` (41 net, 43 ký hiệu = 39 linh kiện + 4 PWR_FLAG, mọi chân); PWR_FLAG đủ |
| PCB | 27/27 net tín hiệu đã đi dây (GND bằng đổ đồng 2 lớp); **DRC KiCad: 0 vi phạm, 0 pad chưa nối, 0 lỗi footprint** |
| Linh kiện | Mã LCSC kiểm tra tồn kho/giá qua API JLCPCB (11/2026) |
| Firmware | `idf.py build` thành công (ESP-IDF v6.0.2, esp-matter main / Matter 1.5, esp32h2), 1.66 MB, còn 16 % phân vùng OTA, không cảnh báo trong mã ứng dụng |
| Chưa làm được trong môi trường này | Chạy thử trên phần cứng thật, đo dòng thực tế, thử và hiệu chuẩn với module thật, kiểm tra anten/vỏ — cần bo mẫu |

## Bắt đầu nhanh

```bash
# Phần cứng: mở hardware/h2-soil-sensor.kicad_pro trong KiCad; file sản xuất ở hardware/fab/
# Firmware:
. esp-idf/export.sh && . esp-matter/export.sh
cd firmware && idf.py set-target esp32h2 && idf.py build
idf.py -p /dev/ttyACM0 flash monitor     # USB Serial/JTAG qua pad J1 (D+ = 8, D− = 7, GND = 2), pin đã lắp
```

1. Cáp đi kèm module thường là PH2.0 → đầu Dupont cái, **không cắm được vào J4**: dùng cáp PH2.0-3P hai đầu (nối thẳng) hoặc
   bấm lại đầu; đo để chắc GND → J4-1, VCC → J4-2, AOUT → J4-3.
2. Sau khi nạp: thiết bị mở BLE commissioning 15 phút — quét mã QR in trong log bằng ứng dụng Home (Apple Home, Google Home,
   SmartThings, Home Assistant…).
3. Hiệu chuẩn module: nhấn 2 lần nút khi đầu dò khô trong không khí (KHÔ), 3 lần khi đầu dò ngập nước tới vạch giới hạn (ƯỚT).

## Các phiên bản

| Phiên bản | Commit | Mô tả |
|---|---|---|
| v1 | `3c3f9e9` | Bo dạng que cắm đất 26 × 212 mm: đầu dò điện dung in trên PCB + TLC555, SHT40 và NTC trên bo, đế pin CR123A trên bo |
| v2 | `08ab9fe` | Bo 36 × 60 mm cắm module có sẵn: module đất, module I²C nhiệt/ẩm, đầu dò NTC; pin qua JST hoặc pad |
| v3 | hiện tại | Bo 26 × 45 mm chỉ cho module “Capacitive Soil Moisture Sensor v1.2”; pad nạp tròn thay header |
