# 7. Rủi ro và lưu ý khi dùng ngoài trời

## 7.1 Nước, hơi ẩm và ăn mòn

| Rủi ro | Hậu quả | Biện pháp |
|---|---|---|
| Nước thấm vào hộp điện tử (mưa, tưới, ngưng tụ) | Rò dòng, chập, ăn mòn module ESP/tiếp điểm pin, tiêu hao pin | Hộp **IP65 trở lên** có gioăng; mọi cáp vào qua **ốc siết cáp** (cable gland), cáp đi xuống tạo “vòng nhỏ giọt” trước khi vào hộp; **lỗ thở ePTFE (Gore)** để cân bằng áp suất (tránh “bơm” hơi ẩm vào khi nhiệt độ ngày/đêm thay đổi); gói silica gel; conformal coating cả bo (trừ nút, header, cổng JST, tiếp điểm pin) |
| Cổng JST-PH / header 2.54 mm không kín nước | Ăn mòn chân cắm, đọc sai, mất kết nối | Mọi cổng phải nằm **trong hộp**; chỉ cáp đi ra ngoài. Không để đầu nối cáp nằm ngoài trời |
| **Phần linh kiện của module độ ẩm đất** không được phủ (chỉ phần đầu dò được phủ) | Nước/sương làm hỏng mạch dao động và tách đỉnh trên module → số đo trôi hoặc chết module | Phủ conformal coating hoặc epoxy phần linh kiện **và mép cắt PCB** của module (2–3 lớp), rồi bọc co nhiệt có keo; đầu nối PH2.0 trên module cũng bọc kín sau khi cắm cáp |
| Mép PCB của module lộ sợi thủy tinh trong đất | Nước thấm dọc sợi FR4 (wicking) → tách lớp, điện dung trôi dần qua nhiều tháng | Phủ kỹ mép đầu dò; kiểm tra và hiệu chuẩn lại định kỳ (mỗi mùa); có module dự phòng |
| Tiếp điểm hộp pin bị oxy hoá | Mất nguồn chập chờn | Hộp pin tiếp điểm chống oxy hoá, mỡ tiếp điểm (dielectric grease); hoặc hàn dây pin thẳng vào J3 |
| Ngưng tụ trên cảm biến nhiệt/ẩm không khí / độ ẩm 100 % kéo dài | Cảm biến bị “creep”, đọc sai cao | Đặt module sau màng/lỗ thở hoặc trong tấm che bức xạ thông thoáng; **không phủ coating lên lỗ cảm biến**; ưu tiên module SHT4x/SHT3x có màng bảo vệ nếu có |
| Đầu dò NTC bị thấm nước (theo dây vào ống thép) | Nhiệt độ đất sai hoặc hở mạch (firmware bỏ giá trị) | Dùng đầu dò vỏ thép không gỉ đúc kín; đoạn dây vào hộp qua ốc siết cáp |

## 7.2 Rủi ro riêng của module mua sẵn

| Rủi ro | Hậu quả | Biện pháp |
|---|---|---|
| **Chất lượng module đất không đồng đều**: một số bản rẻ dùng NE555 (không chạy ở 3.3 V) hoặc lỗi lắp ráp | AOUT đứng yên, không đổi giữa khô/ướt, hoặc nằm dưới 200 mV (firmware coi là “không có module”) | Chọn module dùng **TLC555**; **thử từng module trong không khí và trong nước** trước khi lắp đặt (log hiển thị `soil … mV`), loại module có chênh lệch nhỏ; mua dư |
| Thứ tự chân không thống nhất (cáp PH 2.0 thẳng/đảo; module I²C khác hãng; hộp pin có JST) | Cấp nguồn ngược vào module → hỏng module; I²C không trả lời | Đo cáp bằng đồng hồ trước khi cắm: J4 = GND/VCC/AOUT, J6 = VCC/GND/SCL/SDA, J2 chân 1 = “+”. Pin ngược được Q1 chặn (không hỏng, nhưng thiết bị không chạy) |
| Cắm đầu dò quá vạch giới hạn | Nước/đất chạm phần linh kiện → hỏng module; số đo phụ thuộc độ sâu | **Chỉ cắm tới vạch giới hạn** in trên module; dùng cọc/ống dẫn hướng để giữ độ sâu cố định |
| Mỗi module có điểm KHÔ/ƯỚT khác nhau | Sai số lớn nếu dùng giá trị mặc định (2500/1200 mV) | Hiệu chuẩn từng module (nhấn 2/3 lần); thay module = hiệu chuẩn lại |
| Module I²C có LED nguồn / LDO dòng tĩnh lớn | Tốn thêm dòng trong mỗi cửa sổ đo | Gỡ LED; chọn module chạy trực tiếp 3.3 V |
| Dây I²C dài | Bus lỗi do điện dung dây, nhiễu | Đặt module I²C gần bo (trong hộp có lỗ thở hoặc sát hộp), dây ngắn; firmware chạy 100 kHz, kiểm tra CRC và bỏ giá trị lỗi |
| Thay/thêm/bớt module sau khi đã ghép nối | Endpoint chỉ được tạo cho cảm biến có mặt lúc khởi động → thiếu ô hoặc ô không cập nhật | Cắm module trước khi lắp pin; khi đổi bộ cảm biến: khởi động lại, xoá thiết bị khỏi app và ghép lại |

