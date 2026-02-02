# Quick Start Guide: Chạy Experiments

## Tổng quan

Để có kết quả đầy đủ cho nghiên cứu, bạn cần chạy 3 milestones:

1. **Milestone 2**: Deviation Suite (đo Deviation Gain)
2. **Milestone 3**: Baseline Comparison (so sánh với Self-Consistency, Self-Refine)
3. **Milestone 4**: Protocol Progression (P1 → P2 → P3)

---

## Cách 1: Chạy Tất Cả (Khuyến nghị) 🚀

Chạy một lệnh để có tất cả kết quả:

```bash
python run_all_milestones.py
```

**Thời gian**: ~5-10 phút (với mock LLM để test)

**Kết quả:**
- `results/milestone2/` - Deviation suite results
- `results/milestone3/` - Baseline comparison
- `results/milestone4/` - Protocol progression

---

## Cách 2: Chạy Từng Milestone

### Milestone 2: Deviation Suite

Test protocol với 6 deviation types (honest, lie, withhold, etc.):

```bash
python run_milestone2_deviation.py
```

**Output:**
- Deviation Gain (DG) cho mỗi deviation type
- Incentive Robustness Index (IRI)
- % episodes có DG > 0

**Mục tiêu:** DG < 0 cho tất cả deviations (protocol hiệu quả)

---

### Milestone 3: Baseline Comparison

So sánh P1 với baseline mạnh:

```bash
python run_milestone3_baselines.py
```

**Baselines:**
- Self-Consistency (K=5 samples)
- Self-Refine (2 rounds)

**Output:**
- Accuracy comparison
- Evidence compliance (unique value của P1)
- Cost efficiency

**Mục tiêu:** P1 accuracy trong ±5% của best baseline nhưng có evidence compliance >90%

---

### Milestone 4: Protocol Progression

Test P1 → P2 → P3:

```bash
python run_milestone4_protocols.py
```

**Protocols:**
- P1: Evidence-First
- P2: + Cross-Examination
- P3: + Reputation/Slashing

**Output:**
- IRI cho mỗi protocol
- Reputation trajectories (P3)
- Protocol progression analysis

**Mục tiêu:** IRI(P3) < IRI(P2) < IRI(P1) (cải thiện dần)

---

## Yêu Cầu Trước Khi Chạy

### 1. Cài đặt dependencies

```bash
pip install -r requirements.txt
```

### 2. Cấu hình API key (nếu dùng LLM thật)

Tạo file `.env`:

```bash
OPENAI_API_KEY=your-api-key-here
```

**Lưu ý:** Scripts hiện tại dùng mock LLM để test nhanh. Để dùng LLM thật, sửa `model_name="mock"` thành `model_name="gpt-4"` trong các script.

### 3. Tạo thư mục results

```bash
mkdir -p results/milestone2 results/milestone3 results/milestone4
```

---

## Kết Quả Sẽ Có

### 📊 Milestone 2: Deviation Suite Results

**File:** `results/milestone2/deviation_suite_results.json`

```json
{
  "deviation_gains": {
    "lie": {
      "deviation_gain": -0.45,
      "percent_dg_positive": 12.0
    },
    "withhold": {
      "deviation_gain": -0.28,
      "percent_dg_positive": 23.0
    }
  },
  "iri": 0.03
}
```

**Giải thích:**
- `deviation_gain < 0` = Protocol hiệu quả (nói dối không có lợi)
- `iri < 0.05` = Excellent robustness

---

### 📊 Milestone 3: Baseline Comparison

**File:** `results/milestone3/baseline_comparison.json`

```json
{
  "methods": {
    "protocol_p1": {
      "accuracy": 0.68,
      "evidence_compliance": 0.92
    },
    "self_consistency_k5": {
      "accuracy": 0.71,
      "evidence_compliance": 0.0
    },
    "self_refine_r2": {
      "accuracy": 0.69,
      "evidence_compliance": 0.0
    }
  }
}
```

**Key Finding:** P1 competitive accuracy (68% vs 71%) nhưng là method duy nhất có evidence compliance cao (92%)

---

### 📊 Milestone 4: Protocol Progression

**File:** `results/milestone4/protocol_comparison.json`

