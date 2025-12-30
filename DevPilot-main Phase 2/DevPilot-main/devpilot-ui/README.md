# DevPilot Frontend

Modern Next.js frontend for the DevPilot AI-Powered SDLC Platform.

## 🚀 Features

- ✅ **Modern Stack**: Next.js 14 with React 18 and TypeScript
- ✅ **Responsive Design**: Tailwind CSS with mobile-first approach
- ✅ **Error Handling**: Global error boundary for production stability
- ✅ **SEO Optimized**: Meta tags, Open Graph, and proper semantic HTML
- ✅ **Security Headers**: HSTS, XSS Protection, Content Security
- ✅ **Loading States**: Suspense boundaries and loading components
- ✅ **API Integration**: Ready-to-use API client for backend communication
- ✅ **Production Ready**: Optimized build configuration

## 📋 Prerequisites

- Node.js 18.x or higher
- npm or yarn package manager

## 🛠️ Installation

1. Clone the repository
2. Navigate to the frontend directory:
   ```bash
   cd devpilot-ui
   ```

3. Install dependencies:
   ```bash
   npm install
   ```

4. Copy environment file:
   ```bash
   cp .env.example .env.local
   ```

5. Update environment variables in `.env.local`

## 🏃 Running the Application

### Development Mode
```bash
npm run dev
```
Open [http://localhost:3000](http://localhost:3000)

### Production Build
```bash
npm run build
npm start
```

### Type Checking
```bash
npm run type-check
```

### Linting
```bash
npm run lint
```

## 📁 Project Structure

```
devpilot-ui/
├── src/
│   ├── app/              # Next.js app directory
│   │   ├── layout.tsx    # Root layout with metadata
│   │   ├── page.tsx      # Main application page
│   │   ├── loading.tsx   # Loading UI
│   │   └── globals.css   # Global styles
│   ├── components/       # React components
│   │   ├── Dashboard.tsx
│   │   ├── Header.tsx
│   │   ├── Sidebar.tsx
│   │   ├── ErrorBoundary.tsx
│   │   └── Loading.tsx
│   └── lib/              # Utilities and API client
│       └── api.ts
├── public/               # Static assets
├── next.config.mjs       # Next.js configuration
├── tailwind.config.ts    # Tailwind CSS configuration
└── tsconfig.json         # TypeScript configuration
```

## 🎨 Features

### Dashboard Tabs
- **Overview**: System statistics and recent activity
- **Projects**: Project management with progress tracking
- **Agents**: AI agent status and monitoring
- **Workflows**: Workflow visualization (coming soon)
- **Artifacts**: Document and artifact management
- **Integrations**: GitHub, Jira, Slack integration

### API Client
The API client (`src/lib/api.ts`) provides methods for:
- Project management
- Agent status monitoring
- Artifact handling
- SDLC execution

## 🔒 Security Features

- HTTPS enforcement (Strict-Transport-Security)
- XSS protection headers
- Content-Type sniffing prevention
- Frame protection (Clickjacking prevention)
- Referrer policy configuration

## 🌐 Environment Variables

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_ENV=development
NEXT_PUBLIC_ENABLE_ANALYTICS=false
NEXT_PUBLIC_ENABLE_MONITORING=false
```

## 🚀 Deployment

### Vercel (Recommended)
```bash
vercel
```

### Docker
```bash
docker build -t devpilot-ui .
docker run -p 3000:3000 devpilot-ui
```

### Manual
```bash
npm run build
npm start
```

## 📊 Performance

- Server-side rendering (SSR)
- Automatic code splitting
- Image optimization
- Font optimization
- Gzip compression enabled

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📝 License

Copyright © 2025 DevPilot Team

## 🆘 Support

For issues and questions, please open an issue on GitHub.
