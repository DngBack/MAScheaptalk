# Hướng Dẫn Chạy Thực Tế Với OpenAI

## 🎯 Bạn Đã Sẵn Sàng!

Tất cả code đã được cập nhật để dùng **gpt-4o-mini** (model rẻ nhất của OpenAI, chỉ ~$0.15 per 1M tokens).

---

## 🔑 Bước 1: Setup API Key

### Cách 1: Dùng file .env (Khuyến nghị)

```bash
# Tạo file .env
echo "OPENAI_API_KEY=sk-your-actual-key-here" > .env
```

### Cách 2: Export trong terminal

```bash
export OPENAI_API_KEY=sk-your-actual-key-here
```

---

## 🚀 Bước 2: Chạy Experiments

### Cách Nhanh Nhất - Dùng Script Tự Động

```bash
./setup_and_run.sh
```

Script này sẽ:
- ✅ Kiểm tra API key
- ✅ Cho bạn chọn milestone nào chạy
- ✅ Tự động chạy và báo kết quả

### Hoặc Chạy Trực Tiếp

#### Milestone 2: Deviation Suite
```bash
python run_milestone2_deviation.py
```

#### Milestone 3: Baseline Comparison
```bash
python run_milestone3_baselines.py
```

#### Milestone 4: Protocol Progression
```bash
python run_milestone4_protocols.py
```

#### Tất Cả Cùng Lúc
```bash
python run_all_milestones.py
```

---

## 💰 Chi Phí Ước Tính

### Test Run (10 tasks - như hiện tại)
- **Milestone 2**: 10 tasks × 6 deviations = 60 episodes
- **Milestone 3**: 10 tasks × 3 methods = 30 episodes
- **Milestone 4**: 10 tasks × 3 protocols × 4 deviations = 120 episodes
- **Tổng**: ~210 episodes
- **Chi phí**: ~$0.20-0.30 USD (rất rẻ!)

### Full Run (100 tasks cho paper)
Để có kết quả đầy đủ cho paper, sửa trong scripts:
```python
num_samples=10  →  num_samples=100
```

- **Tổng**: ~2,100 episodes
- **Chi phí**: ~$2-3 USD (vẫn rất rẻ với gpt-4o-mini!)

---

## ⏱️ Thời Gian

### Test Run (10 tasks)
- **Milestone 2**: 5-10 phút
- **Milestone 3**: 3-5 phút  
- **Milestone 4**: 10-15 phút
- **Tổng**: ~20-30 phút

### Full Run (100 tasks)
- **Tổng**: 2-3 giờ

---

## 📊 Kiểm Tra Kết Quả

Sau khi chạy, kiểm tra:

```bash
# Xem results
ls -lh results/milestone*/

# Xem milestone 2 results
cat results/milestone2/deviation_suite_results.json | python -m json.tool

# Xem milestone 3 results
cat results/milestone3/baseline_comparison.json | python -m json.tool

# Xem milestone 4 results
cat results/milestone4/protocol_comparison.json | python -m json.tool
```

---

## 🔍 Metrics Quan Trọng

### Milestone 2: Deviation Suite
Tìm trong `results/milestone2/deviation_suite_results.json`:
```json
{
  "iri": 0.03,                    // < 0.05 = Excellent!
  "deviation_gains": {
    "lie": {
      "deviation_gain": -0.45,    // < 0 = Protocol hiệu quả
      "percent_dg_positive": 12.0 // % episodes nói dối có lợi
    }
  }
}
```

### Milestone 3: Baseline Comparison
Tìm trong `results/milestone3/baseline_comparison.json`:
```json
{
  "methods": {
    "protocol_p1": {
      "accuracy": 0.68,
      "evidence_compliance": 0.92  // Unique value!
    },
    "self_consistency_k5": {
      "accuracy": 0.71
    }
  }
}
```

### Milestone 4: Protocol Progression
Tìm trong `results/milestone4/protocol_comparison.json`:
```json
{
  "P1_Evidence_First": {"iri": 0.15},
  "P2_Cross_Exam": {"iri": 0.08},    // Better!
  "P3_Slashing": {"iri": 0.03}       // Best!
}
```

---

## ❓ Troubleshooting

### Lỗi: OPENAI_API_KEY not set
```bash
# Kiểm tra API key
echo $OPENAI_API_KEY

# Nếu rỗng, set lại
export OPENAI_API_KEY=sk-your-key
```

### Lỗi: Rate limit exceeded
Nếu gặp rate limit, đợi 1 phút hoặc:
- Giảm số tasks: `num_samples=10` → `num_samples=5`
- Thêm delay giữa requests (sẽ tự động retry)

### Lỗi: Invalid API key
- Kiểm tra key có đúng format: `sk-...`
- Kiểm tra key còn active trên OpenAI dashboard
- Kiểm tra account có credits

### Dataset FEVER không load được
Không vấn đề! Script tự tạo mock data để test. Mock data đủ để kiểm tra pipeline hoạt động.

---

## 🎯 Checklist Trước Khi Chạy Full

- [ ] API key đã set và valid
- [ ] Test run (10 tasks) chạy thành công
- [ ] Kiểm tra metrics có ý nghĩa (DG < 0, IRI < 0.15)
- [ ] Đã tạo results/ folders
- [ ] Đã commit code hiện tại (backup)

Sau khi test OK, tăng lên 100 tasks cho paper!

---

## 📝 Notes

- **Model**: Đang dùng `gpt-4o-mini` (rẻ, nhanh, chất lượng tốt)
- **Costs**: Mỗi 1M tokens = $0.15 (input) + $0.60 (output)
- **Average**: ~1000 tokens per episode = $0.001 per episode
- **Safety**: Scripts có retry logic cho rate limits
- **Reproducibility**: Seeds fixed (42, 43, 44) trong configs

---

## 🚀 Ready to Go!

```bash
# Chạy ngay!
./setup_and_run.sh
```

Good luck! 🎉
