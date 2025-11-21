# Component Library MCP

A comprehensive Model Context Protocol (MCP) server for creating, managing, and reusing components from successful design clones. This server provides intelligent component parsing, analysis, organization, and export capabilities.

## 🌟 Features

### Core Functionality
- **Multi-Framework Support**: React, Vue, HTML, Web Components, Svelte, Angular
- **Intelligent Parsing**: Automatic component analysis and metadata extraction
- **Design Token Extraction**: Automatic extraction of colors, typography, spacing, shadows
- **Quality Analysis**: Comprehensive quality scoring and improvement suggestions
- **Component Organization**: Library-based organization with categorization

### Advanced Capabilities
- **Clone Integration**: Direct integration with website cloning workflows
- **Batch Operations**: Analyze, update, and export multiple components
- **Export Formats**: NPM packages, CDN bundles, Git repos, ZIP files, Storybook
- **Variant Generation**: Create component variants with different props/styles
- **Design System Creation**: Generate design systems from component libraries

### Quality Assurance
- **Accessibility Analysis**: WCAG compliance checking and recommendations
- **Performance Analysis**: Bundle size estimation and optimization suggestions
- **Code Quality Scoring**: Comprehensive quality metrics
- **Documentation Generation**: Automatic README and API documentation

## 🚀 Installation

```bash
cd /Users/marc/Documents/Cline/MCP/component-library-mcp
npm install
npm run build
```

## 🔧 Configuration

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "component-library": {
      "command": "node",
      "args": ["/Users/marc/Documents/Cline/MCP/component-library-mcp/dist/index.js"]
    }
  }
}
```

## 📚 Usage

### Creating a Component Library

```javascript
// Create a new library
mcp__component-library__create_component_library({
  name: "my-design-system",
  description: "Components from successful website clones"
})
```

### Adding Components from Clones

```javascript
// Add components from a cloned website
mcp__component-library__add_components_from_clone({
  libraryName: "my-design-system",
  cloneData: {
    url: "https://example.com",
    components: [
      {
        name: "HeroSection",
        html: "<div class='hero'>...</div>",
        css: ".hero { background: #f0f0f0; }",
        js: "// Interactive behavior",
        type: "react"
      }
    ],
    designTokens: {
      colors: { primary: "#007bff" },
      spacing: { medium: "1rem" }
    }
  }
})
```

### Searching Components

```javascript
// Search for button components
mcp__component-library__search_components({
  category: "button",
  type: "react",
  tags: ["accessible"],
  searchTerm: "primary"
})
```

### Analyzing Component Quality

```javascript
// Analyze a component
mcp__component-library__analyze_component({
  libraryName: "my-design-system",
  componentId: "hero-section-abc123"
})
```

### Exporting Components

```javascript
// Export as NPM package
mcp__component-library__export_components({
  componentIds: [
    { library: "my-design-system", id: "button-xyz789" },
    { library: "my-design-system", id: "hero-abc123" }
  ],
  format: "npm",
  includeTests: true,
  includeDocs: true,
  minify: false
})
```

## 🏗️ Architecture

### Component Parser
- **Multi-framework detection**: Automatically detects React, Vue, HTML, etc.
- **Metadata extraction**: Props, dependencies, variants, accessibility features
- **Design token extraction**: Colors, typography, spacing from styles
- **File relationship mapping**: Finds related test, story, and documentation files

### Component Analyzer
- **Complexity analysis**: Simple, moderate, or complex classification
- **Quality scoring**: 0-100 score based on documentation, testing, accessibility
- **Performance analysis**: Bundle size estimation and optimization recommendations
- **Accessibility audit**: WCAG compliance checking and improvement suggestions

### Component Library Manager
- **Library organization**: Multiple libraries with versioning
- **Component relationships**: Variants, dependencies, and compositions
- **Search and filtering**: Advanced search with relevance scoring
- **Batch operations**: Process multiple components efficiently

### Export System
- **NPM packages**: Ready-to-publish packages with TypeScript definitions
- **CDN bundles**: Minified bundles for direct browser usage
- **Storybook integration**: Complete Storybook setup with stories
- **Git repositories**: Structured repos with documentation and examples

## 🔍 Component Analysis

The analyzer provides comprehensive insights:

### Quality Metrics
- **Documentation coverage**: Description, prop documentation, README files
- **Testing coverage**: Unit tests, integration tests, test quality
- **Accessibility score**: ARIA labels, keyboard navigation, screen reader support
- **Props validation**: TypeScript interfaces, PropTypes, validation
- **Code structure**: Separation of concerns, modularity, reusability

### Performance Analysis
- **Bundle size estimation**: Component + dependencies size calculation
- **Optimization recommendations**: Code splitting, lazy loading, memoization
- **Dependency analysis**: Heavy dependencies, peer dependency conflicts
- **Rendering performance**: React-specific optimizations (memo, callbacks, effects)

### Accessibility Audit
- **WCAG compliance**: Level A, AA, AAA compliance checking
- **Keyboard navigation**: Tab order, focus management, keyboard shortcuts
- **Screen reader support**: ARIA labels, roles, live regions
- **Color contrast**: Automated contrast ratio checking
- **Interactive elements**: Proper roles, states, and properties

## 📁 File Structure

```
component-library-mcp/
├── src/
│   ├── index.ts                 # MCP server entry point
│   ├── types.ts                 # TypeScript type definitions
│   ├── componentParser.ts       # Multi-framework component parsing
│   ├── componentAnalyzer.ts     # Quality and performance analysis
│   ├── componentExporter.ts     # Export to various formats
│   ├── componentLibrary.ts      # Library management
│   ├── parsers/
│   │   ├── reactParser.ts       # React component analysis
│   │   ├── vueParser.ts         # Vue component analysis
│   │   └── htmlParser.ts        # HTML/Web Component analysis
│   └── utils/
│       └── tokenExtractor.ts    # Design token extraction
├── templates/                   # Component templates
│   ├── react-component.tsx
│   ├── vue-component.vue
│   └── web-component.js
└── component-libraries/         # Storage directory
    └── [library-name]/
        ├── library.json         # Library metadata
        └── components/          # Component files
            └── [component-id]/
                ├── component.tsx
                ├── styles.css
                ├── test.tsx
                └── metadata.json
