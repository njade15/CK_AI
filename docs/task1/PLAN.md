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

Chưa triển khai solver hoặc benchmark ở giai đoạn này. Hướng dẫn môi trường và chạy test ở [README Task 1](../../source/task1_nqueens/README.md).

Đã chạy ngày 26/11/2026 trên Windows, Python 3.12.10 trong môi trường ảo:

```powershell
.\.venv\Scripts\python.exe -m pip install --no-index -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -t . -v
```

Kết quả: dependency hiện không cần gói bên thứ ba; 27 test đạt. Đây là kiểm thử nền tảng bằng fixture, không phải benchmark solver. Chưa kiểm tra trên macOS/Linux hoặc các phiên bản Python khác.

## Giai đoạn 2 Chốt yêu cầu và mô hình SAT

Đối chiếu đầy đủ PDF đề chính thức và xác nhận quy định môn học, tiêu chí nghiệm thu, phiên bản thư viện và môi trường đánh giá. Nội dung tài liệu phân công là nguồn tham khảo nội bộ; không thay thế đề chính thức.

Mô hình dự kiến: biến mệnh đề cho mỗi ô `(row, column)` biểu diễn có quân hậu. Diễn đạt chính xác số quân mỗi hàng/cột và ràng buộc không tấn công trên hai họ đường chéo; mô tả cách chuyển thành CNF và ánh xạ biến. Chọn cách mã hóa sau khi chốt yêu cầu; chưa tạo bộ mã hóa ở giai đoạn nền tảng.

Nghiệm thu: kiểm thử ánh xạ, CNF trên bàn nhỏ và đối chiếu kết quả với validator độc lập; kiểm tra N=1, N=2/3 và N=4.

## Giai đoạn 3 PySAT và Glucose3

Triển khai solver theo OOP, bổ sung dependency rõ phiên bản sau khi xác minh tương thích. Trả `SolveResult`, đo thời gian thực tế, lưu thống kê solver thực sự cung cấp. Chỉ dùng UNSAT khi đã chứng minh vô nghiệm; dừng theo ngân sách phải trả LIMIT_REACHED. Giải mã nghiệm thành tọa độ và kiểm tra bằng validator.

Nghiệm thu: test tích hợp SAT/UNSAT, hành vi giới hạn và lỗi; đối chiếu nghiệm với các trường hợp đã biết.

## Giai đoạn 4 Min-Conflicts và heuristic

Triển khai thuật toán cơ sở, sau đó heuristic đề xuất; tách rõ từng cấu hình. Quy định ngân sách bước/thời gian, seed và restart để so sánh công bằng. Thất bại trong ngân sách trả LIMIT_REACHED, không tự kết luận UNSAT.

Nghiệm thu: test số xung đột, cập nhật trạng thái, khả năng lặp lại theo seed, hết giới hạn và xác nhận nghiệm bằng validator.

## Giai đoạn 5 Thực nghiệm thực tế

Chốt tập N ≥ 4, số lần lặp, seed, ngân sách và chỉ số so sánh trước khi chạy. Lưu dữ liệu thực tế dưới [results/task1](../../results/task1/README.md), gồm trạng thái mỗi lần chạy và cả trường hợp hết giới hạn/lỗi. Ghi hệ điều hành, CPU, Python, dependency, commit và câu lệnh để tái lập. Không điền dữ liệu chưa đo hoặc loại bỏ âm thầm lần chạy thất bại.

Nghiệm thu: tái chạy một tập nhỏ, kiểm tra toàn bộ nghiệm được tuyên bố SAT, phân tích tỷ lệ thành công, thời gian và giới hạn của so sánh.

## Giai đoạn 6 Báo cáo và nghiệm thu cuối

Viết phần mô hình, phương pháp, heuristic, kết quả và hạn chế bằng số liệu đã chạy. Kiểm tra lại định dạng báo cáo và gói nộp theo đề chính thức. Review phần Task 1, chạy test trên môi trường sạch rồi mới đề nghị merge tại bước nghiệm thu cuối.
