# Min-Conflicts cơ sở cho N-Queens

## Biểu diễn và các lớp

`MinConflictsBoard` giữ vector `rows[column] = row`, có đúng N phần tử nguyên từ 0 đến N−1. Mỗi cột luôn có đúng một hậu; hàng có thể lặp. Đây không phải vector cột theo từng hàng. Khi trả lời giải cho `SolutionValidator` và hiển thị, chuyển sang tọa độ `(rows[column], column)`.

`MinConflictsSolver(problem, seed=None, max_steps=10000, initial_state=None)` nhận cấu hình, kiểm tra rồi sao chép trạng thái khởi tạo tùy chọn để không sửa dữ liệu của người gọi. `max_steps` phải là số nguyên không âm, seed là số nguyên hoặc None; không chấp nhận bool. Trạng thái khởi tạo sai kích thước/kiểu/phạm vi bị từ chối trước khi tìm kiếm.

Mỗi lần `solve()` tạo một `random.Random(seed)` riêng. Nếu không có `initial_state`, thực hiện N lần `randrange(N)` độc lập để chọn hàng cho từng cột; không khởi tạo bằng hoán vị. Nếu có trạng thái, dùng nguyên trạng thái đó, không tiêu thụ các lần rút số để khởi tạo hàng. Không đọc hoặc thay đổi global random. Seed None dùng nguồn khởi tạo hệ thống, không hứa tái lập; seed cố định và cùng cấu hình/phiên bản Python tái lập lựa chọn và kết quả, không tái lập thời gian đo.

## Đếm xung đột và loại chính quân đang xét

Board duy trì số quân trên từng hàng, đường chéo `row−column` và đường chéo `row+column`. Với quân tại cột c đang xét hàng r:

```text
score(c,r) = row_count[r]
           + descending_count[r-c]
           + ascending_count[r+c]
           - (3 nếu r == rows[c], ngược lại 0)
```

Chỉ số mảng đường chéo xuống phải trong mã được dịch thêm N−1 để không âm. Khi xét hàng hiện tại, chính hậu đó xuất hiện trong cả ba bộ đếm, nên trừ 3. Khi xét hàng khác trong cùng cột, chính hậu cũ không nằm trên hàng hoặc hai đường chéo của ô ứng viên, nên không trừ. Hai hậu ở hai cột khác nhau không thể cùng chia sẻ hơn một trong ba đường này, vì vậy không đếm lặp một quân đối thủ.

`conflicts(c)` trả số quân khác tấn công quân hiện tại. `conflicted_columns()` chỉ chứa các cột có điểm dương. `conflicting_pairs` là tổng điểm của các quân chia 2; mỗi cặp tấn công được đếm từ cả hai phía. Một lần chấm điểm và cập nhật các bộ đếm mất O(1); chọn quân xung đột và chấm mọi hàng mất O(N) mỗi bước, bộ nhớ trạng thái O(N). Các bộ đếm không thay đổi quy tắc chọn của thuật toán cơ sở.

## Vòng lặp và ngân sách

1. Khởi tạo trạng thái và RNG riêng.
2. Kiểm tra các quân xung đột. Nếu không có, chuyển sang tọa độ và gọi validator độc lập; chỉ trả SAT khi validator đạt.
3. Nếu đã dùng hết `max_steps`, trả LIMIT_REACHED, không có lời giải; không kết luận UNSAT.
4. Chọn đều ngẫu nhiên một cột trong các quân đang xung đột.
5. Đánh giá tất cả N hàng của cột, kể cả hàng hiện tại, không đếm chính hậu đang xét.
6. Chọn đều ngẫu nhiên một hàng trong mọi hàng có điểm thấp nhất và cập nhật trạng thái.
7. Tính một bước rồi quay lại kiểm tra trạng thái ở bước 2.

**Một bước** là một lần chọn quân, đánh giá mọi hàng, phá hòa và thực hiện phép gán hàng. Nếu chọn lại hàng hiện tại, vẫn tính một bước. `steps` đếm các phép gán; `moves` chỉ đếm các phép gán làm đổi hàng. Chấp nhận bước không đổi hàng khi hàng hiện tại cũng đạt điểm thấp nhất, không loại nó khỏi tập phá hòa.

Kiểm tra trạng thái diễn ra trước bước đầu và ngay sau mọi cập nhật, kể cả lần cập nhật thứ `max_steps`. Vì vậy nghiệm hình thành ở bước cuối vẫn được nhận. Với `max_steps=0`, trạng thái đầu hợp lệ trả SAT với steps=0; trạng thái đầu có xung đột trả LIMIT_REACHED với steps=0. N=2/3 cũng chỉ trả LIMIT_REACHED khi hết bước; phương pháp này không chứng minh vô nghiệm.

