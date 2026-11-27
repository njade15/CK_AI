# Phân tích lượt chính thức ngày 26 tháng 11 năm 2026

Nguồn: [trials.csv](trials.csv), [summary.csv](summary.csv), [cấu hình](config.json) và [metadata](metadata.json). [REPORT.md](REPORT.md) chứa toàn bộ bảng và biểu đồ được tạo tự động; phần này diễn giải các kết quả đã đo, không thay thế dữ liệu gốc.

## Độ đầy đủ và khả năng tái hiện

Mã chạy là commit `2781502d6e92eefda54fdb6c772c8d65a40c0330`, nhánh feature/task1-nqueens, working tree sạch lúc bắt đầu. Máy Intel Core i7-14650HX, Windows 11, Python 3.12.10, python-sat 1.9.dev25, matplotlib 3.11.2; phiên bản toàn bộ gói có trong metadata. Chạy tuần tự một worker, không restart. Vòng thực thi 325 lượt mất 51,5227783 s, không gồm vẽ biểu đồ và thu thập metadata.

25 lượt SAT (5 lượt/N) đều có nghiệm hợp lệ. 300 lượt MC (30 seed/N/chiến lược) có 293 nghiệm hợp lệ và 7 LIMIT_REACHED. Không có ERROR, TIMEOUT hoặc NOT_RUN; không thiếu lượt nào trong kế hoạch. [audit.json](audit.json) xác nhận đủ 150 cặp cùng seed/trạng thái đầu và kiểm tra lại mọi nghiệm được báo SAT.

Deadline 15 s cho SAT và 5 s cho MC không bị chạm trong bộ dữ liệu này. Điều đó không phải bằng chứng rằng giới hạn không hoạt động: kiểm thử pipeline đã thực sự dừng worker đang sleep 10 s theo deadline 2 s, giữ snapshot tiến độ và kiểm tra không còn tiến trình con. Các fixture kiểm thử không được đưa vào CSV thí nghiệm.

## SAT và phạm vi thời gian

Các giá trị sau là trung vị của 5 phép đo mỗi N, chuyển từ giây trong summary.csv sang mili giây. Mệnh đề được đếm trên CNF thực sinh; khớp công thức đã yêu cầu.

