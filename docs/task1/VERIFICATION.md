# Xác minh Task 1 trước PR

Ngày kiểm tra: 26/11/2026. Kết luận: **đủ điều kiện kỹ thuật để tạo PR cho Task 1**.
Chưa tạo PR, push hoặc merge. Nghiệm thu môn học/gói nộp cuối là bước riêng.

## Git và phiên bản được kiểm tra

Đã chạy `git status --short --branch`, `git remote -v`, `git branch --show-current`,
`git log -8 --oneline`, `git worktree list`, `git rev-parse HEAD`,
`git merge-base HEAD origin/main` và `git diff --check`.

- Nhánh đầu phiên và nhánh tiếp tục: `feature/task1-nqueens`. Không đổi tên hoặc chuyển nhánh.
- Origin fetch/push: `https://github.com/njade15/CK_AI.git`.
- HEAD trước rà soát: `101e83b7000be60eaad2375edbb56ae4433cc32e` (dữ liệu/phân tích).
- Mã benchmark chính thức: `2781502d6e92eefda54fdb6c772c8d65a40c0330`.
- Commit gốc/merge-base với origin/main hiện có: `d55dcddbfb96ab6a8a0808279bd0c9b5bb2ecbf6`.
- Working tree đầu phiên sạch, một worktree hiện tại. Không có thay đổi người dùng cần di chuyển.
- Lịch sử Task 1: nền tảng `d2ae416`, SAT `f7c70cd`, baseline `e324472`,
  heuristic `65717c1`, benchmark `2781502`, dữ liệu `101e83b`.

Kiểm tra lại trên nền `101e83b` cùng các thay đổi review trong commit chứa tài liệu này.
Lấy hash commit review sau checkout bằng:

```sh
git log -1 --format=%H -- docs/task1/VERIFICATION.md
```

Không fetch trong giai đoạn này; trạng thái origin/main là remote-tracking ref tại máy,
không phải xác nhận GitHub không có commit mới. Không sửa Task 2/3, không reset hoặc xóa dữ liệu cũ.

## Môi trường sạch và dependency

Windows 11 `Windows-11-10.0.26200-SP0`, AMD64, Intel Core i7-14650HX, 24 CPU logic.
CPython 3.12.10, MSC v.1943 64 bit. Môi trường ảo mới tạo trong thư mục tạm,
không tái sử dụng `.venv` của repository. Các lệnh thực tế chạy từ gốc repository:

```powershell
$reviewRoot = 'C:\Users\Admin\AppData\Local\Temp\vscode-agent-codex-sandbox-qJXnGg\nqueens-review-20261126'
# Đích chưa tồn tại khi bắt đầu. Không dùng lại đích này để tạo môi trường "sạch" lần sau.
& 'C:\Users\Admin\AppData\Local\Programs\Python\Python312\python.exe' -m venv "$reviewRoot\venv"
$python = Join-Path $reviewRoot 'venv\Scripts\python.exe'
& $python -m pip install -r requirements-benchmark.txt
& $python -m pip check
& $python -m unittest discover -s tests -t . -v
```

`requirements-benchmark.txt` bao gồm `-r requirements.txt`, nên cài cả dependency runtime theo README.
Cài đặt thành công. `pip check`: **No broken requirements found**.
92 test gốc chạy lại đạt trong 3,048 s. Sau bổ sung review: **105 test đạt**, lần chạy 3,162 s.
Thời gian chạy test là quan sát của phiên kiểm tra, không phải benchmark thuật toán.

| Gói | Phiên bản thực cài |
| --- | --- |
| python-sat | 1.9.dev25 |
| matplotlib | 3.11.2 |
| pip | 25.0.1 |
| contourpy | 1.4.0 |
| cycler | 0.12.1 |
| fonttools | 4.69.1 |
| kiwisolver | 1.5.1 |
| numpy | 2.5.5 |
| packaging | 26.4 |
| pillow | 13.0.0 |
| pyparsing | 3.3.3 |
| python-dateutil | 4.0.0 |
| six | 1.17.0 |
| tzdata | 2026.6 |

