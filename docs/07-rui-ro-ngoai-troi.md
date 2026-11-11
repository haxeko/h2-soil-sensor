# 7. Rủi ro và lưu ý khi dùng ngoài trời

## 7.1 Nước, hơi ẩm và ăn mòn

| Rủi ro | Hậu quả | Biện pháp |
|---|---|---|
| Nước thấm vào hộp điện tử (mưa, tưới, ngưng tụ) | Rò dòng, chập, ăn mòn module/giá pin, tiêu hao pin | Hộp IP67 (gioăng O-ring), keo epoxy/silicone trung tính tại khe que đi ra, **lỗ thở ePTFE (Gore)** để cân bằng áp suất (tránh “bơm” hơi ẩm vào khi nhiệt độ ngày/đêm thay đổi), gói silica gel, conformal coating cả phần điện tử (trừ SHT40, nút, tiếp điểm pin, header) |
| Mép PCB lộ sợi thủy tinh trong đất | Nước thấm dọc sợi FR4 (wicking) → tách lớp, điện dung trôi dần | Phủ coating kỹ mép que và mũi nhọn (nhúng 2–3 lần); hoặc bọc co nhiệt có keo; chọn mask phủ mép nếu nhà sản xuất hỗ trợ |
| Lỗ via trong vùng điện cực | Nước theo lỗ via vào lõi | Via **tented/plugged**, coating phủ kín; có thể bỏ via khâu điện cực (chỉ dùng điện cực 1 lớp) nếu không đặt được via plugged |
| Lớp phủ trầy xước/rỗ khi cắm vào đất đá | Đồng tiếp xúc đất → số đo nhảy, ăn mòn điện hoá | Lớp phủ 50–100 µm, dùng dụng cụ tạo lỗ trước khi cắm, không cắm vào đất có sỏi cứng; kiểm tra định kỳ |
| Tiếp điểm pin bị oxy hoá | Mất nguồn chập chờn | Giá pin mạ vàng (BH-123A-B5BA003), mỡ tiếp điểm (dielectric grease) |
| Ngưng tụ trên SHT40 / độ ẩm 100 % kéo dài | SHT40 bị “creep”, đọc sai cao | Dùng bản AD1F (màng PTFE); có thể bật heater của SHT40 định kỳ (lệnh 0x39/0x2F) khi RH > 95 % lâu; đặt cảm biến ở vị trí thông thoáng có mái che |

## 7.2 Độ chính xác của đầu dò điện dung

| Yếu tố | Ảnh hưởng | Biện pháp |
|---|---|---|
| **Độ mặn / độ dẫn điện của đất** (phân bón, nước nhiễm mặn) | Ở 0.5–0.7 MHz phần dẫn điện vẫn làm tăng “điện dung biểu kiến” → báo ẩm cao hơn thực tế | Hiệu chuẩn trên chính loại đất; nếu đất mặn dùng kích thích LEDC 2–4 MHz (R14) để giảm ảnh hưởng; coi kết quả là **độ ẩm tương đối** chứ không phải VWC tuyệt đối |
| Nhiệt độ | Diode tách đỉnh −2 mV/°C, hằng số điện môi của nước giảm theo nhiệt độ, tần số 555 trôi | Bù nhiệt bằng NTC trên que (`SOIL_TEMP_COMP_UV_PER_C`); hiệu chỉnh hệ số theo thực nghiệm (đo que trong đất ở 2 nhiệt độ) |
| Khe hở không khí quanh que (cắm xiên, đất xốp, đất nứt khi khô) | Đọc khô hơn thực tế | Cắm thẳng đứng, nén nhẹ đất quanh que, tưới nhẹ sau khi cắm |
| Que không cắm tới vạch | Sai lệch theo độ sâu | Cắm đúng **SOIL LINE**; vạch nằm 4 mm trên mép trên điện cực |
| Lớp phủ thay đổi độ dày | Lệch điểm KHÔ/ƯỚT | **Hiệu chuẩn sau khi phủ**; mỗi que hiệu chuẩn riêng |
| Rễ cây, đá sát điện cực | Nhiễu cục bộ | Chọn vị trí đại diện vùng rễ, tránh sát gốc |
| Đông đá | Nước đá có hằng số điện môi ~3 → báo “khô”; đất đông nở có thể đẩy que lên | Bỏ qua số đo khi nhiệt độ đất < 0 °C (có sẵn nhiệt độ đất để lọc ở phía automation) |

## 7.3 Nhiệt độ, nắng và tia UV

- Hộp kín dưới nắng có thể nóng 60–70 °C: TPS63900 (≤ 85 °C môi trường), TLC555I (≤ 85 °C), pin CR123A (–40…+70 °C hoạt động; dung lượng và tự xả xấu đi khi nóng). Dùng hộp **màu sáng**, nhựa ASA/PC chống UV, có che nắng.
- SHT40 trong hộp hoặc gần hộp đen sẽ đo **nhiệt độ hộp, không phải không khí**: đặt ở đảo có rãnh phay, thông ra ngoài qua màng, có tấm che bức xạ (radiation shield) nếu cần số liệu khí tượng chuẩn.
- Lạnh (< 0 °C): dung lượng CR123A giảm và điện trở trong tăng → xung TX có thể làm sụt áp; C1 47 µF và ngưỡng khoá 2.05 V giúp tránh reset liên tục. Cân nhắc giảm TX power nếu vùng lạnh.
- Nhựa và gioăng lão hoá UV sau 2–3 năm: kiểm tra khi thay pin.

