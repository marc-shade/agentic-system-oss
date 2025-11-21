#!/usr/bin/env node
/**
 * Complete Component Library MCP Integration Workflow
 * Demonstrates end-to-end component library creation from successful clones
 */

// Example 1: Create a component library from cloned website
async function createLibraryFromClone() {
  // 1. Create a new component library
  const libraryResult = await mcp__component_library__create_component_library({
    name: "e-commerce-components",
    description: "Reusable components extracted from successful e-commerce site clones"
  });
  
  console.log("✅ Created library:", libraryResult);

  // 2. Add components from a successful clone operation
  const cloneData = {
    url: "https://stripe.com",
    components: [
      {
        name: "PricingCard",
        html: `
          <div class="pricing-card">
            <h3 class="pricing-title">Pro Plan</h3>
            <div class="pricing-price">$29/month</div>
            <ul class="pricing-features">
              <li>Feature 1</li>
              <li>Feature 2</li>
              <li>Feature 3</li>
            </ul>
            <button class="pricing-button">Get Started</button>
          </div>
        `,
        css: `
          .pricing-card {
            background: white;
            border-radius: 8px;
            padding: 2rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            --primary-color: #635bff;
            --text-color: #32325d;
          }
          .pricing-title {
            color: var(--text-color);
            font-size: 1.5rem;
            margin-bottom: 1rem;
          }
          .pricing-price {
            color: var(--primary-color);
            font-size: 2rem;
            font-weight: bold;
            margin-bottom: 1.5rem;
          }
          .pricing-button {
            background: var(--primary-color);
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 4px;
            cursor: pointer;
          }
        `,
        js: `
          // Add click tracking
          document.addEventListener('click', (e) => {
            if (e.target.classList.contains('pricing-button')) {
              console.log('Pricing button clicked');
            }
          });
        `,
        type: "html"
      },
      {
        name: "FeatureShowcase",
        html: `
          <div class="feature-showcase">
            <div class="feature-icon">🚀</div>
            <h4 class="feature-title">Fast Performance</h4>
            <p class="feature-description">Lightning-fast processing and delivery</p>
          </div>
        `,
        css: `
          .feature-showcase {
            text-align: center;
            padding: 2rem;
            --accent-color: #00d924;
          }
          .feature-icon {
            font-size: 3rem;
            margin-bottom: 1rem;
          }
          .feature-title {
            color: var(--accent-color);
            margin-bottom: 0.5rem;
          }
        `,
        type: "html"
      }
    ],
    designTokens: {
      colors: {
        primary: "#635bff",
        accent: "#00d924",
        text: "#32325d",
        background: "#ffffff"
      },
      spacing: {
        small: "0.5rem",
        medium: "1rem",
        large: "2rem"
      },
      borderRadius: {
        small: "4px",
        medium: "8px"
      }
    }
  };

  const addResult = await mcp__component_library__add_components_from_clone({
    libraryName: "e-commerce-components",
    cloneData: cloneData
  });

  console.log("✅ Added components:", addResult);
  return addResult;
}

// Example 2: Analyze component quality and performance
async function analyzeComponentQuality() {
  // Search for components to analyze
  const searchResult = await mcp__component_library__search_components({
    category: "display",
    searchTerm: "pricing"
  });

  if (searchResult.content[0].text.includes("Found 0")) {
    console.log("No components found to analyze");
    return;
  }

  // Get component details (assuming we found components)
  const componentData = JSON.parse(searchResult.content[1].text);
  const firstComponent = componentData[0];

  // Analyze the component
  const analysisResult = await mcp__component_library__analyze_component({
    libraryName: firstComponent.library,
    componentId: firstComponent.component.id
  });

  console.log("📊 Component Analysis:", analysisResult);

  // Update component based on analysis recommendations
  const updateResult = await mcp__component_library__update_component({
    libraryName: firstComponent.library,
    componentId: firstComponent.component.id,
    updates: {
      tags: ["analyzed", "pricing", "stripe-style"],
      description: "High-quality pricing card component extracted from Stripe clone",
      accessibility: {
        ariaLabels: true,
        keyboardNav: true,
        screenReaderSupport: true,
        wcagLevel: "AA"
      }
    }
  });

  console.log("✅ Updated component:", updateResult);
}