Không đưa venv/cache vào Git. `.gitignore` đã bao phủ `.venv/`, `__pycache__/`,
các cache và các mẫu credential; venv review nằm ngoài repository. Chỉ kiểm tra thay đổi
được stage trong phiên này, không tuyên bố đã thực hiện kiểm toán bí mật toàn lịch sử Git.

## Rà soát mô hình, thuật toán và OOP

Đã đọc mã nguồn và tests Task 1, [MODEL.md](MODEL.md), [MIN_CONFLICTS.md](MIN_CONFLICTS.md)
và [BENCHMARK.md](BENCHMARK.md), đối chiếu các yêu cầu được giao trong hội thoại.

- Logic mệnh đề: biến Boolean cho từng ô, tọa độ từ 0, `id=r*N+c+1`, không biến phụ.
  Mỗi hàng có một mệnh đề OR tồn tại và các cặp phủ định để có tối đa một hậu.
  Cột và hai họ đường chéo chỉ dùng cặp phủ định. Không cần OR cho cột:
  N hậu ở N hàng, cùng cột tối đa một, suy ra mỗi cột đúng một hậu.
- Encoder đếm danh sách thực sinh. Công thức tổng
  `N + N²(N−1) + N(N−1)(2N−1)/3` khớp, N=4 có 16 biến và 80 mệnh đề
  (4/24/24/14/14 theo năm nhóm). Các N benchmark có 80/736/6336/52608/428800 mệnh đề.
  Tests so sánh độc lập tập cặp tấn công N=4 và mọi phép gán Boolean N=1..3.
- Adapter dùng `pysat.solvers.Glucose3` từ gói `python-sat`; có decode đầy đủ,
  validator tọa độ độc lập và `delete()` trong finally, cả khi nạp/solve/validator lỗi.
  False là UNSAT, unknown là LIMIT_REACHED, exception/model sai là ERROR.
- Min-Conflicts giữ `rows[column]=row`; khởi tạo các hàng độc lập, RNG riêng,
  loại self khỏi ba bộ đếm. Chọn quân xung đột, đánh giá mọi hàng, phá hòa ngẫu nhiên.
  Một bước là một phép gán kể cả giữ nguyên hàng. Kiểm tra trạng thái đầu và sau bước cuối.
  max_steps=0 rõ ràng, hết bước là LIMIT_REACHED; không restart hoặc suy ra UNSAT.
- RandomConflictedSelector và MaxConflictedSelector chỉ khác chọn biến, cùng vòng lặp,
  chấm hàng/phá hòa, khởi tạo, giới hạn. Vector đầu được sao chép; không sửa dữ liệu cặp.
  Tests kiểm tra cực đại duy nhất/hòa, counter so với đếm trực tiếp, seed/RNG,
  baseline đã ghi và validator từ chối nghiệm sai cho cả hai chiến lược.
- OOP phân vai Problem/Result, Encoder/CNF, SAT adapter, MC Board/Solver/Selectors,
  Validator và hiển thị. Benchmark/phân tích là hàm điều phối, không nhân đôi thuật toán.

## Review riêng thay đổi SAT khi thêm benchmark

Lệnh: `git diff 65717c1 2781502 -- source/task1_nqueens/sat_solver.py`.
Diff chỉ thêm import kiểu, tham số `progress=None` và ba lần gọi callback với bản sao
statistics sau sinh CNF, nạp solver và solve. Không đổi CNF, lời gọi native, decode,
validator, cleanup hoặc phân loại trạng thái. Không có thay đổi SAT từ `2781502` đến `101e83b`.

