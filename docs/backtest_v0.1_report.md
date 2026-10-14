# Backtest bộ quy tắc SMC XAUUSD v0.1

Ngày chạy: 14/10/2026 · Dữ liệu: FX:XAUUSD qua TradingView MCP · Mã: `backtest/smc_v01.py` · Quy tắc: `docs/SMC_XAUUSD_rules_v0.1.md`

> ⚠️ **Mẫu quá nhỏ để kết luận.** 3 tháng chỉ cho ra 5–6 lệnh. Đây là kết quả kiểm tra logic, **không phải** bằng chứng chiến lược thắng hay thua.

## 1. Dữ liệu và giới hạn
| Khung | Có từ | Ghi chú |
|---|---|---|
| M5 | 14/09/2026 | Feed TradingView chỉ cho ~1 tháng M5 (đã thử cả OANDA) |
| M15 | 14/07/2026 | Đủ 3 tháng |
| H1 / H4 / D1 | 05/2026 / 2024 / 2010 | Dùng cho mốc thoát và bối cảnh |
| Lịch tin | 14/07 → 14/10 | 77 tin Mỹ mức "high" |

Vì thiếu M5, chạy 2 chế độ:
- **Exact (1 tháng, 14/09 → 14/10):** đúng quy tắc, M15 setup + M5 entry/SL/thoát.
- **Proxy (3 tháng, 17/07 → 14/10):** dùng M15 thay cho mọi bước M5. **Đây là xấp xỉ, không phải quy tắc thật.** Trên cùng tháng chồng lấn, proxy chỉ ra 2 lệnh so với 6 lệnh của exact, nên proxy lọc khắt khe hơn và không đại diện chính xác.

Chi phí giả định: 0,40 $/oz cho mỗi lệnh (spread + phí + trượt). Vào lệnh bằng giá mở của nến kế tiếp. SL khớp trong nến; nếu một nến chạm cả SL và mục tiêu, tính SL trước (thận trọng).

## 2. Kết quả
### Exact (M5, 1 tháng)
| | |
|---|---|
| Lệnh đã đóng | **5** (thêm 1 lệnh SELL còn mở) |
| Thắng / thua | **0 / 5** |
| Tổng | **−5,30R** |
| Lệnh đang mở | SELL 14/10 13:30 tại 4152,83, SL 4164,13, đang +0,38R |

| Hướng | Vào lệnh | Entry | SL | Thoát | R | Lý do | Vùng | D1 |
|---|---|---|---|---|---|---|---|---|
| BUY | 14/09 10:10 | 4335,76 | 4326,17 | 14/09 11:35 | −1,04 | SL | OB | ngược |
| BUY | 25/09 11:30 | 4271,17 | 4266,94 | 25/09 11:55 | −1,09 | SL | OB | ngược |
| SELL | 02/10 18:30 | 4180,56 | 4189,20 | 02/10 19:30 | −1,05 | SL | OB | thuận |
| SELL | 05/10 13:35 | 4149,99 | 4156,81 | 05/10 14:05 | −1,06 | SL | FVG | thuận |
| SELL | 13/10 09:35 | 4167,86 | 4174,79 | 13/10 09:35 | −1,06 | SL | OB | thuận |
| SELL | 14/10 13:30 | 4152,83 | 4164,13 | (đang mở) | +0,38 | — | FVG | thuận |

### Proxy (M15, 3 tháng)
| | |
|---|---|
| Lệnh | **5** |
| Thắng / hòa / thua | 1 / 1 / 3 (tỷ lệ thắng 20%) |
| Tổng | **+5,32R** (cả lợi nhuận đến từ **1 lệnh +8,45R**) |
| Profit factor / Max DD | 2,7 / 2,1R |
| Chi phí 0 → 0,80 $ | +5,49R → +5,13R (ít ảnh hưởng) |

| Hướng | Vào lệnh | Entry | SL | Thoát | R | Lý do | Vùng | D1 |
|---|---|---|---|---|---|---|---|---|
| SELL | 21/07 05:45 | 4003,85 | 4020,53 | 21/07 07:30 | −1,02 | SL | FVG | thuận |
| BUY | 14/08 14:00 | 4335,61 | 4326,42 | 18/08 01:00 | **+8,45** | Chạm mốc + CHoCH | FVG | ngược |
| SELL | 10/09 00:45 | 4413,63 | 4422,68 | 10/09 08:00 | 0,00 | Hòa vốn | OB | thuận |
| BUY | 25/09 11:45 | 4271,96 | 4266,33 | 25/09 11:45 | −1,07 | SL | OB | ngược |
| SELL | 02/10 18:30 | 4180,56 | 4189,92 | 02/10 19:30 | −1,04 | SL | OB | thuận |

