# DevPilot - Complete Setup & Deployment Guide

## 🚀 Quick Start (5 Minutes)

### Prerequisites
- Python 3.10+
- Node.js 18+
- Redis (via Docker or local)
- Git

### 1. Clone & Setup Backend

```bash
cd "DevPilot-main Phase 2"
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file:
```env
# LLM API Keys
GEMINI_API_KEY=your_gemini_key_here
GROQ_API_KEY=your_groq_key_here
OPENAI_API_KEY=your_openai_key_here

# Redis
REDIS_URL=redis://localhost:6379

# Database
DATABASE_URL=sqlite:///./devpilot.db
```

### 3. Start Redis

```bash
docker run -d -p 6379:6379 redis:7-alpine
```

### 4. Run Backend

```bash
python app_api.py
```

Backend runs at `http://localhost:8000`

### 5. Setup Frontend (Optional - TypeScript UI)

```bash
cd devpilot-ui
npm install
npm run dev
```

Frontend runs at `http://localhost:3000`

### 6. Run Streamlit UI (Alternative)

```bash
streamlit run app_streamlit.py
```

Streamlit runs at `http://localhost:8501`

---

## 📦 Installation Details

### Install Python Dependencies

```bash
pip install -r requirements.txt
```

**Note**: This includes pytest, which was missing:
```bash
pip install pytest pytest-asyncio pytest-cov
```

### Install TypeScript Frontend

```bash
cd devpilot-ui
npm install
```

---

## 🧪 Testing

### Run Python Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src/dev_pilot --cov-report=html

# Run specific test file
pytest tests/test_agents.py -v
```

### Test FastAPI Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Get agent status
curl http://localhost:8000/api/v2/agents/status

# View API docs
open http://localhost:8000/docs
```

### Test WebSocket

```bash
# Use wscat
npm install -g wscat
wscat -c ws://localhost:8000/ws/agents
```

---

## 🔒 Security Configuration

### 1. API Key Management

**Don't store keys in code!** Use environment variables or a secrets manager.

```python
# ✅ Good
api_key = os.getenv("GEMINI_API_KEY")

# ❌ Bad
api_key = "hardcoded_key_here"
```

### 2. Add Rate Limiting

Install:
```bash
pip install slowapi
```

Update `fastapi_app.py`:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/api/v2/projects")
@limiter.limit("10/minute")
async def create_project(...):
    ...
```

### 3. Add Authentication

```bash
pip install python-jose[cryptography] passlib[bcrypt]
```

See `analysis_report.md` for full authentication implementation.

---

## 🚀 Production Deployment

### Option 1: Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: devpilot
      POSTGRES_USER: devpilot
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  backend:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - redis
      - postgres
    environment:
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://devpilot:${DB_PASSWORD}@postgres:5432/devpilot
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - GROQ_API_KEY=${GROQ_API_KEY}
    volumes:
      - ./logs:/app/logs

  frontend:
    build: ./devpilot-ui
    ports:
      - "3000:3000"
    depends_on:
      - backend
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000

volumes:
  redis_data:
  postgres_data:
```

Run:
```bash
docker-compose up -d
```

### Option 2: Manual Deployment

1. **Setup server** (Ubuntu/Debian):
```bash
sudo apt update
sudo apt install python3.10 python3-pip nginx redis-server postgresql
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
pip install gunicorn
```

3. **Run with Gunicorn**:
```bash
gunicorn src.dev_pilot.api.fastapi_app:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile logs/access.log \
  --error-logfile logs/error.log
```

4. **Configure Nginx**:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

5. **SSL with Certbot**:
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## 📊 Monitoring

### Add Logging

```python
from loguru import logger

# Configure
logger.add(
    "logs/devpilot_{time}.log",
    rotation="1 day",
    retention="30 days",
    level="INFO"
)
```

### Health Monitoring

```bash
# Check health endpoint
curl http://localhost:8000/health

# Monitor logs
tail -f logs/*.log
```

### Performance Monitoring

Install Prometheus/Grafana for metrics.

---

## 🔧 Troubleshooting

### Issue: Redis Connection Failed
```bash
# Check if Redis is running
redis-cli ping
# Should return: PONG

# Restart Redis
docker restart redis
```

### Issue: Module Not Found
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Issue: Port Already in Use
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Or use different port
uvicorn app:app --port 8001
```

### Issue: WebSocket Connection Failed
- Check CORS settings in FastAPI
- Ensure WebSocket endpoint is `/ws/*` not `/api/ws/*`
- Verify firewall allows WebSocket connections

---

## 📚 Additional Resources

- **API Documentation**: http://localhost:8000/docs
- **Analysis Report**: See `analysis_report.md` for all identified issues
- **TypeScript Frontend**: See `typescript-frontend-guide.md`
- **Architecture**: See original planning documents in `plans/` directory

---

## ✅ Pre-flight Checklist

Before deploying to production:

- [ ] All environment variables configured
- [ ] Redis running and accessible
- [ ] Database migrations applied
- [ ] API keys secured (not in code)
- [ ] Rate limiting enabled
- [ ] Authentication implemented
- [ ] HTTPS/SSL configured
- [ ] Logging configured
- [ ] Monitoring setup
- [ ] Backup strategy in place
- [ ] Tests passing (pytest)
- [ ] Load testing completed

---

## 🎯 Next Steps

1. **Fix Critical Issues** - See `analysis_report.md` for 43 identified drawbacks
2. **Add Authentication** - Implement JWT/OAuth2
3. **Complete Testing** - Achieve >80% coverage
4. **Performance Testing** - Load test with realistic data
5. **Production Deploy** - Use Docker Compose or K8s

---

*Last Updated: December 30, 2024*
*Status: 90% Feature Complete - Production Hardening Needed*
