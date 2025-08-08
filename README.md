# LangGraph Research Project: Advanced Multi-Model Workflows

> **Комплексный проект для изучения продвинутых паттернов LangGraph с локальными моделями**

## 🎯 Обзор проекта

Этот проект демонстрирует enterprise-grade паттерны для построения отказоустойчивых AI-систем с использованием LangGraph и локальных моделей Ollama. От простых workflows до сложных multi-model систем принятия решений.

## 🚀 Быстрый старт

### Предварительные требования
1. **Python 3.12+** и **uv**
2. **Ollama** с моделями: `llama3.2:1b`, `llama3.2:3b`, `llama3.1:8b`

### Установка
```bash
# Установите зависимости
uv sync

# Убедитесь что Ollama запущен
ollama serve

# Скачайте модели (если не установлены)
ollama pull llama3.2:1b
ollama pull llama3.2:3b  
ollama pull llama3.1:8b
```

### Запуск примеров
```bash
# Базовая проверка
python run_example.py basic

# Запуск по фазам (рекомендуемая последовательность)
python run_example.py 2  # Обработка документов
python run_example.py 3  # Условное ветвление
python run_example.py 4  # Retry механизмы
python run_example.py 5  # Fallback стратегии
python run_example.py 6  # Комплексный workflow (ФИНАЛ)
```

## 📋 Структура проекта

```mermaid
graph TD
    A[Project Root] --> B[src/]
    A --> C[examples/]
    A --> D[docs/]
    
    B --> E[models/]
    B --> F[nodes/]
    B --> G[workflows/]
    
    E --> E1[local_model_manager.py]
    E --> E2[model_configs.py]
    E --> E3[fallback_chain.py]
    E --> E4[retry_handler.py]
    
    F --> F1[classification.py]
    F --> F2[processing.py]
    F --> F3[decision.py]
    F --> F4[loan_processing_nodes.py]
    
    G --> G1[state.py]
    G --> G2[document_processing.py]
    G --> G3[conditional_workflow.py]
    G --> G4[loan_application_state.py]
    G --> G5[complex_loan_workflow.py]
    
    C --> H[Phase Examples]
    H --> H1[basic_setup_test.py]
    H --> H2[phase2_document_processing.py]
    H --> H3[phase3_conditional_branching.py]
    H --> H4[phase4_retry_mechanisms.py]
    H --> H5[phase5_fallback_strategies.py]
    H --> H6[phase6_complex_workflow.py]
```

## 🚀 6-фазное обучение

### Phase 1: Базовая настройка

**Цель:** Настройка локальных моделей и базовых retry/fallback механизмов

```mermaid
graph LR
    A[Start] --> B[Initialize Models]
    B --> C{Model Available?}
    C -->|Yes| D[Test Basic Prompt]
    C -->|No| E[Log Error]
    D --> F{Response OK?}
    F -->|Yes| G[Success]
    F -->|No| H[Retry with Fallback]
    H --> I[Next Model]
    I --> C
    E --> J[End with Error]
    G --> K[Complete]
```

**Ожидаемые результаты:**
- ✅ 3 модели инициализированы (Fast: llama3.2:1b, Standard: llama3.2:3b, Reasoning: llama3.1:8b)
- ✅ Базовые retry механизмы работают
- ✅ Fallback между моделями при сбоях

### Phase 2: Простая обработка документов

**Цель:** Создание LangGraph workflow для обработки документов

```mermaid
graph TD
    A[Document Input] --> B[Classification Node]
    B --> C[Extraction Node]
    C --> D[Validation Node]
    D --> E[Finalization Node]
    E --> F[Final Result]
    
    B --> B1[Fast Model]
    C --> C1{Document Type}
    C1 -->|Invoice| C2[Standard Model]
    C1 -->|Contract| C3[Reasoning Model]
    C1 -->|Receipt| C4[Fast Model]
    
    D --> D1[Standard Model]
    
    style B fill:#e1f5fe
    style C fill:#f3e5f5
    style D fill:#e8f5e8
    style E fill:#fff3e0
```

