# 7. Rủi ro và lưu ý khi dùng ngoài trời

## 7.1 Nước, hơi ẩm và ăn mòn

| Rủi ro | Hậu quả | Biện pháp |
|---|---|---|
| Nước thấm vào hộp điện tử (mưa, tưới, ngưng tụ) | Rò dòng, chập, ăn mòn module ESP/mối hàn, tiêu hao pin | Hộp **IP65 trở lên** có gioăng; cáp module vào qua **ốc siết cáp** (cable gland), tạo “vòng nhỏ giọt” trước khi vào hộp; **lỗ thở ePTFE (Gore)** để cân bằng áp suất (tránh “bơm” hơi ẩm vào khi nhiệt độ ngày/đêm thay đổi); gói silica gel; conformal coating cả bo (che nút, J4 và pad J1 khi phủ) |
| Cổng J4 (JST-PH) không kín nước | Ăn mòn chân cắm, đọc sai, mất kết nối | J4 phải nằm **trong hộp**; chỉ cáp đi ra ngoài |
| **Phần linh kiện của module độ ẩm đất** không được phủ (chỉ phần đầu dò được phủ) | Nước/sương làm hỏng mạch dao động và tách đỉnh trên module → số đo trôi hoặc chết module | Phủ conformal coating hoặc epoxy phần linh kiện **và mép cắt PCB** của module (2–3 lớp), rồi bọc co nhiệt có keo; đầu nối PH2.0 trên module cũng bọc kín sau khi cắm cáp |
| Mép PCB của module lộ sợi thủy tinh trong đất | Nước thấm dọc sợi FR4 (wicking) → tách lớp, điện dung trôi dần qua nhiều tháng | Phủ kỹ mép đầu dò; kiểm tra và hiệu chuẩn lại định kỳ (mỗi mùa); có module dự phòng |
| Pad nạp J1 là đồng trần (không kem hàn) | Oxy hoá pad, rò giữa các pad khi ẩm | Bề mặt ENIG; sau lần nạp cuối phủ coating hoặc dán băng Kapton lên J1; cập nhật về sau qua OTA |
| Tiếp điểm trong hộp pin bị oxy hoá | Mất nguồn chập chờn | Hộp pin tiếp điểm tốt, mỡ tiếp điểm (dielectric grease); phía bo dây pin đã hàn chết vào J3 nên không có tiếp điểm cắm |

## 7.2 Rủi ro riêng của module “Capacitive Soil Moisture Sensor v1.2”

