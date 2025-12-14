#!/bin/bash

# Synthetic Data MCP - Production Deployment Script
# This script automates the deployment of the Synthetic Data MCP platform

set -euo pipefail

# Configuration
NAMESPACE="synthetic-data"
RELEASE_NAME="synthetic-data-mcp"
CHART_PATH="./helm/synthetic-data-mcp"
DOMAIN="${DOMAIN:-synthetic-data.example.com}"
ENVIRONMENT="${ENVIRONMENT:-production}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if running in correct directory
    if [[ ! -f "Chart.yaml" && ! -f "helm/synthetic-data-mcp/Chart.yaml" ]]; then
        log_error "Please run this script from the project root directory"
        exit 1
    fi
    
    # Check required tools
    local tools=("kubectl" "helm" "docker")
    for tool in "${tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "$tool is not installed or not in PATH"
            exit 1
        fi
    done
    
    # Check Kubernetes connectivity
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
    
    log_success "All prerequisites satisfied"
}

# Build and push Docker image
build_and_push_image() {
    log_info "Building Docker image..."
    
    local image_tag="${REGISTRY:-docker.io}/${IMAGE_REPOSITORY:-synthetic-data-mcp}:${IMAGE_TAG:-latest}"
    
    # Build image with security scanning
    docker build \
        --build-arg PYTHON_VERSION=3.11.10 \
        --build-arg DEBIAN_VERSION=bookworm \
        -t "$image_tag" \
        .
    
    # Security scan (if Trivy is available)
    if command -v trivy &> /dev/null; then
        log_info "Scanning image for vulnerabilities..."
        trivy image --severity HIGH,CRITICAL "$image_tag"
    fi
    
    # Push image if registry is configured
    if [[ -n "${REGISTRY:-}" ]]; then
        log_info "Pushing image to registry..."
        docker push "$image_tag"
        log_success "Image pushed successfully"
    fi
    
    log_success "Image built: $image_tag"
    export BUILT_IMAGE="$image_tag"
}

# Setup Helm repositories
setup_helm_repos() {
    log_info "Setting up Helm repositories..."
    
    helm repo add bitnami https://charts.bitnami.com/bitnami
    helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo add cert-manager https://charts.jetstack.io
    
    helm repo update
    
    log_success "Helm repositories configured"
}

# Install cert-manager for TLS
install_cert_manager() {
    log_info "Installing cert-manager..."
    
    # Check if cert-manager is already installed
    if kubectl get namespace cert-manager &> /dev/null; then
        log_warn "cert-manager already installed"
        return 0
    fi
    
    helm install cert-manager cert-manager/cert-manager \
        --namespace cert-manager \
        --create-namespace \
        --version v1.13.0 \
        --set installCRDs=true \
        --wait
    
    # Install ClusterIssuer for Let's Encrypt
    kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@${DOMAIN}
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
    
    log_success "cert-manager installed and configured"
}

# Install NGINX Ingress Controller
install_ingress_nginx() {
    log_info "Installing NGINX Ingress Controller..."
    
    # Check if already installed
    if kubectl get namespace ingress-nginx &> /dev/null; then
        log_warn "NGINX Ingress already installed"
        return 0
    fi
    
    helm install ingress-nginx ingress-nginx/ingress-nginx \
        --namespace ingress-nginx \
        --create-namespace \
        --set controller.metrics.enabled=true \
        --set controller.podAnnotations."prometheus\.io/scrape"=true \
        --set controller.podAnnotations."prometheus\.io/port"=10254 \
        --wait
    
    log_success "NGINX Ingress Controller installed"
}

# Generate and validate configuration
generate_config() {
    log_info "Generating deployment configuration..."
    
    # Create values override file
    cat > values-${ENVIRONMENT}.yaml <<EOF
global:
  imageRegistry: "${REGISTRY:-docker.io}"
  imagePullSecrets: []

image:
  repository: "${IMAGE_REPOSITORY:-synthetic-data-mcp}"
  tag: "${IMAGE_TAG:-latest}"

deployment:
  replicas: ${REPLICAS:-3}

ingress:
  enabled: true
  className: nginx
  hosts:
    - host: ${DOMAIN}
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: synthetic-data-tls
      hosts:
        - ${DOMAIN}

autoscaling:
  enabled: true
  minReplicas: ${MIN_REPLICAS:-3}
  maxReplicas: ${MAX_REPLICAS:-20}

postgresql:
  enabled: true
  auth:
    database: synthetic_data
    username: synthetic
    password: "${DB_PASSWORD:-$(openssl rand -base64 32)}"

redis:
  enabled: true
  auth:
    enabled: true
    password: "${REDIS_PASSWORD:-$(openssl rand -base64 32)}"

monitoring:
  enabled: true

secrets:
  values:
    openaiApiKey: "${OPENAI_API_KEY:-}"
    apiKey: "${API_KEY:-$(openssl rand -hex 32)}"
    jwtSecret: "${JWT_SECRET:-$(openssl rand -base64 64)}"
    encryptionKey: "${ENCRYPTION_KEY:-$(openssl rand -hex 32)}"
    dbPassword: "${DB_PASSWORD:-$(openssl rand -base64 32)}"
    redisPassword: "${REDIS_PASSWORD:-$(openssl rand -base64 32)}"
EOF
    
    log_success "Configuration generated: values-${ENVIRONMENT}.yaml"
}