**Тестовые сценарии:**
- 📄 Invoice processing
- 📄 Contract analysis
- 📄 Receipt extraction

**Ожидаемые результаты:**
- ✅ Классификация документов с confidence scores
- ✅ Структурированное извлечение данных в JSON
- ✅ Валидация извлеченной информации
- ✅ Среднее время: ~8.6 секунд на документ

### Phase 3: Условное ветвление

**Цель:** Интеллектуальная маршрутизация на основе характеристик документов

```mermaid
graph TD
    A[Document Input] --> B[Classification]
    B --> C[Routing Decision]
    
    C --> D{Confidence >= 0.6?}
    D -->|No| E[Enhanced Analysis]
    D -->|Yes| F{Document Type}
    
    F -->|Contract + Length > 2000| G[Expert Analysis]
    F -->|Contract + Length <= 2000| H[Standard Processing]
    F -->|Invoice + Complex| I[Detailed Processing]
    F -->|Invoice + Simple| J[Fast Processing]
    F -->|Receipt| J
    F -->|Unknown| E
    
    G --> K[Quality Check]
    H --> K
    I --> K
    J --> K
    E --> K
    
    K --> L{Quality OK?}
    L -->|No| M[Retry Decision]
    L -->|Yes| N[Human Review Check]
    
    M --> O{Retry Count < 2?}
    O -->|Yes| P[Retry Processing]
    O -->|No| N
    
    P --> K
    N --> Q{Need Review?}
    Q -->|Yes| R[Manual Review]
    Q -->|No| S[Complete]
    
    style E fill:#ffcdd2
    style G fill:#f8bbd9
    style I fill:#e1bee7
    style J fill:#c8e6c9
    style H fill:#dcedc8
```

**Маршрутизация:**
- 🔀 **Enhanced Analysis**: Confidence < 0.6
- 🔀 **Expert Analysis**: Complex contracts (>2000 chars)
- 🔀 **Detailed Processing**: Complex invoices
- 🔀 **Fast Processing**: Simple documents
- 🔀 **Standard Processing**: Standard contracts

**Ожидаемые результаты:**
- ✅ Автоматическое переключение между 5 путями обработки
- ✅ Retry механизмы с улучшенными моделями
- ✅ Human review triggers для edge cases

### Phase 4: Продвинутые retry механизмы

**Цель:** Circuit breakers и exponential backoff

```mermaid
sequenceDiagram
    participant C as Client
    participant CB as Circuit Breaker
    participant M1 as Fast Model
    participant M2 as Standard Model
    participant M3 as Reasoning Model
    
    C->>CB: Request
    CB->>M1: Attempt 1
    M1-->>CB: Timeout
    Note over CB: Wait 1s (exp backoff)
    CB->>M1: Attempt 2
    M1-->>CB: Error
    Note over CB: Wait 2s
    CB->>M1: Attempt 3
    M1-->>CB: Error
    Note over CB: Circuit OPEN for M1
    CB->>M2: Fallback to Standard
    M2->>CB: Success
    CB->>C: Result
    
    Note over CB: Fast Model Circuit Breaker
    Note over CB: State: CLOSED -> OPEN -> HALF-OPEN
```

**Retry стратегии по моделям:**
- **Fast Model**: 4 попытки, base_delay=0.5s
- **Standard Model**: 3 попытки, base_delay=1.0s  
- **Reasoning Model**: 2 попытки, base_delay=2.0s

**Circuit Breaker состояния:**
```mermaid
stateDiagram-v2
    [*] --> Closed
    Closed --> Open: failure_threshold_exceeded
    Open --> HalfOpen: timeout_elapsed
    HalfOpen --> Closed: success
    HalfOpen --> Open: failure
    
    note right of Open: Requests fail fast
    note right of Closed: Normal operation
    note right of HalfOpen: Test recovery
```

