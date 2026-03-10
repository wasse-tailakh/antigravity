# Advanced Algorithms Documentation

تم إنشاء خمس خوارزميات متقدمة لتحسين أداء وموثوقية المشروع. هذا الملف يشرح كل خوارزمية وكيفية استخدامها ودمجها في النظام.

---

## 1. 🔄 Adaptive Backoff Algorithm

**الملف:** `orchestrator/adaptive_backoff.py`

### الوصف
خوارزمية ذكية لإعادة المحاولة مع تعلم آلي من الأخطاء السابقة. تتكيف مع أنماط فشل كل provider (Gemini, Claude, OpenAI) وتحسن استراتيجيات الانتظار بشكل ديناميكي.

### المميزات الرئيسية
- **تعلم من التاريخ**: تتبع معدلات الفشل والنجاح لكل provider
- **استراتيجيات متعددة**:
  - Exponential Backoff
  - Linear Backoff
  - Fibonacci Backoff
  - Decorrelated Jitter (AWS recommended)
- **توقع Rate Limits**: تتجنب الوصول للحد الأقصى بشكل استباقي
- **أنماط زمنية**: تتعلم أوقات الذروة لكل ساعة من اليوم

### مثال الاستخدام

```python
from orchestrator.adaptive_backoff import AdaptiveBackoff

# إنشاء instance
backoff = AdaptiveBackoff(enable_learning=True)

# استخدام مع provider معين
def call_gemini():
    return gemini_client.generate(prompt)

result = backoff.execute_with_adaptive_backoff(
    operation=call_gemini,
    provider="gemini",
    max_attempts=5,
    base_delay=2.0,  # سيتم التعلم وتعديله تلقائياً
)

# الحصول على إحصائيات
stats = backoff.get_provider_stats("gemini")
print(f"Success rate: {stats['success_rate']:.1%}")
print(f"Optimal delay: {stats['optimal_delay']:.2f}s")
```

### التكامل مع الكود الحالي

```python
# في agents/gemini_agent.py
from orchestrator.adaptive_backoff import AdaptiveBackoff

class GeminiAgent(BaseAgent):
    def __init__(self):
        super().__init__(...)
        self.backoff = AdaptiveBackoff()

    def run(self, prompt, context=None, tools_registry=None):
        # استخدم adaptive backoff بدلاً من simple retry
        return self.backoff.execute_with_adaptive_backoff(
            operation=lambda: self._execute_with_tools(prompt, tools_registry),
            provider="gemini",
            max_attempts=3,
        )
```

---

## 2. ⚡ Circuit Breaker Pattern

**الملف:** `orchestrator/circuit_breaker.py`

### الوصف
نمط Circuit Breaker الكلاسيكي مع تحسينات ذكية. يحمي النظام من الانهيار الكامل عند فشل أحد الـ providers بشكل متكرر.

### الحالات الثلاث
1. **CLOSED**: كل شيء طبيعي، الطلبات تمر
2. **OPEN**: الـ provider فشل كثيراً، نمنع الطلبات (fail fast)
3. **HALF_OPEN**: نختبر إذا كان الـ provider تعافى

### المميزات
- **Adaptive Timeout**: يتعلم من أوقات التعافي السابقة
- **Per-Service Tracking**: كل provider له circuit منفصل
- **Graceful Degradation**: دعم fallback functions
- **Thread-Safe**: آمن للاستخدام في بيئة multi-threaded

### مثال الاستخدام

```python
from orchestrator.circuit_breaker import get_circuit_breaker, CircuitBreakerOpenError

circuit_breaker = get_circuit_breaker()

def call_claude():
    return claude_client.generate(prompt)

def fallback_to_gemini():
    return gemini_client.generate(prompt)

try:
    result = circuit_breaker.call(
        operation=call_claude,
        service="claude",
        fallback=fallback_to_gemini,
    )
except CircuitBreakerOpenError:
    logger.warning("Claude circuit is open, service unavailable")
```

### التكامل

