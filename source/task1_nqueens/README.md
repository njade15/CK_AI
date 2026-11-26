# Task 1 N-Queens

Python theo OOP, dùng Python 3.10 trở lên. Đã có SAT với CNF từng cặp và Glucose3; chưa có Min-Conflicts. Dependency: `python-sat==1.9.dev25` (tên import `pysat`), cài từ tệp dependency ở gốc repository.

## Mô hình dữ liệu

- `NQueensProblem(n)`: bàn cờ vuông với `n` nguyên dương; từ chối `bool`, số thực và chuỗi. N=1, 2, 3 vẫn là đầu vào hợp lệ; khả năng có nghiệm là trách nhiệm của solver về sau.
- `Position`: tọa độ `(row, column)` nguyên, đánh số từ 0 đến `n - 1`. Một lời giải có đúng `n` tọa độ, không cần sắp thứ tự.
- `SolutionValidator(problem).validate(queens)`: trả về `bool`, kiểm tra số quân, kiểu tọa độ, phạm vi, trùng ô, hàng, cột và hai hướng đường chéo. Dùng các tập hợp với khóa đường chéo `row - column` và `row + column`; thời gian và bộ nhớ O(N). Không tìm nghiệm.
- `SolveResult`: chứa `status`, `solution`, `elapsed_seconds`, `statistics` và `message` tùy chọn. Chỉ `SAT` mang lời giải ứng viên; phải dùng validator để xác nhận lời giải theo bàn cờ. Các container đầu vào được sao chép. Thống kê mặc định rỗng, thời gian phải hữu hạn và không âm.
- `render_board(problem, queens)`: trả chuỗi ASCII; `print_board(...)` in ra terminal hoặc text stream. Hàng 0 ở trên cùng; `Q` là quân hậu và `.` là ô trống. Hai hàm chỉ nhận lời giải đầy đủ, hợp lệ.
- `CNFEncoder(problem)`: ánh xạ `id = row*N + column + 1`, ánh xạ ngược, giải mã model có dấu và sinh CNF. Đúng một hậu mỗi hàng; tối đa một mỗi cột/đường chéo; dùng từng cặp, không có biến phụ hoặc ràng buộc dư.
- `SATNQueensSolver(problem).solve()`: trả `SolveResult`, đo thời gian sinh CNF, tạo/nạp solver, gọi solve và tổng; xác nhận nghiệm bằng validator, giải phóng solver trong `finally`. Xem [mô hình và phạm vi thống kê](../../docs/task1/MODEL.md).

| Trạng thái | Ý nghĩa |
| --- | --- |
| `SAT` | Solver tìm được lời giải ứng viên; cần kiểm tra bằng validator. |
| `UNSAT` | Đã chứng minh không có lời giải. |
| `LIMIT_REACHED` | Hết thời gian, số bước hoặc tài nguyên; chưa kết luận vô nghiệm. |
| `ERROR` | Có lỗi khi chạy; dùng `message` để mô tả, không ghi thông tin nhạy cảm. |

Sau này solver phải đo thời gian thực tế bằng đồng hồ đơn điệu như `time.perf_counter()`. Không dùng thời gian/thống kê fixture của test làm số liệu thực nghiệm. Khi bị giới hạn, có thể ghi thống kê đã đo nhưng không trả bàn cờ chưa hợp lệ như một lời giải.

## Chuẩn bị và chạy kiểm tra

Chạy từ thư mục gốc repository. Không cần kích hoạt môi trường ảo.

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -t . -v
.\.venv\Scripts\python.exe -m source.task1_nqueens 4
.\.venv\Scripts\python.exe -m source.task1_nqueens 8
```

macOS / Linux (Python 3.10 trở lên):

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -t . -v
.venv/bin/python -m source.task1_nqueens 4
.venv/bin/python -m source.task1_nqueens 8
```

CLI SAT in trạng thái, thống kê và bàn cờ nếu có nghiệm. Hiện chưa có tùy chọn giới hạn tài nguyên; không nhầm lần giải hết giới hạn với UNSAT. Exit code: 0 cho SAT/UNSAT, 1 cho ERROR, 2 cho lỗi đối số, 3 cho LIMIT_REACHED.

Ví dụ chỉ in lời giải N=4 đã biết, không gọi solver, từ PowerShell:

```powershell
.\.venv\Scripts\python.exe -c "from source.task1_nqueens import NQueensProblem, print_board; print_board(NQueensProblem(4), [(0, 1), (1, 3), (2, 0), (3, 2)])"
```

Đây là dữ liệu lời giải cố định để minh họa giao diện, không phải kết quả chạy solver. Xem [kế hoạch](../../docs/task1/PLAN.md) và [quy ước kết quả](../../results/task1/README.md).
