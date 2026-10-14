# FX:XAUUSD — Bộ quy tắc SMC v0.1
Ngày ghi nhận: 14/10/2026. Trạng thái: bản quy tắc nghiên cứu đã tổng hợp từ quyết định trong cuộc trò chuyện; chưa backtest, chưa xác nhận lợi nhuận, chưa tự động đặt lệnh.

## 1. Phạm vi và nguyên tắc
- Sản phẩm nghiên cứu: FX:XAUUSD. Nguồn giá broker thực thi chưa xác định.
- SMC đa khung; giao dịch theo nhịp hiện tại, kể cả nhịp retracement ngược xu hướng chính D1.
- D1: bối cảnh xu hướng chính và premium/discount theo range LuxAlgo.
- H4/H1: bối cảnh nhịp hiện tại, POI và mốc đối diện.
- M15: internal CHoCH xác nhận chuyển hướng cục bộ; không bắt buộc thêm BOS trước entry.
- M5: xác nhận entry bằng nến; internal CHoCH dùng cho thoát tại mốc HTF.
- Giao dịch mọi phiên trong giờ thị trường mở; được giữ qua đêm và cuối tuần. Lựa chọn này thay thế quy tắc không qua đêm ban đầu.
- Tối đa một vị thế vàng cùng lúc; không thêm lệnh tại OB khi đã có lệnh FVG.
- D1 thuận hướng và giao dịch nhịp hồi được ghi riêng để so sánh.

## 2. Nguồn cấu trúc và cài đặt LuxAlgo
Đã duyệt: internal cho CHoCH M15/M5; swing cho bối cảnh D1/H4/H1 và swing HTF.
Ảnh cài đặt đã đọc:
- Mode Historical, Style Colored; Color Candles tắt.
- Internal Structure bật, bullish/bearish All; Confluence Filter tắt.
- Swing Structure bật, bullish/bearish All; Show Swings Points tắt, ô giá trị 50; Strong/Weak High/Low bật.
- Internal OB bật, số hiển thị 5; Swing OB tắt, ô số hiển thị 6.
- OB filter ATR; OB mitigation High/Low.
- EQH/EQL bật; bars confirmation 3, threshold 0.1.
- FVG tắt; Auto Threshold bật; timeframe Chart; Extend FVG 1.
- Premium/Discount tắt; Daily/Weekly/Monthly highs/lows tắt.
Các số 5 và 6 là số OB hiển thị, không phải swing length.
Đề xuất chỉnh chart chưa được xác nhận đã thực hiện: bật FVG, premium/discount; OB mitigation Close; muốn thấy swing OB HTF cần bật mục này.
Hiển thị chart không tự cung cấp dữ liệu indicator cho MCP. Phải kiểm tra đúng phiên bản mã nguồn LuxAlgo và tái tạo phần logic cần dùng; chưa khẳng định Pine mới trùng indicator.

## 3. CHoCH M15 và displacement
- CHoCH xác nhận bằng nến M15 đóng phá cấu trúc internal, không chỉ râu.
- Nến phá có thân abs(close-open) >= ATR(14) M15 của nến trước.
- Buy: close nằm trong 25% trên cùng của high-low; Sell: trong 25% dưới cùng.
- Nhịp đó tạo FVG; chỉ sử dụng sau khi đủ ba nến xác nhận.
- Các ngưỡng trên là thông số kiểm thử do người dùng duyệt, không phải chuẩn SMC duy nhất.
- Chọn FVG hình thành sớm nhất thuộc nhịp displacement, còn hiệu lực khi bắt đầu chờ retest.
- Không chuyển sang FVG khác khi FVG đã chọn thất bại; chuyển OB dự phòng.
- OB dự phòng: internal OB M15 theo logic LuxAlgo gắn với nhịp CHoCH, dùng biên High-Low của nến OB; cố định sau khi được xác nhận.
- Không có OB hợp lệ hoặc OB đã bị vô hiệu: hủy setup.
- Ranh giới của “nhịp displacement” và cách gắn duy nhất OB/FVG với sự kiện CHoCH cần đối chiếu mã nguồn/chart khi triển khai; chưa tự thêm giới hạn nến.