| Rủi ro | Hậu quả | Biện pháp |
|---|---|---|
| **Tin bán hàng sai thông số**: “60 µA / 300 µW”, “chân DO”, “biến trở xanh”, “ngõ ra số 0 V / 5 V” là của cảm biến loại điện trở | Tính sai dòng/pin, tìm chân không tồn tại | Module điện dung v1.2 chỉ có 3 chân GND, VCC, AOUT; ngõ ra analog 0–3 V; dòng ~5 mA ([DFRobot SEN0193](https://wiki.dfrobot.com/sen0193/)) – các tính toán ở [05](05-nang-luong-va-tuoi-tho-pin.md) dùng 5 mA |
| **Chất lượng không đồng đều**: một số bản dùng NE555 (không chạy ở 3.3 V) hoặc lỗi lắp ráp | AOUT đứng yên, không đổi giữa khô/ướt, hoặc dưới 200 mV (firmware coi là “không có module”) | Đọc chữ trên IC 8 chân (**TLC555**); **thử từng module trong không khí và trong nước** (log `soil … mV`): chênh lệch nên ≥ ~1 V; loại module lỗi, mua dư |
| Cáp đi kèm là PH2.0 → Dupont cái, không vừa J4; cáp PH hai đầu có loại đảo chiều | Không cắm được; hoặc cấp nguồn ngược vào module → hỏng module | Dùng cáp PH2.0-3P hai đầu **nối thẳng** hoặc bấm lại đầu; đo bằng đồng hồ: GND → J4-1, VCC → J4-2, AOUT → J4-3 |
| Cắm đầu dò quá vạch giới hạn | Nước/đất chạm phần linh kiện → hỏng module; số đo phụ thuộc độ sâu | **Chỉ cắm tới vạch giới hạn** in trên module; dùng cọc/ống dẫn hướng để giữ độ sâu cố định |
| Mỗi module có điểm KHÔ/ƯỚT khác nhau | Sai số lớn nếu dùng giá trị mặc định (2500/1200 mV) | Hiệu chuẩn từng module (nhấn 2/3 lần); thay module = hiệu chuẩn lại |
| Module hỏng/rút ra | Firmware bỏ qua giá trị không hợp lệ và **không cập nhật** – controller giữ giá trị cũ | Tạo automation cảnh báo khi độ ẩm đất không đổi quá vài giờ |

## 7.3 Độ chính xác của phép đo điện dung

| Yếu tố | Ảnh hưởng | Biện pháp |
|---|---|---|
| **Độ mặn / độ dẫn điện của đất** (phân bón, nước nhiễm mặn) | Phần dẫn điện làm tăng “điện dung biểu kiến” → báo ẩm cao hơn thực tế | Hiệu chuẩn trên chính loại đất; coi kết quả là **độ ẩm tương đối** chứ không phải VWC tuyệt đối |
| Nhiệt độ | Mạch dao động/tách đỉnh của module trôi theo nhiệt, hằng số điện môi của nước giảm theo nhiệt độ; bo v3 không có cảm biến nhiệt để bù | Đặt module chỗ ít nắng chiếu trực tiếp; so sánh xu hướng theo cùng giờ trong ngày; hiệu chuẩn ở nhiệt độ gần điều kiện sử dụng |
| Khe hở không khí quanh đầu dò (cắm xiên, đất xốp, đất nứt khi khô) | Đọc khô hơn thực tế | Cắm thẳng đứng, nén nhẹ đất quanh đầu dò, tưới nhẹ sau khi cắm |
| Rễ cây, đá sát đầu dò | Nhiễu cục bộ | Chọn vị trí đại diện vùng rễ, tránh sát gốc |
| Nhiễu trên cáp analog | Số đo dao động | R12/C13 lọc RC, 64 mẫu trimmed mean; cáp ngắn, không đi song song dây điện lưới |
| Đông đá | Nước đá có hằng số điện môi ~3 → báo “khô”; đất đông nở có thể đẩy đầu dò lên | Bỏ qua số đo khi trời dưới 0 °C (dùng nhiệt độ từ cảm biến/thời tiết khác trong automation) |

## 7.4 Nhiệt độ, nắng và tia UV

- Hộp kín dưới nắng có thể nóng 60–70 °C: TPS63900 (≤ 85 °C môi trường), pin CR123A (–40…+70 °C hoạt động; dung lượng và tự xả
  xấu đi khi nóng). Dùng hộp **màu sáng**, nhựa ASA/PC chống UV, có che nắng.
- Lạnh (< 0 °C): dung lượng CR123A giảm và điện trở trong tăng (dây hộp pin làm tăng thêm) → xung TX có thể làm sụt áp; C1 47 µF
  và ngưỡng khoá 2.05 V giúp tránh reset liên tục. Cân nhắc giảm TX power nếu vùng lạnh.
- Nhựa, gioăng, vỏ cáp lão hoá UV sau 2–3 năm: kiểm tra khi thay pin; dùng cáp có vỏ chống UV hoặc luồn ống.

## 7.5 Kết nối vô tuyến (Thread)

- Anten ở độ cao vài cm trên mặt đất, cạnh cây và đất ẩm → suy hao lớn hơn trong nhà. Đảm bảo có **Thread router** (thiết bị
  cắm điện: bóng đèn/ổ cắm Matter-Thread, border router) trong vòng ~10–20 m, ưu tiên đường nhìn thẳng. Nên gắn hộp lên cọc
  cao hơn mặt đất, nối xuống module bằng cáp.
- Giữ anten hướng lên trên, không bọc vỏ kim loại, khoảng trống ≥ 15 mm; **không để cáp module, hộp pin hay vật kim loại vòng
  qua phía anten**; không đặt sát hàng rào kim loại/ống nước.
- Kiểm tra RSSI/LQI (log OpenThread, hoặc ứng dụng Home Assistant/OTBR) sau khi lắp; nếu biên dưới −85 dBm, tăng
  `CONFIG_THREAD_TX_POWER_DBM` lên +16…+20 dBm (đổi lại tiêu thụ tăng ~7 %).
- Thiết bị SED phụ thuộc parent: nếu router tắt, thiết bị tìm parent mới (tốn năng lượng); tránh đặt chỉ một router duy nhất.
- Mưa lớn/sương làm suy hao thêm vài dB – để dư biên liên kết.

## 7.6 Điện, an toàn và độ bền cơ khí

- **ESD / xung cảm ứng trên cáp**: cáp module dài là “ăng-ten” thu xung (người chạm, sét lan truyền). Đường AOUT có **D3**
  (TVS 3.3 V) kẹp về GND và R12 1 kΩ hạn dòng vào ADC; VCC/GND của cáp nối thẳng vào rail VSENS/GND có tụ C7/C14. Không lắp ở
  vị trí cao trống trải.
- Cắm/rút module khi đang chạy: VSENS chỉ có điện ~1.5 s mỗi lần đo nên thường an toàn, nhưng nên tháo pin khi thay module.
- Pin lithium: không dùng pin sạc 3.7 V/4.2 V lâu dài nếu không có kế hoạch (mạch chịu được tới 5.5 V nhưng ngưỡng % pin là
  cho Li-MnO<sub>2</sub>); không để pin trong hộp kín dưới nắng gắt quá lâu; thu gom pin hỏng đúng quy định.
- Chống ngược cực có sẵn (Q1) – vẫn đánh dấu rõ cực + trên hộp pin và trên dây.
- Cơ khí: bo không có lỗ vít → dán chắc bằng băng keo xốp 2 mặt (mặt dưới), kẹp hoặc keo nến để bo không xoay/rung; cố định
  hộp pin và giảm lực kéo cho cáp module và dây pin (ốc siết cáp, dây rút, keo) để không giật J4 hay mối hàn J3. Module đất
  không dùng để “đóng” vào đất cứng – tạo lỗ trước bằng que sắt nhỏ.
- Máy cắt cỏ, động vật gặm dây/hộp: đặt cọc báo hiệu, luồn cáp trong ống bảo vệ.

## 7.7 Phần mềm và vận hành

| Rủi ro | Biện pháp |
|---|---|
| Firmware treo trong vùng xa | Task watchdog mặc định của ESP-IDF; OTA Requestor để cập nhật lỗi từ xa |
| Pin cạn không phát hiện kịp | Power Source: `BatChargeLevel` Warning (≤ 20 %) / Critical (≤ 5 %), `BatReplacementNeeded` (≤ 10 %) → tạo automation cảnh báo; Li-MnO<sub>2</sub> có đường xả phẳng nên % ở giữa chỉ là ước lượng |
| Hệ sinh thái chưa hỗ trợ Soil Sensor (Matter 1.5) | Endpoint 2 (Humidity Sensor) mô phỏng độ ẩm đất để hiển thị trong Apple Home/Google Home; đặt tên rõ “Độ ẩm đất” trong app |
| Chứng chỉ thử (test DAC) | Chỉ dùng cá nhân/thử nghiệm; sản phẩm thương mại cần chứng nhận CSA và DAC thật |
| Mất hiệu chuẩn | Hiệu chuẩn lưu trong NVS, giữ qua factory reset; ghi lại giá trị `dry_mv/wet_mv` (log) để nạp lại khi thay bo – nhưng **thay module thì phải hiệu chuẩn lại** |

## 7.8 Danh sách kiểm tra trước khi lắp đặt

- [ ] Dòng nền đo tại R10: ~30–35 µA (phía pin); VSENS (J4-2) = 0 V giữa các lần đo
- [ ] Module đúng loại điện dung v1.2 (IC TLC555), đã thử trong không khí và trong nước (chênh lệch ≥ ~1 V); phần linh kiện + mép cắt đã bịt kín
- [ ] Cáp PH2.0-3P đã đo đúng chân (GND → J4-1, VCC → J4-2, AOUT → J4-3); dây pin hàn đúng cực (“+” pad vuông)
- [ ] Hiệu chuẩn KHÔ/ƯỚT cho đúng module sẽ lắp, sau khi đã bịt kín module
- [ ] Hộp kín: gioăng, ốc siết cáp, lỗ thở ePTFE, silica gel; bo dán chắc; pad J1 đã được phủ/che sau lần nạp cuối
- [ ] Commissioning thành công, thấy EP1 (Soil Sensor) và EP2 (bản sao độ ẩm), LQI/RSSI ổn định tại vị trí lắp
- [ ] Đầu dò cắm thẳng, tới vạch giới hạn; automation cảnh báo pin yếu, độ ẩm đất thấp và “không cập nhật” đã được tạo