Không có restart, không chọn quân xung đột nhiều nhất, không khởi tạo tham lam, không thêm heuristic phá hòa. Nếu validator phát hiện lỗi ở ứng viên không còn xung đột theo bộ đếm, trả ERROR và không mang lời giải. Exception khi chạy cũng trả ERROR; lỗi cấu hình được báo trước khi tìm kiếm.

## Ví dụ một vòng lặp N=4

Xét `rows = (1,3,0,0)`: hậu ở `(1,0), (3,1), (0,2), (0,3)`. Chỉ hai hậu cột 2 và 3 cùng hàng, nên có một cặp xung đột. Ví dụ chọn ngẫu nhiên cột 3. Điểm khi chuyển hậu của cột này:

| Hàng ứng viên | Số quân khác xung đột | Giải thích |
| --- | ---: | --- |
| 0 | 1 | Cùng hàng với hậu cột 2; đã loại chính hậu cột 3 |
| 1 | 3 | Cùng hàng với cột 0, chéo với cột 1 và cột 2 |
| 2 | 0 | Không tấn công quân khác |
| 3 | 1 | Cùng hàng với hậu cột 1 |

Hàng tối ưu duy nhất là 2. Cập nhật thành `(1,3,0,2)`, steps=1 và moves=1. Kiểm tra lại không còn xung đột, validator xác nhận tọa độ `((1,0),(3,1),(0,2),(2,3))`, rồi trả SAT, ngay cả khi max_steps=1.

```text
. . Q .
Q . . .
. . . Q
. Q . .
```

Đây là ví dụ giải thích thuật toán, không phải số liệu benchmark. Với Python 3.12.10 và seed=0, trạng thái đầu trên tái hiện đúng lần chọn cột 3 trong kiểm thử.

## Thống kê và trạng thái

Kết quả dùng chung `SolveResult`. Thống kê gồm seed (`system` nếu None), max_steps, steps, moves, số cặp xung đột đầu/cuối và chuỗi vector trạng thái đầu/cuối. `final_state` chỉ là dữ liệu chẩn đoán; khi LIMIT_REACHED nó không phải lời giải và `solution` vẫn là None. Trường cuối có thể không tồn tại nếu xảy ra lỗi trước khi thu thập được.

`total_seconds` bằng `elapsed_seconds`, đo bằng `time.perf_counter()` từ đầu `solve()` đến sau thu thập thống kê và kiểm tra nghiệm, trước khi tạo `SolveResult`. Bao gồm tạo RNG, khởi tạo board, các bước tìm kiếm và validator; không gồm kiểm tra cấu hình constructor, import hoặc in CLI. Chỉ có số đo thực tế, không dùng thời gian từ fixture.

## Lệnh chạy

Từ gốc repository, dùng môi trường ảo đã cài dependency chung của Task 1. SAT vẫn là phương pháp mặc định, các tùy chọn Min-Conflicts chỉ hợp lệ khi chọn đúng phương pháp.

```powershell
# Khởi tạo ngẫu nhiên, có seed, không restart
.\.venv\Scripts\python.exe -m source.task1_nqueens 8 --method min-conflicts --seed 42 --max-steps 1000

# Tái hiện vòng lặp N=4 nêu trên
.\.venv\Scripts\python.exe -m source.task1_nqueens 4 --method min-conflicts --seed 0 --max-steps 1 --initial-state 1,3,0,0

# Không được di chuyển: trả LIMIT_REACHED và exit code 3
.\.venv\Scripts\python.exe -m source.task1_nqueens 4 --method min-conflicts --max-steps 0 --initial-state 0,0,0,0

# Toàn bộ kiểm thử Task 1
.\.venv\Scripts\python.exe -m unittest discover -s tests -t . -v
```

Trên macOS/Linux, thay executable bằng `.venv/bin/python`. Exit code giữ nguyên quy ước chung: 0 cho SAT/UNSAT, 1 cho ERROR, 2 cho lỗi đối số, 3 cho LIMIT_REACHED. Min-Conflicts không trả UNSAT.

Kiểm thử đối chiếu các bộ đếm với cách đếm trực tiếp trên mọi trạng thái N=3 và sau các cập nhật; kiểm tra ví dụ thủ công N=4, không đếm chính hậu, tái lập seed, độc lập global random, khởi tạo ngẫu nhiên độc lập, đầu vào sai, bước không đổi hàng, không restart, giới hạn 0, nghiệm ở bước cuối, validator từ chối và CLI. Mock chỉ dùng để kiểm soát lựa chọn hoặc tiêm lỗi; không coi mock là thí nghiệm thực tế.