```

## 🔄 Integration with Design Cloning Suite

This MCP server seamlessly integrates with the broader 2AS Design Cloning Suite:

### Website-Scraper-MCP Integration
- Automatically processes scraped components
- Extracts design tokens from CSS
- Maintains source URL tracking

### Enhanced-Memory-MCP Integration
- Stores successful component patterns
- Learns from clone operation success rates
- Provides intelligent component recommendations

### Image-Gen-MCP Integration
- Generates component assets and icons
- Maintains design consistency across generated assets
- Uses stored design tokens for asset generation

### Claude-Flow-MCP Orchestration
- Coordinates multi-step component creation workflows
- Manages parallel processing of component batches
- Orchestrates end-to-end clone-to-component pipelines

## 🛠️ Development

### Building
```bash
npm run build
```

### Development Mode
```bash
npm run dev
```

### Testing
```bash
npm test
```

## 🎯 Use Cases

### 1. Website Clone Processing
Extract and organize reusable components from successful website clones, maintaining design consistency and code quality.

### 2. Design System Creation
Build comprehensive design systems from component libraries, with automated token extraction and theme generation.

### 3. Component Quality Assurance
Maintain high-quality component libraries with automated analysis, scoring, and improvement recommendations.

### 4. Multi-Framework Support
Support diverse technology stacks while maintaining consistent component organization and export capabilities.

### 5. Team Collaboration
Enable teams to share, discover, and reuse components across projects with comprehensive documentation and testing.

## 🔮 Future Enhancements

- **AI-powered Component Generation**: Generate new components based on design patterns
- **Component Composition**: Intelligent composition of existing components
- **Performance Monitoring**: Real-world performance tracking for deployed components
- **Design Token Synchronization**: Sync with design tools like Figma
- **Component Testing Automation**: Automated visual regression testing
- **API Integration**: REST/GraphQL APIs for component management

## 📄 License

MIT License - Built by 2 Acre Studios for the 2AS Design Cloning Suite.