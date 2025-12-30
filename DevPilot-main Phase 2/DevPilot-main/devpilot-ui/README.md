# DevPilot TypeScript Frontend - README

## 🚀 Quick Start

```bash
npm install
npm run dev
```

Visit `http://localhost:3000`

## 📦 Tech Stack

- **Next.js 14** - React framework
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **Axios** - HTTP client
- **Zustand** - State management
- **React Hot Toast** - Notifications
- **Lucide React** - Icons

## 🏗️ Project Structure

```
devpilot-ui/
├── app/
│   ├── layout.tsx              # Root layout
│   ├── page.tsx                # Home page
│   ├── dashboard/              # Dashboard pages
│   └── globals.css             # Global styles
├── components/
│   ├── sdlc/                   # SDLC components
│   ├── agents/                 # Agent components
│   ├── forms/                  # Form components
│   └── ui/                     # UI primitives
├── lib/
│   ├── api-client.ts           # API client
│   ├── websocket.ts            # WebSocket manager
│   ├── store.ts                # State management
│   └── utils.ts                # Utilities
└── hooks/                      # Custom React hooks
```

## 🔧 Configuration

Create `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

## 🎨 Key Features

- ✅ Real-time WebSocket updates
- ✅ SDLC progress tracking
- ✅ Agent status monitoring
- ✅ Project management
- ✅ Stage approval workflow
- ✅ Toast notifications
- ✅ Responsive design

## 📝 Available Scripts

```bash
npm run dev          # Start development server
npm run build        # Build for production
npm run start        # Start production server
npm run lint         # Run ESLint
npm run type-check   # Run TypeScript compiler
```

## 🔗 API Integration

The frontend connects to FastAPI backend at `http://localhost:8000`.

### Endpoints Used:
- `POST /api/v2/projects` - Create project
- `GET /api/v2/projects/{id}/status` - Get status
- `POST /api/v2/projects/{id}/approve` - Approve stage
- `POST /api/v2/projects/{id}/reject` - Reject stage
- `GET /api/v2/agents/status` - Get agent status
- `WS /ws/agents` - WebSocket connection

## 🧪 Testing

```bash
# Run tests (when configured)
npm test

# Type check
npm run type-check
```

## 📚 Learn More

- [Next.js Documentation](https://nextjs.org/docs)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Tailwind CSS](https://tailwindcss.com/docs)

## 🚀 Deployment

### Vercel (Recommended)

```bash
vercel
```

### Docker

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

```bash
docker build -t devpilot-ui .
docker run -p 3000:3000 devpilot-ui
```

## 📄 License

MIT