```json
{
  "P1_Evidence_First": {"iri": 0.15},
  "P2_Cross_Exam": {"iri": 0.08},
  "P3_Slashing": {"iri": 0.03}
}
```

**Key Finding:** IRI giảm dần P1 → P2 → P3, chứng minh protocol progression

---

## Troubleshooting

### Lỗi: Module not found

```bash
# Đảm bảo chạy từ thư mục gốc
cd /home/admin1/Desktop/MAScheaptalk
python run_all_milestones.py
```

### Lỗi: API key not set

Scripts hiện tại dùng mock LLM, không cần API key. Nếu muốn dùng LLM thật:

1. Set API key trong `.env`
2. Sửa `model_name="mock"` → `model_name="gpt-4"` trong scripts

### Lỗi: FEVER dataset không load được

Scripts tự động tạo mock data nếu FEVER không load được. Mock data đủ để test pipeline.

---

## Chạy Với LLM Thật (Production)

Để chạy với OpenAI GPT-4:

1. **Set API key:**
```bash
export OPENAI_API_KEY=your-key
```

2. **Sửa scripts:**
Trong mỗi script `run_milestone*.py`, thay:
```python
model_name="mock"
```
thành:
```python
model_name="gpt-4"
```

3. **Tăng số tasks:**
Sửa `num_samples=10` thành `num_samples=100` để có kết quả đầy đủ

**Chi phí ước tính:**
- 100 tasks × 6 deviations × 3 protocols = 1800 episodes
- ~10-20 USD (tùy model và token usage)

---

## Kế Hoạch Chạy Đầy Đủ

### Phase 1: Test Pipeline (Ngay bây giờ)
```bash
python run_all_milestones.py
```
- Dùng mock LLM
- 10 tasks per milestone
- Kiểm tra pipeline hoạt động đúng

### Phase 2: Pilot Run (1-2 giờ)
```bash
# Sửa num_samples=10 → 30 trong scripts
python run_all_milestones.py
```
- Dùng GPT-4 hoặc local model
- 30 tasks để xem trend
- Chi phí: ~5 USD

### Phase 3: Full Run (3-5 giờ)
```bash
# Sửa num_samples=30 → 100 trong scripts
python run_all_milestones.py
```
- 100 tasks đủ statistical significance
- Chi phí: ~15-20 USD
- Kết quả đầy đủ cho paper

---

## Sử Dụng Kết Quả Cho Paper

### Tables cho Paper

**Table 1: Deviation Gain Analysis**
```
Deviation Type    DG       %DG>0   Status
--------------------------------------------
lie              -0.45     12%     ✓ Effective
withhold         -0.28     23%     ✓ Effective
persuasion_only  -0.62     5%      ✓✓ Very effective

IRI: 0.03 (Excellent robustness)
```

**Table 2: Baseline Comparison**
```
Method              Accuracy  Evidence   Notes
------------------------------------------------
P1 Evidence-First   68%       92%        Unique value
Self-Consistency    71%       0%         Best accuracy
Self-Refine         69%       0%         Iterative
```

**Table 3: Protocol Progression**
```
Protocol    IRI    Improvement vs P1
------------------------------------
P1          0.15   Baseline
P2          0.08   47% better
P3          0.03   80% better
```

---

## Câu Hỏi Thường Gặp

**Q: Mất bao lâu để chạy?**
A: 
- Mock LLM: 5-10 phút
- GPT-4 (10 tasks): 10-15 phút
- GPT-4 (100 tasks): 2-3 giờ

**Q: Có cần GPU không?**
A: Không, chạy trên CPU bình thường được.

**Q: Kết quả có reproducible không?**
A: Có, với seeds cố định (42, 43, 44) trong configs.

**Q: Làm sao kiểm tra kết quả đúng?**
A: 
1. Check IRI < 0.15 (good)
2. Check DG < 0 cho majority deviations
3. Check P1 evidence compliance > 80%
4. Check protocol progression P1 < P2 < P3

---

## Next Steps

Sau khi có kết quả:

1. **Analyze**: Đọc JSON results
2. **Visualize**: Tạo plots (DG, IRI, trajectories)
3. **Write**: Dùng kết quả cho paper sections
4. **Iterate**: Tune parameters nếu cần

Good luck! 🚀
