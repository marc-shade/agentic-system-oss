# Monitoring Stack Port Assignments

All ports have been carefully selected using the Port Manager tool to avoid conflicts with standard services.

## Assigned Ports

### Prometheus (Metrics Collection)
- **Port**: 9700
- **Protocol**: HTTP
- **Endpoint**: http://localhost:9700
- **Health**: http://localhost:9700/-/healthy

### Loki (Log Aggregation)
- **HTTP Port**: 9900
- **gRPC Port**: 9901
- **Protocol**: HTTP/gRPC
- **Endpoint**: http://localhost:9900
- **Health**: http://localhost:9900/ready

### Grafana (Visualization)
- **Port**: 9500
- **Protocol**: HTTP
- **Direct Access**: http://localhost:9500
- **Proxy Access**: http://localhost:3101/grafana (Recommended)
- **Health**: http://localhost:9500/api/health

## Port Selection Process

Ports were selected using the Port Manager CLI:
```bash
/Volumes/FILES/code/kutiraai/bin/pm find 9500 9600  # Grafana: 9500
/Volumes/FILES/code/kutiraai/bin/pm find 9700 9800  # Prometheus: 9700
/Volumes/FILES/code/kutiraai/bin/pm find 9900 10000 # Loki: 9900
```

## Why Non-Standard Ports?

Standard monitoring ports are commonly used by many services and can cause conflicts:
- Prometheus default (9090) - Used by many monitoring solutions
- Loki default (3100) - Conflicts with development servers
- Grafana default (3000) - Extremely common for Node.js/React apps

By using non-standard ports in the 9500-9900 range, we avoid these conflicts while keeping ports organized and memorable.

## Port Verification

Before starting services, all ports were verified as available:
```bash
lsof -i :9500  # Grafana
lsof -i :9700  # Prometheus
lsof -i :9900  # Loki HTTP
lsof -i :9901  # Loki gRPC
```

## Integration Points

### Vite Proxy (Frontend)
The Vite development server (port 3101) proxies Grafana:
```javascript
'/grafana': {
  target: 'http://localhost:9500',
  changeOrigin: true,
  ws: true
}
```

**File**: `/Volumes/FILES/code/kutiraai/vite.config.mjs`

### Data Sources
Grafana data sources are configured to use the correct ports:
- Prometheus: `http://localhost:9700`
- Loki: `http://localhost:9900`

**File**: `/Volumes/SSDRAID0/agentic-system/monitoring/grafana/provisioning/datasources/datasources.yml`

## Port Conflicts

If you encounter port conflicts:
```bash
# Check for conflicts
/Volumes/FILES/code/kutiraai/bin/pm conflicts

# Find alternative ports
/Volumes/FILES/code/kutiraai/bin/pm find START END

# Kill process on specific port
/Volumes/FILES/code/kutiraai/bin/pm kill PORT
```

## Future Port Assignments

When adding new monitoring components, use the Port Manager to find available ports:
```bash
# Find next available port in 9xxx range
/Volumes/FILES/code/kutiraai/bin/pm find 9000 10000
```

Keep monitoring ports organized in the 9xxx range for easy management and discovery.

---

**Last Updated**: 2025-11-03
**Status**: ✅ All ports verified and operational