**Ожидаемые результаты:**
- ✅ Exponential backoff: 1s → 2s → 4s → 8s
- ✅ Circuit breakers для каждой модели
- ✅ Автоматическое восстановление (half-open → closed)
- ✅ 100% success rate для Standard/Reasoning моделей

### Phase 5: Сложные стратегии отказоустойчивости

**Цель:** 5-уровневые fallback стратегии с кэшированием

```mermaid
graph TD
    A[Request] --> B[Level 1: Full Service]
    B --> C{Success?}
    C -->|Yes| D[Return Result]
    C -->|No| E[Level 2: Degraded Service]
    
    E --> F{Success?}
    F -->|Yes| D
    F -->|No| G[Level 3: Minimal Service]
    
    G --> H{Success?}
    H -->|Yes| D
    H -->|No| I[Level 4: Cache Only]
    
    I --> J{Cache Hit?}
    J -->|Yes| K[Return Cached]
    J -->|No| L[Level 5: Human Handoff]
    
    L --> M[Queue for Human]
    
    style B fill:#4caf50
    style E fill:#ff9800
    style G fill:#f44336
    style I fill:#9c27b0
    style L fill:#607d8b
    
    subgraph "Service Levels"
        B1[All models available<br/>Full reasoning capability]
        E1[Limited models<br/>Reduced complexity]
        G1[Single model<br/>Basic responses]
        I1[No models<br/>Cached responses only]
        L1[No automation<br/>Human intervention]
    end
```

**Кэширование стратегии:**

```mermaid
graph LR
    A[Request] --> B{Exact Match?}
    B -->|Yes| C[Return Cached]
    B -->|No| D{Semantic Match?}
    D -->|Yes| E[Return Similar]
    D -->|No| F{Template Match?}
    F -->|Yes| G[Return Template]
    F -->|No| H[Process Request]
    
    H --> I[Cache Result]
    I --> J[Return Result]
```

**Model Voting System:**
```mermaid
graph TD
    A[Critical Decision] --> B[Fast Model Vote]
    A --> C[Standard Model Vote] 
    A --> D[Reasoning Model Vote]
    
    B --> E[Consensus Engine]
    C --> E
    D --> E
    
    E --> F{All Agree?}
    F -->|Yes| G[High Confidence Result]
    F -->|No| H{Majority?}
    H -->|Yes| I[Medium Confidence Result]
    H -->|No| J[Human Review Required]
```

**Ожидаемые результаты:**
- ✅ 5 уровней деградации сервиса
- ✅ Model voting для критических решений
- ✅ Intelligent caching (exact/semantic/template)
- ✅ Human handoff queue management
- ✅ 100% uptime даже при полных сбоях моделей

### Phase 6: Комплексный бизнес-процесс

**Цель:** Реальная система обработки кредитных заявок

```mermaid
graph TD
    subgraph "Loan Application Processing Workflow"
        A[Application Input] --> B[Initialize Processing]
        B --> C[Document Analysis]
        C --> D{Documents Valid?}
        D -->|No| E[Document Retry]
        E --> C
        D -->|Yes| F[Extract Applicant Info]
        
        F --> G[Risk Assessment]
        G --> H[Credit Check]
        H --> I[Financial Assessment]
        I --> J[Collateral Assessment]
        
        J --> K[Decision Engine]
        K --> L{Auto Decision?}
        L -->|Yes| M[Automated Approval/Denial]
        L -->|No| N[Human Review Queue]
        
        M --> O[Final Result]
        N --> P[Manual Review]
        P --> O
        
        E --> Q{Max Retries?}
        Q -->|Yes| R[Human Escalation]
        R --> N
    end
    
    subgraph "Multi-Model Coordination"
        C --> C1[Fast: Document Classification]
        F --> F1[Standard: Data Extraction]
        G --> G1[Reasoning: Risk Analysis]
        K --> K1[Voting: Final Decision]
    end
    
    subgraph "Quality Gates"
        QG1[Document Completeness]
        QG2[Data Validation]
        QG3[Risk Thresholds]
        QG4[Policy Compliance]
    end
    
    style M fill:#4caf50
    style N fill:#ff9800
    style R fill:#f44336
```