## 4. Retest và entry
Gọi biên vùng là L (dưới), U (trên), độ rộng W = U-L.
### Buy
1. Sau setup tăng M15, chờ hồi về FVG đã chọn.
2. Ngưỡng xuyên 30% từ trên xuống: U-0.3W. Nến phải thực sự giao với vùng.
3. Nến M5 đầu tiên đạt ngưỡng là nến mốc; ghi high của nến này và giữ cố định.
4. Từ nến M5 tiếp theo: close > high nến mốc thì xác nhận Buy.
5. Chỉ râu vượt không đủ. Không cập nhật nến mốc sang các nến chờ.
6. Nếu trước entry M5 close < L: FVG thất bại, bỏ mốc cũ và chuyển OB; áp dụng lại 30% với nến mốc mới.
### Sell
1. Sau setup giảm M15, chờ hồi lên FVG.
2. Ngưỡng xuyên 30% từ dưới lên: L+0.3W.
3. Nến mốc là M5 đầu tiên đạt ngưỡng; giữ cố định low.
4. Nến M5 sau close < low nến mốc thì xác nhận Sell.
5. Nếu trước entry M5 close > U: chuyển OB với mốc mới; logic đối xứng.
### Chung
- OB bị đóng phá theo cùng nguyên tắc: hủy toàn bộ setup.
- Không giới hạn 30 phút; chờ miễn vùng và setup còn hiệu lực.
- M15 CHoCH ngược hướng trong lúc chờ: hủy setup và nến mốc.
- Điều kiện đóng phá được ưu tiên trước entry; không mua/bán trong vùng đã vô hiệu.
- Vào market ngay sau nến M5 xác nhận đóng.
- Không thêm yêu cầu CHoCH M5 cho entry.
- Backtest mô phỏng giá mở nến kế tiếp cùng chi phí/trượt giá; không giả định khớp đúng close nến xác nhận.

## 5. SL và bảo vệ vốn
- Buy: SL = low thấp nhất từ nến mốc tới hết nến xác nhận - buffer.
- Sell: SL = high cao nhất trong cùng khoảng + buffer.
- Buffer = 0.2 x ATR(14) M5 tại nến xác nhận; chốt cố định lúc vào.
- Không nới SL theo ATR sau entry.
- SL được kích hoạt intrabar, không chờ nến đóng. Giá khớp có thể khác do gap/trượt giá.
- 1R là rủi ro giá ban đầu tính từ entry thực tế tới SL ban đầu.
- Đạt +1R: dời SL về hòa vốn có bù chi phí; sau đó giữ nguyên, không trailing.
- Chi phí, cách bù hòa vốn, lot và rủi ro tiền chưa chốt. User yêu cầu tạm để sizing sang sau; không được coi lot 0.1 là đã phê duyệt cho bot.

