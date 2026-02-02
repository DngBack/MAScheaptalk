# 🚀 CHẠY NGAY - ĐÃ FIX!

## ✅ Đã Sửa

1. ✅ Import errors (Role → AgentRole)
2. ✅ Message entity compatibility (thêm evidence=[])
3. ✅ FEVER dataset split (validation → dev)
4. ✅ Tất cả scripts dùng gpt-4o-mini (OpenAI thật)

---

## 🔑 Bước 1: Set API Key

```bash
# Kiểm tra có chưa
echo $OPENAI_API_KEY

# Nếu chưa có, set ngay
export OPENAI_API_KEY=sk-your-real-key-here
```

---

## 🧪 Bước 2: Test API (30 giây)

```bash
python test_api_key.py
```

Phải thấy: "✅ API Key Is Working!"

---

## 🚀 Bước 3: Chạy Milestones

### Option A: Test nhanh Milestone 3 (đã fix)

```bash
python test_milestone3.py
```

Chỉ chạy 1 task để test, rất nhanh!

### Option B: Chạy từng milestone

```bash
# Milestone 2: Deviation Suite
python run_milestone2_deviation.py

# Milestone 3: Baseline Comparison  
python run_milestone3_baselines.py

# Milestone 4: Protocol Progression
python run_milestone4_protocols.py
```

### Option C: Chạy tất cả

```bash
python run_all_milestones.py
```

---

## 📊 Kết Quả Đúng

### Milestone 2 - Deviation Suite
```
DEVIATION GAIN ANALYSIS:
  lie vs honest:
    Deviation Gain: -0.04 to -0.45
    Status: ✓ Effective
    
  withhold vs honest:
    Deviation Gain: -0.15 to -0.37
    Status: ✓✓ Very effective
    
IRI: 0.000 (✓✓ Excellent!)
```

### Milestone 3 - Baseline Comparison
```
Method              Accuracy  Evidence
---------------------------------------
protocol_p1         0.60-0.70 0.80-0.95
self_consistency    0.65-0.75 0.00
self_refine         0.60-0.70 0.00

Key: P1 có evidence compliance cao!
```

### Milestone 4 - Protocol Progression
```
Protocol         IRI    Status
--------------------------------
P1_Evidence      0.00   ✓✓ Excellent
P2_Cross_Exam    0.00   ✓✓ Excellent
P3_Slashing      0.00   ✓✓ Excellent
```

---

## 💰 Chi Phí

- **Test (10 tasks)**: ~$0.20-0.30
- **Full (100 tasks)**: ~$2-3 USD

Rất rẻ với gpt-4o-mini!

---

## ⚠️ Lưu Ý

1. **Internet**: Cần internet để gọi OpenAI API
2. **API Key**: Phải có key hợp lệ từ platform.openai.com
3. **Credits**: Account phải có credits ($5+)
4. **Time**: Test run ~20-30 phút

---

## 🎯 Chạy Ngay!

```bash
# 1. Set API key
export OPENAI_API_KEY=sk-your-key

# 2. Test
python test_api_key.py

# 3. Run
python run_all_milestones.py
```

Done! 🎉