Callback nằm ngoài ba phép đo pha, nhưng nằm trong tổng solver. Tổng benchmark SAT
do đó bao gồm callback/IPC; CLI gọi không callback. `perf_counter` đo thời gian trôi qua,
không phải CPU time. Tổng tính đến sau cleanup, trước đóng gói SolveResult, không gồm
spawn/import/CLI; parent wall bao gồm các phần đó và teardown.

Đã thêm hai test hồi quy: kết quả SAT/UNSAT, nghiệm, snapshot độc lập và phạm vi pha
khi bật callback; exception callback sau nạp phải ERROR và giải phóng native solver.
Không đòi thời gian hai lần chạy bằng nhau. CLI thật cũng đã chạy lại như bảng dưới.
Không sửa `sat_solver.py`, encoder, MC hoặc benchmark runner trong giai đoạn review.

## Review .gitattributes và checksum

Tệp chỉ có một dòng chú thích (không tác động) và một quy tắc:

```gitattributes
results/task1/** -text whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol
```

| Thành phần | Ý nghĩa và phạm vi |
| --- | --- |
| `results/task1/**` | Mọi tệp trong cây results/task1 ở mọi độ sâu, kể cả PNG, dữ liệu và tệp kết quả thêm về sau. Không áp dụng source, tests, docs hoặc các đường dẫn khác. |
| `-text` | Tắt chuyển đổi LF/CRLF của Git cho các tệp khớp, bảo toàn byte/checksum khi add/checkout. Không tự tắt diff hoặc kiểm tra whitespace. |
| `whitespace=...` | Ghi đè danh sách kiểm tra whitespace cho riêng các đường dẫn khớp. Không sửa core.whitespace toàn repository. |
| `blank-at-eol` | Phát hiện khoảng trắng thừa cuối dòng. |
| `blank-at-eof` | Phát hiện dòng trắng thừa cuối tệp. |
| `space-before-tab` | Phát hiện dấu cách đứng ngay trước tab trong phần thụt đầu dòng. |
| `cr-at-eol` | Xem CR trước LF là phần kết thúc dòng, không tự coi CR của CRLF hợp lệ là khoảng trắng thừa. Dấu cách/tab thừa trước CR vẫn bị kiểm tra. |

Đã chạy `git check-attr text whitespace -- results/task1/main-20261126/trials.csv source/task1_nqueens/sat_solver.py docs/task1/MODEL.md`:
CSV là text unset và có đúng danh sách trên; source/docs đều unspecified, giữ cơ chế mặc định.
`git config --show-origin --get core.whitespace` không có giá trị (exit 1, không phải lỗi kiểm thử).
Không sửa `.gitattributes` hoặc cấu hình Git trong phiên này.

Đã tạo Git repository fixture ở thư mục tạm với cùng attributes, stage ba tệp rồi chạy
`git diff --cached --check -- <tệp>`: trailing space ngoài results exit 2, trailing space
trong results dùng CRLF cũng exit 2, CRLF thuần hợp lệ exit 0. Vì vậy kiểm tra khoảng trắng
vẫn hoạt động cả trong và ngoài phạm vi. Fixture không nằm trong dữ liệu thí nghiệm.

SHA256 của **19 tệp** trong manifest main/smoke đều khớp cả byte working tree và
`git show 101e83b:<đường-dẫn>` (đọc blob bằng Python subprocess ở chế độ bytes).
Không tính chính manifest vào manifest của nó. SHA256 trials chính thức:
`9d6892a903a07fb932b9d40d8f72de9d897ab70cafc8a89c013a6d327058a9a1`.

## Dữ liệu và tái tạo phân tích

Đúng 325 lượt chính thức = 25 SAT + 300 MC. 25 SAT có nghiệm hợp lệ;
MC có 293 SAT hợp lệ và 7 LIMIT_REACHED, mọi lượt hết bước đều ghi 5000 bước.
Không có TIMEOUT/ERROR/NOT_RUN trong lượt chính thức. Giữ nguyên các seed thất bại:
max N=8: 1,6,16; max N=16: 8,19; random N=16: 14,28. Không diễn giải thành vô nghiệm.

