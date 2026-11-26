# Mô hình SAT cho N-Queens

## Biến Boolean và tọa độ

Với bàn N × N, mỗi ô có một biến `x[r,c]`: True khi đặt hậu tại ô đó. Hàng và cột đánh số từ 0 đến N−1. Không dùng biến phụ.

Ánh xạ sang số nguyên dương của DIMACS:

```text
id(r,c) = r*N + c + 1
(r,c) = divmod(id - 1, N)
```

Literal `id` biểu diễn `x[r,c]`; literal `-id` biểu diễn phủ định. Số 0 không phải biến/literal hợp lệ trong bộ mã hóa. `decode_variable` chỉ nhận id dương; `decode_model` nhận đầy đủ N² literal có dấu, mỗi biến đúng một lần, rồi lấy các biến dương làm tọa độ hậu. Kết quả giải mã phải qua `SolutionValidator` trước khi trả SAT.

Bảng id khi N=4:

| r / c | 0 | 1 | 2 | 3 |
| --- | --- | --- | --- | --- |
| 0 | 1 | 2 | 3 | 4 |
| 1 | 5 | 6 | 7 | 8 |
| 2 | 9 | 10 | 11 | 12 |
| 3 | 13 | 14 | 15 | 16 |

## Các nhóm ràng buộc

CNF là phép hội của tất cả mệnh đề dưới đây. Mỗi tuple số nguyên trong mã biểu diễn một mệnh đề OR. At-most-one được mã hóa từng cặp: với mọi cặp biến phân biệt `a,b` trong một nhóm, thêm `(-a OR -b)`. Nhóm có k biến sinh `k(k−1)/2` mệnh đề, nhóm đơn không sinh mệnh đề.

### Mỗi hàng có đúng một hậu

Mỗi hàng gồm một mệnh đề at-least-one và các mệnh đề at-most-one. Hàng 0 của N=4:

```text
(1 OR 2 OR 3 OR 4)
(-1 OR -2) AND (-1 OR -3) AND (-1 OR -4)
AND (-2 OR -3) AND (-2 OR -4) AND (-3 OR -4)
```

Áp dụng cho cả N hàng, tạo đúng N hậu và không cho hai hậu cùng hàng.

### Mỗi cột có nhiều nhất một hậu

Với cột 0 của N=4, nhóm biến là `[1,5,9,13]`. Tạo sáu cặp âm, ví dụ `(-1 OR -5)` và `(-9 OR -13)`.

Không thêm at-least-one cho cột: đã có đúng N hậu từ ràng buộc hàng, và N cột đều có tối đa một hậu, nên mỗi cột tự có đúng một hậu. Thêm các mệnh đề này sẽ dư và làm thay đổi số đếm yêu cầu.

### Mỗi đường chéo có nhiều nhất một hậu

- Hướng xuống phải: các ô cùng `r−c`. Đường chính N=4 có biến `[1,6,11,16]`.
- Hướng xuống trái: các ô cùng `r+c`. Đường đối chính N=4 có biến `[4,7,10,13]`.

Áp dụng at-most-one từng cặp cho mọi đường của mỗi hướng. Không thêm at-least-one cho đường chéo; không thêm giới hạn tổng số hậu, mệnh đề đối xứng hoặc ràng buộc đặc biệt cho N=2/3. N=1 tự sinh một mệnh đề đơn `(1)`.

## Số biến và mệnh đề

Số biến là N². Tổng số mệnh đề hàng at-most-one và cột at-most-one là `2*N*choose(N,2) = N²(N−1)`.

Độ dài các đường chéo trong một hướng là `1,2,...,N−1,N,N−1,...,2,1`. Số mệnh đề của một hướng:

```text
D(N) = choose(N,2) + 2 * sum(choose(k,2), k=1..N-1)
     = N(N−1)(2N−1)/6
```

Do có hai hướng, tổng:

```text
C(N) = N + N²(N−1) + N(N−1)(2N−1)/3
```

| Nhóm | N=4 | N=8 |
| --- | ---: | ---: |
| Hàng at-least-one | 4 | 8 |
| Hàng at-most-one | 24 | 224 |
| Cột at-most-one | 24 | 224 |
| Đường chéo xuống phải | 14 | 140 |
| Đường chéo xuống trái | 14 | 140 |
| Tổng | **80** | **736** |
| Số biến | 16 | 64 |

Đây là số đếm theo mô hình, không phải số liệu hiệu năng. Chương trình đếm độ dài các nhóm mệnh đề thực sự được sinh; công thức chỉ dùng để đối chiếu trong test/tài liệu. Thống kê `clauses_total` đếm CNF đầu vào, không phải số mệnh đề nội bộ sau khi Glucose3 đơn giản hóa hoặc học thêm mệnh đề.

## Ví dụ nghiệm và bố trí sai N=4

Nghiệm đã biết `[(0,1),(1,3),(2,0),(3,2)]` tương ứng biến True `{2,8,9,15}`; tất cả biến còn lại False. Mỗi hàng có một biến True, không có cặp hậu cùng cột/đường chéo, nên mọi mệnh đề đều True.

