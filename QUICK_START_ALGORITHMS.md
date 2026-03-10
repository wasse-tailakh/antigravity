# 🚀 دليل البدء السريع - Quick Start Guide
## الخوارزميات المتقدمة | Advanced Algorithms

## ⚡ البدء في 5 دقائق | Get Started in 5 Minutes

### 1. جرّب الـ Demo | Try the Demo

```bash
python demo_advanced_system.py
```

سترى 4 أمثلة عملية لكيفية عمل جميع الخوارزميات معاً!

You'll see 4 practical examples of all algorithms working together!

### 2. استخدام أساسي | Basic Usage

```python
from orchestrator.adaptive_backoff import AdaptiveBackoff
from orchestrator.circuit_breaker import get_circuit_breaker
from memory.smart_cache import SmartCache

# Setup
backoff = AdaptiveBackoff()
circuit = get_circuit_breaker()
cache = SmartCache()

# استدعاء محمي وذكي | Protected smart call
def safe_llm_call(prompt, provider="gemini"):
    # 1. تحقق من الـ cache | Check cache
    cached = cache.get(f"{provider}:{prompt}")
    if cached:
        return cached

    # 2. استدعِ مع حماية | Call with protection
    def operation():
        return backoff.execute_with_adaptive_backoff(
            operation=lambda: your_agent.run(prompt),
            provider=provider,
        )

    result = circuit.call(operation, service=provider)

    # 3. احفظ في الـ cache | Save to cache
    cache.set(f"{provider}:{prompt}", result)

    return result

# استخدم! | Use it!
response = safe_llm_call("Explain REST APIs")
```

### 3. استخدام متقدم | Advanced Usage

```python
from orchestrator.executor_v2 import EnhancedExecutor

# كل شيء مدمج! | Everything integrated!
executor = EnhancedExecutor()

results = executor.execute_task(
    "Build a todo app with backend API and tests"
)

# اطبع الإحصائيات | Print statistics
executor.print_detailed_stats()
```

---

## 📚 الملفات المهمة | Important Files

### للقراءة | For Reading
1. **[IMPROVEMENTS_SUMMARY.md](IMPROVEMENTS_SUMMARY.md)** - ملخص سريع بالعربي والإنجليزي
2. **[ADVANCED_ALGORITHMS.md](ADVANCED_ALGORITHMS.md)** - توثيق شامل لكل خوارزمية
3. **[BEFORE_AFTER_COMPARISON.md](BEFORE_AFTER_COMPARISON.md)** - مقارنة تفصيلية

### للتطبيق | For Implementation
1. **[demo_advanced_system.py](demo_advanced_system.py)** - أمثلة عملية شاملة
2. **[executor_v2.py](orchestrator/executor_v2.py)** - Executor محسّن جاهز

---

## 🎯 الخوارزميات الـ 5 | The 5 Algorithms

### 1. 🔄 Adaptive Backoff
**ملف | File:** `orchestrator/adaptive_backoff.py`

**ماذا يفعل | What it does:** إعادة محاولة ذكية تتعلم من الأخطاء

**متى تستخدمه | When to use:** مع كل API call لـ LLM

**سطر واحد | One-liner:**
```python
result = backoff.execute_with_adaptive_backoff(operation, provider="gemini")
```

### 2. ⚡ Circuit Breaker
**ملف | File:** `orchestrator/circuit_breaker.py`

**ماذا يفعل | What it does:** يمنع الانهيار الكامل عند فشل service

**متى تستخدمه | When to use:** لحماية جميع الـ agents

**سطر واحد | One-liner:**
```python
result = circuit.call(operation, service="claude", fallback=gemini_fallback)
```

### 3. 📊 Smart Priority Queue
**ملف | File:** `orchestrator/smart_priority_queue.py`

**ماذا يفعل | What it does:** جدولة ذكية للمهام

**متى تستخدمه | When to use:** عند تنفيذ مهام متعددة

**سطر واحد | One-liner:**
```python
queue.enqueue(task_id, payload, priority=TaskPriority.HIGH, deadline=...)
```

### 4. ✅ Quality Scorer
**ملف | File:** `orchestrator/quality_scorer.py`

