# Task 1 N-Queens

Nền tảng Python theo OOP, dùng Python 3.10 trở lên. Chưa có thuật toán SAT hay Min-Conflicts.

## Mô hình dữ liệu

- `NQueensProblem(n)`: bàn cờ vuông với `n` nguyên dương; từ chối `bool`, số thực và chuỗi. N=1, 2, 3 vẫn là đầu vào hợp lệ; khả năng có nghiệm là trách nhiệm của solver về sau.
- `Position`: tọa độ `(row, column)` nguyên, đánh số từ 0 đến `n - 1`. Một lời giải có đúng `n` tọa độ, không cần sắp thứ tự.
- `SolutionValidator(problem).validate(queens)`: trả về `bool`, kiểm tra số quân, kiểu tọa độ, phạm vi, trùng ô, hàng, cột và hai hướng đường chéo. Dùng các tập hợp với khóa đường chéo `row - column` và `row + column`; thời gian và bộ nhớ O(N). Không tìm nghiệm.
- `SolveResult`: chứa `status`, `solution`, `elapsed_seconds`, `statistics` và `message` tùy chọn. Chỉ `SAT` mang lời giải ứng viên; phải dùng validator để xác nhận lời giải theo bàn cờ. Các container đầu vào được sao chép. Thống kê mặc định rỗng, thời gian phải hữu hạn và không âm.
- `render_board(problem, queens)`: trả chuỗi ASCII; `print_board(...)` in ra terminal hoặc text stream. Hàng 0 ở trên cùng; `Q` là quân hậu và `.` là ô trống. Hai hàm chỉ nhận lời giải đầy đủ, hợp lệ.

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
```

macOS / Linux (Python 3.10 trở lên):

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -t . -v
```

Ví dụ in lời giải N=4 đã biết, từ PowerShell:

```powershell
.\.venv\Scripts\python.exe -c "from source.task1_nqueens import NQueensProblem, print_board; print_board(NQueensProblem(4), [(0, 1), (1, 3), (2, 0), (3, 2)])"
```

Đây là dữ liệu lời giải cố định để minh họa giao diện, không phải kết quả chạy solver. Xem [kế hoạch](../../docs/task1/PLAN.md) và [quy ước kết quả](../../results/task1/README.md).