Bố trí `[(0,0),(1,1),(2,2),(3,3)]` tương ứng `{1,6,11,16}`. Mệnh đề đường chéo `(-1 OR -6)` là False, nên CNF không được thỏa. Thiếu hậu ở một hàng làm mệnh đề at-least-one của hàng đó False.

## Luồng giải và quản lý tài nguyên

`SATNQueensSolver(problem).solve()` sinh CNF, tạo `Glucose3`, nạp CNF bằng `append_formula`, gọi `solve()`, lấy và giải mã model nếu SAT, rồi kiểm tra bằng validator độc lập. Native solver được gọi `delete()` trong `finally`, kể cả khi nạp, giải, giải mã hoặc kiểm tra nghiệm bị lỗi.

| Kết quả | Trạng thái trả về |
| --- | --- |
| `solve()` trả True, model hợp lệ và validator đạt | SAT |
| `solve()` trả False | UNSAT |
| Solver trả unknown (`None`) | LIMIT_REACHED, không kết luận vô nghiệm |
| Exception hoặc model sai/thiếu, lỗi giải phóng solver | ERROR, không mang lời giải |

CLI hiện dùng `solve()` không giới hạn, chưa cung cấp tùy chọn timeout hoặc ngân sách. Nhánh unknown được kiểm tra bằng mock để bảo toàn hợp đồng trạng thái; không tuyên bố đã thực hiện thí nghiệm hết giới hạn. Không tự kết luận UNSAT khi có lỗi hoặc bị ngắt.

Dependency là [python-sat trên PyPI](https://pypi.org/project/python-sat/1.9.dev25/), import từ `pysat.solvers`. Phiên bản hiện ghim `1.9.dev25`; đây là bản phát triển đã được kiểm tra trên môi trường hiện tại. Cách nạp, giải và giải phóng native solver theo [API chính thức PySAT](https://pysathq.github.io/docs/html/api/solvers.html).

## Định nghĩa thời gian và thống kê

Mọi khoảng thời gian đều đo bằng `time.perf_counter()`, đơn vị giây. Đây là thời gian thực trôi qua của tiến trình, không phải thời gian CPU.

| Trường thống kê | Phạm vi |
| --- | --- |
| `num_variables` | N² biến Boolean của encoder, không có biến phụ |
| `clauses_<nhóm>` | Độ dài danh sách mệnh đề thực sự sinh của từng nhóm |
| `clauses_total` | Tổng số mệnh đề CNF đầu vào |
| `cnf_generation_seconds` | Tạo encoder, ánh xạ và nhóm đường chéo, sinh mệnh đề, gom CNF và đếm nhóm |
| `solver_initialization_seconds` | Khởi tạo `Glucose3()` và nạp toàn bộ CNF bằng `append_formula()` |
| `solve_seconds` | Chỉ lời gọi `solver.solve()` |
| `solver_restarts/conflicts/decisions/propagations` | Các bộ đếm thực tế lấy từ `accum_stats()` của Glucose3 |
| `total_seconds` | Từ đầu `SATNQueensSolver.solve()` đến sau `delete()`, trước khi tạo `SolveResult` |

`SolveResult.elapsed_seconds` bằng `total_seconds`. Tổng bao gồm ba pha trên cùng việc đếm/tổ chức thống kê, lấy model, giải mã, kiểm tra nghiệm, xử lý lỗi và giải phóng solver. Tổng không bao gồm import thư viện, tạo/kiểm tra `NQueensProblem`, tạo `SolveResult`, xử lý đối số CLI và in kết quả. Vì có các công việc ngoài ba pha, không yêu cầu tổng bằng đúng tổng ba thời gian pha.

Nếu một pha có lỗi, vẫn đo thời gian đã thực sự trôi qua của pha đó; pha chưa bắt đầu không có khóa thời gian. Không điền số 0 thay cho phép đo chưa thực hiện. CLI in 9 chữ số thập phân, không có nghĩa đồng hồ có độ chính xác tuyệt đối đến nano giây. Không dùng một lần chạy smoke test để kết luận hiệu năng hay khả năng mở rộng.

## Chạy và kiểm tra

Từ gốc repository, sau khi cài dependency trong môi trường ảo:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m source.task1_nqueens 4
.\.venv\Scripts\python.exe -m source.task1_nqueens 8
.\.venv\Scripts\python.exe -m unittest discover -s tests -t . -v
```

Exit code: 0 cho SAT/UNSAT; 1 cho ERROR; 2 cho lỗi đối số; 3 cho LIMIT_REACHED. Mỗi lần chạy CLI in trạng thái, số đếm, thời gian và bộ đếm solver; chỉ SAT mới in tọa độ và bàn cờ.

Kiểm thử gồm ánh xạ khứ hồi, model có dấu, số đếm N=1..12, chính xác tập mệnh đề N=4 không có ràng buộc dư, nghiệm đúng/bố trí sai, đánh giá mọi phép gán Boolean cho N=1..3 đối chiếu validator, Glucose3 thực cho N=1,2,3,4,8, CLI và các đường lỗi/cleanup. Các tình huống lỗi/unknown dùng mock, được phân biệt với kiểm tra tích hợp thật.
