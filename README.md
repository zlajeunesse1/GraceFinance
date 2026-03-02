# GraceFinance — Frontend

> Smarter Finance is Right Around the Corner™

## Quick Start

```bash
# Install dependencies
npm install

# Start dev server (runs on http://localhost:3000)
npm run dev

# Build for production
npm run build
```

## Project Structure

```
gracefinance/
├── public/
│   └── favicon.svg              # GraceFinance logo favicon
├── src/
│   ├── api/
│   │   └── auth.js              # Auth API calls (stubbed for FastAPI)
│   ├── components/
│   │   ├── AuthLayout.jsx       # Shared auth page wrapper
│   │   ├── Button.jsx           # Reusable button with loading state
│   │   ├── Input.jsx            # Reusable form input with validation
│   │   ├── Logo.jsx             # GraceFinance logo
│   │   ├── ParticleBackground.jsx # Animated canvas background
│   │   └── SocialAuth.jsx       # Google/Apple login buttons + divider
│   ├── context/
│   │   └── AuthContext.jsx      # Auth state management (user, token)
│   ├── hooks/                   # Custom hooks (future)
│   ├── pages/
│   │   ├── DashboardPage.jsx    # Post-login dashboard (placeholder)
│   │   ├── ForgotPasswordPage.jsx
│   │   ├── LoginPage.jsx
│   │   └── SignupPage.jsx
│   ├── App.jsx                  # Router + protected/public routes
│   ├── index.css                # Tailwind + global styles
│   └── main.jsx                 # Entry point
├── index.html
├── package.json
├── postcss.config.js
├── tailwind.config.js
└── vite.config.js               # Vite config with /api proxy to FastAPI
```

## Connecting to FastAPI

The Vite dev server proxies `/api` requests to `http://localhost:8000` (your FastAPI backend).

### Expected Endpoints

| Method | Endpoint           | Body                              | Response                     |
|--------|--------------------|------------------------------------|------------------------------|
| POST   | `/api/auth/login`  | `{ email, password }`             | `{ token, user }`            |
| POST   | `/api/auth/signup` | `{ name, email, password }`       | `{ token, user }`            |
| POST   | `/api/auth/forgot` | `{ email }`                       | `{ message }`                |
| GET    | `/api/auth/me`     | — (Bearer token in header)        | `{ id, name, email }`        |

To connect, open `src/api/auth.js` and uncomment the real `apiFetch` calls (the TODO comments show you exactly where).

## Tech Stack

- **React 18** + **Vite 6** — fast dev server & builds
- **React Router 6** — client-side routing with protected routes
- **Tailwind CSS 3** — utility-first styling with custom GraceFinance theme
- **Context API** — lightweight auth state management

## What's Next

- [ ] Build FastAPI auth endpoints (login, signup, forgot password)
- [ ] Set up PostgreSQL user table
- [ ] Implement JWT token auth
- [ ] Add OAuth (Google, Apple) social login
- [ ] Build out the dashboard
- [ ] Add Claude API integration for financial coaching
