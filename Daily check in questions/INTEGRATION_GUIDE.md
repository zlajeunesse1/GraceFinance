# GraceFinance Daily Check-In Integration Guide

## 🎯 What You're Building

A sophisticated emotional intelligence layer that sits BEFORE traditional finance dashboards. Users get 2-3 thoughtful questions about their money mindset every time they log in, creating psychological engagement before showing them numbers.

---

## 📁 Files You Now Have

1. **money_questions_database.json** - 60 starter questions (foundation for 5,000)
2. **checkin_api.py** - FastAPI backend routes
3. **DailyCheckIn.jsx** - React frontend component
4. **database_schema.py** - PostgreSQL schema
5. **question_generation_framework.md** - Guide to scale to 5,000 questions

---

## 🔧 Integration Steps

### Step 1: Database Setup

```bash
# Add the new tables to your PostgreSQL database
# In your project directory:

# 1. Copy the schema file
cp database_schema.py app/models/checkin_models.py

# 2. Create migration
alembic revision --autogenerate -m "Add daily checkin tables"

# 3. Run migration
alembic upgrade head
```

**Tables created:**
- `user_checkin_responses` - Stores all answers
- `user_stress_trends` - Aggregated daily metrics
- `user_financial_profiles` - User context for personalization
- `checkin_insights` - Auto-generated insights
- `question_rotation_logs` - Prevents question repetition

### Step 2: Backend Integration

```python
# In your main FastAPI app (main.py or app.py):

from checkin_api import router as checkin_router

app = FastAPI()

# Include the check-in routes
app.include_router(checkin_router)

# The routes will be available at:
# - GET /api/checkin/daily-questions
# - POST /api/checkin/submit-answers
# - GET /api/checkin/analytics
# - GET /api/checkin/insights
```

**Update with your actual auth:**

```python
# In checkin_api.py, replace mock dependencies with:

from app.auth import get_current_user  # Your actual auth
from app.database import get_db        # Your actual DB session

# Then uncomment the Depends() in route signatures
```

### Step 3: Load Question Database

```python
# In your app startup (main.py):

import json
import os

@app.on_event("startup")
async def load_questions():
    """Load questions database into memory on startup"""
    questions_path = os.path.join(os.path.dirname(__file__), "money_questions_database.json")
    
    with open(questions_path, "r") as f:
        global QUESTIONS_DB
        QUESTIONS_DB = json.load(f)
    
    print(f"✅ Loaded {len(QUESTIONS_DB['questions'])} questions")
```

### Step 4: Frontend Integration

**Option A: Modal Overlay (Recommended)**
Show check-in as modal on login, user can skip or complete:

```jsx
// In your main App.jsx or Dashboard.jsx

import { useState, useEffect } from 'react';
import DailyCheckIn from './components/DailyCheckIn';

function Dashboard() {
  const [showCheckIn, setShowCheckIn] = useState(false);
  
  useEffect(() => {
    // Check if user already completed today's check-in
    checkIfCheckInNeeded();
  }, []);
  
  const checkIfCheckInNeeded = async () => {
    const lastCheckIn = localStorage.getItem('lastCheckInDate');
    const today = new Date().toDateString();
    
    if (lastCheckIn !== today) {
      setShowCheckIn(true);
    }
  };
  
  const handleCheckInComplete = (insights) => {
    localStorage.setItem('lastCheckInDate', new Date().toDateString());
    setShowCheckIn(false);
    
    // Show insights to user
    if (insights.length > 0) {
      // Display insights modal or notification
    }
  };
  
  const handleCheckInSkip = () => {
    setShowCheckIn(false);
  };
  
  return (
    <>
      {showCheckIn && (
        <DailyCheckIn 
          onComplete={handleCheckInComplete}
          onSkip={handleCheckInSkip}
        />
      )}
      
      {/* Your regular dashboard */}
      <YourDashboardContent />
    </>
  );
}
```

**Option B: Dedicated Route**
Make check-in a required step before dashboard:

```jsx
// In your routing (App.jsx):

<Routes>
  <Route path="/checkin" element={<DailyCheckIn />} />
  <Route path="/dashboard" element={<ProtectedDashboard />} />
</Routes>

// In ProtectedDashboard:
useEffect(() => {
  const lastCheckIn = localStorage.getItem('lastCheckInDate');
  const today = new Date().toDateString();
  
  if (lastCheckIn !== today) {
    navigate('/checkin');
  }
}, []);
```

