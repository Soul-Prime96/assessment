# 🤖 Business Operations AI Agent

A production-ready, **multi-agent AI system** that streamlines business operations through intelligent data analysis, automated workflow management, exception handling, and human-in-the-loop oversight.

Built with the **Google Antigravity SDK** and powered by **Gemini**.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📊 **Data Analysis** | Ingests CSV/JSON, computes KPIs, detects trends and anomalies |
| 🚨 **Exception Monitoring** | Evaluates KPIs against configurable business rules |
| 💡 **Smart Recommendations** | Generates ranked, structured action recommendations |
| ⚙️ **Workflow Automation** | Auto-generates reports, queues notifications, archives data |
| 👤 **Human Oversight** | Mandatory approval gate for HIGH/CRITICAL actions |
| 📋 **Audit Trail** | Every decision logged to `output/audit_log.json` |

---

## 🏗️ Architecture

```
Orchestrator Agent
├── Data Analyst Subagent     → KPIs, trends, anomalies
├── Exception Monitor Subagent → Rule violations, severity classification
├── Recommender Subagent      → Ranked action recommendations
└── Workflow Manager Subagent  → Reports, notifications, archiving
```

---

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.10+
- Anaconda (or any Python 3.10+ environment)
- A free Gemini API key from [aistudio.google.com/app/api-keys](https://aistudio.google.com/app/api-keys)

### 2. Install Dependencies

```bash
cd biz-ops-agent
pip install -r requirements.txt
```

### 3. Configure API Key

```bash
copy .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

Or set it directly:
```bash
set GEMINI_API_KEY=your_key_here   # Windows
export GEMINI_API_KEY=your_key_here  # Linux/Mac
```

### 4. Run

#### 🌐 Launch Web Dashboard (Streamlit):
```bash
streamlit run app.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser to view the interactive dashboard, review exceptions, approve actions, and generate reports.

#### 🚀 Deploy to Cloud (Streamlit Community Cloud):
1. Go to **[share.streamlit.io](https://share.streamlit.io)** and log in with your GitHub account.
2. Click **"New app"**.
3. Select your repository: `SARTHAKGUPTAAIML0119/biz-ops-agent`.
4. Main file path: `app.py`.
5. Click **"Deploy"**! You will get an instant public live URL (e.g. `https://biz-ops-agent.streamlit.app`).

#### 💻 Command Line Interface:

**Interactive mode:**
```bash
python main.py
```

**Full analysis on the included demo data:**
```bash
python main.py --mode full --file data/sample_sales.csv
```

**Other modes:**
```bash
python main.py --mode analyze    # KPI analysis only
python main.py --mode monitor    # Analysis + exception detection
python main.py --mode recommend  # Analysis + exceptions + recommendations
python main.py --mode workflow   # Reporting workflow only
```

**Autonomous mode (no human prompts):**
```bash
python main.py --mode full --no-interactive
```

---

## 📁 Project Structure

```
biz-ops-agent/
├── main.py                    # CLI entry point
├── orchestrator.py            # Central orchestrator with safety policies
├── agents/
│   ├── data_analyst.py        # Data analysis subagent config
│   ├── workflow_manager.py    # Workflow automation subagent config
│   ├── exception_monitor.py   # Exception detection subagent config
│   └── recommender.py         # Recommendation subagent config
├── tools/
│   ├── data_tools.py          # Data ingestion, KPIs, trends, anomalies
│   ├── workflow_tools.py      # Reports, notifications, archiving
│   ├── exception_tools.py     # Rule engine, threshold checks, audit log
│   └── recommendation_tools.py # Action generation and prioritization
├── models/
│   └── schemas.py             # Pydantic data contracts
├── data/
│   ├── sample_sales.csv       # 1,800-row demo dataset (90 days × 5 products × 4 regions)
│   └── business_rules.json    # Configurable business thresholds
└── output/                    # Generated reports, audit logs, notifications
```

---

## ⚙️ Configuring Business Rules

Edit `data/business_rules.json` to match your operational targets:

```json
{
  "revenue_drop_threshold": 0.15,     // 15% revenue decline triggers alert
  "margin_floor_pct": 25.0,           // Gross margin below 25% is an exception
  "inventory_critical_days": 7,       // <7 days of inventory = CRITICAL
  "refund_rate_max_pct": 5.0,         // >5% refund rate triggers investigation
  "avg_revenue_per_unit_floor": 15.0  // <$15 ASP triggers pricing review
}
```

---

## 👤 Human Oversight

The system enforces human review at multiple levels:

1. **Recommendation flags**: Any `HIGH` or `CRITICAL` severity action has `requires_human_approval: true`
2. **Tool-level policy**: `archive_data` requires explicit `[y/N]` confirmation in interactive mode
3. **Audit log**: Every decision (automated or human) is logged to `output/audit_log.json`
4. **Budget controls**: Max 40 model calls and 60 tool calls per session prevents runaway execution

---

## 📊 Demo Dataset

The included `sample_sales.csv` contains 1,800 synthetic records with:
- **90 days** of sales data (Aug–Oct 2024)
- **5 products**: Widget A, Widget B, Gadget Pro, Gadget Lite, SmartKit
- **4 regions**: North, South, East, West
- **Intentional anomalies** to trigger the exception system:
  - Revenue dip of ~35% in days 60–75 (triggers `revenue_drop_threshold`)
  - Revenue spike on Gadget Pro/North on day 45 (triggers anomaly detection)

---

## 📋 Output Files

After running, check the `output/` directory:

| File | Contents |
|------|----------|
| `business_report_*.md` | Markdown KPI/exceptions/recommendations report |
| `business_report_*.html` | Styled HTML report for stakeholders |
| `audit_log.json` | All exceptions and decisions logged |
| `notification_queue.json` | Queued operations team notifications |
| `session_transcript.json` | Full agent response history |
| `archive/` | Timestamped copies of processed data files |

---

## 🔒 Security & Safety

- Shell command execution (`run_command`) is **always denied**
- File writes are scoped to the `output/` directory by tool design
- Budget limits prevent runaway agent loops
- Human approval is **mandatory** for irreversible high-impact actions
- API key is never hardcoded — read from environment only
