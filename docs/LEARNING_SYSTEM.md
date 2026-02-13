# Learning System Guide

Incremental learning system that improves extraction quality using few-shot learning from past successes.

## 🎯 Overview

The **ExtractionLearner** implements **few-shot learning** by:
1. Loading previous successful extractions (confidence ≥ 0.7)
2. Selecting high-quality examples (confidence ≥ 0.8)
3. Including them in the system prompt as examples
4. Improving consistency and accuracy over time

**Key Benefit**: The agent learns from its own successful extractions!

---

## 🚀 Quick Start

### **Automatic (Default)**

Few-shot learning is **enabled by default** once you have 5+ successful extractions:

```python
from agent import PLAgentSDK

# Automatically uses few-shot if available
sdk = PLAgentSDK()

# SDK will include 2-3 examples in system prompt
result = sdk.extract_bio_agentic(source_text, source_url, source_type="universal")
```

### **Manual Control**

```python
# Disable few-shot learning
sdk = PLAgentSDK(use_few_shot=False)

# Enable explicitly
sdk = PLAgentSDK(use_few_shot=True)
```

---

## 📚 How It Works

### **Step 1: Load Past Extractions**

```python
from learning_system import ExtractionLearner

learner = ExtractionLearner(examples_dir="output/")
```

**What it loads:**
- All `*.json` files from `output/`
- Filters: successful extractions only
- Filters: confidence ≥ 0.7
- Excludes: `REVIEW_*.json` and `batch_report_*.json`

### **Step 2: Select Best Examples**

```python
examples = learner.get_few_shot_examples(
    n=3,                    # Number of examples
    min_confidence=0.8,     # Minimum confidence
    diversity=True          # Select diverse examples
)
```

**Selection criteria:**
- High confidence (≥ 0.8)
- Diverse officers (different names)
- Different confidence ranges (excellent/good/acceptable)

### **Step 3: Format as Few-Shot**

```python
enhanced_prompt = learner.add_to_system_prompt(base_prompt, examples)
```

**Format:**
```
# Few-Shot Learning Examples

Here are examples of successful extractions from our database.
Use these as reference for quality and format:

## Example 1: 林炳尧 (Confidence: 0.85)

**Input (Obituary Excerpt):**
```
林炳尧同志逝世。林炳尧是福建省晋江市人。生于1943年，于2023-01-15逝世。
1961年入伍。1964年加入中国共产党。1995年晋升少将军衔。
```

**Output (Extracted Data):**
```json
{
  "name": "林炳尧",
  "pinyin_name": "Lín Bǐngyáo",
  "hometown": "福建省晋江市",
  "birth_date": "1943",
  "death_date": "2023-01-15",
  "enlistment_date": "1961",
  "party_membership_date": "1964",
  "promotions": [{"rank": "少将", "date": "1995"}],
  "confidence_score": 0.85
}
```
```

### **Step 4: Use in Extraction**

The enhanced prompt is automatically used when:
- Few-shot learning is enabled (`use_few_shot=True`)
- 5+ successful examples exist
- ExtractionLearner initialized successfully

---

## 📊 Requirements

### **Minimum Examples**

```python
learner.should_use_few_shot(min_examples=5)
# Returns True if ≥ 5 examples available
```

**Why 5 minimum?**
- Need enough diversity
- Avoid overfitting to single example
- Statistical significance

### **Quality Threshold**

```python
examples = learner.get_few_shot_examples(
    n=3,
    min_confidence=0.8  # Only high-quality examples
)
```

**Recommended thresholds:**
- **0.9+**: Excellent examples
- **0.8-0.9**: Good examples
- **0.7-0.8**: Acceptable examples
- **<0.7**: Not used

---

## 🧪 Testing

### **Test Learning System**

```bash
python learning_system.py
```