### Step 5: Install Required Packages

```bash
# Backend
pip install fastapi sqlalchemy psycopg2-binary alembic python-jose[cryptography] --break-system-packages

# Frontend
npm install framer-motion
# or
yarn add framer-motion
```

### Step 6: Environment Variables

```bash
# Add to your .env file:

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/gracefinance

# Check-in Settings
CHECKIN_QUESTIONS_PER_SESSION=3
CHECKIN_ROTATION_DAYS=30
CHECKIN_MIN_STRESS_FOR_ALERT=8
```

---

## 🎨 Customization Options

### Change Colors to Match Your Brand

In `DailyCheckIn.jsx`, update the Tailwind classes:

```jsx
// Current: Teal/Emerald theme
className="bg-gradient-to-r from-teal-500 to-emerald-500"

// Change to your brand colors:
className="bg-gradient-to-r from-blue-500 to-purple-500"
className="bg-gradient-to-r from-pink-500 to-rose-500"
className="bg-gradient-to-r from-orange-500 to-amber-500"
```

### Adjust Number of Questions

```python
# In checkin_api.py:

# Change from 3 to 2 questions:
selected_questions = select_daily_questions(
    user_context=user_context,
    num_questions=2,  # ← Change this
    exclude_ids=user_context["recently_answered_ids"]
)
```

### Change Question Rotation Period

```python
# In checkin_api.py, update user_context query:

"recently_answered_ids": get_recently_answered_questions(
    user_id=current_user.id,
    days=30  # ← Change this (14 days = faster rotation, 60 days = slower)
)
```

---

## 📊 Analytics & Insights Setup

### Daily Cron Job to Calculate Trends

```python
# Create: app/tasks/calculate_daily_trends.py

from sqlalchemy import func
from app.models import UserCheckInResponse, UserStressTrend
from datetime import datetime, timedelta

async def calculate_daily_stress_trends():
    """
    Run this daily to aggregate stress scores
    """
    yesterday = datetime.now() - timedelta(days=1)
    
    # Get all users who answered yesterday
    users = db.query(UserCheckInResponse.user_id).filter(
        UserCheckInResponse.answered_at >= yesterday
    ).distinct()
    
    for user in users:
        # Calculate average stress
        stress_responses = db.query(func.avg(UserCheckInResponse.answer_numeric)).filter(
            UserCheckInResponse.user_id == user.user_id,
            UserCheckInResponse.question_category == "money_stress",
            UserCheckInResponse.answered_at >= yesterday
        ).scalar()
        
        # Create/update trend record
        trend = UserStressTrend(
            user_id=user.user_id,
            date=yesterday,
            average_stress=stress_responses
        )
        db.add(trend)
    
    db.commit()
```

Schedule with cron:
```bash
# Run daily at 2 AM
0 2 * * * cd /path/to/gracefinance && python -c "from app.tasks.calculate_daily_trends import calculate_daily_stress_trends; calculate_daily_stress_trends()"
```

### Insight Generation Logic

```python
# In checkin_api.py, enhance submit_answers endpoint:

def generate_insights_from_responses(user_id, recent_responses):
    """
    Auto-generate insights based on patterns
    """
    insights = []
    
    # High stress detection
    high_stress_count = sum(1 for r in recent_responses if r.answer_numeric >= 8)
    if high_stress_count >= 3:
        insights.append({
            "type": "high_stress_alert",
            "title": "We're Here to Help",
            "description": "You've reported high stress 3 times this week. Let's create an action plan together.",
            "action_button": "Get Support"
        })
    
    # Positive trend detection
    stress_trend = get_stress_trend(user_id, days=14)
    if len(stress_trend) >= 7:
        recent_avg = sum(stress_trend[-3:]) / 3
        older_avg = sum(stress_trend[:3]) / 3
        
        if recent_avg < older_avg - 1.5:  # Significant improvement
            insights.append({
                "type": "positive_trend",
                "title": "Stress Decreasing! 📉",
                "description": f"Your stress has dropped {int((older_avg - recent_avg) * 10)}% over the past 2 weeks!",
                "emoji": "🎉"
            })
    
    # Pattern detection (bill stress timing)
    day_of_month = datetime.now().day
    if 25 <= day_of_month <= 31:
        bill_stress = check_historical_stress_at_month_end(user_id)
        if bill_stress:
            insights.append({
                "type": "pattern_detected",
                "title": "End of Month Pattern",
                "description": "You tend to feel stressed around bill time. Let's set up automatic reminders.",
                "action_button": "Create Bill Calendar"
            })
    
    return insights
```

