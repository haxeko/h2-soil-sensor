# 4. Hướng dẫn layout PCB

File KiCad: `hardware/h2-soil-sensor.kicad_pcb` (KiCad 7 trở lên; mở bằng KiCad 8/9 sẽ tự nâng định dạng).
Bo v2 đã được đặt linh kiện, đi dây đầy đủ (32/32 net tín hiệu; GND bằng đổ đồng), đổ đồng GND hai lớp và khâu via.
**DRC: 0 vi phạm, 0 pad chưa nối, 0 lỗi footprint** (`hardware/docs/drc_report.txt`). File sản xuất: `hardware/fab/`
(Gerber + khoan zip, BOM, CPL). Ảnh minh hoạ lắp ráp: [`render_v2.png`](../hardware/docs/render_v2.png); vị trí + ký hiệu
linh kiện: [`assembly_top.pdf`](../hardware/docs/assembly_top.pdf).

| Mặt trên (F.Cu + silkscreen) | Mặt dưới (B.Cu, nhìn gương) |
|---|---|
| ![top](../hardware/docs/pcb_top.png) | ![bottom](../hardware/docs/pcb_bottom.png) |

## 4.1 Thông số bo

| Mục | Giá trị |
|---|---|
| Kích thước | 36 × 60 mm, vát 4 góc 1 mm; module U2 nhô thêm 6 mm (vùng anten) qua mép trên |
| Lớp | 2 lớp, FR4 1.6 mm, đồng 1 oz; **mọi linh kiện ở mặt trên** |
| Luật | track mặc định 0.2 mm / khe hở 0.2 mm; net *Power* (+3V3, VBAT, VBAT_RAW, VIN_BB, LX1/2, VSENS, GND) 0.4 mm; net *Analog* (SOIL_AOUT, SOIL_ADC, NTC_ADC, VBAT_ADC) 0.25 mm, khe hở 0.3 mm; via 0.6/0.3 mm; đồng–mép bo 0.45 mm (router giữ 0.5 mm); lỗ–lỗ 0.25 mm |
| Lỗ khoan | 0.3 mm (via, via nhiệt), 0.75 mm (JST-PH), 1.0 mm (header 2.54 mm), 1.1 mm (pad dây pin J3), 3.2 mm không mạ (M3) |
| Kết quả đi dây | 285 đoạn dây (F.Cu 530 mm, B.Cu 177 mm); 205 via 0.6/0.3 mm = 69 via tín hiệu + 136 via GND (32 fan-out + 104 khâu) |
| Khả năng sản xuất | Nằm trong năng lực tiêu chuẩn JLCPCB/PCBWay 2 lớp (footprint TPS63900 dùng via nhiệt 0.3 mm) |

## 4.2 Bố trí theo vùng

Toạ độ bo (mm), gốc ở góc trên trái, y tăng xuống dưới.

| Vùng | Nội dung | Lưu ý |
|---|---|---|
| y −6…0 (ngoài bo) | Anten PCB của module | Không bo, không đồng, không linh kiện; trong hộp không để cáp, pin, vít kim loại ở phía này; vỏ cách anten ≥ 15 mm |
| x 9…27, y 0…14 | U2 ESP32-H2-WROOM-02C, đặt giữa mép trên | Module sát mép, vùng anten nhô ra ngoài (phương án tốt nhất theo *ESP32-H2 Hardware Design Guidelines*); mặt trên dưới thân module chỉ có GND (router cấm đi dây lớp trên), 9 via nhiệt ở EPAD |
| x ≈ 4, y 2…13 / góc trên phải | C9, C8 sát chân 3V3, R11 (IO8), C12 (DNP) / LED D2 + R22 | |
| y ≈ 16…18 | Y1, C10, C11 (DNP) ngay dưới module, gần IO13/IO14 | Đường XTAL ngắn |
| x 2…12, y 20…32 | Tầng nguồn TPS63900: C1, R10, C2, C3, U1, L1, C4, C5, R2–R4 | Vòng VIN và VOUT ngắn nhất, đi dây tay và khoá |
| x 13…25, y 20…31 | Đo pin (Q2, Q3, R5–R8, C6) + công tắc VSENS (Q4, R9, C7) | |
| mép phải, y 20…38 | J1 PROG 1×8 | Nhãn chân 3V3…D+ in cạnh header; xa anten |
| y 34…38 | SW1 BOOT (trái), TP1–TP4 | |
| mép trái, y 41…51 | Pin: J2 JST-PH 2P (y = 45), J3 2 pad “−” (x 2.4) / “+” (x 7.0) ở y = 50.8; Q1 + R1 | Nhãn BAT, “−”, “+” |
| x 17…29, y 43…51 | U3 SRV05-4, R12/C13 (SOIL), R18/C19 (NTC), R19/R20/C20 (I²C), C14 | Nằm giữa các cổng và ESP32-H2 |
| mép dưới, y 56…58 | J4 SOIL (x 10–14), J7 NTC (x 19–21), J6 I²C (x 25.6–33.2) | Mọi cáp cảm biến ra cùng một phía; nhãn chân in cạnh cổng |
| H1 (3.8; 56.5), H2 (32.3; 44.5) | Lỗ M3 | Không có đường mạch/via trong bán kính 3.2 mm (dưới đầu vít), vẫn đổ GND |

