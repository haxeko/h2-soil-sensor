# Hardware (KiCad) – bo mạch v3, 26 × 45 mm

- Mở `h2-soil-sensor.kicad_pro` bằng KiCad 7/8/9. Thư viện riêng `h2soil` (symbol ESP32-H2-WROOM-02C, VBAT, VSENS; footprint
  module ESP32-H2, pad nạp `ProgPads_2x04_P2.54mm_D1.5mm` và WSON-10 via nhiệt 0.3 mm) đã khai báo trong `sym-lib-table` /
  `fp-lib-table` của project (`${KIPRJMOD}/lib/...`).
- `docs/schematic.pdf` – schematic 5 trang (sơ đồ khối, Power, MCU, Sensors, UI); `docs/pcb_top.*`, `docs/pcb_bottom.*`
  (mặt dưới nhìn gương), `docs/assembly_top.pdf` (vị trí + ký hiệu linh kiện); `docs/render.png`, `render_top.png`,
  `render_bottom.png` (ảnh minh hoạ); `docs/drc_report.txt` – báo cáo DRC (0 vi phạm, 0 pad chưa nối).
- `fab/h2-soil-sensor_gerbers.zip` (Gerber + khoan Excellon), `fab/h2-soil-sensor_BOM_JLCPCB.csv` và
  `fab/h2-soil-sensor_CPL_JLCPCB.csv` (35 linh kiện SMT lắp máy, kể cả U1), `fab/h2-soil-sensor_not_assembled.csv` (module ESP,
  J4 THT hàn tay, pad J1/J3).

## Cổng kết nối

| Ký hiệu | Loại | Chân |
|---|---|---|
| J3 | 2 pad xuyên lỗ hàn dây pin (lỗ 1.1 mm, bước 4.6 mm) | pad 1 vuông = “+” (VBAT_RAW), pad 2 tròn = “−” (GND); silkscreen “− BAT +” |
| J4 | JST-PH 2.0 3P (B3B-PH-K-S) – module độ ẩm đất | 1 = GND, 2 = VCC (VSENS), 3 = AOUT; J4 xoay 180°: chân 1 (GND) ở bên phải, nhãn silkscreen “A V G” |
| J1 | 8 pad tròn SMD Ø1.5 mm, lưới 2.54 mm, 2 hàng × 4, không phủ kem hàn | hàng sát mép bo (trái → phải): 1 = 3V3, 3 = TX, 5 = EN, 7 = D−; hàng trong: 2 = GND, 4 = RX, 6 = IO9, 8 = D+; pad 1 có chữ “1” |

Cáp đi kèm module thường là PH2.0 → Dupont cái, không vừa J4: dùng cáp PH2.0-3P hai đầu nối thẳng (hoặc bấm lại đầu) và đo
để chắc GND → GND trước khi cắm.

## Tái tạo từ script

Toàn bộ schematic/PCB được sinh từ `tools/design.py` (danh sách linh kiện, net, footprint, mã LCSC, ghi chú):

```bash
cd tools
python3 gen_footprints.py ..
python3 gen_schematic.py ..
python3 check_netlist.py ../h2-soil-sensor.kicad_sch    # "nets: 41  components checked: 43 ... OK"
python3 gen_pcb.py          # đặt linh kiện + đi dây (router.py) + đổ đồng + DRC; tự chạy với PYTHONHASHSEED=0 → kết quả lặp lại
python3 make_fab.py         # Gerber/khoan zip, BOM/CPL JLCPCB, not_assembled.csv, PDF, pcb_top/bottom.png
python3 render.py           # ảnh minh hoạ render_top/render_bottom/render.png
```

Yêu cầu: KiCad 7 (`kicad-cli`, module Python `pcbnew`), Python ≥ 3.10, numpy, Pillow, poppler-utils (render ảnh).
Các script giả định thư viện KiCad ở `/usr/share/kicad/{symbols,footprints}` (sửa hằng `KICAD_FP` / `KICAD_SYM_DIR` nếu khác).
Lưu ý: chạy lại `gen_pcb.py` sẽ ghi đè mọi chỉnh sửa tay trong `.kicad_pcb`.