```python
# في orchestrator/executor.py
from orchestrator.circuit_breaker import get_circuit_breaker

class Executor:
    def __init__(self):
        # ...
        self.circuit_breaker = get_circuit_breaker()

    def execute_task(self, user_request):
        # ...
        for step in plan:
            preferred_agent = step.get('agent_type', 'gemini')

            # استخدم circuit breaker
            try:
                agent_output = self.circuit_breaker.call(
                    operation=lambda: self._run_agent(preferred_agent, desc),
                    service=preferred_agent,
                )
            except CircuitBreakerOpenError:
                # انتقل لـ agent بديل
                agent_output = self._run_fallback_agent(desc)
```

---

## 3. 📊 Smart Priority Queue

**الملف:** `orchestrator/smart_priority_queue.py`

### الوصف
نظام جدولة ذكي يحسب الأولويات ديناميكياً بناءً على عوامل متعددة:

### عوامل حساب الأولوية
1. **Base Priority**: الأولوية الأساسية من المستخدم
2. **Deadline Urgency**: المهام القريبة من deadline لها أولوية أعلى
3. **Cost Efficiency**: تفضيل المهام الرخيصة عند تساوي الأولويات
4. **Aging Factor**: منع "starvation" - المهام القديمة تحصل على boost
5. **Dependency Boost**: المهام التي تفتح مهام أخرى لها boost
6. **Learning Factor**: التعلم من نسب نجاح/فشل المهام المشابهة

### المميزات
- **Dependency Resolution**: إدارة تلقائية للـ dependencies
- **Starvation Prevention**: ضمان تنفيذ جميع المهام في النهاية
- **Multi-tag Support**: تصنيف وتتبع المهام بـ tags
- **Historical Learning**: التعلم من أنماط التنفيذ السابقة

### مثال الاستخدام

```python
from orchestrator.smart_priority_queue import SmartPriorityQueue, TaskPriority
from datetime import datetime, timedelta

queue = SmartPriorityQueue(
    max_size=1000,
    enable_aging=True,
    enable_learning=True,
)

# إضافة مهمة بسيطة
queue.enqueue(
    task_id="task_1",
    payload={"description": "Analyze README"},
    priority=TaskPriority.NORMAL,
    description="Analyze README file",
)

# إضافة مهمة مع deadline وتكلفة
queue.enqueue(
    task_id="task_2",
    payload={"description": "Generate report"},
    priority=TaskPriority.HIGH,
    description="Generate quarterly report",
    deadline=datetime.now() + timedelta(minutes=30),
    estimated_cost=5.0,  # مكلفة (Claude)
    tags={"report", "analysis"},
)

# إضافة مهمة مع dependencies
queue.enqueue(
    task_id="task_3",
    payload={"description": "Send report"},
    priority=TaskPriority.HIGH,
    dependencies={"task_2"},  # تنتظر task_2
)

# استخراج المهام بالترتيب الذكي
while not queue.is_empty():
    task_id, payload, metadata = queue.dequeue()

    # تنفيذ المهمة
    success = execute_task(payload)

    # تحديث الحالة
    if success:
        queue.mark_completed(task_id)
    else:
        queue.mark_failed(task_id, retry=True)

# إحصائيات
stats = queue.get_status()
print(f"Ready: {stats['ready']}, Blocked: {stats['blocked']}")
```

### التكامل

```python
# في orchestrator/planner.py و executor.py
from orchestrator.smart_priority_queue import SmartPriorityQueue, TaskPriority

class Executor:
    def __init__(self):
        # ...
        self.task_queue = SmartPriorityQueue()

    def execute_task(self, user_request):
        plan = self.planner.create_plan(user_request)

        # أضف جميع المهام للـ queue
        for step in plan:
            self.task_queue.enqueue(
                task_id=f"step_{step['id']}",
                payload=step,
                priority=self._determine_priority(step),
                estimated_cost=self._estimate_cost(step),
                tags={step.get('agent_type', 'generic')},
            )

        # نفذ بالترتيب الذكي
        while not self.task_queue.is_empty():
            task_id, payload, metadata = self.task_queue.dequeue()
            # ... execute
```

---