## 7.3 Độ chính xác của phép đo điện dung

| Yếu tố | Ảnh hưởng | Biện pháp |
|---|---|---|
| **Độ mặn / độ dẫn điện của đất** (phân bón, nước nhiễm mặn) | Phần dẫn điện làm tăng “điện dung biểu kiến” → báo ẩm cao hơn thực tế | Hiệu chuẩn trên chính loại đất; coi kết quả là **độ ẩm tương đối** chứ không phải VWC tuyệt đối |
| Nhiệt độ | Mạch dao động/tách đỉnh của module trôi theo nhiệt, hằng số điện môi của nước giảm theo nhiệt độ | Bù nhiệt tuỳ chọn bằng NTC (`SOIL_TEMP_COMP_UV_PER_C`, mặc định tắt): đo hệ số k của module trong chậu đất ở 2 nhiệt độ rồi mới bật |
| Khe hở không khí quanh đầu dò (cắm xiên, đất xốp, đất nứt khi khô) | Đọc khô hơn thực tế | Cắm thẳng đứng, nén nhẹ đất quanh đầu dò, tưới nhẹ sau khi cắm |
| Rễ cây, đá sát đầu dò | Nhiễu cục bộ | Chọn vị trí đại diện vùng rễ, tránh sát gốc |
| Nhiễu trên cáp analog | Số đo dao động | R12/C13 lọc RC, 64 mẫu trimmed mean; cáp ngắn, không đi song song dây điện lưới |
| Đông đá | Nước đá có hằng số điện môi ~3 → báo “khô”; đất đông nở có thể đẩy đầu dò lên | Bỏ qua số đo khi nhiệt độ đất < 0 °C (dùng NTC để lọc ở phía automation) |

## 7.4 Nhiệt độ, nắng và tia UV

- Hộp kín dưới nắng có thể nóng 60–70 °C: TPS63900 (≤ 85 °C môi trường), pin CR123A (–40…+70 °C hoạt động; dung lượng và tự xả
  xấu đi khi nóng). Dùng hộp **màu sáng**, nhựa ASA/PC chống UV, có che nắng.
- Module nhiệt/ẩm không khí trong hộp sẽ đo **nhiệt độ hộp, không phải không khí**: đặt ngoài hộp trong tấm che bức xạ
  (radiation shield) nếu cần số liệu khí tượng chuẩn.
- Lạnh (< 0 °C): dung lượng CR123A giảm và điện trở trong tăng (dây pin dài làm tăng thêm) → xung TX có thể làm sụt áp; C1 47 µF
  và ngưỡng khoá 2.05 V giúp tránh reset liên tục. Cân nhắc giảm TX power nếu vùng lạnh.
- Nhựa, gioăng, vỏ cáp lão hoá UV sau 2–3 năm: kiểm tra khi thay pin; dùng cáp có vỏ chống UV hoặc luồn ống.

## 7.5 Kết nối vô tuyến (Thread)

- Anten ở độ cao vài cm trên mặt đất, cạnh cây và đất ẩm → suy hao lớn hơn trong nhà. Đảm bảo có **Thread router** (thiết bị
  cắm điện: bóng đèn/ổ cắm Matter-Thread, border router) trong vòng ~10–20 m, ưu tiên đường nhìn thẳng. Nên gắn hộp lên cọc
  cao hơn mặt đất, nối xuống đầu dò bằng cáp.
- Giữ anten hướng lên trên, không bọc vỏ kim loại, khoảng trống ≥ 15 mm; **không để cáp cảm biến, hộp pin hay vít kim loại vòng
  qua phía anten**; không đặt sát hàng rào kim loại/ống nước.
- Kiểm tra RSSI/LQI (log OpenThread, hoặc ứng dụng Home Assistant/OTBR) sau khi lắp; nếu biên dưới −85 dBm, tăng
  `CONFIG_THREAD_TX_POWER_DBM` lên +16…+20 dBm (đổi lại tuổi thọ pin giảm ~6 %).
