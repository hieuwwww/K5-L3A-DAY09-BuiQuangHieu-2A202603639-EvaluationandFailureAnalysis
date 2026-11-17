# Trace case: từ trace tới quyết định sai đầu tiên

Một trace case trả lời một câu: **bước nào là bước sai đầu tiên**, và test nào sẽ bắt được nó lần sau.

```bash
cd src
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11   # đối chứng
```

Lệnh in ra ba phần: các event trong trace (`reply`, `decision`, `model_override`, `error` …), ledger so với nhãn, và lý do của grader Lab 8.

## Mẫu điền (mỗi nhóm 1 case, lấy từ trial đang fail trong report)

| Trường | Nội dung |
|---|---|
| Trial | `seeded_regression C-002@11`, `R-seeded_regression-C-002-s11` |
| Triệu chứng | Lab 8 FAIL `status resolved != denied`; reply 20.000đ, ledger 20000 nhưng nhãn 0. |
| Bước sai đầu tiên | Event 3 `model_override`: `{"delay_days": 5}`. |
| Vì sao là bước *đầu tiên* | Event 1 handoff chỉ đọc; event 2 investigator trả order đúng delay=2; event 3 mới thay bằng ticket=5. |
| Failure mode | FM-03 ticket_trust |
| Đối chứng | `fixed C-002@11`, `R-fixed-C-002-s11`: event 3 quote=0, không override, status denied, ledger 0, Lab 8 PASS. |
| Regression test | `tests/test_lab9_trace_case.py::test_ticket_override_is_first_bad_step_and_fixed_restores_db_fact`: thực chạy cả hai, variant sai bị grader từ chối và fixed pass. |
| Chưa chắc chắn | Không chứng minh nguyên nhân bên trong model thật; đây là công tắc lỗi deterministic của MockLLM/variant, không phải quan sát production. |

## Quy tắc

- Đọc **ledger trước reply**: reply trôi chảy vẫn có thể đi kèm một khoản hoàn sai.
- "Bước sai đầu tiên" phải dẫn số event cụ thể, không phải "agent bị nhầm".
- Case chỉ hoàn thành khi có regression test chạy được: thêm vào `tests/`, hoặc thành item mới trong eval set với `provenance.from_trace`.