150 cặp MC khớp kế hoạch Random(seed), trạng thái đầu, seed, N, max_steps=5000,
timeout=5 s và không restart. Thứ tự chiến lược luân phiên theo repeat. SAT có 5 lượt/N,
timeout=15 s; tổng budget 600 s. Metadata ghi commit `2781502`, dirty=false tại đầu lượt chính thức.
Smoke riêng 10 lượt, dirty=true tại commit cha, đã được công bố trong README kết quả.

Đã dùng `shutil.copytree` sao chép toàn bộ main/smoke sang `$reviewRoot` rồi gọi
`benchmark_analysis.analyze()` trên từng bản sao. Kết quả audit 325 và 10 lượt đạt.
So sánh bytes mọi tệp với bản gốc: **không có khác biệt**, bao gồm summary.csv,
audit.json, REPORT.md, ba PNG và SHA256SUMS.txt. ANALYSIS.md được sao chép nguyên trạng.
Đã mở xem ba PNG chính thức tái tạo: đơn vị giây/bước/%, chú thích và nguồn rõ ràng;
SAT chỉ vẽ solve, MC vẽ tổng thuật toán, chi phí wall riêng. Sáu PNG main/smoke đều byte-identical.

Tests mới đối chiếu từng trường summary với CSV; mọi ô số của 5 hàng SAT, 5 hàng MC và
3 hàng seed thất bại trong ANALYSIS với raw CSV. Đã đọc lại diễn giải và đối chiếu các
tổng chi phí N=8/N=16, số mẫu, thời gian phiên chạy và giới hạn từ summary/metadata.
Không tìm thấy sai lệch dữ liệu, bảng hoặc biểu đồ; không loại lượt bất lợi.

Lệnh tái tạo an toàn cho PowerShell/macOS/Linux trong [BENCHMARK.md](BENCHMARK.md).
Analyzer ghi tại đích nên chỉ chạy trên bản sao tạm khi xác minh.

## Phân tích ghép cặp bổ sung

[paired-20261126](../../results/task1/paired-20261126/REPORT.md) giữ riêng 150 cặp cùng seed,
với trạng thái cả hai chiến lược, kể cả các cặp bị loại khỏi tập cùng thành công.
Số cặp cùng thành công theo N=4/8/16/32/64 là **30/27/26/30/30**.
Chỉ trên tập này, tính từng hiệu `max - random`, sau đó lấy trung vị; không lấy hiệu hai trung vị.
Không sửa REPORT/ANALYSIS/summary gốc, không chạy lại solver, không thay thống kê toàn bộ lượt.

Ví dụ N=32: hai median riêng là 79,5 và 76,5 bước nhưng median hiệu từng cặp là **+8 bước**,
median hiệu thời gian **+0,0003417 s**. Đây là hai phép thống kê khác nhau, không mâu thuẫn.
N=16 dùng 26 cặp chung, thay vì so hai tập 28 thành công không trùng nhau.
Không kiểm định ý nghĩa thống kê hay tuyên bố ưu thế tổng quát. CSV giữ full precision;
báo cáo hiển thị 6 chữ số có nghĩa. Provenance ghi hash ba đầu vào và mã phân tích,
manifest mới có bốn tệp và đã được kiểm tra; các manifest cũ giữ nguyên.

Lệnh đã chạy: `python -m source.task1_nqueens.paired_analysis results/task1/main-20261126 results/task1/paired-20261126`.
Cũng chạy trên đích tạm ở ổ C trong khi nguồn ở ổ D; đã xử lý link khác ổ đĩa.
Test xác nhận đích tồn tại bị từ chối và không đổi nội dung.

## Smoke CLI thực tế

Dùng `$python` của venv sạch; mỗi lệnh chạy qua subprocess với timeout 30 s,
đối chiếu exit code, dòng Status và chỉ có tọa độ/bàn cờ ở SAT.