**Типы кредитных заявок:**

```mermaid
graph LR
    subgraph "Test Scenarios"
        A[High Quality Personal]
        B[Risky Business Loan]
        C[Insufficient Income]
    end
    
    subgraph "Expected Outcomes"
        A --> A1[Approved ✅]
        B --> B1[Manual Review ⚠️]
        C --> C1[Declined ❌]
    end
    
    subgraph "Processing Paths"
        A --> A2[Fast Track<br/>Standard Models]
        B --> B2[Detailed Analysis<br/>Reasoning Model]
        C --> C2[Automated Rejection<br/>Fast Model]
    end
```

**Детальный workflow обработки заявки:**

```mermaid
sequenceDiagram
    participant App as Application
    participant DA as Document Analyzer
    participant RE as Risk Engine
    participant DE as Decision Engine
    participant HQ as Human Queue
    
    App->>DA: Submit Documents
    DA->>DA: Extract Pay Stub Data
    DA->>DA: Extract Bank Statement
    DA->>DA: Extract Credit Report
    DA->>App: Document Analysis Complete
    
    App->>RE: Consolidated Data
    RE->>RE: Calculate Risk Score
    RE->>RE: Assess Debt-to-Income
    RE->>RE: Evaluate Credit History
    RE->>App: Risk Assessment Complete
    
    App->>DE: Risk Profile + Financial Data
    DE->>DE: Apply Business Rules
    DE->>DE: Calculate Approval Amount
    
    alt Auto Decision Possible
        DE->>App: Approved/Declined
    else Manual Review Required
        DE->>HQ: Queue for Review
        HQ->>App: Pending Manual Review
    end
    
    Note over App: Processing Time: 30-60s
    Note over DA: Models: Fast + Standard
    Note over RE: Model: Reasoning
    Note over DE: Model: Voting System
```

**Система принятия решений:**

```mermaid
flowchart TD
    A[Loan Application] --> B{Credit Score}
    B -->|>=750| C[High Quality Path]
    B -->|600-749| D[Standard Path]
    B -->|<600| E[High Risk Path]
    
    C --> C1{DTI Ratio}
    C1 -->|<0.3| C2[Auto Approve]
    C1 -->|0.3-0.4| C3[Conditional Approval]
    C1 -->|>0.4| D
    
    D --> D1{Employment}
    D1 -->|Stable| D2[Manual Review]
    D1 -->|Unstable| E
    
    E --> E1{Income vs Amount}
    E1 -->|Sufficient| D2
    E1 -->|Insufficient| E2[Auto Decline]
    
    style C2 fill:#4caf50
    style C3 fill:#ff9800
    style D2 fill:#2196f3
    style E2 fill:#f44336
```

**Ожидаемые результаты:**
- ✅ Обработка 3 типов заявок с разными исходами
- ✅ Multi-model coordination: 30+ model operations
- ✅ Advanced retry patterns: exponential backoff + circuit breakers
- ✅ Human escalation для edge cases
- ✅ Детальная трассировка каждого решения
- ✅ Enterprise-grade отказоустойчивость

## 🏗️ Архитектурные паттерны

### 1. Multi-Model Coordination

```mermaid
graph TB
    subgraph "Model Tier Strategy"
        A[Fast Model<br/>llama3.2:1b] --> A1[Classification<br/>Quick Decisions<br/>Simple Extraction]
        B[Standard Model<br/>llama3.2:3b] --> B1[Validation<br/>Structured Analysis<br/>Business Logic]
        C[Reasoning Model<br/>llama3.1:8b] --> C1[Complex Reasoning<br/>Risk Assessment<br/>Final Decisions]
    end
    
    subgraph "Coordination Patterns"
        D[Sequential] --> D1[Fast → Standard → Reasoning]
        E[Parallel] --> E1[All models vote on result]
        F[Conditional] --> F1[Route based on complexity]
    end
    
    style A fill:#e8f5e8
    style B fill:#e3f2fd
    style C fill:#fce4ec
```

