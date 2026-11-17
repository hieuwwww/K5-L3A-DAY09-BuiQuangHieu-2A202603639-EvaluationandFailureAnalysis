# Ledger + evaluation — hướng dẫn cho thành viên phụ trách

Vai thứ tư trong `TEAM.md` phụ trách **kiểm chứng ledger và đánh giá**, không sửa
`lab8/durability.py`, `lab8/policy.py`, `lab8/metrics.py`, config hay dữ liệu.

1. Thêm hoặc sửa test trong `src/tests/` cho approval gắn đúng claim, trần hoàn
   tiền theo đơn, idempotency khi retry và resume sau injected crash. Test phải
   xác minh ledger và audit thật; không chỉ so trạng thái `RunResult`.
2. Từ thư mục `src/`, chạy `python -m pytest -q` và
   `python -m pytest -q -m student -o addopts=` sau khi ba shape hoàn thành.
3. Chạy benchmark với đủ bốn shape, 14 claim public và seed 11,22,33,44,55;
   chạy crash suite 20 điểm theo `src/reports/README.md`. Không sửa JSON bằng tay.
4. Dùng số liệu từ report được sinh ra để điền `report/team/decision_adr.md`,
   `report/team/research_card.md` và `report/team/group_report.md`, sau đó chạy
   `python -m lab8.check_submission`. Ghi commit/test thực tế trong `TEAM.md`.
