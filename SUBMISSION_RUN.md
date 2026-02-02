# Chạy thí nghiệm cho submission paper

Hướng dẫn set up và chạy đầy đủ để có kết quả đủ mạnh cho paper (500 task, optional multi-seed).

---

## 1. Cấu hình trong `.env`

Thêm hoặc sửa trong file `.env` (copy từ `.env.example` nếu chưa có):

```env
OPENAI_API_KEY=sk-your-key-here

# Submission run: 500 tasks (đủ cho paper)
NUM_TASKS=500
NUM_SAMPLES=500
SEED=42
```

- **NUM_TASKS**: Số claim sẽ chạy thí nghiệm (M2/M3/M4). Mặc định **500** cho submission.
- **NUM_SAMPLES**: Số dòng FEVER load từ HuggingFace. Nên đặt **= NUM_TASKS** (500).
- **SEED**: Seed cho reproducibility. Đổi thành 123, 456 để chạy multi-seed (báo mean ± std).

Tùy chọn:

- **USE_LLM_EVIDENCE_EVAL=1**: Bật đánh giá evidence bằng LLM (tốn thêm API).
- **OPENAI_MODEL=gpt-4o-mini**: Model mặc định (tiết kiệm); có thể đổi `gpt-4o` nếu cần.

---

## 2. Chạy một lần (500 task, 1 seed)

```bash
cd /path/to/MAScheaptalk
source .venv/bin/activate   # hoặc: source venv/bin/activate
# Đảm bảo .env có NUM_TASKS=500, NUM_SAMPLES=500, SEED=42
python run_all_milestones.py
```

Nhấn Enter khi được hỏi. Cả 3 milestone (M2, M3, M4) sẽ chạy với **500 task** và **seed 42**.

Kết quả:

- `results/milestone2/deviation_suite_results.json`
- `results/milestone3/baseline_comparison.json`
- `results/milestone4/protocol_comparison.json`

---

## 3. Chạy multi-seed trong một lần (báo mean ± std)

Để chạy **nhiều seed trong một lần** rồi tự động gộp mean ± std, thêm vào **`.env`**:

```env
SEEDS=42,123,456
```

Rồi chạy:

```bash
python run_all_milestones.py
```

Chương trình sẽ:

1. Chạy Milestone 2, 3, 4 với **SEED=42** → copy kết quả sang `seed42.json`, `protocol_comparison_seed42.json`
2. Chạy lại M2, M3, M4 với **SEED=123** → copy sang `seed123.json`, ...
3. Chạy lại với **SEED=456** → copy sang `seed456.json`, ...
4. Gọi script gộp và ghi **results/submission_multi_seed_summary.json** (mean ± std cho IRI, accuracy, payoff, evidence_match_score, DG).

**Lưu ý:** Nếu không set `SEEDS`, chỉ chạy một lần với `SEED` (mặc định 42). Để chạy multi-seed thủ công (từng seed rồi copy file), xem mục 3b bên dưới.

### 3b. Chạy multi-seed thủ công (từng seed, copy file rồi gộp)

Nếu bạn không dùng `SEEDS` trong .env mà muốn chạy từng seed rồi gộp:

```bash
SEED=42   python run_all_milestones.py
# Copy: results/milestone2/deviation_suite_results.json → results/milestone2/seed42.json, tương tự M3/M4
SEED=123  python run_all_milestones.py
# Copy tương tự → seed123.json, protocol_comparison_seed123.json
SEED=456  python run_all_milestones.py
# Copy → seed456.json, ...
python scripts/aggregate_multi_seed_results.py
```

---

## 4. Chạy từng milestone riêng

Nếu chỉ cần M2 hoặc M3/M4:

```bash
python run_milestone2_deviation.py
python run_milestone3_baselines.py
python run_milestone4_protocols.py
```

Vẫn đọc **NUM_TASKS**, **NUM_SAMPLES**, **SEED** từ `.env` (mặc định 500, 500, 42).

---

## 5. Test nhanh (ít task)

Để test pipeline trước khi chạy 500:

Trong `.env` đặt:

```env
NUM_TASKS=10
NUM_SAMPLES=10
SEED=42
```

Rồi chạy `python run_all_milestones.py` như trên. Xong test thì đổi lại 500 cho submission.

---

## 6. Ước lượng thời gian và chi phí (500 task)

- **Milestone 2**: 500 task × 6 deviation types = 3000 episode → vài giờ, chi phí API tùy model.
- **Milestone 3**: 500 task × 3 methods (P1 + 2 baselines) → tương đương.
- **Milestone 4**: 500 task × 4 deviation types × 3 protocols = 6000 episode → lâu nhất.

Tổng 500 task cho cả 3 milestone: có thể **vài giờ đến một ngày** (tùy API và máy). Dùng **gpt-4o-mini** sẽ rẻ và nhanh hơn gpt-4o.

---

## 7. Số liệu cần cho paper

Sau khi chạy (1 seed hoặc 3 seed), trong các file JSON có:

- **Deviation Gain (DG)** từng loại, **IRI**
- **Accuracy**, **evidence_compliance**, **evidence_match_score**, **mean_payoff** theo method/protocol
- So sánh P1 vs baseline (M3), so sánh P1 vs P2 vs P3 (M4)

Nếu chạy multi-seed: tính **mean ± std** cho từng metric rồi ghi vào bảng trong paper.
