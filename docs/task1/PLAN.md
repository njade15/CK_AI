# Kế hoạch Task 1 N-Queens

## Phạm vi và quy tắc

Phụ trách Task 1, phát triển trên `feature/task1-nqueens` theo yêu cầu cập nhật. Không phát triển trực tiếp trên `main`, không sửa Task 2/3, không force push hoặc xóa thay đổi hiện có. Chưa merge trước nghiệm thu cuối. Giai đoạn nền tảng chỉ commit cục bộ, chưa push.

Sau mỗi giai đoạn báo các tệp thay đổi, lệnh kiểm tra thực sự đã chạy, kết quả và giới hạn. Không tạo số liệu thí nghiệm giả, không coi hết giới hạn tìm kiếm là chứng minh vô nghiệm.

## Giai đoạn 1 Nền tảng

- [x] Tách mã, kiểm thử, tài liệu và dữ liệu Task 1.
- [x] `NQueensProblem` kiểm tra N nguyên dương, không chấp nhận bool.
- [x] `SolveResult` phân biệt SAT, UNSAT, LIMIT_REACHED và ERROR.
- [x] Validator tọa độ độc lập kiểm tra đúng N quân, phạm vi, ô, hàng, cột và đường chéo.
- [x] Hiển thị bàn cờ ASCII trên terminal.
- [x] Viết kiểm thử lời giải N=4, các vi phạm ràng buộc, đầu vào sai, trạng thái kết quả và hiển thị.
- [x] Xác nhận kiểm thử thực tế đạt trước commit; ghi kết quả trong báo cáo giai đoạn.

Tại thời điểm hoàn thành giai đoạn 1 chưa triển khai solver hoặc benchmark. Hướng dẫn môi trường và chạy test ở [README Task 1](../../source/task1_nqueens/README.md).

Đã chạy ngày 26/11/2026 trên Windows, Python 3.12.10 trong môi trường ảo:

```powershell
.\.venv\Scripts\python.exe -m pip install --no-index -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -t . -v
```

Kết quả: dependency hiện không cần gói bên thứ ba; 27 test đạt. Đây là kiểm thử nền tảng bằng fixture, không phải benchmark solver. Chưa kiểm tra trên macOS/Linux hoặc các phiên bản Python khác.

## Giai đoạn 2 Chốt yêu cầu và mô hình SAT

Đối chiếu đầy đủ PDF đề chính thức và xác nhận quy định môn học, tiêu chí nghiệm thu, phiên bản thư viện và môi trường đánh giá. Nội dung tài liệu phân công là nguồn tham khảo nội bộ; không thay thế đề chính thức.

Đã triển khai mô hình theo yêu cầu cập nhật: biến mỗi ô, tọa độ từ 0, `id = r*N + c + 1`; đúng một hậu mỗi hàng và tối đa một mỗi cột/đường chéo, dùng mã hóa từng cặp. Không thêm at-least-one cho cột hoặc ràng buộc dư. [MODEL.md](MODEL.md) giải thích CNF N=4, công thức số mệnh đề và phạm vi đo thời gian.

Nghiệm thu: kiểm thử ánh xạ, CNF trên bàn nhỏ và đối chiếu kết quả với validator độc lập; kiểm tra N=1, N=2/3 và N=4.

## Giai đoạn 3 PySAT và Glucose3

Đã triển khai `SATNQueensSolver`, CLI và dependency `python-sat==1.9.dev25`. Trả `SolveResult`, đo thời gian thực tế bằng `perf_counter`, lấy bộ đếm Glucose3, giải mã và kiểm tra bằng validator, giải phóng solver trong `finally`. False trả UNSAT; unknown trả LIMIT_REACHED; lỗi trả ERROR. Hiện gọi solve không giới hạn, chưa có tùy chọn ngân sách.

Nghiệm thu: test tích hợp SAT/UNSAT, hành vi giới hạn và lỗi; đối chiếu nghiệm với các trường hợp đã biết.

