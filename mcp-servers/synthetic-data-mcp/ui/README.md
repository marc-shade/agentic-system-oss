# Synthetic Data Discovery UI

A comprehensive React-based frontend for the synthetic-data-mcp platform, providing enterprise-grade data discovery, generation, and privacy management capabilities.

## 🚀 Features

### Core Capabilities
- **Dashboard** - System overview with real-time metrics and status monitoring
- **Schema Explorer** - Browse and manage database connections and schemas
- **Data Generator** - Interactive synthetic data generation with AI models
- **Privacy Controls** - HIPAA/GDPR compliance monitoring and privacy budget management
- **Query Builder** - Visual SQL query construction and execution
- **Data Preview** - Advanced data exploration with filtering and sorting
- **Export Manager** - Multi-format data export capabilities
- **API Explorer** - Interactive API documentation and testing
- **Compliance Dashboard** - Regulatory compliance monitoring and reporting

### Technical Features
- **Modern React 18** with TypeScript and Vite
- **shadcn/ui Components** with Tailwind CSS
- **State Management** using Zustand and TanStack Query
- **Real-time Updates** via WebSocket integration
- **Dark Mode Support** with system preference detection
- **Responsive Design** mobile-first approach
- **Accessibility** WCAG 2.1 AA compliance
- **Error Boundaries** with graceful error handling
- **Performance Optimized** with code splitting and lazy loading

## 🛠 Tech Stack

### Core Technologies
- **React 18** - UI framework with concurrent features
- **TypeScript** - Type-safe development
- **Vite** - Fast build tool and dev server
- **Tailwind CSS** - Utility-first CSS framework

### UI Components
- **shadcn/ui** - High-quality, accessible components
- **Radix UI** - Unstyled, accessible UI primitives
- **Lucide React** - Beautiful, customizable icons
- **Framer Motion** - Smooth animations and transitions

### State Management
- **Zustand** - Lightweight state management
- **TanStack Query** - Server state management and caching
- **React Hook Form** - Performant forms with easy validation
- **Zod** - TypeScript-first schema validation

### Data Visualization
- **Recharts** - Composable charting library
- **TanStack Table** - Headless table building

### Development Tools
- **ESLint** - Code linting and formatting
- **TypeScript** - Static type checking
- **Vitest** - Unit testing framework

## 🏗 Project Structure

```
ui/
├── public/                 # Static assets
├── src/
│   ├── components/         # Reusable UI components
│   │   ├── ui/            # shadcn/ui components
│   │   ├── dashboard/     # Dashboard-specific components
│   │   ├── layout/        # Layout components (Header, Sidebar, Footer)
│   │   ├── providers/     # Context providers
│   │   └── guards/        # Route guards
│   ├── pages/             # Page components
│   ├── stores/            # Zustand stores
│   ├── lib/               # Utility libraries
│   ├── types/             # TypeScript type definitions
│   ├── hooks/             # Custom React hooks
│   └── assets/            # Assets (images, fonts, etc.)
├── package.json
├── vite.config.ts
├── tailwind.config.js
└── tsconfig.json
```

## 🚦 Getting Started

### Prerequisites
- Node.js 18+ and npm/yarn/pnpm
- Running synthetic-data-mcp backend server

### Installation

1. **Clone and navigate to the UI directory**
   ```bash
   cd synthetic-data-mcp/ui
   ```

2. **Install dependencies**
   ```bash
   npm install
   # or
   yarn install
   # or
   pnpm install
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and configure:
   ```env
   VITE_API_URL=http://localhost:8000
   VITE_WS_URL=ws://localhost:8000/ws
   ```

4. **Start the development server**
   ```bash
   npm run dev
   ```

5. **Open your browser**
   Navigate to `http://localhost:3000`

### Default Credentials
For development/demo purposes:
- **Email**: admin@synthdata.com
- **Password**: admin123

## 📦 Available Scripts

```bash
# Development
npm run dev              # Start development server
npm run build           # Build for production
npm run preview         # Preview production build locally

# Code Quality
npm run lint            # Run ESLint
npm run type-check      # Run TypeScript type checking

# Testing
npm run test            # Run unit tests
npm run test:ui         # Run tests with UI
```

## 🎨 UI Components

