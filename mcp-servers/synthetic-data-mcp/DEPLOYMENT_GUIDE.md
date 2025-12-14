# Synthetic Data MCP - Production Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the Synthetic Data MCP Platform in production environments using Docker, Docker Compose, and Kubernetes.

## Quick Start

### Prerequisites

- Docker 24.0+ and Docker Compose v2.20+
- Kubernetes 1.20+ cluster (for K8s deployment)
- Helm 3.8+ (for Helm deployment)
- kubectl configured with cluster access
- 16GB+ RAM and 100GB+ storage recommended

### 1. Local Development with Docker Compose

```bash
# Clone the repository
git clone https://github.com/marc-shade/synthetic-data-mcp.git
cd synthetic-data-mcp

# Copy environment template
cp .env.example .env

# Edit .env with your configuration
nano .env

# Start all services
docker-compose up -d

# Check service health
docker-compose ps
```

Access the application:
- Main API: http://localhost:3000
- Metrics: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9091

### 2. Production Kubernetes Deployment

#### Option A: Direct Kubernetes Manifests

```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Apply ConfigMaps and Secrets (update secrets first!)
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml

# Apply RBAC
kubectl apply -f k8s/rbac.yaml

# Apply storage
kubectl apply -f k8s/pvc.yaml

# Deploy application
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# Deploy load balancer (nginx)
kubectl apply -f k8s/nginx-deployment.yaml

# Configure autoscaling
kubectl apply -f k8s/hpa.yaml

# Set up ingress
kubectl apply -f k8s/ingress.yaml
```

#### Option B: Helm Chart (Recommended)

```bash
# Add required Helm repositories
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install with Helm
helm install synthetic-data-mcp ./helm/synthetic-data-mcp \
  --namespace synthetic-data \
  --create-namespace \
  --set ingress.hosts[0].host=synthetic-data.yourdomain.com \
  --set secrets.values.openaiApiKey="your-openai-key" \
  --set postgresql.auth.password="secure-db-password" \
  --set redis.auth.password="secure-redis-password"

# Check deployment status
helm status synthetic-data-mcp -n synthetic-data
kubectl get pods -n synthetic-data
```

## Configuration

### Environment Variables

#### Core Application Settings
```bash
SYNTHETIC_DATA_LOG_LEVEL=INFO          # Logging level
SYNTHETIC_DATA_PRIVACY_MODE=LOCAL      # Privacy mode
PORT=3000                              # Application port
MAX_WORKERS=4                          # Worker processes
REQUEST_TIMEOUT=300                    # Request timeout
MAX_RECORD_COUNT=100000                # Max records per request
```

#### Database Configuration
```bash
POSTGRES_HOST=synthetic-postgres       # PostgreSQL host
POSTGRES_PORT=5432                     # PostgreSQL port
POSTGRES_DB=synthetic_data             # Database name
POSTGRES_USER=synthetic                # Database user
POSTGRES_PASSWORD=secure_password      # Database password
```

#### Redis Configuration
```bash
REDIS_HOST=synthetic-redis             # Redis host
REDIS_PORT=6379                        # Redis port
REDIS_PASSWORD=secure_redis_password   # Redis password (optional)
```

#### LLM Provider Configuration
```bash
# OpenAI
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4

# Ollama (local)
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=llama3.1:8b
```

#### Security Settings
```bash
API_KEY=your_api_key                   # API authentication key
JWT_SECRET=your_jwt_secret             # JWT signing secret
ENCRYPTION_KEY=your_encryption_key     # Data encryption key
```

### Security Configuration

#### 1. Generate Secure Keys

```bash
# Generate API key
openssl rand -hex 32

# Generate JWT secret
openssl rand -base64 64

# Generate encryption key
openssl rand -hex 32
```

#### 2. TLS/SSL Setup

For production, configure TLS certificates:

```bash
# Create certificate secret
kubectl create secret tls synthetic-data-tls \
  --cert=path/to/certificate.crt \
  --key=path/to/private.key \
  -n synthetic-data
```

#### 3. Network Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: synthetic-data-netpol
  namespace: synthetic-data