// Example 3: Generate component variants
async function generateComponentVariants() {
  // Search for a base component
  const searchResult = await mcp__component_library__search_components({
    searchTerm: "pricing"
  });

  if (searchResult.content[0].text.includes("Found 0")) {
    console.log("No pricing components found");
    return;
  }

  const componentData = JSON.parse(searchResult.content[1].text);
  const baseComponent = componentData[0];

  // Generate variants
  const variantsResult = await mcp__component_library__generate_component_variants({
    libraryName: baseComponent.library,
    componentId: baseComponent.component.id,
    variants: [
      {
        name: "basic",
        props: { plan: "Basic", price: "$9", features: ["Feature 1", "Feature 2"] },
        description: "Basic pricing tier"
      },
      {
        name: "pro",
        props: { plan: "Pro", price: "$29", features: ["All Basic", "Feature 3", "Feature 4"] },
        description: "Professional pricing tier"
      },
      {
        name: "enterprise",
        props: { plan: "Enterprise", price: "$99", features: ["All Pro", "Feature 5", "Priority Support"] },
        description: "Enterprise pricing tier"
      }
    ]
  });

  console.log("🔄 Generated variants:", variantsResult);
}

// Example 4: Create a design system
async function createDesignSystem() {
  const designSystemResult = await mcp__component_library__create_design_system({
    libraryName: "e-commerce-components",
    designSystemName: "Stripe-Inspired Design System",
    includeTokens: true,
    generateThemes: true
  });

  console.log("🎨 Created design system:", designSystemResult);
}

// Example 5: Export components in different formats
async function exportComponents() {
  // Get all components from the library
  const libraryResult = await mcp__component_library__get_library({
    name: "e-commerce-components"
  });

  const libraryData = JSON.parse(libraryResult.content[1].text);
  const componentIds = libraryData.components.map(comp => ({
    library: "e-commerce-components",
    id: comp.componentId
  }));

  // Export as NPM package
  const npmExport = await mcp__component_library__export_components({
    componentIds: componentIds,
    format: "npm",
    includeTests: true,
    includeDocs: true,
    includeStories: true,
    outputPath: "./exports/npm-package"
  });

  console.log("📦 NPM Package Export:", npmExport);

  // Export as Storybook
  const storybookExport = await mcp__component_library__export_components({
    componentIds: componentIds,
    format: "storybook",
    includeStories: true,
    includeDocs: true,
    outputPath: "./exports/storybook"
  });

  console.log("📚 Storybook Export:", storybookExport);

  // Export as CDN bundle
  const cdnExport = await mcp__component_library__export_components({
    componentIds: componentIds,
    format: "cdn",
    minify: true,
    outputPath: "./exports/cdn"
  });

  console.log("🌐 CDN Export:", cdnExport);
}

// Example 6: Batch operations
async function batchOperations() {
  // Get all components for analysis
  const libraryResult = await mcp__component_library__get_library({
    name: "e-commerce-components"
  });

  const libraryData = JSON.parse(libraryResult.content[1].text);
  const componentIds = libraryData.components.map(comp => ({
    library: "e-commerce-components",
    id: comp.componentId
  }));

  // Batch analyze all components
  const batchAnalysis = await mcp__component_library__batch_analyze_components({
    componentIds: componentIds
  });

  console.log("📊 Batch Analysis Results:", batchAnalysis);

  // Process analysis results
  const analysisData = JSON.parse(batchAnalysis.content[1].text);
  
  // Identify components that need improvement
  const lowQualityComponents = analysisData.filter(analysis => 
    analysis.analysis && analysis.analysis.qualityScore < 70
  );

  if (lowQualityComponents.length > 0) {
    console.log(`⚠️  Found ${lowQualityComponents.length} components needing improvement:`);
    lowQualityComponents.forEach(comp => {
      console.log(`- ${comp.componentName}: Score ${comp.analysis.qualityScore}`);
      console.log(`  Issues: ${comp.analysis.issues.join(', ')}`);
      console.log(`  Suggestions: ${comp.analysis.suggestions.slice(0, 3).join(', ')}`);
    });
  }
}