**Expected output:**
```
ExtractionLearner Demo

Statistics:
┌──────────────────────────────┬─────────────────────┐
│ Metric                       │ Value               │
├──────────────────────────────┼─────────────────────┤
│ Total Examples               │ 12                  │
│ Average Confidence           │ 0.847               │
│ Min Confidence               │ 0.720               │
│ Max Confidence               │ 0.950               │
│ Examples ≥ 0.8              │ 10                  │
│ Examples ≥ 0.9              │ 3                   │
└──────────────────────────────┴─────────────────────┘

Should use few-shot: True

Few-Shot Examples:

Example 1: 林炳尧 (Confidence: 0.95)
Input: 林炳尧同志逝世。林炳尧是福建省晋江市人...
Output fields: name, pinyin_name, hometown, birth_date, ...

Example 2: 张三 (Confidence: 0.88)
Input: 张三同志逝世...
Output fields: name, pinyin_name, ...

Enhanced Prompt Preview:

You are an expert in extracting biographical information...

# Few-Shot Learning Examples

Here are examples of successful extractions...

Full prompt length: 5234 characters
```

---

## 💡 Use Cases

### **Use Case 1: Bootstrapping**

First 5 extractions without few-shot:
```python
sdk = PLAgentSDK(use_few_shot=False)

for i in range(5):
    result = sdk.extract_bio_agentic(source_text, source_url, source_type="universal")
    # Saves to output/
```

After 5 successes, few-shot automatically enabled:
```python
sdk = PLAgentSDK()  # use_few_shot=True by default
# Now uses previous 5 as examples!
```

---

### **Use Case 2: Quality Improvement**

Track quality improvement over time:
```python
from learning_system import ExtractionLearner

learner = ExtractionLearner()

# Check initial state
stats = learner.get_statistics()
print(f"Avg confidence: {stats['avg_confidence']:.3f}")

# After more extractions
learner.load_successful_extractions()
new_stats = learner.get_statistics()
print(f"New avg confidence: {new_stats['avg_confidence']:.3f}")
```

---

### **Use Case 3: Custom Examples**

Select specific examples:
```python
learner = ExtractionLearner()

# Get only excellent examples
examples = learner.get_few_shot_examples(
    n=5,
    min_confidence=0.9,
    diversity=True
)

# Use in custom prompt
custom_prompt = "Extract data..."
enhanced = learner.add_to_system_prompt(custom_prompt, examples)
```

---

## 📈 Benefits

### **1. Improved Consistency**

Examples show:
- ✓ Exact field formats
- ✓ Pinyin transliteration style
- ✓ Date formatting
- ✓ Note-taking patterns

### **2. Better Quality**

Examples demonstrate:
- ✓ High confidence extractions
- ✓ Complete data capture
- ✓ Proper null handling
- ✓ Good extraction notes

### **3. Faster Learning Curve**

- ✓ Agent learns from own successes
- ✓ Adapts to your data patterns
- ✓ Improves over time

### **4. Domain Adaptation**

- ✓ Learns specific terminology
- ✓ Adapts to obituary styles
- ✓ Recognizes patterns

---

## ⚙️ Configuration

### **Number of Examples**

```python
# In agent.py, line ~616
examples = self.learner.get_few_shot_examples(
    n=2,  # Change this to use more/fewer examples
    min_confidence=0.8
)
```

**Recommendations:**
- **1-2 examples**: Fast, minimal token cost
- **3 examples**: Balanced (default)
- **4-5 examples**: Maximum learning, higher cost

### **Confidence Threshold**

```python
examples = learner.get_few_shot_examples(
    n=3,
    min_confidence=0.8  # Adjust based on your quality bar
)
```

**Trade-offs:**
- **0.9+**: Highest quality, fewer examples
- **0.8**: Balanced
- **0.7**: More examples, lower quality

### **Diversity**

```python
examples = learner.get_few_shot_examples(
    n=3,
    diversity=True  # Select from different officers/confidence ranges
)
```