spec:
  podSelector:
    matchLabels:
      app: synthetic-data-mcp
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 3000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: synthetic-postgres
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app: synthetic-redis
    ports:
    - protocol: TCP
      port: 6379
```

## Scaling and Performance

### Horizontal Pod Autoscaling

The deployment includes HPA configuration that automatically scales based on:

- **CPU utilization**: Target 70%
- **Memory utilization**: Target 80%
- **Custom metrics**: Request rate, response time (requires Prometheus adapter)

Scale range: 3-20 pods with smart scaling policies.

### Resource Requirements

#### Minimum Requirements (per pod)
- **CPU**: 1 core
- **Memory**: 2GB
- **Storage**: 50GB

#### Recommended Production
- **CPU**: 2 cores
- **Memory**: 4GB
- **Storage**: 200GB (with model storage)

### Performance Tuning

#### 1. Database Optimization

```bash
# PostgreSQL tuning
kubectl patch configmap postgres-config -p '{"data":{"shared_preload_libraries":"pg_stat_statements","max_connections":"200","shared_buffers":"1GB","effective_cache_size":"3GB","work_mem":"50MB"}}'
```

#### 2. Redis Optimization

```bash
# Redis memory optimization
kubectl patch configmap redis-config -p '{"data":{"maxmemory":"2gb","maxmemory-policy":"allkeys-lru","tcp-keepalive":"300"}}'
```

#### 3. Application Tuning

```bash
# Worker process optimization
kubectl set env deployment/synthetic-data-mcp MAX_WORKERS=8 -n synthetic-data
kubectl set env deployment/synthetic-data-mcp REQUEST_TIMEOUT=300 -n synthetic-data
```

## Monitoring and Observability

### Prometheus Metrics

The application exposes metrics on `/metrics`:

- **Request metrics**: Rate, duration, errors
- **Business metrics**: Records generated, privacy checks
- **System metrics**: Memory usage, CPU usage
- **Database metrics**: Connection pool, query performance

### Grafana Dashboards

Pre-configured dashboards for:

- **Application Performance**: Request latency, throughput, error rates
- **Resource Usage**: CPU, memory, network, storage
- **Business Metrics**: Generation rate, data quality metrics
- **Security Metrics**: Authentication failures, privacy violations

### Health Checks

#### Application Health Endpoints

- `GET /health` - Basic health check
- `GET /ready` - Readiness check
- `GET /metrics` - Prometheus metrics

#### Kubernetes Health Probes

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 3000
  initialDelaySeconds: 30
  periodSeconds: 30

readinessProbe:
  httpGet:
    path: /ready
    port: 3000
  initialDelaySeconds: 15
  periodSeconds: 10
```

### Log Management

#### Structured Logging

The application uses structured JSON logging with the following levels:

- **ERROR**: Application errors, exceptions
- **WARN**: Performance issues, deprecated usage
- **INFO**: Request/response, business events
- **DEBUG**: Detailed execution flow (dev only)

#### Log Aggregation

For production, configure log aggregation:

```yaml
# Fluentd DaemonSet for log collection
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluentd
spec:
  selector:
    matchLabels:
      app: fluentd
  template:
    spec:
      containers:
      - name: fluentd
        image: fluent/fluentd-kubernetes-daemonset:v1-debian-elasticsearch
```

## Backup and Recovery

### Database Backups

#### Automated PostgreSQL Backups

```bash
# Create backup job
kubectl create job postgres-backup-$(date +%Y%m%d) \
  --from=cronjob/postgres-backup \
  -n synthetic-data
```

#### Backup CronJob

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
  namespace: synthetic-data
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: postgres-backup
            image: postgres:15-alpine
            command:
            - /bin/bash
            - -c
            - |
              pg_dump -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB > /backup/backup-$(date +%Y%m%d).sql
              # Upload to object storage
            env:
            - name: POSTGRES_HOST
              value: synthetic-postgres
          restartPolicy: OnFailure