Ở thời điểm nghiệm thu SAT, đã chạy toàn bộ 47 test Task 1 ngày 26/11/2026 trên Windows/Python 3.12.10 và đạt, gồm 27 test nền tảng. Glucose3 thực xác nhận N=1,4,8 có nghiệm hợp lệ và N=2,3 vô nghiệm. Số mệnh đề thực sinh khớp công thức N=1..12, riêng N=4 là 80. Nhánh unknown/lỗi/cleanup kiểm tra bằng mock; không coi đó là thí nghiệm tài nguyên thực tế. Chưa kiểm tra SAT trên macOS/Linux; tại mốc đó chưa benchmark hoặc triển khai Min-Conflicts, chưa push hoặc merge.

## Giai đoạn 4 Min-Conflicts và heuristic

Đã triển khai Min-Conflicts cơ sở: vector hàng theo cột, khởi tạo ngẫu nhiên độc lập, RNG riêng, chọn quân xung đột ngẫu nhiên và phá hòa ngẫu nhiên giữa mọi hàng tối ưu. Có seed, max_steps và trạng thái khởi tạo tùy chọn. Một bước là một phép gán, kể cả không đổi hàng; kiểm tra trước bước đầu và sau cập nhật cuối. Hết bước trả LIMIT_REACHED, nghiệm qua validator độc lập. Chi tiết và ví dụ N=4 trong [MIN_CONFLICTS.md](MIN_CONFLICTS.md).

Chưa triển khai restart hoặc heuristic đề xuất. Các cấu hình này chỉ được bổ sung ở giai đoạn được yêu cầu sau, tách rõ khỏi baseline. Chưa có benchmark so sánh hoặc giới hạn thời gian.

Nghiệm thu: test số xung đột, cập nhật trạng thái, khả năng lặp lại theo seed, hết giới hạn và xác nhận nghiệm bằng validator.

Kết quả giai đoạn baseline ngày 26/11/2026 trên Windows/Python 3.12.10: toàn bộ 67 test Task 1 đạt bằng `python -m unittest discover -s tests -t . -v`, gồm 47 test trước đó và 20 test mới. Lần chạy đầu phát hiện một fixture CLI dùng nhầm cách biểu diễn hàng/cột; đã sửa fixture theo vector hàng theo cột và chạy lại toàn bộ đạt. `pip check` đạt; CLI thực tế N=4 với trạng thái `(1,3,0,0)`, seed=0, max_steps=1 trả SAT sau bước cuối; N=8 seed=42, max_steps=1000 trả SAT; trạng thái xung đột với max_steps=0 trả LIMIT_REACHED/exit code 3. Đây là kiểm tra chức năng, chưa phải benchmark; chưa kiểm tra trên macOS/Linux. Chưa push hoặc merge.

## Giai đoạn 5 Thực nghiệm thực tế

Chốt tập N ≥ 4, số lần lặp, seed, ngân sách và chỉ số so sánh trước khi chạy. Lưu dữ liệu thực tế dưới [results/task1](../../results/task1/README.md), gồm trạng thái mỗi lần chạy và cả trường hợp hết giới hạn/lỗi. Ghi hệ điều hành, CPU, Python, dependency, commit và câu lệnh để tái lập. Không điền dữ liệu chưa đo hoặc loại bỏ âm thầm lần chạy thất bại.

Nghiệm thu: tái chạy một tập nhỏ, kiểm tra toàn bộ nghiệm được tuyên bố SAT, phân tích tỷ lệ thành công, thời gian và giới hạn của so sánh.

## Giai đoạn 6 Báo cáo và nghiệm thu cuối

Viết phần mô hình, phương pháp, heuristic, kết quả và hạn chế bằng số liệu đã chạy. Kiểm tra lại định dạng báo cáo và gói nộp theo đề chính thức. Review phần Task 1, chạy test trên môi trường sạch rồi mới đề nghị merge tại bước nghiệm thu cuối.
