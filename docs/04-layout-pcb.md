# 4. Hướng dẫn layout PCB

File KiCad: `hardware/h2-soil-sensor.kicad_pcb` (KiCad 7 trở lên; mở bằng KiCad 8/9 sẽ tự nâng định dạng).
Bo đã được đặt linh kiện, đi dây đầy đủ (38/38 net), đổ đồng GND hai lớp và khâu via. **DRC: 0 vi phạm, 0 pad chưa nối**
(`hardware/docs/drc_report.txt`). File sản xuất: `hardware/fab/` (Gerber + khoan zip, BOM, CPL).

| Mặt trên (F.Cu + silkscreen) | Mặt dưới (B.Cu, nhìn gương) |
|---|---|
| ![top](../hardware/docs/pcb_top.png) | ![bottom](../hardware/docs/pcb_bottom.png) |

## 4.1 Thông số bo

| Mục | Giá trị |
|---|---|
| Kích thước | 26 × 212 mm (phần điện tử 26 mm, que 20 mm, mũi nhọn 12 mm); module nhô thêm 6 mm (anten) phía trên |
| Lớp | 2 lớp, FR4 1.6 mm, đồng 1 oz |
| Luật | track mặc định 0.2 mm / khe hở 0.2 mm; net *Power* (+3V3, VBAT, VIN_BB, LX1/2, VSENS, GND) 0.4 mm; net *Analog* (PROBE_*, SOIL_ADC, NTC_ADC, OSC_OUT) 0.25 mm, khe hở 0.3 mm; via 0.6/0.3 mm; mép bo 0.45 mm; lỗ–lỗ 0.25 mm |
| Khả năng sản xuất | Nằm trong năng lực tiêu chuẩn JLCPCB/PCBWay 2 lớp (không cần via 0.2 mm – footprint TPS63900 đã đổi via nhiệt sang 0.3 mm) |

## 4.2 Bố trí theo vùng (từ trên xuống)

| Vùng (y, mm) | Nội dung | Lưu ý |
|---|---|---|
| −6…0 | Anten PCB của module (ngoài bo) | Không bo, không đồng, không linh kiện; vỏ hộp cách anten ≥ 15 mm mọi phía |
| 0…14 | ESP32-H2-WROOM-02C | Module đặt sát mép trên, vùng anten nhô ra ngoài (phương án tốt nhất theo *ESP32-H2 Hardware Design Guidelines*); mặt trên dưới thân module là GND, cấm đi dây lớp trên dưới thân module; 9 via nhiệt ở EPAD |
| 15…33 | Tầng nguồn TPS63900 (trái), đo pin + công tắc VSENS (phải), LED | Vòng VIN–C2/C3–GND và VOUT–C4/C5–GND ngắn nhất; L1 ngay cạnh LX1/LX2 |
| 33…48 | SW1 (BOOT), SW2 (RESET, DNP), test point, **đảo SHT40** | Đảo SHT40 cách nhiệt bằng rãnh phay 0.8 × 13 mm, sát mép phải để thông với lỗ thở của vỏ |
| 48…52 | J1 header 1×8 | Nhãn chân in ở mặt dưới |
| 53…101 | Q1 chống ngược cực, **giá pin CR123A** | Pin (vỏ kim loại) cách anten > 50 mm → không làm lệch tần anten; dưới giá pin chỉ có mặt GND + vài đường tín hiệu |
| 102…121 | Front-end đầu dò: TLC555, D1, C17, R15–R18, NTC divider, lỗ M2 | Đặt **sát vạch mặt đất** để dây PROBE_SENSE ngắn nhất (điện dung ký sinh nhỏ, ít nhiễu) |
| 124 | **SOIL LINE** (vạch silkscreen) | Phần dưới vạch phủ conformal coating, nằm trong đất |
| 121…198 | Điện cực: SENSE 8 × 66 mm ở giữa; GND 3 mm hai mép + thanh đáy; cả 2 lớp, khâu via mỗi 10 mm | Không đổ đồng GND giữa các điện cực; khe SENSE–GND 2.4 mm |
| ~173 | NTC RT1 (≈ 5 cm dưới mặt đất) | Nằm trong kênh riêng mép phải: dải GND lớp trên hẹp lại 1.2 mm để chừa chỗ cho đường NTC_ADC, đường này được dải GND che chắn khỏi điện cực SENSE |
| 200…212 | Mũi nhọn | Không có đồng |

## 4.3 Quy tắc layout quan trọng

### Anten và RF
1. Vùng anten của module **không có đồng ở mọi lớp** – ở bo này vùng anten nằm hẳn ngoài mép bo.
2. GND liên tục dưới thân module, nhiều via GND quanh module (khoảng cách ≤ 2.5 mm) để làm “mặt phẳng phản xạ” cho anten.
3. Không đặt linh kiện cao/kim loại (pin, header) gần anten; vỏ hộp: nhựa không pha carbon/kim loại, khe hở ≥ 15 mm.
4. Đường UART/USB không chạy sát vùng anten.

