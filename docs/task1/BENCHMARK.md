# Benchmark tái hiện Task 1

## Cấu hình công bố trước lượt chính thức

[benchmark_full.json](benchmark_full.json) cố định SAT N=4,8,16,32,64 với 5 lượt/N, timeout 15 s/lượt; Min-Conflicts cùng N, 30 seed 0..29/N/chiến lược, max_steps=5000, timeout 5 s/lượt, không restart. Tổng 325 lượt, chạy tuần tự một worker; ngân sách toàn bộ vòng chạy 600 s, không gồm thu thập metadata/vẽ biểu đồ. Không thay cấu hình theo kết quả.

[benchmark_smoke.json](benchmark_smoke.json) là kiểm tra pipeline riêng: SAT N=4,8 mỗi N một lượt; MC N=4,8 với hai seed/chiến lược và max_steps=100. Không gộp smoke vào dữ liệu chính thức. Chạy và kiểm tra smoke trước, sau đó commit mã và cấu hình trước khi chạy chính thức. Commit dữ liệu/phân tích sau khi audit đạt.

## Phạm vi đo và timeout

`benchmark.py` tạo tiến trình con bằng multiprocessing spawn cho mỗi lượt. Parent đo deadline từ trước spawn đến khi nhận kết quả. Hết hạn gọi terminate, join tối đa 1 s, rồi kill và join tối đa 1 s nếu cần. Đây là giới hạn thực thi được cả khi native Glucose3 chưa trả về, không phải kiểm tra timeout sau solve. Độ trễ hệ điều hành và teardown có thể làm wall quan sát vượt deadline. Lượt worker không trả kết quả là ERROR; hết deadline là TIMEOUT, không phải UNSAT.

SAT gửi snapshot số đếm và thời gian sau từng pha hoàn tất. Khi timeout, chỉ giữ phép đo đã nhận; pha bị ngắt để trống. Với progress callback, tổng SAT tính cả chi phí gửi snapshot ngoài các khoảng pha; từng pha sinh CNF/tạo-nạp/solve vẫn đo riêng bằng perf_counter. Tổng thuật toán không gồm spawn/import/CLI; các phạm vi chi tiết khác theo [MODEL.md](MODEL.md).

Biểu đồ dùng trục N theo log cơ số 2 với nhãn N thực tế, phù hợp tập kích thước tăng gấp đôi; trục thời gian và số bước giữ đơn vị ghi trên từng panel.

`observed_wall_seconds` là thời gian parent quan sát từ trước spawn đến sau teardown, gồm startup/import/IPC và cả lượt lỗi/timeout. Đây là chi phí thực thi toàn lượt, không thay cho solve_seconds hay algorithm_total_seconds. Không suy đoán tổng thuật toán của lượt bị kill. MC total dùng nguyên phép đo của solver, bao gồm chọn biến. Khi bị timeout MC chưa trả được bộ đếm bước thì để trống, không điền max_steps.

Mỗi trạng thái MC được tạo một lần bằng Random(seed), sao chép cho hai bản; mỗi solver có RNG riêng với cùng seed. Thứ tự random/max luân phiên theo lượt để giảm lệch do thứ tự cố định. Mọi nghiệm SAT được kiểm tra bằng validator trong solver và lại kiểm tra ở parent; nghiệm sai được ghi ERROR với solver_status gốc. Không loại lượt thất bại. Nếu hết ngân sách toàn phiên, vẫn tạo dòng NOT_RUN cho mọi lượt chưa thực hiện, kèm lý do.

## Đầu ra và nguồn gốc

Mỗi thư mục kết quả mới gồm trials.csv, config.json, metadata.json, audit.json, summary.csv, REPORT.md, sat.png, min_conflicts.png, costs.png và SHA256SUMS.txt. Không ghi đè thư mục cũ. CSV flush sau từng lượt để giữ các dòng đã hoàn tất nếu phiên chạy bị ngắt; audit không cho thiếu dòng so với kế hoạch.

Metadata ghi commit, nhánh, working tree dirty và danh sách thay đổi tại thời điểm bắt đầu, trước khi tạo thư mục đầu ra; Python, phiên bản mọi package trong venv, OS, CPU nếu lấy được, số CPU logic và thời điểm UTC. Mã từ chối chạy với working tree dirty trừ khi chỉ định `--allow-dirty` cho smoke. Thư mục dữ liệu mới tự làm checkout dirty sau khi chạy; không làm sai snapshot trước khi chạy. Không thu thập biến môi trường hoặc thông tin đăng nhập.

SAT tổng hợp số mệnh đề và trung vị solve theo N, kèm số mẫu phép đo hoàn tất và số timeout/lỗi/chưa chạy. MC tổng hợp tỷ lệ SAT hợp lệ/tổng lượt được lên kế hoạch, tỷ lệ trên lượt thực thi cũng có trong summary.csv; trung vị bước/thời gian trên lượt thành công và số mẫu. Không thành công thì median là ô trống trong CSV và N/A trong báo cáo.

