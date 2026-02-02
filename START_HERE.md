# 🚀 BẮT ĐẦU CHẠY THỰC TẾ

## Bước 1: Setup API Key (1 phút)

```bash
# Tạo file .env
echo "OPENAI_API_KEY=sk-your-actual-key" > .env
```

Thay `sk-your-actual-key` bằng key thật từ https://platform.openai.com/api-keys

## Bước 2: Test API Key (30 giây)

```bash
python test_api_key.py
```

Nếu thấy "✅ API Key Is Working!" → Sẵn sàng!

## Bước 3: Chạy Experiments

### Cách 1: Dùng Script Tự Động (Dễ nhất)

```bash
./setup_and_run.sh
```

Chọn milestone nào muốn chạy (1-4).

### Cách 2: Chạy Trực Tiếp

```bash
# Milestone 2: Deviation Suite
python run_milestone2_deviation.py

# Milestone 3: Baseline Comparison  
python run_milestone3_baselines.py

# Milestone 4: Protocol Progression
python run_milestone4_protocols.py

# Hoặc tất cả
python run_all_milestones.py
```

## Kết Quả

Sau khi chạy xong, xem kết quả ở:

```
results/
├── milestone2/deviation_suite_results.json
├── milestone3/baseline_comparison.json
└── milestone4/protocol_comparison.json
```

## Chi Phí

- **Test run (10 tasks)**: ~$0.20-0.30 (RẺ!)
- **Full run (100 tasks)**: ~$2-3 USD

Đang dùng `gpt-4o-mini` - model rẻ nhất của OpenAI.

## Thời Gian

- **Test run**: 20-30 phút
- **Full run**: 2-3 giờ

## Metrics Quan Trọng

✅ **Milestone 2**: IRI < 0.05 = Excellent robustness  
✅ **Milestone 3**: Evidence compliance > 90% = Unique value  
✅ **Milestone 4**: IRI giảm dần P1→P2→P3 = Protocol progression  

## Troubleshooting

**Lỗi API key?**
```bash
# Kiểm tra
echo $OPENAI_API_KEY

# Set lại
export OPENAI_API_KEY=sk-your-key
```

**Lỗi rate limit?**
- Đợi 1 phút
- Hoặc giảm tasks: sửa `num_samples=10` → `5`

## Đọc Thêm

- [`RUN_REAL.md`](RUN_REAL.md) - Hướng dẫn chi tiết
- [`QUICK_START.md`](QUICK_START.md) - Giải thích metrics
- [`IMPLEMENTATION_SUMMARY.md`](IMPLEMENTATION_SUMMARY.md) - Technical details

---

**Ready? Chạy ngay:**

```bash
python test_api_key.py && ./setup_and_run.sh
```

🎉 Good luck!