**ماذا يفعل | What it does:** تقييم جودة ردود الـ LLM

**متى تستخدمه | When to use:** بعد كل استجابة LLM

**سطر واحد | One-liner:**
```python
score = scorer.score_response(response, request, expected_format="json")
```

### 5. 💾 Smart Cache
**ملف | File:** `memory/smart_cache.py`

**ماذا يفعل | What it does:** تخزين مؤقت ذكي مع TTL متكيف

**متى تستخدمه | When to use:** لتخزين نتائج مكلفة

**سطر واحد | One-liner:**
```python
result = cache.get_or_compute(key, compute_fn, cost=5.0)
```

---

## 🎨 أمثلة سريعة | Quick Examples

### مثال 1: حماية Agent من Rate Limits
### Example 1: Protect Agent from Rate Limits

```python
from orchestrator.adaptive_backoff import AdaptiveBackoff

backoff = AdaptiveBackoff()

# سيحاول بذكاء حتى 5 مرات | Will smartly retry up to 5 times
result = backoff.execute_with_adaptive_backoff(
    operation=lambda: gemini_agent.run("Explain AI"),
    provider="gemini",
    max_attempts=5,
)
```

### مثال 2: Failover تلقائي عند فشل Claude
### Example 2: Auto-Failover When Claude Fails

```python
from orchestrator.circuit_breaker import get_circuit_breaker

circuit = get_circuit_breaker()

result = circuit.call(
    operation=lambda: claude_agent.run(prompt),
    service="claude",
    fallback=lambda: gemini_agent.run(prompt),  # Auto fallback!
)
```

### مثال 3: جدولة ذكية لمهام متعددة
### Example 3: Smart Scheduling for Multiple Tasks

```python
from orchestrator.smart_priority_queue import SmartPriorityQueue, TaskPriority
from datetime import datetime, timedelta

queue = SmartPriorityQueue()

# مهمة عادية | Normal task
queue.enqueue("task1", {"prompt": "Analyze code"}, TaskPriority.NORMAL)

# مهمة عاجلة مع deadline | Urgent task with deadline
queue.enqueue(
    "task2",
    {"prompt": "Security audit"},
    TaskPriority.CRITICAL,
    deadline=datetime.now() + timedelta(minutes=30),
)

# سيُنفَّذ task2 أولاً! | task2 will execute first!
task_id, payload, metadata = queue.dequeue()
```

### مثال 4: التحقق من جودة الرد
### Example 4: Verify Response Quality

```python
from orchestrator.quality_scorer import ResponseQualityScorer

scorer = ResponseQualityScorer()

response = agent.run("Write a function to sort a list")

quality = scorer.score_response(
    response=response,
    request="Write a function to sort a list",
    expected_format="code",
)

if quality.overall_score < 50:
    print(f"Poor quality! Issues: {quality.flags}")
    print(f"Recommendations: {quality.recommendations}")
    # أعد المحاولة | Retry
```

### مثال 5: تخزين نتائج مكلفة
### Example 5: Cache Expensive Results

```python
from memory.smart_cache import SmartCache

cache = SmartCache()

# سيُستدعى compute_fn فقط عند عدم وجوده في الـ cache
# compute_fn only called if not in cache
plan = cache.get_or_compute(
    key=f"plan:{user_request}",
    compute_fn=lambda: planner.create_plan(user_request),
    cost=5.0,  # مكلف | Expensive
    tags={"planning"},
)

# المرة الثانية: من الـ cache فوراً! | Second time: from cache instantly!
same_plan = cache.get_or_compute(
    key=f"plan:{user_request}",
    compute_fn=lambda: planner.create_plan(user_request),
)
```

---

## 📊 قياس التحسينات | Measure Improvements

### قبل التطبيق | Before Implementation

```python
import time

start = time.time()
# قم بتنفيذ مهمة | Execute a task
results = original_executor.execute_task("Build todo app")
baseline_time = time.time() - start

print(f"Baseline time: {baseline_time:.2f}s")
print(f"Success rate: {calculate_success_rate(results):.1%}")
```

