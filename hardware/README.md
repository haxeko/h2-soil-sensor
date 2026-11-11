# Hardware (KiCad)

- Mở `h2-soil-sensor.kicad_pro` bằng KiCad 7/8/9. Thư viện riêng `h2soil` (symbol + footprint) đã khai báo trong
  `sym-lib-table` / `fp-lib-table` của project (`${KIPRJMOD}/lib/...`).
- `docs/schematic.pdf` – schematic 5 trang; `docs/pcb_top.*`, `docs/pcb_bottom.*`, `docs/assembly_top.pdf` – PCB;
  `docs/drc_report.txt` – báo cáo DRC (0 vi phạm).
- `fab/h2-soil-sensor_gerbers.zip` (Gerber + khoan Excellon), `fab/h2-soil-sensor_BOM_JLCPCB.csv`,
  `fab/h2-soil-sensor_CPL_JLCPCB.csv`, `fab/h2-soil-sensor_not_assembled.csv`.

## Tái tạo từ script

Toàn bộ schematic/PCB được sinh từ `tools/design.py` (danh sách linh kiện, net, footprint, mã LCSC):

```bash
cd tools
python3 gen_footprints.py ..
python3 gen_schematic.py ..
python3 check_netlist.py ../h2-soil-sensor.kicad_sch
export KICAD7_FOOTPRINT_DIR=/usr/share/kicad/footprints   # đường dẫn thư viện KiCad của máy bạn
python3 gen_pcb.py          # đặt linh kiện + đi dây (router.py) + đổ đồng + DRC  (~1 phút)
python3 make_fab.py
```

Yêu cầu: KiCad 7 (`kicad-cli`, module Python `pcbnew`), Python ≥ 3.10, numpy, Pillow, poppler-utils (render ảnh).
Lưu ý: chạy lại `gen_pcb.py` sẽ ghi đè mọi chỉnh sửa tay trong `.kicad_pcb`.