## 4.3 Quy tắc layout quan trọng

### Anten và RF
1. Vùng anten của module **không có đồng ở mọi lớp** – ở bo này vùng anten nằm hẳn ngoài mép bo.
2. GND liên tục dưới thân module, nhiều via GND quanh module để làm “mặt phẳng phản xạ” cho anten.
3. Không đặt linh kiện cao/kim loại gần anten: cổng pin và các cổng cảm biến (cùng cáp) đều ở nửa dưới bo; khi lắp vào hộp,
   đi cáp và đặt hộp pin phía dưới bo, không vòng qua đầu anten. Vỏ nhựa không pha carbon/kim loại, khe hở ≥ 15 mm.
4. Đường UART/USB không chạy sát vùng anten (J1 bắt đầu từ y = 20).

### Tầng nguồn TPS63900
1. C2 (10 µF) + C3 (100 nF) sát VIN/GND; C4/C5 (2 × 22 µF) sát VOUT/GND – đây là hai vòng dòng xung quan trọng nhất.
2. L1 ngay cạnh LX1/LX2; đường LX ngắn, rộng (0.4 mm) và **không** chạy dưới các tín hiệu analog.
3. EP (pad nhiệt) nối GND bằng 6 via 0.3 mm; chân SEL và GND (pin 8) nối thẳng vào EP.
4. Điện trở CFG1–3 sát chân, không có tụ, đường ngắn (< 10 pF).
5. R10 (0 Ω) đặt trên đường VBAT→VIN_BB để đo dòng (tháo ra, gắn ampe kế/PPK2).

### Cổng cảm biến, analog và ESD
1. Cổng cảm biến dồn về mép dưới, cổng pin ở mép trái → cáp không đi qua vùng module/anten và gom được qua 1–2 ốc siết cáp.
2. U3 nằm trên đường từ cổng tới ESP32-H2; R12/C13 đặt sát nhau, C19 cạnh R18; net analog 0.25 mm, khe hở 0.3 mm.
3. C14/C20 (tụ đệm VSENS) gần các cổng; C7 cạnh Q4.
4. Silkscreen mặt trên ghi tên chân cạnh mọi cổng (GND VCC AOUT, NTC, VCC GND SCL SDA, “−/+”, PROG); mặt dưới in tóm tắt
   (SOIL: GND VCC AOUT; I2C: VCC GND SCL SDA; NTC: 10k B3950; BAT 2.0–3.3V, reverse protected). Ký hiệu linh kiện nằm ở lớp
   F.Fab (xem `assembly_top.pdf`), không in lên silkscreen.

### Nối đất và khâu via
- Mặt GND ở cả 2 lớp trên toàn bo (khe hở vùng đổ 0.3 mm, độ dày tối thiểu 0.25 mm, thermal relief 0.3/0.4 mm cho chân THT;
  pad GND của J1 nối đặc).
- 32 via fan-out cho pad GND SMD + 104 via khâu theo lưới 2.5 mm; mọi đảo đồng phải chạm via/lỗ GND, nếu không được thêm via
  hoặc tự loại bỏ.