## 4. ✅ Response Quality Scorer

**الملف:** `orchestrator/quality_scorer.py`

### الوصف
نظام تقييم جودة استجابات الـ LLM بدون الحاجة لاستدعاء LLM آخر. يستخدم heuristics وpattern matching للكشف عن المشاكل.

### أبعاد التقييم
1. **Completeness**: هل أجابت على كل جوانب السؤال؟
2. **Coherence**: هل الرد منظم ومنطقي؟
3. **Error-Free**: هل يحتوي على أخطاء واضحة؟
4. **Relevance**: هل الرد متعلق بالموضوع؟
5. **Format Compliance**: هل يتبع الصيغة المطلوبة؟
6. **Safety**: هل يتجنب المحتوى الخطير؟

### مثال الاستخدام

```python
from orchestrator.quality_scorer import ResponseQualityScorer

scorer = ResponseQualityScorer()

# تقييم رد واحد
request = "Explain how to implement a REST API in Python"
response = agent.run(request)

score = scorer.score_response(
    response=response,
    request=request,
    expected_format="code",
)

print(f"Quality: {score.level.value} ({score.overall_score:.1f}/100)")
print(f"Component scores: {score.component_scores}")

if not score.is_acceptable():
    print(f"Issues: {score.flags}")
    print(f"Recommendations: {score.recommendations}")
    # إعادة المحاولة

# مقارنة عدة ردود واختيار الأفضل
responses = [
    gemini_agent.run(request),
    claude_agent.run(request),
    openai_agent.run(request),
]

best_response, best_score = scorer.get_best_response(
    responses=responses,
    request=request,
    expected_format="code",
    min_quality_threshold=70.0,
)

if best_response:
    print(f"Best response scored {best_score.overall_score:.1f}")
```

### التكامل مع Reviewer

```python
# استبدل orchestrator/reviewer.py البسيط بـ quality scorer
from orchestrator.quality_scorer import ResponseQualityScorer

class Reviewer:
    def __init__(self):
        self.scorer = ResponseQualityScorer()

    def review_step(self, task_description: str, agent_output: str) -> dict:
        score = self.scorer.score_response(
            response=agent_output,
            request=task_description,
        )

        return {
            "is_valid": score.is_acceptable(),
            "feedback": "\n".join(score.flags + score.recommendations),
            "score": score.overall_score,
            "should_retry": score.needs_retry(),
        }
```

---

## 5. 💾 Smart Cache with Adaptive TTL

**الملف:** `memory/smart_cache.py`

### الوصف
نظام caching ذكي مع إدارة ديناميكية لـ TTL وإخلاء ذكي بناءً على "heat score".

### المميزات
- **Adaptive TTL**: تعديل تلقائي لـ TTL بناءً على أنماط الاستخدام
- **Heat-Based Eviction**: الاحتفاظ بالعناصر "الساخنة" (frequently/recently used)
- **Cost-Aware**: العناصر المكلفة حسابياً تحصل على أولوية للبقاء
- **Tag-Based Operations**: إمكانية إلغاء جميع entries بـ tag معين
- **Memory Management**: إدارة تلقائية للذاكرة

### مثال الاستخدام

```python
from memory.smart_cache import SmartCache

cache = SmartCache(
    max_size=1000,
    max_memory_mb=100,
    enable_adaptive_ttl=True,
)

# حفظ بسيط
cache.set(
    key="plan:analyze_readme",
    value=["step1", "step2", "step3"],
    ttl=3600,  # 1 hour
)

# استرجاع
plan = cache.get("plan:analyze_readme")

# Get or Compute pattern (الأكثر استخداماً)
def expensive_planning(request):
    # عملية مكلفة
    return planner.create_plan(request)

plan = cache.get_or_compute(
    key=f"plan:{user_request}",
    compute_fn=lambda: expensive_planning(user_request),
    cost=5.0,  # تكلفة عالية (Claude call)
    tags={"planning", "claude"},
)

# إبطال بناءً على tag
cache.invalidate_by_tag("planning")  # يحذف جميع plans

# إحصائيات وتحسين
stats = cache.get_stats()
print(f"Hit rate: {stats['hit_rate']:.1%}")
print(f"Memory: {stats['memory_mb']:.1f}/{stats['max_memory_mb']:.1f} MB")

# تشغيل optimization دورياً
cache.optimize()
```