### بعد التطبيق | After Implementation

```python
start = time.time()
# نفس المهمة مع النظام المحسّن | Same task with enhanced system
results = enhanced_executor.execute_task("Build todo app")
enhanced_time = time.time() - start

improvement = ((baseline_time - enhanced_time) / baseline_time) * 100
print(f"Enhanced time: {enhanced_time:.2f}s")
print(f"Improvement: {improvement:.1f}%")
print(f"Success rate: {calculate_success_rate(results):.1%}")

# اطبع إحصائيات مفصلة | Print detailed stats
enhanced_executor.print_detailed_stats()
```

---

## 🐛 استكشاف الأخطاء | Troubleshooting

### المشكلة: Circuit Breaker يفتح كثيراً
### Issue: Circuit Breaker Opens Too Often

```python
# زد الـ threshold | Increase threshold
circuit = CircuitBreaker(
    failure_threshold=10,  # بدلاً من 5 | Instead of 5
    timeout=60.0,          # بدلاً من 30 | Instead of 30
)
```

### المشكلة: Cache Hit Rate منخفض
### Issue: Low Cache Hit Rate

```python
# زد الـ TTL | Increase TTL
cache = SmartCache(
    default_ttl=7200,  # ساعتان بدلاً من ساعة | 2 hours instead of 1
    max_size=1000,     # المزيد من العناصر | More items
)
```

### المشكلة: المهام لا تُنفذ بالترتيب المتوقع
### Issue: Tasks Not Executing in Expected Order

```python
# استخدم أولويات أعلى | Use higher priorities
queue.enqueue(
    task_id="important_task",
    payload=task,
    priority=TaskPriority.CRITICAL,  # بدلاً من NORMAL | Instead of NORMAL
)
```

---

## 🔍 الخطوات التالية | Next Steps

1. ✅ **جرّب الـ Demo**
   ```bash
   python demo_advanced_system.py
   ```

2. ✅ **اقرأ التوثيق الشامل**
   - [ADVANCED_ALGORITHMS.md](ADVANCED_ALGORITHMS.md)
   - [BEFORE_AFTER_COMPARISON.md](BEFORE_AFTER_COMPARISON.md)

3. ✅ **ابدأ التكامل التدريجي**
   - ابدأ بـ Circuit Breaker
   - أضف Adaptive Backoff
   - ثم Smart Cache
   - ثم Quality Scorer
   - أخيراً Priority Queue

4. ✅ **قس النتائج**
   - قارن الأداء قبل وبعد
   - راقب الإحصائيات
   - اضبط الإعدادات

---

## 💡 نصائح | Tips

### للأداء الأفضل | For Best Performance
- ✅ استخدم Smart Cache مع العمليات المكلفة فقط
- ✅ ضع TTL مناسب (لا قصير جداً ولا طويل جداً)
- ✅ راقب cache hit rate واضبط الإعدادات

### للموثوقية | For Reliability
- ✅ استخدم Circuit Breaker مع جميع الـ external calls
- ✅ وفر fallback دائماً عند الإمكان
- ✅ راقب حالة الـ circuits

### للتكلفة | For Cost Optimization
- ✅ استخدم Priority Queue لتحسين الترتيب
- ✅ فعّل cost optimization في الـ queue
- ✅ استخدم Quality Scorer لتقليل retries

---

## ❓ أسئلة؟ | Questions?

راجع:
- **التوثيق الكامل:** [ADVANCED_ALGORITHMS.md](ADVANCED_ALGORITHMS.md)
- **المقارنة التفصيلية:** [BEFORE_AFTER_COMPARISON.md](BEFORE_AFTER_COMPARISON.md)
- **الأمثلة:** [demo_advanced_system.py](demo_advanced_system.py)

Check:
- **Full Documentation:** [ADVANCED_ALGORITHMS.md](ADVANCED_ALGORITHMS.md)
- **Detailed Comparison:** [BEFORE_AFTER_COMPARISON.md](BEFORE_AFTER_COMPARISON.md)
- **Examples:** [demo_advanced_system.py](demo_advanced_system.py)

---

**بالتوفيق! Good luck!** 🚀✨
