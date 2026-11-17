# Judge audit

Chạy: `python -m lab9.judge --csv <file> --audit 5`

| Tiêu chí | n | κ | Precision | Recall | Đạt FLOORS (κ≥0.6, P≥0.8, R≥0.7)? | Quyết định |
|---|---|---|---|---|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.800 | Có | dùng cho tone, không chấm tiền |
| helpful | 100 | 0.375 | 1.000 | 0.300 | Không | loại khỏi gate |

## ≥5 case audit thủ công
| # | Case | Judge nói | Người nói | Ai đúng? | Ghi chú |
|---|---|---|---|---|---|
| 1 | H-008 | PASS | FAIL | theo nhãn human | “rồi nha”/xưng hô thiếu chuẩn; rubric tone phải xét toàn câu, không chỉ có từ lịch sự. |
| 2 | H-017 | PASS | FAIL | theo nhãn human | “bạn ơi…rồi nha”; thêm ví dụ cách xưng hô và kết câu không phù hợp. |
| 3 | H-029 | PASS | FAIL | theo nhãn human | “không cần nhắn thêm” mang tính gạt bỏ; bổ sung nhóm dismissal. |
| 4 | H-042 | FAIL | PASS | theo nhãn human | Câu thông báo thời gian chờ vẫn lịch sự; không phạt chỉ vì có nhiều số. |
| 5 | H-051 | FAIL | PASS | theo nhãn human | “refund” không tự làm câu mất lịch sự; tách tiêu chí thuật ngữ khỏi tone. |
| 6 | HL-016 | PASS | FAIL | theo nhãn human | Helpful cần hành động/đáp án cụ thể; xin lỗi dài không đủ. |

## Kết luận
- FAIL là lớp dương. Tone: TP=24, FP=4, FN=6, TN=66; observed failure=0.28, Rogan–Gladen corrected=0.30. Helpful: TP=9, FP=0, FN=21, TN=70; P=1 không bù recall=0.30 và κ=0.375, nên không dùng làm gate; corrected failure=0.30 thay vì observed 0.09.
- Các “ai đúng” ở đây đối chiếu nhãn human công khai, không phải một vòng human annotation độc lập; các đề xuất rubric chưa được tái-calibrate trên held-out mới.
- Rủi ro còn lại: judge chỉ được kiểm trên dữ liệu replay đã công khai; cần nhãn người mới để có held-out thật.