```

### Disaster Recovery

#### 1. Backup Strategy

- **Database**: Daily full backups, hourly incrementals
- **Application data**: Persistent volume snapshots
- **Configuration**: GitOps with infrastructure as code
- **Secrets**: External secret management (Vault, AWS Secrets Manager)

#### 2. Recovery Procedures

```bash
# Restore from backup
kubectl create job postgres-restore --from=cronjob/postgres-restore -n synthetic-data

# Verify data integrity
kubectl exec -it postgres-pod -- psql -U synthetic -d synthetic_data -c "SELECT COUNT(*) FROM audit_trail;"

# Check application health
kubectl get pods -n synthetic-data
curl -f https://synthetic-data.yourdomain.com/health
```

## Security Best Practices

### 1. Image Security

```bash
# Scan images for vulnerabilities
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image synthetic-data-mcp:latest
```

### 2. Runtime Security

```yaml
# Pod Security Standards
apiVersion: v1
kind: Namespace
metadata:
  name: synthetic-data
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

### 3. Network Security

```bash
# Enable network policies
kubectl apply -f k8s/network-policy.yaml

# Configure firewall rules
# Allow only necessary traffic on ports 80, 443, 3000
```

### 4. Secrets Management

Use external secret management systems:

```bash
# Example with AWS Secrets Manager
helm install external-secrets external-secrets/external-secrets \
  --namespace external-secrets-system \
  --create-namespace
```

## Troubleshooting

### Common Issues

#### 1. Pod CrashLoopBackOff

```bash
# Check pod logs
kubectl logs -f deployment/synthetic-data-mcp -n synthetic-data

# Check resource limits
kubectl describe pod -l app=synthetic-data-mcp -n synthetic-data

# Check health endpoints
kubectl exec -it deployment/synthetic-data-mcp -- curl localhost:3000/health
```

#### 2. Database Connection Issues

```bash
# Test database connectivity
kubectl exec -it deployment/synthetic-data-mcp -- \
  python -c "import psycopg2; print('DB OK')"

# Check database logs
kubectl logs -f deployment/synthetic-postgres -n synthetic-data
```

#### 3. Memory Issues

```bash
# Check memory usage
kubectl top pods -n synthetic-data

# Adjust resource limits
kubectl patch deployment synthetic-data-mcp -p '{"spec":{"template":{"spec":{"containers":[{"name":"synthetic-data-mcp","resources":{"limits":{"memory":"6Gi"}}}]}}}}'
```

### Performance Issues

#### 1. High Response Times

```bash
# Check metrics
curl -s http://synthetic-data.yourdomain.com/metrics | grep response_time

# Scale up if needed
kubectl scale deployment synthetic-data-mcp --replicas=10 -n synthetic-data
```

#### 2. Database Performance

```bash
# Check slow queries
kubectl exec -it postgres-pod -- psql -U synthetic -c "SELECT query, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"
```

## Maintenance

### Regular Maintenance Tasks

#### 1. Update Dependencies

```bash
# Update Helm chart dependencies
helm dependency update ./helm/synthetic-data-mcp

# Update application image
kubectl set image deployment/synthetic-data-mcp \
  synthetic-data-mcp=synthetic-data-mcp:v0.2.0 -n synthetic-data
```

#### 2. Certificate Renewal

```bash
# Check certificate expiration
kubectl get certificates -n synthetic-data

# Force renewal if needed
kubectl delete certificate synthetic-data-tls -n synthetic-data
kubectl apply -f k8s/certificates.yaml
```

#### 3. Database Maintenance

```bash
# Run VACUUM on PostgreSQL
kubectl exec -it postgres-pod -- psql -U synthetic -c "VACUUM ANALYZE;"

# Update statistics
kubectl exec -it postgres-pod -- psql -U synthetic -c "ANALYZE;"
```

### Monitoring Dashboard

Access monitoring dashboards:

- **Grafana**: https://grafana.yourdomain.com
- **Prometheus**: https://prometheus.yourdomain.com
- **Application**: https://synthetic-data.yourdomain.com

## Support

For issues and questions:

- **Documentation**: https://synthetic-data-mcp.readthedocs.io
- **GitHub Issues**: https://github.com/marc-shade/synthetic-data-mcp/issues
- **Email**: marc@2acrestudios.com

---

*Last updated: 2025-08-31*