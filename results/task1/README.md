# Dữ liệu thực nghiệm Task 1

Đã có [lượt benchmark chính thức ngày 26/11/2026](main-20261126/REPORT.md), [phân tích kết quả](main-20261126/ANALYSIS.md) và [dữ liệu từng lượt](main-20261126/trials.csv). Chạy đủ 325 lượt: 318 SAT hợp lệ và 7 LIMIT_REACHED, không có timeout/lỗi/chưa chạy. Mã chạy commit `2781502d6e92eefda54fdb6c772c8d65a40c0330`, working tree sạch khi bắt đầu. Xem metadata và cấu hình trong thư mục kết quả để tái hiện.

[Smoke pipeline](smoke-20261126/REPORT.md) được giữ riêng, không gộp vào kết quả chính thức. Smoke chạy khi mã benchmark đang phát triển: metadata ghi parent commit `65717c1` và dirty=true. Sau khi hoàn thiện, báo cáo/biểu đồ được tái tạo từ cùng CSV bằng mã phân tích ở commit `2781502`; không chạy lại hoặc thay dữ liệu từng lượt smoke.

Các thư mục chứa cấu hình, môi trường, audit, CSV tổng hợp, ba biểu đồ và SHA256SUMS.txt. Thư mục chính thức còn có ANALYSIS.md diễn giải số liệu; bảng/biểu đồ tự động có thể tái tạo bằng `python -m source.task1_nqueens.benchmark_analysis <thư-mục-kết-quả>`. Không suy ra ưu thế heuristic chỉ từ trung vị trên lượt thành công.

Khi xác minh, sao chép thư mục dữ liệu sang thư mục tạm rồi chạy analyzer trên bản sao:
analyzer ghi lại bảng, báo cáo, biểu đồ và checksum tại đích. Xem [lệnh an toàn cho hai shell](../../docs/task1/BENCHMARK.md).
[So sánh ghép cặp bổ sung](paired-20261126/REPORT.md) giữ 150 cặp cùng seed và chỉ tính chênh lệch
trên các cặp cùng thành công. Phần này giữ riêng, không thay thế thống kê chính thức hoặc chạy lại solver.
[Xác minh trước PR](../../docs/task1/VERIFICATION.md) ghi kết quả kiểm tra lại và môi trường thực tế.

Mỗi lần chạy cần ghi tối thiểu: thuật toán/cấu hình, N, seed nếu có, ngân sách, trạng thái SAT/UNSAT/LIMIT_REACHED/ERROR, thời gian đo thực tế và thống kê có sẵn. Lưu tọa độ nghiệm SAT để validator có thể kiểm chứng. Không đổi lần chạy hết giới hạn thành UNSAT.

Kèm metadata gồm commit, phiên bản Python/dependency, OS/CPU, câu lệnh và thời điểm chạy. Nếu một chỉ số không đo được, để trống hoặc ghi rõ không có; không điền số giả. Dữ liệu cố định trong kiểm thử không phải dữ liệu benchmark.