## 7.4 Kết nối vô tuyến (Thread)

- Anten ở độ cao vài cm trên mặt đất, cạnh cây và đất ẩm → suy hao lớn hơn trong nhà. Đảm bảo có **Thread router** (thiết bị
  cắm điện: bóng đèn/ổ cắm Matter-Thread, border router) trong vòng ~10–20 m, ưu tiên đường nhìn thẳng.
- Giữ anten hướng lên trên, không bọc vỏ kim loại, khoảng trống ≥ 15 mm; không đặt sát hàng rào kim loại/ống nước.
- Kiểm tra RSSI/LQI (log OpenThread, hoặc ứng dụng Home Assistant/OTBR) sau khi lắp; nếu biên dưới −85 dBm, tăng
  `CONFIG_THREAD_TX_POWER_DBM` lên +16…+20 dBm (đổi lại tuổi thọ pin giảm ~8 %).
- Thiết bị SED phụ thuộc parent: nếu router tắt, thiết bị tìm parent mới (tốn năng lượng); tránh đặt chỉ một router duy nhất.
- Mưa lớn/sương làm suy hao thêm vài dB – để dư biên liên kết.

## 7.5 Điện, an toàn và độ bền cơ khí

- **ESD / sét lan truyền**: que dài trong đất là “ăng-ten” thu xung cảm ứng; điện cực được cách điện hoàn toàn (mask + coating)
  nên không có đường dẫn trực tiếp. Không lắp ở vị trí cao trống trải; có thể thêm TVS điện dung thấp trên PROBE_SENSE nếu cần.
- Pin lithium: không dùng pin sạc 3.7 V/4.2 V lâu dài nếu không có kế hoạch (mạch chịu được tới 5.5 V nhưng ngưỡng % pin là
  cho Li-MnO<sub>2</sub>); không để pin trong hộp kín dưới nắng gắt quá lâu; thu gom pin hỏng đúng quy định.
- Chống ngược cực có sẵn (Q1) – vẫn đánh dấu rõ cực + trên hộp.
- Lực cắm: FR4 1.6 mm có thể gãy ở chỗ chuyển tiếp 26 → 20 mm; dùng ống/vỏ bọc phần chuyển tiếp, tạo lỗ trước bằng que sắt.
- Máy cắt cỏ, động vật gặm dây/hộp: đặt cọc báo hiệu, hộp chắc chắn.

## 7.6 Phần mềm và vận hành

| Rủi ro | Biện pháp |
|---|---|
| Firmware treo trong vùng xa | Task watchdog mặc định của ESP-IDF; OTA Requestor để cập nhật lỗi từ xa |
| Pin cạn không phát hiện kịp | Power Source: `BatChargeLevel` Warning (≤ 20 %) / Critical (≤ 5 %), `BatReplacementNeeded` (≤ 10 %) → tạo automation cảnh báo; Li-MnO<sub>2</sub> có đường xả phẳng nên % ở giữa chỉ là ước lượng |
| Hệ sinh thái chưa hỗ trợ Soil Sensor (Matter 1.5) | Endpoint 2 (Humidity Sensor) mô phỏng độ ẩm đất để hiển thị trong Apple Home/Google Home; đặt tên rõ “Độ ẩm đất” trong app |
| Chứng chỉ thử (test DAC) | Chỉ dùng cá nhân/thử nghiệm; sản phẩm thương mại cần chứng nhận CSA và DAC thật |
| Mất hiệu chuẩn | Hiệu chuẩn lưu trong NVS, giữ qua factory reset; ghi lại giá trị `dry_mv/wet_mv` (log) để nạp lại khi thay bo |

## 7.7 Danh sách kiểm tra trước khi lắp đặt

- [ ] Dòng ngủ đo tại R10: 30–40 µA (phía pin)
- [ ] TP6 có sóng vuông 0.5–0.7 MHz khi đo; SOIL_ADC (TP5) trong không khí 1.3–1.5 V, trong nước 0.7–0.9 V
- [ ] Đã phủ coating que (2 lớp), mép và mũi que; che SHT40/nút/header/tiếp điểm pin khi phủ
- [ ] Hiệu chuẩn KHÔ/ƯỚT sau khi phủ và lắp vỏ
- [ ] Hộp kín: gioăng, keo khe que, lỗ thở ePTFE, silica gel, cực + ghi rõ
- [ ] Commissioning thành công, thấy đủ endpoint, LQI/RSSI ổn định tại vị trí lắp
- [ ] Automation cảnh báo pin yếu và độ ẩm đất ngưỡng thấp đã được tạo
