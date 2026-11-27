# Benchmark Task 1 — pipeline-smoke

Nguồn dữ liệu: [trials.csv](trials.csv). Bảng tổng hợp: [summary.csv](summary.csv).
Cấu hình: [config.json](config.json). Môi trường và provenance: [metadata.json](metadata.json).
Commit mã nguồn: `65717c1da561474ecf72994cb4e74f349fc08ed2`; working tree dirty khi bắt đầu: `True`.
Máy: Intel(R) Core(TM) i7-14650HX; Windows-11-10.0.26200-SP0; Python 3.12.10.
Kiểm tra dữ liệu: 10 lượt theo kế hoạch, 8 nghiệm hợp lệ; audit đạt.

Chưa chạy (NOT_RUN): 0 lượt, lý do nếu có là hết ngân sách toàn phiên.
Đã bắt đầu nhưng bị dừng bởi deadline (TIMEOUT): 0 lượt.
Lỗi (ERROR): 0 lượt. Lý do từng lượt nằm ở cột message của trials.csv;
timeout không phải kết luận vô nghiệm và không có tổng thời gian thuật toán hoàn tất.

## Thiết kế

SAT: 1 lượt/N, không warmup, timeout 5 s/lượt.
Min-Conflicts: 2 seed/N/chiến lược, max_steps=100,
timeout 5 s/lượt, không restart. Mỗi cặp dùng cùng seed và bản sao cùng trạng thái đầu;
thứ tự hai chiến lược luân phiên theo lượt. Một worker tại một thời điểm, ngân sách toàn phiên 60 s.

## SAT

Trung vị solve chỉ đo lời gọi Glucose3.solve(), đơn vị giây; không gồm sinh CNF/nạp solver.
n solve là số lượt có phép đo solve hoàn tất, kể cả nếu giai đoạn sau bị lỗi/timeout.
Timeout trong solve không có thời gian solve hoàn tất và không được thay bằng thời gian timeout.

| N | Biến | Mệnh đề | Median solve (s) | n solve | SAT hợp lệ | Timeout | Lỗi | Chưa chạy |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 4 | 16 | 80 | 1.52e-05 | 1 | 1 | 0 | 0 | 0 |
| 8 | 64 | 736 | 5.35e-05 | 1 | 1 | 0 | 0 | 0 |

![Số mệnh đề và thời gian SAT solve](sat.png)

## Min-Conflicts

Tỷ lệ thành công = SAT hợp lệ / tổng lượt được lên kế hoạch. Bảng luôn giữ số lượt chưa chạy nếu có.
Trung vị bước/thời gian bên dưới chỉ trên các lượt thành công, có số mẫu đi kèm; không có thành công dùng N/A.
Thời gian thuật toán tính cả chọn biến, chọn hàng, cập nhật, khởi tạo RNG/board, kiểm tra và thống kê.

| N | Chiến lược | Thành công | Tổng lượt | Tỷ lệ | Median bước | n bước | Median thuật toán (s) | n thời gian |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 4 | max_conflicted | 2 | 2 | 1 | 2.5 | 2 | 7.03e-05 | 2 |
| 8 | max_conflicted | 0 | 2 | 0 | N/A | 0 | N/A | 0 |
| 4 | random_conflicted | 2 | 2 | 1 | 7 | 2 | 7.97e-05 | 2 |
| 8 | random_conflicted | 2 | 2 | 1 | 67.5 | 2 | 0.00043295 | 2 |

![Min-Conflicts: tỷ lệ và các trung vị có điều kiện thành công](min_conflicts.png)

## Chi phí trên mọi lượt và thất bại

Wall quan sát bao gồm spawn/import, thuật toán, IPC và teardown, tính cả TIMEOUT và lỗi.
Đây không phải thời gian solve hoặc tổng thuật toán. Tổng thuật toán hoàn tất chỉ cộng các số đo có sẵn;
lượt timeout không có tổng thuật toán hoàn tất, nên báo số mẫu riêng và dùng wall để biểu diễn chi phí toàn bộ.
Số bước đã ghi có thể thiếu khi tiến trình bị dừng; không suy đoán bước chưa được báo.

| Phương pháp | Chiến lược | N | Hết bước/unknown | Timeout | Lỗi | Chưa chạy | Tổng bước đã ghi | n bước | Tổng thuật toán hoàn tất (s) | n thuật toán | Tổng wall mọi lượt (s) | n wall |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| min-conflicts | max_conflicted | 4 | 0 | 0 | 0 | 0 | 5 | 2 | 0.0001406 | 2 | 0.313675 | 2 |
| min-conflicts | max_conflicted | 8 | 2 | 0 | 0 | 0 | 200 | 2 | 0.0014844 | 2 | 0.263684 | 2 |
| min-conflicts | random_conflicted | 4 | 0 | 0 | 0 | 0 | 14 | 2 | 0.0001594 | 2 | 0.287921 | 2 |
| min-conflicts | random_conflicted | 8 | 0 | 0 | 0 | 0 | 135 | 2 | 0.0008659 | 2 | 0.275736 | 2 |
| sat | N/A | 4 | 0 | 0 | 0 | 0 | N/A | 0 | 0.0002381 | 1 | 0.133575 | 1 |
| sat | N/A | 8 | 0 | 0 | 0 | 0 | N/A | 0 | 0.0006637 | 1 | 0.143542 | 1 |

![Chi phí mọi lượt Min-Conflicts](costs.png)

## Phạm vi và giới hạn

Timeout được parent thực thi từ trước spawn đến khi nhận kết quả, terminate/kill worker khi hết hạn;
wall quan sát còn gồm tối đa hai lần join 1 s và độ trễ lập lịch. Không chỉ kiểm tra thời gian sau khi solver trả về.
SAT gửi snapshot các pha hoàn tất để giữ số đếm và thời gian trước timeout; tổng SAT bao gồm chi phí callback/IPC,
còn từng pha CNF/nạp/solve không tính callback đó. Min-Conflicts total bao gồm chi phí chọn biến.
Các ô trống trong CSV là không có phép đo, không phải 0; summary.csv giữ ô trống, báo cáo hiển thị N/A.
Mọi TIMEOUT, ERROR, LIMIT_REACHED, NOT_RUN còn nguyên trong CSV. Xem audit.json và SHA256SUMS.txt để kiểm tra.
Đây là kết quả mô tả trên một máy, tập N/seed và ngân sách đã công bố. Không suy ra chiến lược tốt hơn nói chung;
trung vị trên lượt thành công chịu ảnh hưởng chọn mẫu, cần đọc cùng tỷ lệ thành công và chi phí toàn bộ.
Không so trực tiếp SAT solve với tổng thuật toán Min-Conflicts hoặc wall pipeline. Chưa kiểm tra macOS/Linux.