- Thiết bị SED phụ thuộc parent: nếu router tắt, thiết bị tìm parent mới (tốn năng lượng); tránh đặt chỉ một router duy nhất.
- Mưa lớn/sương làm suy hao thêm vài dB – để dư biên liên kết.

## 7.6 Điện, an toàn và độ bền cơ khí

- **ESD / xung cảm ứng trên cáp**: cáp module dài là “ăng-ten” thu xung (người chạm, sét lan truyền). Bốn đường đi ra khỏi hộp
  (AOUT, NTC, SDA, SCL) có **U3 SRV05-4** kẹp về VSENS/GND, AOUT có thêm R12 1 kΩ hạn dòng vào ADC. Không lắp ở vị trí cao trống
  trải; nối đất vỏ kim loại (nếu có) không được chạm mạch.
- Cắm/rút module khi đang chạy: VSENS chỉ có điện ~1.5 s mỗi lần đo nên thường an toàn, nhưng nên tháo pin khi thay module.
- Pin lithium: không dùng pin sạc 3.7 V/4.2 V lâu dài nếu không có kế hoạch (mạch chịu được tới 5.5 V nhưng ngưỡng % pin là
  cho Li-MnO<sub>2</sub>); không để pin trong hộp kín dưới nắng gắt quá lâu; thu gom pin hỏng đúng quy định.
- Chống ngược cực có sẵn (Q1) – vẫn đánh dấu rõ cực + trên hộp pin và trên dây.
- Cơ khí: bắt bo bằng 2 vít M3 vào trụ trong hộp; cố định hộp pin (không để treo trên dây); giảm lực kéo cho cáp bằng ốc siết cáp
  hoặc dây rút; module đất không dùng để “đóng” vào đất cứng – tạo lỗ trước bằng que sắt nhỏ.
- Máy cắt cỏ, động vật gặm dây/hộp: đặt cọc báo hiệu, luồn cáp trong ống bảo vệ.

## 7.7 Phần mềm và vận hành

| Rủi ro | Biện pháp |
|---|---|
| Firmware treo trong vùng xa | Task watchdog mặc định của ESP-IDF; OTA Requestor để cập nhật lỗi từ xa |
| Pin cạn không phát hiện kịp | Power Source: `BatChargeLevel` Warning (≤ 20 %) / Critical (≤ 5 %), `BatReplacementNeeded` (≤ 10 %) → tạo automation cảnh báo; Li-MnO<sub>2</sub> có đường xả phẳng nên % ở giữa chỉ là ước lượng |
| Module hỏng/rút ra mà không biết | Firmware bỏ qua giá trị không hợp lệ và **không cập nhật** – controller vẫn hiển thị giá trị cũ → tạo automation cảnh báo khi độ ẩm đất không đổi quá vài giờ |
| Hệ sinh thái chưa hỗ trợ Soil Sensor (Matter 1.5) | Endpoint 2 (Humidity Sensor) mô phỏng độ ẩm đất để hiển thị trong Apple Home/Google Home; đặt tên rõ “Độ ẩm đất” trong app |
| Chứng chỉ thử (test DAC) | Chỉ dùng cá nhân/thử nghiệm; sản phẩm thương mại cần chứng nhận CSA và DAC thật |
| Mất hiệu chuẩn | Hiệu chuẩn lưu trong NVS, giữ qua factory reset; ghi lại giá trị `dry_mv/wet_mv` (log) để nạp lại khi thay bo – nhưng **thay module thì phải hiệu chuẩn lại** |

## 7.8 Danh sách kiểm tra trước khi lắp đặt

- [ ] Dòng nền đo tại R10: ~30–35 µA (phía pin); TP4 (VSENS) = 0 V giữa các lần đo
- [ ] Từng module đất đã thử trong không khí và trong nước (chênh lệch rõ ràng), phần linh kiện + mép cắt đã bịt kín
- [ ] Cáp đã đo đúng thứ tự chân (J4, J6, J7, J2/J3); module được cắm **trước** khi lắp pin
- [ ] Hiệu chuẩn KHÔ/ƯỚT cho đúng module sẽ lắp, sau khi đã bịt kín module
- [ ] Hộp kín: gioăng, ốc siết cáp, lỗ thở ePTFE, silica gel; cổng JST ở trong hộp; cực + ghi rõ
- [ ] Commissioning thành công, thấy đủ endpoint (soil, nhiệt độ đất nếu có NTC, không khí nếu có module I²C), LQI/RSSI ổn định
- [ ] Đầu dò cắm thẳng, tới vạch giới hạn; automation cảnh báo pin yếu, độ ẩm đất thấp và “không cập nhật” đã được tạo