---

## 🚀 Feature Roadmap

### Phase 1: MVP (Week 1-2)
- ✅ Basic question delivery
- ✅ Response storage
- ✅ Simple analytics dashboard

### Phase 2: Personalization (Week 3-4)
- [ ] Life stage detection
- [ ] Smart question routing
- [ ] Pattern detection
- [ ] Stress trend graphs

### Phase 3: AI Integration (Week 5-8)
- [ ] Claude API integration for coaching
- [ ] Personalized insights generation
- [ ] Action plan creation
- [ ] Follow-up question suggestions

### Phase 4: Advanced Features (Week 9-12)
- [ ] Peer comparisons (anonymous)
- [ ] Community insights
- [ ] Gamification (streaks, badges)
- [ ] Export data for therapists

---

## 🧪 Testing

### Test the API

```bash
# Start your FastAPI server
uvicorn main:app --reload

# Test getting questions
curl http://localhost:8000/api/checkin/daily-questions \
  -H "Authorization: Bearer YOUR_TOKEN"

# Test submitting answers
curl -X POST http://localhost:8000/api/checkin/submit-answers \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '[
    {"question_id": "MS001", "answer": 7},
    {"question_id": "MG002", "answer": "Build emergency fund"}
  ]'
```

### Test the Frontend

```jsx
// Add a test button in your dev environment:

<button onClick={() => setShowCheckIn(true)}>
  Test Check-In Flow
</button>
```

---

## 📈 Success Metrics

Track these KPIs:

1. **Engagement Rate**: % users who complete check-in vs skip
2. **Completion Rate**: % who finish all questions vs abandon
3. **Average Time**: How long users spend on check-in
4. **Stress Trends**: Are user stress scores improving over time?
5. **Insight Clicks**: Do users act on insights generated?
6. **Return Rate**: Do users come back daily?

---

## 🐛 Common Issues & Solutions

### Issue: Questions repeating too quickly
**Solution**: Increase rotation period in `recently_answered_ids` query

### Issue: Users always skipping check-in
**Solution**: Reduce to 2 questions, make them more engaging, or gamify with streaks

### Issue: High drop-off on open text questions
**Solution**: Replace with multiple choice, or make optional

### Issue: Database getting large with responses
**Solution**: Archive responses older than 1 year to separate table

---

## 🎓 Next Steps

1. **Copy files to your project**
   - Place `checkin_api.py` in `app/routers/`
   - Place `DailyCheckIn.jsx` in `frontend/src/components/`
   - Add database models from `database_schema.py`

2. **Run migrations**
   ```bash
   alembic revision --autogenerate -m "Add checkin tables"
   alembic upgrade head
   ```

3. **Test locally**
   - Start backend: `uvicorn main:app --reload`
   - Start frontend: `npm run dev`
   - Create account, login, see check-in

4. **Generate more questions**
   - Use `question_generation_framework.md` as guide
   - Target 100 questions/week
   - Focus on high-impact categories first

5. **Deploy & Monitor**
   - Deploy to production
   - Track engagement metrics
   - Iterate based on user feedback

---

## 💡 Pro Tips

- **Start with 2 questions** instead of 3 - higher completion rate
- **Vary question types** - don't show 3 scales in a row
- **Time it right** - check-in works best in the morning (10-11 AM)
- **Make skip easy** - don't force it, you want willing engagement
- **Celebrate streaks** - "7 days in a row! 🔥"
- **Show impact** - "Your stress is down 20% this month!"

---

## 🆘 Need Help?

Common questions answered:

**Q: Can users go back and change answers?**
A: Not by default, but you can add an edit feature to the analytics page

**Q: Should check-in be required?**
A: No - make it optional with easy skip. Forced engagement backfires.

**Q: How do I handle users who always pick "5" on scales?**
A: Flag as low-quality data, maybe prompt: "We notice you're picking neutral - everything okay?"

**Q: When should insights appear?**
A: Immediately after completing check-in, and in a dedicated insights section

---

**You're ready to build! 🚀**

This emotional intelligence layer will set GraceFinance apart from every other finance app. You're not just tracking money - you're understanding the human behind the numbers.