- Đường tín hiệu chủ yếu ở lớp trên (229/285 đoạn); lớp dưới giữ mặt GND gần như liền (xem ảnh B.Cu).

## 4.4 Quy trình tạo/tái tạo bo (tự động hoá)

Toàn bộ phần cứng được sinh bằng script Python (`hardware/tools/`), có thể chỉnh và chạy lại:

```bash
cd hardware/tools
python3 gen_footprints.py ..      # thư viện riêng: symbol ESP32-H2/VBAT/VSENS, footprint module + WSON-10 via 0.3 mm
python3 gen_schematic.py ..       # 5 sheet schematic từ design.py
python3 check_netlist.py ../h2-soil-sensor.kicad_sch   # đối chiếu netlist ↔ design.py
python3 gen_pcb.py --check        # chỉ kiểm tra chồng courtyard / ra ngoài bo (fpinfo.py)
python3 gen_pcb.py                # đặt linh kiện, đi dây vòng TPS63900 (khoá), fan-out GND, router 2 lớp, đổ đồng, DRC
python3 make_fab.py               # Gerber+khoan zip, BOM/CPL JLCPCB, not_assembled.csv, PDF schematic/PCB/lắp ráp, PNG
python3 render.py                 # ảnh minh hoạ render_top/render_bottom/render_v2.png
```

- Vị trí linh kiện nằm trong bảng `PLACE` của `gen_pcb.py` (toạ độ bo, mm, mặt trên); đường viền vát góc `OUTLINE`;
  nhãn silkscreen `LABELS`.
- `router.py` là bộ đi dây lưới 0.1 mm hai lớp: A* 8 hướng với chi phí via (14), lớp dưới (×1.8) và đổi hướng (0.4); bản đồ
  chiếm chỗ cho từng cặp bề rộng/khe hở (vật cản được phình theo w/2 + khe hở + 0.05 mm) nên kết quả đạt DRC theo cấu trúc.
  Net ngắn và net nguồn đi trước; net thất bại được đưa lên đầu và đi lại (tối đa 8 lượt – lần chạy hiện tại: 2 lượt,
  32/32 net). Vùng cấm: lớp trên dưới thân module, bán kính 3.2 mm quanh lỗ M3.
- `gen_pcb.py` tự chạy lại chính nó với `PYTHONHASHSEED=0` → thứ tự net và kết quả đi dây **lặp lại y hệt** mỗi lần.
- Các script giả định thư viện KiCad ở `/usr/share/kicad/` (Linux). Chạy lại `gen_pcb.py` sẽ ghi đè mọi chỉnh sửa tay; nếu muốn
  tối ưu thẩm mỹ, mở `.kicad_pcb` trong KiCad, xoá dây không khoá rồi đi lại bằng tay hoặc Freerouting.

## 4.5 Lưu ý đặt hàng và lắp ráp

| Mục | Chọn |
|---|---|
| Độ dày | 1.6 mm |
| Bề mặt | HASL không chì; ENIG nếu bo lưu kho/lắp ở môi trường ẩm (pad không bị oxy hoá trước khi hàn) |
| Via | Tented hoặc để hở đều được (bo nằm trong hộp, không tiếp xúc đất); tented giúp lớp conformal coating phẳng hơn |
| SMT | Mặt trên: 40 linh kiện / 22 mã theo BOM + CPL trong `hardware/fab/` |
| THT | J1, J2, J4, J6, J7 hàn tay (hoặc dịch vụ THT); J1 có thể để trống lỗ cho bản lắp đặt |
| Module ESP32-H2 | Hàn reflow 1 lần (MSL3) hoặc consign; hàn tay cần hot-air/bếp gia nhiệt cho EPAD |
| Kiểm tra sau lắp ráp | Dòng nền tại R10 ≈ 30–35 µA (phía pin, giữa các lần đo); TP4 (VSENS) = 0 V khi ngủ và ≈ 3.3 V trong ~1.5 s mỗi lần đo; AOUT ở J4: trong không khí ~2.4–2.8 V, trong nước ~1.0–1.4 V |