### 2. State Management

```mermaid
classDiagram
    class DocumentProcessingState {
        +document_id: str
        +document_content: str
        +document_type: DocumentType
        +classification_confidence: float
        +extracted_data: Dict
        +validation_results: List
        +models_used: List
        +retry_count: int
        +processing_time: float
        +final_result: Dict
    }
    
    class LoanApplicationState {
        +application_id: str
        +applicant_info: ApplicantInfo
        +loan_details: LoanDetails
        +risk_assessment: RiskAssessment
        +final_decision: DecisionResult
        +processing_steps: List[ProcessingStep]
        +human_review_triggers: List
    }
    
    DocumentProcessingState --|> LoanApplicationState : extends for complex workflows
```

### 3. Error Handling Strategy

```mermaid
graph TD
    A[Error Occurred] --> B{Error Type}
    B -->|Timeout| C[Exponential Backoff]
    B -->|Parse Error| D[Fallback Parser]
    B -->|Model Unavailable| E[Circuit Breaker]
    B -->|Invalid Input| F[Validation Error]
    
    C --> G{Retry < Max?}
    G -->|Yes| H[Wait & Retry]
    G -->|No| I[Fallback Model]
    
    D --> J[Regex Extraction]
    D --> K[Template Matching]
    
    E --> L{Circuit State?}
    L -->|Open| M[Fail Fast]
    L -->|Half-Open| N[Test Request]
    
    F --> O[Human Review]
    
    I --> P[Next Model Tier]
    J --> Q[Partial Results]
    O --> R[Manual Processing]
```

## 🔧 Технические детали

### Модели и их роли

| Модель | Размер | Роль | Use Cases |
|--------|--------|------|-----------|
| **llama3.2:1b** | Fast | Classification, Quick decisions | Document type detection, Simple extraction |
| **llama3.2:3b** | Standard | Validation, Structured analysis | Data validation, Business rules |  
| **llama3.1:8b** | Reasoning | Complex reasoning, Final decisions | Risk assessment, Complex analysis |

### Retry конфигурации

```yaml
Fast Model:
  max_attempts: 4
  base_delay: 0.5s
  strategy: exponential_backoff
  circuit_breaker: 3 failures

Standard Model:
  max_attempts: 3
  base_delay: 1.0s
  strategy: exponential_backoff
  circuit_breaker: 2 failures

Reasoning Model:
  max_attempts: 2
  base_delay: 2.0s
  strategy: exponential_backoff
  circuit_breaker: 2 failures
```

### Fallback уровни

1. **Full Service** - все модели доступны
2. **Degraded Service** - ограниченные модели  
3. **Minimal Service** - одна модель
4. **Cache Only** - только кэшированные ответы
5. **Human Handoff** - ручная обработка

## 📊 Метрики производительности

### Ожидаемые результаты по фазам

```mermaid
gantt
    title Ожидаемое время выполнения фаз
    dateFormat X
    axisFormat %s
    
    section Phase 1
    Basic Setup: 0, 5s
    
    section Phase 2  
    Document Processing: 0, 30s
    
    section Phase 3
    Conditional Branching: 0, 60s
    
    section Phase 4
    Retry Mechanisms: 0, 45s
    
    section Phase 5
    Fallback Strategies: 0, 40s
    
    section Phase 6
    Complex Workflow: 0, 180s
```

### Success Rate цели

| Фаза | Target Success Rate | Key Metrics |
|------|-------------------|-------------|
| Phase 1 | 100% | Model initialization |
| Phase 2 | 95% | Document processing accuracy |
| Phase 3 | 90% | Correct routing decisions |
| Phase 4 | 100% | Circuit breaker functionality |
| Phase 5 | 100% | Fallback system resilience |
| Phase 6 | 85% | End-to-end business process |

## 🚦 Статусы и индикаторы