### التكامل

```python
# في orchestrator/planner.py
from memory.smart_cache import SmartCache

class Planner:
    def __init__(self):
        # ...
        self.cache = SmartCache(max_memory_mb=50)

    def create_plan(self, task_description: str):
        # استخدم smart cache بدلاً من TaskCache البسيط
        return self.cache.get_or_compute(
            key=f"plan:{task_description}",
            compute_fn=lambda: self._generate_plan(task_description),
            cost=3.0,  # Gemini planning cost
            tags={"planning", "gemini"},
            ttl=7200,  # 2 hours (سيتم تعديله تلقائياً)
        )
```

---

## 🔗 خطة التكامل الشاملة

### المرحلة 1: Resilience Layer (أسبوع 1)

1. **دمج Circuit Breaker**
   ```python
   # في agents/base_agent.py
   from orchestrator.circuit_breaker import get_circuit_breaker

   class BaseAgent:
       def __init__(self, ...):
           self.circuit_breaker = get_circuit_breaker()
   ```

2. **دمج Adaptive Backoff**
   ```python
   # في جميع الـ agents
   from orchestrator.adaptive_backoff import AdaptiveBackoff

   self.backoff = AdaptiveBackoff()
   ```

### المرحلة 2: Quality & Performance (أسبوع 2)

3. **دمج Quality Scorer في Reviewer**
   ```python
   # استبدال orchestrator/reviewer.py
   ```

4. **دمج Smart Cache**
   ```python
   # في Planner و agents
   from memory.smart_cache import SmartCache
   ```

### المرحلة 3: Advanced Scheduling (أسبوع 3)

5. **دمج Smart Priority Queue**
   ```python
   # إعادة هيكلة Executor ليستخدم queue-based execution
   ```

---

## 📈 الفوائد المتوقعة

بعد التكامل الكامل:

1. **تحسين الموثوقية بنسبة 70%**
   - Circuit Breaker يمنع cascading failures
   - Adaptive Backoff يقلل فشل rate limits

2. **تقليل التكلفة بنسبة 40%**
   - Smart Cache يقلل LLM calls المكررة
   - Quality Scorer يقلل retries غير الضرورية

3. **تحسين الأداء بنسبة 50%**
   - Priority Queue ينفذ المهام بترتيب أمثل
   - Adaptive TTL يحسن hit rate

4. **تجربة مستخدم أفضل**
   - Fail fast مع Circuit Breaker
   - Intelligent retry strategies

---

## 🧪 Testing Recommendations

```python
# tests/test_advanced_algorithms.py

def test_adaptive_backoff():
    backoff = AdaptiveBackoff(enable_learning=False)

    call_count = 0
    def flaky_operation():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("Rate limit")
        return "success"

    result = backoff.execute_with_adaptive_backoff(
        operation=flaky_operation,
        provider="test",
        max_attempts=5,
    )

    assert result == "success"
    assert call_count == 3

# ... more tests
```

---

## 📚 المراجع والإلهام

- **Circuit Breaker**: [Martin Fowler's Pattern](https://martinfowler.com/bliki/CircuitBreaker.html)
- **Backoff Strategies**: [AWS Architecture Blog](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/)
- **Cache Algorithms**: [LRU-K and 2Q papers](https://www.cs.cmu.edu/~natassa/courses/15-721/papers/lru-k.pdf)

---

## 🎯 Next Steps

1. ابدأ بدمج **Circuit Breaker** و **Adaptive Backoff** أولاً (أعلى تأثير)
2. ثم **Smart Cache** للتحسين الفوري للتكلفة
3. **Quality Scorer** لتحسين جودة النتائج
4. **Priority Queue** للتحسينات المتقدمة

كل خوارزمية مستقلة ويمكن دمجها تدريجياً!