## 6. Mốc H1/H4, R:R và chốt lời
- Mốc thoát chỉ H1/H4, không dùng D1 làm mốc thoát; D1 vẫn là bối cảnh.
- Buy: swing high đã xác nhận, bearish swing OB/FVG còn hiệu lực phía trên.
- Sell: swing low đã xác nhận, bullish swing OB/FVG còn hiệu lực phía dưới.
- Đánh dấu mốc trước entry. Mốc gần nhất dùng kiểm tra R:R tiềm năng >= 1.5 sau chi phí.
- Mốc 1.5R là bộ lọc, không TP cứng; không ép SL để vừa R:R.
- Chạm OB/FVG: high-low M5 giao với vùng.
- Chạm swing: Buy high >= swing high; Sell low <= swing low.
- Sau chạm mốc: M5 internal CHoCH ngược hướng xác nhận bằng close -> chốt toàn bộ, không chờ retest hoặc thêm displacement.
- CHoCH thoát có thể xảy ra ngay trên nến chạm; nếu thứ tự intrabar không xác định từ OHLC, phải ghi nhận hạn chế mô phỏng.
- Chưa tới mốc: CHoCH M5 ngược hướng không tự đóng lệnh.
- Tới mốc mà chưa CHoCH: giữ theo SL.
- OB/FVG HTF bị chính nến H1/H4 đóng phá: bỏ mốc đó, theo dõi mốc tiếp theo.
- Swing đã vượt vẫn được ghi là mốc thanh khoản đã chạm.
- Cách xử lý khi mốc đã chạm bị vô hiệu và CHoCH đến muộn cần kiểm tra trạng thái rõ ràng trong bản triển khai; không áp một CHoCH bất kỳ vào mốc cũ vô thời hạn mà không ghi nhận.
- Mốc quan trọng không bảo đảm đảo chiều; lợi nhuận thực tế có thể dưới 1.5R.

## 7. Tin tức và tái nhập
- Không mở mới từ 30 phút trước tới 15 phút sau tin mạnh liên quan USD/vàng.
- Lệnh mở giữ theo SL và quy tắc thoát.
- Tín hiệu entry trong cửa sổ cấm: bỏ; sau cửa sổ phải có retest mới và nến mốc mới nếu setup còn hiệu lực.
- Danh mục tin, nguồn lịch và múi giờ/DST cần cấu hình; Pine không được giả định tự lấy được lịch kinh tế MCP.
- Mỗi CHoCH M15 tối đa một lệnh đã khớp.
- Sau SL, hòa vốn hoặc chốt: cần CHoCH M15 mới + displacement + retest mới.
- Không dùng lại tín hiệu cũ để vào lại.

## 8. Những điểm chưa chốt hoặc chưa kiểm chứng
Không tự coi các mục này là bộ lọc bắt buộc:
- Premium/discount D1: đã chốt làm bối cảnh/theo dõi; CHƯA chốt “Buy chỉ discount, Sell chỉ premium”, EQ có được entry không.
- CHƯA chốt bắt buộc chạm POI H1/H4 cho mọi entry; mốc thoát H1/H4 không đồng nghĩa POI entry.
- Liquidity sweep có trong checklist mẫu, nhưng CHƯA lượng hóa và chưa được duyệt thành điều kiện bắt buộc cho mọi setup.
- Fib 0.618-0.786 đã thảo luận; CHƯA chốt làm bộ lọc entry.
- Định nghĩa xu hướng chính D1/nhịp hồi và xử lý xung đột H4/H1 cần diễn giải nhất quán bằng logic mã nguồn; không tự suy ra hướng từ một nhãn bất kỳ.
- LuxAlgo FVG invalidation có thể khác quy tắc M5 close xuyên toàn vùng; strategy phải dùng quy tắc đã duyệt thay vì tự dùng cơ chế xóa hình.
- CHƯA có kết quả backtest, forward test hay win rate.
- Broker, quy cách hợp đồng, lot tối thiểu, ký quỹ, spread, phí, swap và sizing còn để sau.

## 9. Nhật ký kiểm thử
Mỗi setup cần ghi: thời gian, hướng D1, nhịp hiện tại; CHoCH M15; displacement; vùng FVG/OB và ID; độ sâu retest; nến mốc; số nến chờ; entry/SL ban đầu; ATR/buffer; mốc HTF/R:R; tin; lý do bỏ/hủy; lần dời BE; lý do thoát; P&L/R sau chi phí.
So sánh riêng: hướng chính/nhịp hồi; entry FVG/OB; hợp lưu Fib/không hợp lưu nếu thu thập; thời gian chờ; mốc H1/H4 và swing/OB/FVG.
Trước khi kết luận: kiểm tra không dùng dữ liệu tương lai, xác nhận HTF đúng thời điểm, phí/trượt giá, dữ liệu ngoài mẫu và forward demo.