| N | Biến | Mệnh đề | Sinh CNF (ms) | Tạo/nạp (ms) | solve() (ms) | Tổng thuật toán (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 4 | 16 | 80 | 0,0540 | 0,0652 | 0,0169 | 0,2623 |
| 8 | 64 | 736 | 0,2062 | 0,2336 | 0,0509 | 0,6879 |
| 16 | 256 | 6336 | 1,4646 | 1,3560 | 1,0066 | 4,1957 |
| 32 | 1024 | 52608 | 6,6676 | 9,9506 | 10,4434 | 28,0662 |
| 64 | 4096 | 428800 | 56,0905 | 79,9651 | 126,0738 | 265,3706 |

Chẳng hạn N=64 có median solve khoảng 126 ms nhưng median tổng thuật toán khoảng 265 ms; không được gọi hai số đó cùng một chỉ số. Tổng còn gồm giải mã, validator, thống kê, callback/IPC snapshot và cleanup. Trung vị các pha không nhất thiết cộng thành trung vị tổng. Parent wall còn có spawn/import và teardown; startup là phần đáng kể ở N nhỏ. Chưa có cơ sở ngoại suy cho N>64 hoặc môi trường chấm bài khác.

## Min-Conflicts: đọc trung vị cùng tỷ lệ thành công

Mỗi N có đúng 30 cặp seed 0..29, cùng trạng thái đầu được sao chép và cùng max_steps=5000. Điểm khác duy nhất của hai cấu hình là chọn quân. Tổng thời gian thuật toán đã tính chi phí chọn biến.

| N | random thành công | max thành công | Median bước random | Median bước max | Median thời gian random (ms) | Median thời gian max (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 4 | 30/30 | 30/30 | 11 | 5,5 | 0,10115 | 0,08345 |
| 8 | 30/30 | 27/30 | 40 | 21 | 0,29390 | 0,22890 |
| 16 | 28/30 | 28/30 | 71,5 | 62,5 | 0,83260 | 0,83585 |
| 32 | 30/30 | 30/30 | 79,5 | 76,5 | 1,57595 | 1,80070 |
| 64 | 30/30 | 30/30 | 112 | 92 | 4,08235 | 3,84305 |

Các median chỉ dùng các lượt thành công; số mẫu bằng tử số ở cột thành công. Max có median bước thấp hơn ở cả năm N trong bộ dữ liệu này. Tuy nhiên, ở N=8 nó thất bại 3 lượt, trong khi random không thất bại. Ở N=32, cả hai thành công toàn bộ nhưng median thời gian max cao hơn dù median bước thấp hơn. Đây là quan sát phù hợp với việc cần xét cả chi phí chọn biến, nhưng chưa đo riêng thời gian selector nên không quy kết nguyên nhân chỉ cho selector.

Tại N=16, random thất bại seed 14 và 28; max thất bại seed 8 và 19. Hai tập 28 lượt thành công không trùng nhau, chỉ có 26 cặp cùng thành công. Vì vậy không đọc chênh lệch hai median có điều kiện như hiệu quả nhân quả trên cùng tập seed. Chưa thực hiện kiểm định thống kê hoặc khoảng tin cậy; 30 seed và một máy không đủ để kết luận heuristic tốt hơn nói chung.

## Chi phí thất bại và các trường hợp chưa giải được

| N | Chiến lược | Seed chưa giải được trong ngân sách | Số bước mỗi lượt |
| --- | --- | --- | ---: |
| 8 | max_conflicted | 1, 6, 16 | 5000 |
| 16 | max_conflicted | 8, 19 | 5000 |
| 16 | random_conflicted | 14, 28 | 5000 |

Lý do cả bảy lượt là hết max_steps; không chứng minh vô nghiệm và không được đổi nhãn thành UNSAT. Không restart hoặc tăng ngân sách để cứu riêng các lượt này. Tất cả còn trong trials.csv cùng thời gian và thông báo lỗi/giới hạn gốc. Các N còn lại không có lượt chưa giải được trong cấu hình đã chạy; không có phần nào bị bỏ qua vì tài nguyên.

N=8 thể hiện rõ tác động của giữ thất bại: tổng bước trên cả 30 lượt random là 1281, max là 16017; tổng thời gian thuật toán tương ứng khoảng 0,0096718 s và 0,1103751 s. Chỉ nhìn median trên các lượt thành công sẽ bỏ qua phần lớn chi phí max trong nhóm này. Tại N=16, tổng thời gian thuật toán random/max khoảng 0,1284582/0,1324800 s, đều đã tính hai lượt thất bại.

Tổng wall trên mọi lượt còn được báo riêng trong REPORT.md và summary.csv, gồm cả startup tiến trình; không dùng nó thay cho tổng thuật toán. Vì không có timeout chính thức nên mọi lượt đều có tổng thuật toán hoàn tất và số bước ghi được. Nhánh N/A được kiểm tra thực tế ở smoke: nhóm max_conflicted N=8 không có thành công với max_steps=100, nên median thành công là N/A, không phải 0.

## Giới hạn và hướng kiểm chứng tiếp

Đây là thí nghiệm đầu tiên không restart, chỉ N=4..64 và seed 0..29. Không mở rộng N hoặc thay seed sau khi xem kết quả. Máy và tải hệ điều hành không phải môi trường macOS của môn học; thời gian rất ngắn ở N nhỏ dễ bị nhiễu. SAT chỉ lặp 5 lượt và không warmup. Đồ thị median là mô tả, không có khoảng tin cậy; sự khác nhau về tập lượt thành công có thể gây lệch chọn mẫu.

Kết quả ủng hộ việc tiếp tục khảo sát giả thuyết giảm bước, đồng thời cho thấy cần tính thất bại và tổng chi phí. Muốn kết luận mạnh hơn cần đăng ký thêm tập seed/N, so sánh theo cặp, đo riêng chi phí selector và kiểm tra môi trường khác. Những thí nghiệm đó chưa chạy, không có số liệu được suy đoán hoặc điền thêm.