### Core Components
- **Button** - Customizable buttons with multiple variants
- **Card** - Flexible card containers with specialized variants
- **Input** - Form inputs with validation and icons
- **Badge** - Status indicators and labels
- **Table** - Data tables with sorting and pagination
- **Progress** - Progress indicators and loading states
- **Alert** - Contextual feedback messages

### Specialized Components
- **MetricCard** - Dashboard metrics display
- **StatusCard** - System status indicators
- **PrivacyBadge** - Privacy level indicators
- **ComplianceBadge** - Compliance status badges
- **DataTable** - Enhanced data grid with features

### Layout Components
- **AppLayout** - Main application layout
- **AuthLayout** - Authentication page layout
- **Sidebar** - Navigation sidebar
- **Header** - Top navigation bar
- **Footer** - Page footer

## 🔐 Authentication & Security

### Authentication Flow
1. User credentials are validated against the backend API
2. JWT tokens are stored securely in localStorage
3. Automatic token refresh and session management
4. Protected routes with authentication guards

### Security Features
- **CSRF Protection** - Built-in request validation
- **XSS Prevention** - Input sanitization and validation
- **Secure Storage** - Encrypted local storage for sensitive data
- **Role-based Access** - Granular permission system

## 🎯 State Management

### Store Architecture
- **Auth Store** - User authentication and session management
- **UI Store** - Global UI state, theme, notifications
- **Data Store** - Application data state and caching

### Data Fetching Strategy
- **TanStack Query** for server state management
- **Optimistic Updates** for better user experience
- **Background Refetching** for real-time data
- **Error Handling** with retry logic and fallbacks

## 🎨 Theming & Styling

### Design System
- **CSS Variables** for consistent theming
- **Dark/Light Mode** with system preference detection
- **Responsive Design** with mobile-first approach
- **Tailwind CSS** for utility-first styling

### Custom Theme Colors
```css
/* Primary brand colors */
--synthetic-primary: 263 70% 50%     /* Purple */
--synthetic-secondary: 193 75% 50%   /* Blue */
--synthetic-accent: 142 76% 36%      /* Green */

/* Privacy level colors */
--privacy-public: Green
--privacy-internal: Blue  
--privacy-confidential: Yellow
--privacy-restricted: Red

/* Compliance colors */
--compliance-hipaa: Blue
--compliance-gdpr: Purple
--compliance-ccpa: Indigo
```

## 📊 Data Visualization

### Chart Types
- **Privacy Budget Charts** - Pie and progress charts
- **System Metrics** - Line and bar charts
- **Activity Timelines** - Time-series visualizations
- **Compliance Dashboards** - Status and trend charts

### Chart Configuration
```typescript
// Example chart configuration
const chartConfig = {
  data: privacyBudgetData,
  responsive: true,
  animations: true,
  theme: 'auto', // Follows system theme
}
```

## 🔄 Real-time Features

### WebSocket Integration
- **Live Updates** - Real-time job status updates
- **System Alerts** - Instant notification of system events
- **Privacy Alerts** - Budget usage notifications
- **Connection Management** - Automatic reconnection handling

### Event Types
```typescript
// WebSocket event handling
websocket.on('job_update', (data) => {
  // Update job status in real-time
})

websocket.on('privacy_alert', (data) => {
  // Show privacy budget warnings
})

websocket.on('system_alert', (data) => {
  // Display system notifications
})
```

## 📱 Responsive Design

### Breakpoint System
```javascript
const breakpoints = {
  sm: '640px',   // Mobile
  md: '768px',   // Tablet  
  lg: '1024px',  // Desktop
  xl: '1280px',  // Large Desktop
  '2xl': '1536px' // Extra Large
}
```

### Mobile-First Approach
- Touch-friendly interface
- Optimized navigation for mobile
- Responsive data tables
- Adaptive layouts

## ♿ Accessibility

### WCAG 2.1 AA Compliance
- **Keyboard Navigation** - Full keyboard support
- **Screen Reader** - Proper ARIA labels and roles
- **Color Contrast** - Meets accessibility standards
- **Focus Management** - Visible focus indicators
- **Semantic HTML** - Proper HTML structure

### Accessibility Testing
```bash
# Run accessibility audits
npm run a11y-audit
```

## 🧪 Testing Strategy

### Testing Stack
- **Vitest** - Unit and integration testing
- **Testing Library** - Component testing utilities
- **MSW** - API mocking for tests
- **Playwright** - End-to-end testing (optional)

