# Đánh giá kết quả run_all_milestones

Dựa trên: `deviation_suite_results.json`, `baseline_comparison.json`, `protocol_comparison.json`  
(Cỡ mẫu: 10 task, 1 run)

---

## 1. Milestone 2 – Deviation Suite (P1 Evidence-First)

### Incentive Robustness Index (IRI)
- **IRI = 0.0225** → Rất thấp: trung bình gần như không deviation nào “có lợi” so với honest.

### Deviation Gain (DG) theo từng loại

| Deviation       | DG      | % episode DG > 0 | Đánh giá |
|-----------------|---------|-------------------|----------|
| no_evidence     | **-0.35** | 30%               | ✓ Lệch chuẩn bất lợi (payoff giảm mạnh) |
| persuasion_only | **-0.60** | 20%               | ✓✓ Rất bất lợi |
| lie             | -0.04   | 30%               | ○ Gần trung tính |
| low_effort      | -0.03   | 30%               | ○ Gần trung tính |
| **withhold**    | **+0.11** | 30%               | ✗ Trung bình có lợi → P1 chưa đủ trừng phạt “giấu bằng chứng” |

### Evidence (honest)
- **evidence_compliance**: 100%
- **evidence_match_score**: 0.675 (string/LLM match vs GT)

**Kết luận M2:** Giao thức P1 làm no_evidence và persuasion_only rất bất lợi; lie/low_effort gần trung tính; **withhold vẫn hơi có lợi** (DG dương). IRI thấp cho thấy tổng thể incentive ổn.

---

## 2. Milestone 3 – Baseline Comparison

### So sánh phương pháp (cùng 10 task, cùng budget)

| Phương pháp           | Accuracy | Evidence compliance | Evidence match | Mean payoff |
|-----------------------|----------|----------------------|----------------|-------------|
| **protocol_p1**       | 10%      | **100%**             | **0.625**      | **-0.03** (cao nhất) |
| self_consistency_k5   | 50%      | 0%                   | 0              | -0.125      |
| self_refine_r2        | 40%      | 0%                   | 0              | -0.25       |

### Xếp hạng
- **Accuracy**: Self-Consistency > Self-Refine > P1.
- **Evidence compliance**: Chỉ P1 = 100%; baseline = 0%.
- **Payoff**: P1 cao nhất (-0.03), sau đó Self-Consistency (-0.125), Self-Refine (-0.25).

**Kết luận M3:** P1 thua baseline về accuracy (10% vs 40–50%) nhưng **thắng về payoff** và **duy nhất có evidence compliance + evidence match**. Phù hợp claim: protocol có giá trị riêng (incentive + bằng chứng), không chỉ “thắng chat tự do”.

---

## 3. Milestone 4 – Protocol Progression (P1 → P2 → P3)

### Tổng quan theo protocol

| Protocol          | IRI    | Honest accuracy | Honest evidence_match | Honest payoff |
|-------------------|--------|------------------|------------------------|---------------|
| P1_Evidence_First | 0.00   | 20%              | 0.72                   | 0.12          |
| P2_Cross_Exam     | 0.00   | 30%              | 0.71                   | 0.23          |
| P3_Slashing       | 0.017  | 40%              | 0.71                   | 0.31          |

- **Honest**: P1 → P2 → P3 tăng dần accuracy (20% → 30% → 40%) và payoff (0.12 → 0.23 → 0.31). Evidence match giữ ổn ~0.71–0.72.
- **IRI**: P1 và P2 = 0; P3 ≈ 0.017 (vẫn rất thấp).

### Deviation Gain theo protocol

**P1:**  
- lie DG = -0.31, withhold DG = -0.13, persuasion_only DG = -0.37 → đều âm.

**P2:**  
- lie DG ≈ 0, withhold DG = -0.10, persuasion_only DG = -0.61 → persuasion_only bị trừng phạt mạnh.

**P3:**  
- lie DG = **+0.05** (hơi dương), withhold DG = -0.20, persuasion_only DG = -0.56.  
- P3 với **lie** trung bình hơi có lợi (có thể do seed/cỡ mẫu nhỏ).

**Kết luận M4:** P2 và P3 cải thiện chất lượng (accuracy, payoff) khi chơi honest so với P1. Về incentive: P1/P2 IRI = 0; P3 vẫn tốt (IRI nhỏ) nhưng lie dương nhẹ → nên chạy thêm task/seed để xác nhận.

---

## 4. Evidence metrics (đã tích hợp)

- **evidence_match_score**: Đã có trong mọi milestone (string match vs GT; nếu bật `USE_LLM_EVIDENCE_EVAL=1` thì kết hợp thêm LLM).
- **evidence_compliance**: % episode có đưa bằng chứng; P1/P2/P3 honest đều 100%; no_evidence/persuasion_only = 0%.

Các số liệu này đều nằm trong file JSON và có thể dùng cho báo cáo/paper.

---

## 5. Tóm tắt một đoạn (có thể dùng cho paper)

Trên 10 task FEVER, giao thức Evidence-First (P1) làm deviation gain của no_evidence và persuasion_only âm mạnh (DG ≈ -0.35 đến -0.60), IRI = 0.0225 (Milestone 2). Withhold vẫn có DG dương nhẹ (+0.11) dưới P1. So với baseline Self-Consistency và Self-Refine (cùng budget), P1 đạt payoff cao nhất và evidence compliance 100%, với evidence_match_score ~0.62–0.72. Tiến triển P1→P2→P3 cải thiện accuracy và payoff khi chơi honest (20%→30%→40% và payoff 0.12→0.23→0.31); IRI giữ ở 0 hoặc rất thấp. Kết luận cần xác nhận lại trên cỡ mẫu lớn hơn và nhiều seed.

---

## 6. Hạn chế và gợi ý bước tiếp theo

- **Cỡ mẫu**: 10 task, 1 run → phương sai cao; nên chạy ít nhất 100–500 task, ≥5 seed, báo mean ± std.
- **Withhold (P1)**: DG dương → có thể tăng penalty cho evidence_match thấp hoặc thêm bước kiểm tra “cherry-pick”.
- **P3 lie**: DG +0.05 → kiểm tra lại với nhiều task/seed; nếu ổn định dương thì xem xét tăng slashing hoặc threshold reputation.
- **Evidence match**: Đã dùng string match (+ optional LLM); có thể bật `USE_LLM_EVIDENCE_EVAL=1` trong `.env` để báo thêm llm_evidence_score trong kết quả.
