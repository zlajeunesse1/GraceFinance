# 🐾 GraceFinance Backend API
### Smarter Finance is Right Around the Corner™

---

## Quick Start

### 1. Install Dependencies
```bash
cd gracefinance
pip install -r requirements.txt
```

### 2. Set Up PostgreSQL
```bash
# Install PostgreSQL if you don't have it
# macOS: brew install postgresql
# Ubuntu: sudo apt install postgresql

# Create the database
createdb gracefinance

# Or via psql:
psql -U postgres
CREATE DATABASE gracefinance;
\q
```

### 3. Configure Environment
```bash
cp .env.example .env
# Edit .env with your actual values:
# - DATABASE_URL (your PostgreSQL connection string)
# - SECRET_KEY (generate a random string)
# - STRIPE keys (from stripe.com dashboard)
# - ANTHROPIC_API_KEY (from console.anthropic.com)
```

### 4. Run the Server
```bash
uvicorn main:app --reload --port 8000
```

### 5. Open API Docs
Go to **http://localhost:8000/docs** — this is your interactive API documentation.
You can test every endpoint right from the browser.

---

## API Endpoints

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/signup` | Create new account |
| POST | `/auth/login` | Login, get JWT token |
| GET | `/auth/me` | Get current user profile |
| PUT | `/auth/onboarding` | Save onboarding financial data |

### Dashboard
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/dashboard/` | Full dashboard data (one call powers entire UI) |

### Debts
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/debts/` | List all debts (sorted by APR) |
| POST | `/debts/` | Add a debt |
| PUT | `/debts/{id}` | Update a debt |
| DELETE | `/debts/{id}` | Remove a debt |

### Transactions
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/transactions/` | Recent transactions (30 days default) |
| POST | `/transactions/` | Add transaction (auto-categorized) |
| POST | `/transactions/bulk` | Bulk import transactions |
| DELETE | `/transactions/{id}` | Delete transaction |

### Bills
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/bills/` | List all bills |
| POST | `/bills/` | Add a bill |
| PUT | `/bills/{id}` | Update a bill |
| DELETE | `/bills/{id}` | Remove a bill |

### Billing (Stripe)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/billing/checkout` | Create Stripe checkout session |
| POST | `/billing/webhook` | Stripe webhook handler |
| GET | `/billing/portal-url` | Customer billing portal |

---

## Project Structure
```
gracefinance/
├── main.py                    # FastAPI app entry point
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variable template
├── app/
│   ├── config.py             # Settings from environment
│   ├── database.py           # PostgreSQL connection
│   ├── models/
│   │   ├── __init__.py
│   │   └── models.py         # SQLAlchemy models (User, Debt, Transaction, Bill)
│   ├── schemas/
│   │   └── __init__.py       # Pydantic request/response schemas
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth.py           # JWT + password hashing
│   │   └── finance.py        # Core financial logic (avalanche, categorizer, etc.)
│   └── routers/
│       ├── __init__.py
│       ├── auth.py           # Signup, login, profile
│       ├── dashboard.py      # Main dashboard endpoint
│       ├── debts.py          # Debt CRUD
│       ├── transactions.py   # Transaction CRUD + auto-categorization
│       ├── bills.py          # Bill CRUD
│       └── billing.py        # Stripe integration
└── tests/
```

---

## What Came From Your Streamlit Prototype

| Streamlit Code | Now Lives In |
|----------------|-------------|
| `categorize()` function | `app/services/finance.py` → `categorize_transaction()` |
| `NEEDS` set | `app/services/finance.py` → `NEEDS_CATEGORIES` |
| Avalanche debt allocation | `app/services/finance.py` → `calculate_avalanche()` |
| Debt-free timeline calc | `app/services/finance.py` → `months_to_debt_free()` |
| Savings rate logic | `app/routers/dashboard.py` → computed in `get_dashboard()` |
| Cash buffer logic | `app/routers/dashboard.py` → computed in `get_dashboard()` |
| Hardcoded DEBTS list | `app/models/models.py` → `Debt` table (per-user) |
| CSV upload | `app/routers/transactions.py` → `/transactions/bulk` endpoint |

---

## Next Steps
1. Get the server running locally with `uvicorn main:app --reload`
2. Open http://localhost:8000/docs and test the signup endpoint
3. Connect your React frontend to these endpoints
4. Set up Stripe test keys at https://dashboard.stripe.com/test
5. Deploy to AWS when ready

**You own every line of this code. No lock-in. No platform fees. This is yours.**