### Circuit Breaker статусы
- 🟢 **CLOSED** - Normal operation
- 🔴 **OPEN** - Failing fast, requests rejected
- 🟡 **HALF-OPEN** - Testing recovery

### Processing статусы
- ⏳ **IN_PROGRESS** - Currently processing
- ✅ **COMPLETED** - Successfully finished
- ❌ **FAILED** - Error occurred
- ⚠️ **REQUIRES_REVIEW** - Needs human intervention
- 🔄 **RETRYING** - Attempting retry

## 📖 Использование

### Запуск отдельных фаз

```bash
# Базовая настройка
python run_example.py basic

# Phase 2: Обработка документов
python run_example.py 2

# Phase 3: Условное ветвление  
python run_example.py 3

# Phase 4: Retry механизмы
python run_example.py 4

# Phase 5: Fallback стратегии
python run_example.py 5

# Phase 6: Комплексный workflow (финал)
python run_example.py 6
```

### Прямой запуск
```bash
python examples/phase2_document_processing.py
python examples/phase3_conditional_branching.py
python examples/phase4_retry_mechanisms.py
python examples/phase5_fallback_strategies.py
python examples/phase6_complex_workflow.py
```

## 🎓 Изученные паттерны

По завершении всех фаз вы овладеете:

### Enterprise Patterns
- ✅ **Multi-model orchestration** - координация разных моделей
- ✅ **Circuit breaker patterns** - защита от каскадных сбоев
- ✅ **Exponential backoff** - интеллектуальные повторные попытки
- ✅ **Graceful degradation** - плавная деградация сервиса
- ✅ **Human-in-the-loop** - эскалация к человеку

### LangGraph Expertise  
- ✅ **Conditional workflows** - динамическая маршрутизация
- ✅ **State management** - управление сложным состоянием
- ✅ **Node composition** - композиция обработчиков
- ✅ **Error boundaries** - изоляция ошибок
- ✅ **Quality gates** - контрольные точки качества

### Production Readiness
- ✅ **Comprehensive monitoring** - детальное логирование
- ✅ **Performance optimization** - кэширование и оптимизация
- ✅ **Fault tolerance** - отказоустойчивость
- ✅ **Scalability patterns** - паттерны масштабирования
- ✅ **Business logic integration** - интеграция бизнес-логики

## 🎉 Финальные достижения

После прохождения всех 6 фаз вы создадите **production-ready** систему со следующими характеристиками:

```mermaid
mindmap
  root((Production Ready LangGraph System))
    Reliability
      Circuit Breakers
      Retry Mechanisms  
      Fallback Strategies
      Error Recovery
    Performance
      Model Coordination
      Intelligent Caching
      Response Optimization
      Resource Management  
    Scalability
      Horizontal Scaling
      Load Distribution
      Queue Management
      Async Processing
    Observability
      Detailed Logging
      Performance Metrics
      Health Monitoring
      Decision Tracing
    Business Value
      Automated Decisions
      Human Escalation
      Audit Trails
      Compliance Ready
```

**Готовы создавать enterprise AI-системы с LangGraph!** 🚀

---

## 👨‍💻 Behind the Code

Этот проект возник из понимания того, что современные ИИ-системы требуют не просто "работающий код", а корпоративную архитектуру. Изучая LangGraph, я столкнулся с недостатком практических примеров сложных многомодельных процессов с правильной обработкой ошибок и стратегиями отказоустойчивости. Иногда лучшие обучающие проекты - это те, которые показывают реальные паттерны, а не игрушечные примеры.

**Больше практических технических проектов**: [@it_jagger](https://t.me/it_jagger)

## Поддержать проект:

ETH (Mainnet): `0x765885e6Cb9e40E1504F80272A7b5B60ffF7b92d`  
USDT (SOL): `GRNmdL1mpdBhgY8cFZggUo5k9eG5ic5QtA6NFTv6ZAbw`

---

*Проект демонстрирует real-world паттерны для построения надежных AI-систем в production среде.*