Chi phí toàn bộ báo tổng/mean/median wall trên mọi lượt đã thực thi, cả thất bại. Tổng bước đã ghi và tổng thời gian thuật toán hoàn tất đi kèm số mẫu có dữ liệu; không coi thiếu là 0. Biểu đồ SAT solve và MC total riêng biệt, có đơn vị, chú thích và nguồn trials.csv → summary.csv. Các kết quả thành công có điều kiện phải đọc cùng tỷ lệ thành công và chi phí thất bại, không chỉ chọn số có lợi.

## Lệnh chạy

Từ thư mục gốc repository. PowerShell đã kiểm chứng trên Windows 11/Python 3.12.10.
Không kích hoạt venv nên không cần đổi ExecutionPolicy. Dùng thư mục mới cho mỗi lần chạy.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-benchmark.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -t . -v

# Smoke: chỉ cho phép dirty ở bước phát triển pipeline; dùng thư mục mới.
.\.venv\Scripts\python.exe -m source.task1_nqueens.benchmark --config docs/task1/benchmark_smoke.json --output results/task1/smoke-new --allow-dirty

# Sau khi commit mã, đảm bảo working tree sạch rồi mới chạy chính thức.
.\.venv\Scripts\python.exe -m source.task1_nqueens.benchmark --config docs/task1/benchmark_full.json --output results/task1/main-new

# Audit và vẽ lại bản SAO tạm; analyzer ghi kết quả vào thư mục được truyền vào.
# Không truyền thư mục dữ liệu chính thức khi chỉ muốn xác minh.
$analysisDir = Join-Path ([IO.Path]::GetTempPath()) ("nqueens-analysis-" + [guid]::NewGuid())
Copy-Item -LiteralPath results/task1/main-20261126 -Destination $analysisDir -Recurse
.\.venv\Scripts\python.exe -m source.task1_nqueens.benchmark_analysis $analysisDir
$pairedDir = Join-Path ([IO.Path]::GetTempPath()) ("nqueens-paired-" + [guid]::NewGuid())
.\.venv\Scripts\python.exe -m source.task1_nqueens.paired_analysis $analysisDir $pairedDir
```

macOS/Linux: hướng dẫn dự kiến, chưa được chạy trên hai hệ điều hành này.
Cần Python 3.10 trở lên và cài được wheel/build native của `python-sat` tương ứng.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-benchmark.txt
.venv/bin/python -m pip check
.venv/bin/python -m unittest discover -s tests -t . -v
.venv/bin/python -m source.task1_nqueens.benchmark --config docs/task1/benchmark_smoke.json --output results/task1/smoke-new --allow-dirty
# Chỉ chạy chính thức sau khi mã được commit và working tree sạch.
.venv/bin/python -m source.task1_nqueens.benchmark --config docs/task1/benchmark_full.json --output results/task1/main-new
analysis_dir=$(mktemp -d)
cp -R results/task1/main-20261126/. "$analysis_dir/"
.venv/bin/python -m source.task1_nqueens.benchmark_analysis "$analysis_dir"
# paired_analysis yêu cầu đích chưa tồn tại; dùng đường dẫn con mới.
.venv/bin/python -m source.task1_nqueens.paired_analysis "$analysis_dir" "$analysis_dir/paired"
```

Phân tích ghép cặp là phần bổ sung: [báo cáo](../../results/task1/paired-20261126/REPORT.md),
[mọi cặp và trạng thái loại khỏi tập cùng thành công](../../results/task1/paired-20261126/pairs.csv).
Chênh lệch được tính từng cặp `max - random`, rồi lấy trung vị; không lấy hiệu hai trung vị thay thế.
Các thống kê thành công có điều kiện này không thay cho tỷ lệ thành công và chi phí toàn bộ lượt.
Không chạy lại solver hoặc sửa dữ liệu gốc. Audit trước khi phân tích cũng yêu cầu đủ số đếm,
phép đo cho lượt hoàn tất, tổng pha SAT không vượt tổng thuật toán và ngân sách hợp lệ.

Kết quả kiểm chứng thực tế, checksum và giới hạn môi trường ở [VERIFICATION.md](VERIFICATION.md).

Với smoke trong quá trình phát triển, có thể dùng đường dẫn tạm ngoài repository để không làm dirty checkout trước lượt chính thức. Sao lưu smoke riêng sau khi lượt chính thức đã ghi snapshot clean. Thời gian không tái lập từng giá trị do nhiễu OS; cấu hình, seed, trạng thái đầu và mã nguồn tái lập được. Chỉ mô tả dữ liệu đo, không ngoại suy từ một máy, một tập seed hoặc các trung vị có điều kiện. Chưa cam kết tương đương hiệu năng trên macOS/Linux.