// Example 7: Integration with Enhanced-Memory-MCP
async function integrateWithMemoryMCP() {
  // Store successful component patterns in Enhanced-Memory-MCP
  const searchResult = await mcp__component_library__search_components({
    category: "display"
  });

  if (!searchResult.content[0].text.includes("Found 0")) {
    const componentData = JSON.parse(searchResult.content[1].text);
    
    for (const result of componentData) {
      // Store pattern in Enhanced-Memory-MCP
      await mcp__enhanced_memory_mcp__create_entities({
        entities: [{
          name: `ComponentPattern_${result.component.name}`,
          entityType: "component_pattern",
          observations: [
            `Component type: ${result.component.type}`,
            `Category: ${result.component.category}`,
            `Tags: ${result.component.tags?.join(', ') || 'none'}`,
            `Quality score: ${result.component.performance?.bundleSize || 'unknown'}`,
            `Design tokens: ${JSON.stringify(result.component.designTokens || {})}`
          ]
        }]
      });
    }

    console.log("🧠 Stored component patterns in Enhanced-Memory-MCP");
  }
}

// Example 8: Advanced search and filtering
async function advancedSearch() {
  console.log("🔍 Advanced Component Search Examples:");

  // Search by type and category
  const reactButtons = await mcp__component_library__search_components({
    type: "react",
    category: "button",
    hasTests: true
  });
  console.log("React buttons with tests:", reactButtons.content[0].text);

  // Search by tags
  const accessibleComponents = await mcp__component_library__search_components({
    tags: ["accessible", "wcag-aa"]
  });
  console.log("Accessible components:", accessibleComponents.content[0].text);

  // Full-text search
  const pricingComponents = await mcp__component_library__search_components({
    searchTerm: "pricing card stripe"
  });
  console.log("Pricing-related components:", pricingComponents.content[0].text);

  // Components with documentation
  const documentedComponents = await mcp__component_library__search_components({
    hasDocs: true,
    hasStorybook: true
  });
  console.log("Well-documented components:", documentedComponents.content[0].text);
}

// Main workflow execution
async function runCompleteWorkflow() {
  console.log("🚀 Starting Complete Component Library MCP Workflow\n");

  try {
    // 1. Create library and add components from clone
    console.log("1️⃣ Creating library from clone...");
    await createLibraryFromClone();
    console.log("");

    // 2. Analyze component quality
    console.log("2️⃣ Analyzing component quality...");
    await analyzeComponentQuality();
    console.log("");

    // 3. Generate component variants
    console.log("3️⃣ Generating component variants...");
    await generateComponentVariants();
    console.log("");

    // 4. Create design system
    console.log("4️⃣ Creating design system...");
    await createDesignSystem();
    console.log("");

    // 5. Export components
    console.log("5️⃣ Exporting components...");
    await exportComponents();
    console.log("");

    // 6. Batch operations
    console.log("6️⃣ Running batch operations...");
    await batchOperations();
    console.log("");

    // 7. Integration with Enhanced-Memory-MCP
    console.log("7️⃣ Integrating with Enhanced-Memory-MCP...");
    await integrateWithMemoryMCP();
    console.log("");

    // 8. Advanced search examples
    console.log("8️⃣ Advanced search examples...");
    await advancedSearch();
    console.log("");

    console.log("✅ Component Library MCP Workflow Complete!");
    console.log("\n📈 Summary:");
    console.log("- Created component library from successful clone");
    console.log("- Analyzed component quality and performance");
    console.log("- Generated component variants");
    console.log("- Created design system with tokens");
    console.log("- Exported components in multiple formats");
    console.log("- Performed batch quality analysis");
    console.log("- Integrated with Enhanced-Memory-MCP");
    console.log("- Demonstrated advanced search capabilities");

  } catch (error) {
    console.error("❌ Workflow error:", error);
  }
}

// Run the workflow if this file is executed directly
if (require.main === module) {
  runCompleteWorkflow();
}

module.exports = {
  createLibraryFromClone,
  analyzeComponentQuality,
  generateComponentVariants,
  createDesignSystem,
  exportComponents,
  batchOperations,
  integrateWithMemoryMCP,
  advancedSearch,
  runCompleteWorkflow
};