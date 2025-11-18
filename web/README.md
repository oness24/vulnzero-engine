# VulnZero Frontend Dashboard

## 🚀 Modern, Futuristic Security Dashboard

A cutting-edge React-based dashboard for the VulnZero AI-Powered Vulnerability Management Platform, featuring real-time updates, smooth animations, and a cybersecurity-focused design aesthetic.

## ✨ Features

### Design & UX
- **🎨 Cybersecurity Aesthetic**: Dark theme with neon accents (cyan, purple, green)
- **💎 Glassmorphism UI**: Modern glass-effect cards with backdrop blur
- **🌊 Smooth Animations**: Framer Motion for fluid micro-interactions
- **📱 Fully Responsive**: Adapts seamlessly to all screen sizes
- **♿ Accessibility First**: WCAG 2.1 AA compliant, keyboard navigation, screen reader support
- **⚡ Performance Optimized**: Code splitting, lazy loading, and optimized builds

### Technical Stack
- **React 18.2**: Latest React with concurrent features
- **Vite**: Ultra-fast build tool and HMR
- **Tailwind CSS 3.4**: Utility-first CSS with custom cybersecurity theme
- **Framer Motion 10**: Production-ready animation library
- **Recharts**: Composable charting library
- **Zustand**: Lightweight state management
- **Socket.IO**: Real-time WebSocket connections
- **Axios**: HTTP client for API communication

## 🎨 Design System

### Color Palette

```css
/* Primary Colors */
cyber-dark: #0a0e27      /* Main background */
cyber-darker: #050812     /* Deeper background */
cyber-blue: #00d9ff       /* Primary accent */
cyber-purple: #b537f2     /* Secondary accent */
cyber-green: #00ff88      /* Success/positive */
cyber-red: #ff0055        /* Critical/error */
cyber-orange: #ff6b35     /* High priority */

/* Status Colors */
status-critical: #ff0055
status-high: #ff6b35
status-medium: #ffa500
status-low: #00ff88
status-info: #00d9ff
```

### Typography

- **Display**: Orbitron (headings, logo)
- **Body**: Inter (UI text)
- **Code**: JetBrains Mono (terminal, code blocks)

### Component Classes

```css
.glass-card          /* Glassmorphism card */
.btn-cyber           /* Cyber-styled button */
.input-cyber         /* Futuristic input field */
.badge-{severity}    /* Status badges */
.stats-card          /* Animated stat cards */
.terminal            /* Terminal-style display */
```

## 📁 Project Structure

```
web/
├── public/                 # Static assets
├── src/
│   ├── components/        # Reusable UI components
│   │   ├── layout/       # Layout components (Navbar, Sidebar)
│   │   ├── ui/           # Base UI components (Button, Card, etc.)
│   │   └── dashboard/    # Dashboard-specific components
│   ├── pages/            # Page components (views)
│   ├── hooks/            # Custom React hooks
│   ├── services/         # API and WebSocket services
│   ├── stores/           # Zustand state stores
│   ├── utils/            # Utility functions
│   ├── types/            # TypeScript types
│   ├── styles/           # Global styles
│   ├── App.jsx           # Main app component
│   └── main.jsx          # Entry point
├── index.html
├── vite.config.js
├── tailwind.config.js
└── package.json
```

## 🚀 Getting Started

### Prerequisites

```bash
Node.js >= 18.0.0
npm >= 9.0.0
```

### Installation

```bash
cd web
npm install
```

### Development

```bash
npm run dev
```

Visit `http://localhost:3000`

### Build for Production

```bash
npm run build
npm run preview
```

## 🎯 Key Components (To Be Implemented)

### Layout Components
- **Navbar**: Top navigation with real-time stats
- **Sidebar**: Collapsible navigation menu with icons
- **Layout**: Main layout wrapper with routing

### Dashboard Components
- **StatsCard**: Animated statistics cards
- **VulnerabilityChart**: Real-time vulnerability trends
- **DeploymentTimeline**: Interactive deployment history
- **AlertFeed**: Live alert notifications
- **SystemHealth**: Real-time system status

### Reusable UI Components
- **Button**: Cybersecurity-styled buttons with variants
- **Card**: Glass-effect cards with animations
- **Badge**: Status badges with severity colors
- **Input**: Futuristic form inputs
- **Modal**: Animated modal dialogs
- **Tooltip**: Contextual tooltips
- **LoadingSpinner**: Animated loading states

## 🔌 API Integration

### REST API

```javascript
import { apiClient } from '@services/api'

// Get vulnerabilities
const vulnerabilities = await apiClient.get('/api/vulnerabilities')

// Deploy patch
const deployment = await apiClient.post('/api/deployments', { patch_id, asset_ids })
```

### WebSocket

```javascript
import { useWebSocket } from '@hooks/useWebSocket'

const { data, isConnected } = useWebSocket('/ws/deployments')
```

## 🎨 Animation Examples

### Entrance Animations

```jsx
<motion.div
  initial={{ opacity: 0, y: 20 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ duration: 0.5 }}
>
  <StatsCard />
</motion.div>
```

### Hover Effects

```jsx
<motion.button
  whileHover={{ scale: 1.05 }}
  whileTap={{ scale: 0.95 }}
  className="btn-cyber"
>
  Deploy Patch
</motion.button>
```

## ♿ Accessibility Features

- **Keyboard Navigation**: Full keyboard support
- **Screen Reader**: ARIA labels and roles
- **Focus Indicators**: Visible focus states
- **High Contrast**: Support for high contrast mode
- **Reduced Motion**: Respects prefers-reduced-motion
- **Color Contrast**: WCAG AA compliant color ratios

## 🔧 Configuration

### Environment Variables

Create `.env` file:

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
VITE_ENABLE_MOCK=false
```

### Vite Proxy

API requests are proxied to the backend:

```javascript
'/api' -> 'http://localhost:8000/api'
'/ws'  -> 'ws://localhost:8000/ws'
```

## 📊 Performance Optimizations

- **Code Splitting**: Route-based code splitting
- **Lazy Loading**: Components loaded on demand
- **Image Optimization**: Automatic image optimization
- **Bundle Analysis**: `npm run build` shows bundle size
- **Caching**: Service worker for offline support

## 🎭 Design Principles

1. **Cybersecurity Aesthetic**: Dark backgrounds, neon accents, terminal-inspired UI
2. **Information Hierarchy**: Clear visual hierarchy with typography and color
3. **Responsive Design**: Mobile-first approach
4. **Performance**: 60fps animations, optimized renders
5. **Accessibility**: Inclusive design for all users
6. **Consistency**: Reusable components and design tokens

## 🛠️ Development Tools

- **ESLint**: Code linting
- **Prettier**: Code formatting
- **Vite DevTools**: Development debugging
- **React DevTools**: Component inspection

## 📱 Responsive Breakpoints

```javascript
sm:  640px   // Mobile landscape
md:  768px   // Tablet
lg:  1024px  // Desktop
xl:  1280px  // Large desktop
2xl: 1536px  // Extra large
```

## 🚀 Deployment

### Docker

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build
FROM nginx:alpine
COPY --from=0 /app/dist /usr/share/nginx/html
```

### Vercel/Netlify

One-click deployments supported with automatic builds.

## 📄 License

See main project LICENSE

## 👥 Contributing

Follow the main project contribution guidelines.

---

Built with ⚡ by the VulnZero team