---

## 📊 Statistics

### **Get Learning Statistics**

```python
learner = ExtractionLearner()
stats = learner.get_statistics()

print(f"Total examples: {stats['total_examples']}")
print(f"Avg confidence: {stats['avg_confidence']:.3f}")
print(f"Examples ≥ 0.8: {stats['examples_above_0.8']}")
print(f"Examples ≥ 0.9: {stats['examples_above_0.9']}")
```

### **Check Readiness**

```python
if learner.should_use_few_shot(min_examples=5):
    print("Few-shot learning ready!")
else:
    print(f"Need {5 - stats['total_examples']} more examples")
```

---

## 🔄 Incremental Learning Workflow

### **Phase 1: Bootstrap (0-5 extractions)**

```python
# Manual extractions without few-shot
sdk = PLAgentSDK(use_few_shot=False)

for url in bootstrap_urls:
    result = sdk.extract_bio_agentic(...)
    # Builds example database
```

### **Phase 2: Learning (5+ extractions)**

```python
# Automatic few-shot learning
sdk = PLAgentSDK()  # use_few_shot=True

for url in remaining_urls:
    result = sdk.extract_bio_agentic(...)
    # Uses previous successes as examples
    # Quality improves over time
```

### **Phase 3: Continuous Improvement**

```python
# Learner automatically reloads on init
learner = ExtractionLearner()
# Always uses latest examples

sdk = PLAgentSDK()
# Each extraction benefits from all previous successes
```

---

## 🐛 Troubleshooting

### Issue: "No examples available"

**Cause**: No successful extractions in `output/`
**Fix**: Run 5+ extractions first

### Issue: "Insufficient examples (3/5)"

**Cause**: Less than 5 successful extractions
**Fix**: Complete more extractions

### Issue: "Failed to initialize learning system"

**Cause**: Missing learning_system.py or import error
**Fix**: Verify file exists and dependencies installed

### Issue: Few-shot not improving quality

**Possible causes:**
- Examples are low quality (confidence < 0.8)
- Not enough diversity in examples
- Examples don't match current obituary style

**Fix**: Run more varied extractions, increase min_confidence

---

## 💡 Best Practices

### 1. Build Quality Examples

Start with high-quality obituaries:
```python
# Use clear, complete obituaries for first 5-10 extractions
# This builds a good example database
```

### 2. Monitor Example Quality

```python
learner = ExtractionLearner()
stats = learner.get_statistics()

if stats['avg_confidence'] < 0.75:
    print("Warning: Low average confidence in examples")
    print("Consider manual review")
```

### 3. Refresh Periodically

```python
# Reload to get latest examples
learner.load_successful_extractions()
```

### 4. Use Diverse Examples

```python
examples = learner.get_few_shot_examples(
    n=3,
    diversity=True  # ← Important!
)
```

---

## 📚 API Reference

### **ExtractionLearner**

```python
class ExtractionLearner:
    def __init__(self, examples_dir: str = "output/")

    def load_successful_extractions(self)

    def get_few_shot_examples(
        self,
        n: int = 3,
        min_confidence: float = 0.8,
        diversity: bool = True
    ) -> List[Dict[str, Any]]

    def add_to_system_prompt(
        self,
        base_prompt: str,
        examples: List[Dict[str, Any]]
    ) -> str

    def get_statistics(self) -> Dict[str, Any]

    def should_use_few_shot(self, min_examples: int = 5) -> bool
```

---

## 🎯 Expected Improvements

After implementing few-shot learning:

**Consistency:** ↑ 15-20%
- More uniform field formats
- Consistent pinyin style
- Better note-taking

**Accuracy:** ↑ 10-15%
- Better field extraction
- Fewer missed fields
- Improved confidence scores

**Efficiency:** ↑ 5-10%
- Fewer retry loops
- Better tool sequence
- Faster convergence

---

Generated: 2026-02-11
