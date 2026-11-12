# Hardware (KiCad) – bo mạch v2, 36 × 60 mm

- Mở `h2-soil-sensor.kicad_pro` bằng KiCad 7/8/9. Thư viện riêng `h2soil` (symbol ESP32-H2-WROOM-02C, VBAT, VSENS; footprint
  module ESP32-H2 và WSON-10 via nhiệt 0.3 mm) đã khai báo trong `sym-lib-table` / `fp-lib-table` của project (`${KIPRJMOD}/lib/...`).
- `docs/schematic.pdf` – schematic 5 trang (sơ đồ khối, Power, MCU, Sensors, UI); `docs/pcb_top.*`, `docs/pcb_bottom.*`
  (mặt dưới nhìn gương), `docs/assembly_top.pdf` (vị trí + ký hiệu linh kiện); `docs/render_v2.png`, `render_top.png`,
  `render_bottom.png` (ảnh minh hoạ); `docs/drc_report.txt` – báo cáo DRC (0 vi phạm, 0 pad chưa nối).
- `fab/h2-soil-sensor_gerbers.zip` (Gerber + khoan Excellon PTH/NPTH), `fab/h2-soil-sensor_BOM_JLCPCB.csv` và
  `fab/h2-soil-sensor_CPL_JLCPCB.csv` (chỉ linh kiện SMT lắp máy), `fab/h2-soil-sensor_not_assembled.csv` (module ESP,
  connector THT hàn tay, DNP, pad/lỗ/test point).

## Cổng kết nối

| Ký hiệu | Loại | Chân |
|---|---|---|
| J2 | JST-PH 2.0 2P (B2B-PH-K-S) | 1 = BAT+ (VBAT_RAW), 2 = GND |
| J3 | 2 pad hàn dây, bước 4.6 mm, lỗ 1.1 mm | “+” (pad vuông, VBAT_RAW), “−” (GND) – song song J2, chỉ dùng một trong hai |
| J4 | JST-PH 2.0 3P (B3B-PH-K-S) – module độ ẩm đất | 1 = GND, 2 = VCC (VSENS), 3 = AOUT |
| J7 | JST-PH 2.0 2P – đầu dò NTC 10k | 1 = NTC_ADC, 2 = GND |
| J6 | header 1×4 2.54 mm – module I²C | 1 = VCC (VSENS), 2 = GND, 3 = SCL, 4 = SDA |
| J1 | header 1×8 2.54 mm – PROG | 1 = 3V3, 2 = GND, 3 = TX, 4 = RX, 5 = EN, 6 = IO9, 7 = D−, 8 = D+ |

Thứ tự chân của cáp JST và của module (nhất là module I²C) **không thống nhất giữa các hãng** – đo bằng đồng hồ trước khi cắm.

## Tái tạo từ script

Toàn bộ schematic/PCB được sinh từ `tools/design.py` (danh sách linh kiện, net, footprint, mã LCSC, ghi chú):

```bash
cd tools
python3 gen_footprints.py ..
python3 gen_schematic.py ..
python3 check_netlist.py ../h2-soil-sensor.kicad_sch    # "nets: 41  components checked: 61 ... OK"
python3 gen_pcb.py          # đặt linh kiện + đi dây (router.py) + đổ đồng + DRC; tự chạy với PYTHONHASHSEED=0 → kết quả lặp lại
python3 make_fab.py         # Gerber/khoan zip, BOM/CPL JLCPCB, not_assembled.csv, PDF, pcb_top/bottom.png
python3 render.py           # ảnh minh hoạ render_top/render_bottom/render_v2.png
```

Yêu cầu: KiCad 7 (`kicad-cli`, module Python `pcbnew`), Python ≥ 3.10, numpy, Pillow, poppler-utils (render ảnh).
Các script giả định thư viện KiCad ở `/usr/share/kicad/{symbols,footprints}` (sửa hằng `KICAD_FP` / `KICAD_SYM_DIR` nếu khác).
Lưu ý: chạy lại `gen_pcb.py` sẽ ghi đè mọi chỉnh sửa tay trong `.kicad_pcb`.
