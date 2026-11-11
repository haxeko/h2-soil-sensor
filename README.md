# H2 Soil Sensor — cảm biến độ ẩm đất Matter over Thread chạy pin

Thiết bị cắm đất (dạng que) đo **độ ẩm đất** (đầu dò điện dung in trên PCB), **nhiệt độ đất** (NTC) và tuỳ chọn
**nhiệt độ/độ ẩm không khí** (SHT40), kết nối **Matter over Thread** bằng **ESP32-H2-WROOM-02C** hoạt động như
**Sleepy End Device / ICD**, nuôi bằng **1 pin CR123A** qua buck-boost **TPS63900** (Iq 75 nA).

| | |
|---|---|
| ![PCB top](hardware/docs/pcb_top.png) | **Phần cứng**: KiCad (schematic phân cấp 5 sheet + PCB 2 lớp 26 × 212 mm, đã đi dây, DRC sạch), Gerber/BOM/CPL cho JLCPCB.<br><br>**Firmware**: ESP-IDF v6.0.2 + esp-matter (Matter 1.5): Soil Sensor (Soil Measurement), Humidity Sensor (tương thích Apple/Google), Temperature/Humidity Sensor (SHT40), Power Source (pin), ICD SIT/LIT, light-sleep, hiệu chuẩn bằng nút nhấn.<br><br>**Tuổi thọ pin ước tính**: ~2.6 năm (SIT, poll 15 s) – ~3.6 năm (LIT, poll 60 s), đo mỗi 15 phút. |

## Tài liệu (tiếng Việt)

1. [Sơ đồ khối và lựa chọn linh kiện](docs/01-so-do-khoi-va-linh-kien.md)
2. [Schematic chi tiết theo khối (nguồn, MCU, cảm biến, nút/LED)](docs/02-schematic.md) — PDF: [`hardware/docs/schematic.pdf`](hardware/docs/schematic.pdf)
3. [BOM kèm mã LCSC (không gồm module ESP)](docs/03-bom.md)
4. [Hướng dẫn layout PCB](docs/04-layout-pcb.md)
5. [Dòng tiêu thụ từng trạng thái và tuổi thọ pin](docs/05-nang-luong-va-tuoi-tho-pin.md) — mô hình: [`docs/power_budget.py`](docs/power_budget.py)
6. [Cấu trúc project firmware và code chính](docs/06-firmware.md)
7. [Rủi ro và lưu ý khi dùng ngoài trời](docs/07-rui-ro-ngoai-troi.md)

## Cấu trúc repository

```
hardware/
├── h2-soil-sensor.kicad_pro / .kicad_sch / .kicad_pcb   # project KiCad (mở bằng KiCad ≥ 7)
├── power.kicad_sch, mcu.kicad_sch, sensors.kicad_sch, ui.kicad_sch
├── lib/h2soil.kicad_sym, lib/h2soil.pretty/             # symbol/footprint riêng (module, giá pin, điện cực, WSON-10)
├── fab/                                                 # Gerber+khoan (zip), BOM & CPL JLCPCB
├── docs/                                                # schematic.pdf, pcb_top/bottom (pdf/png), assembly_top.pdf, drc_report.txt
└── tools/                                               # script sinh schematic/PCB/fab từ design.py (+ router A*)
firmware/                                                # project ESP-IDF + esp-matter
docs/                                                    # tài liệu thiết kế
```

## Trạng thái kiểm chứng

| Hạng mục | Kết quả |
|---|---|
| Schematic | Netlist xuất bằng `kicad-cli` khớp 100 % với `design.py` (47 net, 72 linh kiện, mọi chân); PWR_FLAG đủ |
| PCB | 38/38 net đã đi dây; **DRC KiCad: 0 vi phạm, 0 pad chưa nối, 0 lỗi footprint** |
| Linh kiện | Mã LCSC kiểm tra tồn kho/giá qua API JLCPCB (11/2026) |
| Firmware | `idf.py build` thành công (ESP-IDF v6.0.2, esp-matter main / Matter 1.5, esp32h2), 1.68 MB, còn 14 % phân vùng OTA |
| Chưa làm được trong môi trường này | Chạy thử trên phần cứng thật, đo dòng thực tế, hiệu chuẩn đầu dò, kiểm tra anten/vỏ — cần bo mẫu |

## Bắt đầu nhanh

```bash
# Phần cứng: mở hardware/h2-soil-sensor.kicad_pro trong KiCad; file sản xuất ở hardware/fab/
# Firmware:
. esp-idf/export.sh && . esp-matter/export.sh
cd firmware && idf.py set-target esp32h2 && idf.py build
idf.py -p /dev/ttyACM0 flash monitor     # USB Serial/JTAG qua header J1 (D+, D−, GND), pin đã lắp
```

Sau khi nạp: thiết bị mở BLE commissioning 15 phút — quét mã QR in trong log bằng ứng dụng Home (Apple Home, Google Home,
SmartThings, Home Assistant…). Nhấn 2 lần nút để hiệu chuẩn KHÔ (que trong không khí), 3 lần để hiệu chuẩn ƯỚT (que ngập nước tới vạch).