| Phần sau `& $python -m source.task1_nqueens` | Kết quả | Exit |
| --- | --- | --- |
| `4` | SAT | 0 |
| `8` | SAT | 0 |
| `2` | UNSAT | 0 |
| `3` | UNSAT | 0 |
| `8 --method min-conflicts --strategy random_conflicted --seed 42 --max-steps 1000` | SAT | 0 |
| `8 --method min-conflicts --strategy max_conflicted --seed 42 --max-steps 1000` | SAT | 0 |
| `4 --method min-conflicts --max-steps 0 --initial-state 0,0,0,0` | LIMIT_REACHED, không in nghiệm | 3 |

Test deadline thật tiếp tục đạt: worker sleep 10 s bị dừng theo deadline 2 s,
giữ snapshot, wall dưới 6 s, không còn child process. Nhánh native unknown/lỗi dùng mock,
không tuyên bố đã làm Glucose3 thật timeout với dữ liệu N nhỏ.

## Lỗi, sửa chữa và ảnh hưởng dữ liệu

1. Audit cũ bỏ qua số đếm trống, chưa buộc lượt hoàn tất phải có đủ phép đo,
   chưa kiểm tra effective timeout, tổng pha SAT và đủ bước khi MC báo LIMIT_REACHED.
   Bổ sung các guard cùng hai test âm; dữ liệu cũ đều qua audit chặt hơn.
2. Thiếu hồi quy trực tiếp callback SAT: thêm hai test, không sửa solver.
3. README Task 1 còn nói chưa có số liệu benchmark: sửa, bổ sung liên kết kết quả và
   phân biệt hướng dẫn PowerShell đã kiểm chứng với macOS/Linux dự kiến.
4. Hướng dẫn analyzer có thể khiến người dùng ghi lại báo cáo chính thức khi chỉ muốn
   xác minh: thay bằng quy trình sao chép tạm; bổ sung hướng dẫn benchmark macOS/Linux.
5. Bổ sung phân tích ghép cặp, bốn test tính toán/loại cặp và một test I/O không ghi đè,
   cùng bốn test dữ liệu đã lưu. Khi kiểm tra module mới, đã xử lý đường dẫn khác ổ Windows.

Chỉ sửa mã **audit/phân tích**, tests và tài liệu; không sửa thuật toán, runner,
đồng hồ hoặc ranh giới đo. Số liệu cũ vẫn mô tả commit `2781502`, không gắn lại cho mã mới.
Tái tạo kết quả dẫn xuất khớp từng byte, nên không cần chạy lại benchmark bị ảnh hưởng.
105 = 92 cũ + 2 callback + 2 audit + 5 paired + 4 recorded-data tests.

## Giới hạn và bước tiếp theo

- Chỉ thực chạy Windows 11/CPython 3.12.10; chưa chạy macOS, Linux, Python khác hoặc
  môi trường macOS của môn học. Dependency native trên các môi trường đó chưa xác nhận.
- Gói trực tiếp được ghim, các dependency bắc cầu chưa có lockfile toàn bộ; đã ghi chính xác
  các phiên bản cài trong phiên này. Hiệu năng không thể tái tạo từng con số do tải/OS/IPC.
- Không chạy lại 325 phép đo hay mở rộng N/seed; giữ dữ liệu gốc. Chỉ smoke chức năng,
  test timeout và tái tính phân tích. Chưa đo tách riêng chi phí selector hoặc thêm restart.
- Chưa nghiệm thu lại toàn bộ PDF đề, định dạng báo cáo/gói nộp và tiêu chí chấm cuối.
  Đây là xác minh kỹ thuật theo các yêu cầu Task 1 đã nêu trong hội thoại.
- Có thể tạo PR để người phụ trách review Task 1. Chưa được coi là phê duyệt merge cuối.