### Phễu lọc tín hiệu (proxy 3 tháng)
173 CHoCH M15 → 57 có displacement → 51 có FVG → **5 lệnh khớp**.
- 22 setup bị hủy do CHoCH M15 ngược chiều.
- 14 setup bị hủy do vỡ OB.
- 6 setup bị loại vì R:R < 1,5.
- 3 setup bị thay bởi CHoCH mới.

## 3. Nhận xét về bộ quy tắc
1. **Tần suất: proxy đếm thiếu khoảng 3 lần.** Cùng tháng 14/09 → 14/10 có 16 setup; chạy đúng quy tắc (M5) khớp 6 lệnh, proxy (M15) chỉ khớp 2. Lý do: nến mốc và nến xác nhận trên M15 khó đạt hơn nhiều so với M5. Tần suất thật ước khoảng **5–6 lệnh/tháng**, không phải 2. Vẫn cần 30–50 lệnh mới đánh giá được. Chi tiết từng setup: `docs/backtest_v0.1_setups.md`.
2. **Lệnh vào qua OB dự phòng thua nhiều.** Ở chế độ exact, 4/6 lệnh vào qua OB sau khi FVG thất bại, và cả 4 đều dính SL. FVG thủng thường là dấu hiệu mất đà. Nên thử bỏ OB dự phòng, hoặc yêu cầu CHoCH M5 trước khi vào ở OB. Mẫu còn nhỏ, chưa kết luận được.
3. **FVG quá nhỏ.** Có FVG chỉ rộng 0,48 $ (05/10), nên ngưỡng 30% gần như vô nghĩa. Đề xuất độ rộng tối thiểu, ví dụ ≥ 0,3×ATR(14) M15.
4. **SL quá sát.** SL = đỉnh/đáy nến mốc + 0,2×ATR M5 (khoảng 1 $). Có 2 lệnh dính SL ngay trong nến vào lệnh. Có thể thử đặt SL ngoài mép xa của vùng FVG/OB, hoặc tăng buffer.
5. **Entry thường xa vùng.** Đợi nến M5 đóng vượt nến mốc khiến entry có thể cách vùng 5–10 $ (ví dụ 14/10: FVG 4162–4164, nhưng entry ở 4152). Hệ quả là R:R thực tế xấu đi, vì SL vẫn nằm ở vùng.
6. **Quy tắc thoát hoạt động tốt khi có xu hướng.** Lệnh +8,45R giữ được 3 ngày nhờ chỉ thoát khi đã chạm mốc H1 và có CHoCH M5/M15.
7. Lệnh thuận/ngược D1 có kết quả lẫn lộn, mẫu quá nhỏ để so sánh.

## 4. Những chỗ quy tắc chưa rõ, mình đã tự chọn cách hiểu
| Điểm | Cách đã dùng |
|---|---|
| Ranh giới "nhịp displacement" | Từ nến OB đến nến CHoCH; nến thứ 3 của FVG có thể là CHoCH+1 |
| Định nghĩa FVG M15 | FVG 3 nến cơ bản, không có độ rộng tối thiểu |
| FVG/swing/OB H1-H4 làm mốc | Swing length 50 theo LuxAlgo; FVG theo LuxAlgo auto-threshold; vô hiệu khi nến H1/H4 đóng vượt |
| R:R | (khoảng cách tới mốc gần nhất − chi phí) ÷ (R + chi phí) ≥ 1,5 |
| Không có mốc H1/H4 nào phía trước | Bỏ lệnh |
| R:R không đạt / tín hiệu khi đang có lệnh | Setup bị tiêu (không vào lại) / bỏ nến mốc, chờ nến mốc mới |
| Sau cửa sổ tin | Bỏ nến mốc, tìm nến mốc mới sau khi cửa sổ kết thúc |
| Mốc đã chạm rồi bị vô hiệu | Trạng thái "đã chạm" giữ đến khi thoát |
| CHoCH thoát M5 | Chỉ tính CHoCH (đổi xu hướng internal), không tính BOS |
| FVG thất bại → OB | Nến mốc mới tìm từ nến M5 sau nến làm thủng FVG |
| H4 / D1 | Lấy theo nến H4/D1 của FX (mở 22:00 UTC) |

## 5. Bước tiếp theo đề xuất
1. **Forward test trên tài khoản demo** từ hôm nay, ghi nhật ký theo mục 9 của quy tắc. Cách này nhanh nhất để có thêm mẫu.
2. Kéo thêm M5 từ broker khác (MT5 export) để backtest exact 6–12 tháng.
3. Thử các biến thể: bỏ OB dự phòng · FVG tối thiểu 0,3×ATR · SL ngoài vùng. Chỉ chọn biến thể sau khi đã có mẫu ngoài (out-of-sample) để tránh tối ưu quá mức.

*Tài liệu nghiên cứu, không phải lời khuyên đầu tư.*