### Tầng nguồn TPS63900
1. C2 (10 µF) + C3 (100 nF) sát VIN/GND; C4/C5 (2 × 22 µF) sát VOUT/GND – đây là hai vòng dòng xung quan trọng nhất.
2. L1 đặt sau cùng, ngay cạnh LX1/LX2; đường LX ngắn, rộng (0.4 mm) và **không** chạy dưới các tín hiệu analog.
3. EP (pad nhiệt) nối GND bằng 6 via 0.3 mm; chân SEL và GND (pin 8) nối thẳng vào EP.
4. Điện trở CFG1–3 sát chân, không có tụ, đường ngắn (< 10 pF).
5. R10 (0 Ω) đặt trên đường VBAT→VIN_BB để đo dòng (tháo ra, gắn ampe kế/PPK2).

### Đầu dò điện dung
1. Điện cực đồng **phủ solder mask** (pad chỉ ở lớp Cu, không mở mask) – không có đồng hở trong đất.
2. Không có mặt GND ở lớp đối diện ngay dưới SENSE (điện cực coplanar ở cả 2 lớp) → C ký sinh nhỏ, trường điện phần lớn đi vào đất.
3. Vùng đổ đồng GND dừng ở y = 122 mm (2 mm trên vạch đất); dải GND điện cực nối vào vùng đổ đồng ở đầu trên.
4. Đường PROBE_SENSE (D1, R15 → điện cực) ngắn nhất có thể, khe hở 0.3 mm, không chạy song song đường số.
5. Via khâu trong điện cực được **tented**; khi đặt hàng chọn *“Via covering: tented”* hoặc *plugged* để nước không thấm qua lỗ via.
6. **Hiệu chuẩn lại sau khi phủ coating** (độ dày lớp phủ làm thay đổi điện dung).

### SHT40
1. Rãnh phay cách nhiệt khỏi phần nguồn/MCU; không đổ đồng dưới tâm cảm biến (vùng cấm của footprint Sensirion).
2. Hướng cảm biến về phía lỗ thở/màng của vỏ; **không phủ conformal coating lên SHT40** (che màng PTFE bằng băng keo Kapton khi phủ).

### Nối đất và khâu via
- Mặt GND ở cả 2 lớp trong phần điện tử; ~185 via khâu (lưới 2.5 mm) + via fan-out cho mọi pad GND SMD.
- Đường tín hiệu chủ yếu ở lớp trên; lớp dưới giữ mặt GND gần như liền (xem ảnh B.Cu).
- Các đảo đồng cô lập được tự động loại bỏ (island removal) hoặc nối bằng via.

## 4.4 Quy trình tạo/tái tạo bo (tự động hoá)

Toàn bộ phần cứng được sinh bằng script Python (`hardware/tools/`), có thể chỉnh và chạy lại:

```bash
cd hardware/tools
python3 gen_footprints.py ..      # footprint/symbol riêng: module, giá pin, điện cực, WSON-10 via 0.3 mm
python3 gen_schematic.py ..       # 5 sheet schematic từ design.py
python3 check_netlist.py ../h2-soil-sensor.kicad_sch   # đối chiếu netlist ↔ design.py
export KICAD7_FOOTPRINT_DIR=/usr/share/kicad/footprints
python3 gen_pcb.py                # đặt linh kiện, đi dây tay phần analog/nguồn, router A* 2 lớp, đổ đồng, DRC
python3 make_fab.py               # Gerber+khoan zip, BOM/CPL JLCPCB, PDF lắp ráp, ảnh render
```

- `router.py` là bộ đi dây lưới 0.1 mm hai lớp (A*, chi phí via/lớp dưới/đổi hướng, rip-up & thử lại theo thứ tự net)
  với bản đồ chiếm chỗ theo từng bề rộng/khe hở, nên kết quả đạt DRC theo cấu trúc. Các net nhạy (điện cực, NTC, vòng công suất
  TPS63900) được đi dây tay trong `gen_pcb.py` và khoá lại.
- Nếu muốn tối ưu thẩm mỹ, mở `h2-soil-sensor.kicad_pcb` trong KiCad, xoá dây không khoá rồi đi lại bằng tay hoặc
  Freerouting – vị trí linh kiện và đường analog đã được tối ưu sẵn.

## 4.5 Lưu ý đặt hàng sản xuất

| Mục | Chọn |
|---|---|
| Độ dày | 1.6 mm (que đủ cứng; 2.0 mm nếu đất cứng) |
| Via | Tented (hoặc epoxy plugged) |
| Bề mặt | ENIG nếu môi trường ẩm (pad không bị oxy hoá trước khi hàn) |
| Mask | Bất kỳ; nên chọn mask dày đều (ảnh hưởng điện dung đầu dò) |
| SMT | Mặt trên; module ESP32-H2 hàn reflow 1 lần (MSL3) hoặc consign |
| Xuất xưởng | Kiểm tra: dòng ngủ ≈ 27–35 µA tại R10, oscillator TP6 ≈ 0.5–0.7 MHz, SOIL_ADC trong không khí ≈ 1.3–1.5 V |