### Test Categories
```bash
# Unit Tests
src/components/__tests__/        # Component tests
src/stores/__tests__/           # Store tests  
src/lib/__tests__/             # utility tests

# Integration Tests
src/pages/__tests__/           # Page integration tests

# E2E Tests (optional)
e2e/                          # End-to-end test scenarios
```

## 🚀 Deployment

### Production Build
```bash
# Create optimized production build
npm run build

# Preview production build locally
npm run preview
```

### Build Output
```
dist/
├── index.html          # Main HTML file
├── assets/            # Optimized JS/CSS bundles
│   ├── index.[hash].js
│   └── index.[hash].css
└── favicon.ico        # App favicon
```

### Environment Configuration
```env
# Production environment variables
VITE_API_URL=https://api.yourdomin.com
VITE_WS_URL=wss://api.yourdomain.com/ws
NODE_ENV=production
```

## 🔧 Configuration

### Vite Configuration
Key features enabled:
- **Path Aliases** - `@/*` imports from src
- **Proxy Setup** - API and WebSocket proxying
- **Code Splitting** - Optimized bundle chunking
- **Asset Optimization** - Image and font optimization

### TypeScript Configuration
- **Strict Mode** - Enhanced type checking
- **Path Mapping** - Clean import statements
- **Modern Target** - ES2020+ features

### Tailwind Configuration
- **Custom Design System** - Extended color palette
- **Component Classes** - Reusable utility classes
- **Plugin Integration** - Forms, typography plugins

## 🤝 Contributing

### Development Workflow
1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Code Standards
- **TypeScript** - All code must be properly typed
- **ESLint** - Follow configured linting rules
- **Prettier** - Use consistent code formatting
- **Component Structure** - Follow established patterns

### Commit Convention
```bash
feat: add new dashboard widget
fix: resolve authentication bug  
docs: update API documentation
style: format code with prettier
refactor: optimize data fetching logic
test: add unit tests for user store
```

## 📈 Performance

### Optimization Features
- **Code Splitting** - Dynamic imports for routes
- **Tree Shaking** - Remove unused code
- **Bundle Analysis** - Optimize bundle size
- **Image Optimization** - Compressed assets
- **Caching Strategy** - Efficient browser caching

### Performance Monitoring
```typescript
// Performance metrics tracking
const metrics = {
  LCP: 'Largest Contentful Paint',
  FID: 'First Input Delay', 
  CLS: 'Cumulative Layout Shift'
}
```

## 🐛 Troubleshooting

### Common Issues

**Build Errors**
```bash
# Clear node modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

**TypeScript Errors**
```bash
# Type check the entire project
npm run type-check
```

**API Connection Issues**
- Verify backend server is running on port 8000
- Check CORS configuration
- Ensure environment variables are set correctly

**WebSocket Connection Failed**
- Confirm WebSocket URL is correct
- Check firewall settings
- Verify backend WebSocket server is enabled

## 📚 Resources

### Documentation
- [React Documentation](https://react.dev)
- [TypeScript Handbook](https://www.typescriptlang.org/docs)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [shadcn/ui](https://ui.shadcn.com)
- [TanStack Query](https://tanstack.com/query/latest)
- [Zustand](https://zustand-demo.pmnd.rs)

### Design Resources
- [Tailwind UI Components](https://tailwindui.com)
- [Radix UI Primitives](https://www.radix-ui.com)
- [Lucide Icons](https://lucide.dev)

## 📄 License

This project is part of the synthetic-data-mcp platform. See the main project LICENSE file for details.

## 🏢 Enterprise Features

### Security & Compliance
- **SOC2 Compliance** - Enterprise security standards
- **HIPAA/GDPR Ready** - Healthcare and privacy compliance
- **Audit Trails** - Comprehensive activity logging
- **Role-based Access** - Granular permission system

### Scalability
- **Multi-tenant Support** - Organization isolation
- **Performance Monitoring** - Real-time metrics
- **Load Balancing** - Horizontal scaling support
- **CDN Integration** - Global asset delivery

### Integration
- **SSO Support** - SAML/OAuth integration
- **API-First Design** - Headless architecture
- **Webhook Support** - Event-driven integrations
- **Custom Plugins** - Extensible architecture

---

Built with ❤️ for enterprise synthetic data generation and privacy-compliant data discovery.