# Deploy with Helm
deploy_application() {
    log_info "Deploying application with Helm..."
    
    # Create namespace
    kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
    
    # Label namespace for monitoring
    kubectl label namespace "$NAMESPACE" monitoring=enabled --overwrite
    
    # Install/upgrade the application
    helm upgrade --install "$RELEASE_NAME" "$CHART_PATH" \
        --namespace "$NAMESPACE" \
        --values "values-${ENVIRONMENT}.yaml" \
        --timeout 10m \
        --wait \
        --atomic
    
    log_success "Application deployed successfully"
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."
    
    # Wait for pods to be ready
    kubectl wait --for=condition=ready pod \
        -l "app.kubernetes.io/name=synthetic-data-mcp" \
        -n "$NAMESPACE" \
        --timeout=300s
    
    # Check deployment status
    local deployment_status
    deployment_status=$(kubectl get deployment "$RELEASE_NAME" -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}')
    local desired_replicas
    desired_replicas=$(kubectl get deployment "$RELEASE_NAME" -n "$NAMESPACE" -o jsonpath='{.spec.replicas}')
    
    if [[ "$deployment_status" -eq "$desired_replicas" ]]; then
        log_success "All $deployment_status/$desired_replicas pods are ready"
    else
        log_error "Only $deployment_status/$desired_replicas pods are ready"
        return 1
    fi
    
    # Test health endpoint
    log_info "Testing health endpoint..."
    local service_port
    service_port=$(kubectl get service "$RELEASE_NAME" -n "$NAMESPACE" -o jsonpath='{.spec.ports[0].port}')
    
    if kubectl port-forward "service/$RELEASE_NAME" 8080:$service_port -n "$NAMESPACE" &
    then
        local pf_pid=$!
        sleep 5
        
        if curl -f -s "http://localhost:8080/health" > /dev/null; then
            log_success "Health check passed"
        else
            log_error "Health check failed"
            kill $pf_pid 2>/dev/null || true
            return 1
        fi
        
        kill $pf_pid 2>/dev/null || true
    fi
}

# Display deployment information
show_deployment_info() {
    log_info "Deployment Information"
    echo "========================"
    
    # Get external IP
    local external_ip
    external_ip=$(kubectl get ingress "$RELEASE_NAME" -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "Pending")
    
    echo "Namespace: $NAMESPACE"
    echo "Release: $RELEASE_NAME"
    echo "Domain: https://$DOMAIN"
    echo "External IP: $external_ip"
    echo ""
    
    echo "Useful Commands:"
    echo "  # Check pod status"
    echo "  kubectl get pods -n $NAMESPACE"
    echo ""
    echo "  # View logs"
    echo "  kubectl logs -f deployment/$RELEASE_NAME -n $NAMESPACE"
    echo ""
    echo "  # Port forward for local access"
    echo "  kubectl port-forward service/$RELEASE_NAME 8080:80 -n $NAMESPACE"
    echo ""
    echo "  # Scale deployment"
    echo "  kubectl scale deployment $RELEASE_NAME --replicas=5 -n $NAMESPACE"
    echo ""
    
    # Show resource usage
    echo "Resource Usage:"
    kubectl top pods -n "$NAMESPACE" 2>/dev/null || log_warn "Metrics server not available"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up temporary files..."
    rm -f "values-${ENVIRONMENT}.yaml"
}

# Main deployment function
main() {
    log_info "Starting Synthetic Data MCP deployment..."
    log_info "Environment: $ENVIRONMENT"
    log_info "Domain: $DOMAIN"
    log_info "Namespace: $NAMESPACE"
    
    # Trap cleanup on exit
    trap cleanup EXIT
    
    # Run deployment steps
    check_prerequisites
    build_and_push_image
    setup_helm_repos
    install_cert_manager
    install_ingress_nginx
    generate_config
    deploy_application
    verify_deployment
    show_deployment_info
    
    log_success "Deployment completed successfully!"
    log_info "Application will be available at: https://$DOMAIN"
}

# Script usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -d DOMAIN     Set the application domain (default: synthetic-data.example.com)"
    echo "  -e ENV        Set environment (default: production)"
    echo "  -n NAMESPACE  Set Kubernetes namespace (default: synthetic-data)"
    echo "  -r REGISTRY   Set Docker registry (default: docker.io)"
    echo "  -t TAG        Set image tag (default: latest)"
    echo "  -h            Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  OPENAI_API_KEY    OpenAI API key (required for AI features)"
    echo "  API_KEY          Custom API key (auto-generated if not provided)"
    echo "  DB_PASSWORD      Database password (auto-generated if not provided)"
    echo "  REDIS_PASSWORD   Redis password (auto-generated if not provided)"
    echo ""
    echo "Examples:"
    echo "  # Deploy with custom domain"
    echo "  $0 -d myapp.example.com"
    echo ""
    echo "  # Deploy to staging environment"
    echo "  $0 -e staging -d staging.example.com -t v0.1.0"
}

# Parse command line arguments
while getopts "d:e:n:r:t:h" opt; do
    case $opt in
        d)
            DOMAIN="$OPTARG"
            ;;
        e)
            ENVIRONMENT="$OPTARG"
            ;;
        n)
            NAMESPACE="$OPTARG"
            ;;
        r)
            REGISTRY="$OPTARG"
            ;;
        t)
            IMAGE_TAG="$OPTARG"
            ;;
        h)
            usage
            exit 0
            ;;
        \?)
            log_error "Invalid option: -$OPTARG"
            usage
            exit 1
            ;;
    esac
done

# Run main function
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi