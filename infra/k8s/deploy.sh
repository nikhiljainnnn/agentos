#!/bin/bash
set -e

echo "🚀 AgentOS k3d Deployment Script"
echo "================================="

CLUSTER_NAME="agentos"
REGISTRY_NAME="agentos-registry"
REGISTRY_PORT="5001"

# ─── 1. Create k3d cluster ────────────────────────────────────────────────────
echo "📦 Creating k3d cluster..."
k3d cluster create $CLUSTER_NAME \
  --agents 2 \
  --port "8080:80@loadbalancer" \
  --port "8443:443@loadbalancer" \
  --registry-create $REGISTRY_NAME:$REGISTRY_PORT \
  --k3s-arg "--disable=traefik@server:0" \
  --wait

echo "✅ Cluster created: $CLUSTER_NAME"

# ─── 2. Install nginx ingress ─────────────────────────────────────────────────
echo "🌐 Installing nginx ingress..."
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.11.0/deploy/static/provider/cloud/deploy.yaml
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=90s

# ─── 3. Build and push Docker image ──────────────────────────────────────────
echo "🐳 Building Docker image..."
cd ../../
docker build -t localhost:$REGISTRY_PORT/agentos-gateway:latest .
docker push localhost:$REGISTRY_PORT/agentos-gateway:latest

# Update image in deployment
sed -i "s|agentos-gateway:latest|localhost:$REGISTRY_PORT/agentos-gateway:latest|g" infra/k8s/deployment.yaml

# ─── 4. Deploy infrastructure (postgres, redis, etc.) ────────────────────────
echo "🗄️  Deploying infrastructure..."
kubectl apply -f infra/k8s/infrastructure.yaml

echo "⏳ Waiting for infrastructure..."
kubectl wait --namespace agentos \
  --for=condition=ready pod \
  --selector=tier=database \
  --timeout=120s || true

# ─── 5. Run DB migrations ─────────────────────────────────────────────────────
echo "📊 Running migrations..."
kubectl run --namespace agentos \
  migration-job \
  --image=localhost:$REGISTRY_PORT/agentos-gateway:latest \
  --restart=Never \
  --rm \
  --attach \
  -- alembic upgrade head || echo "⚠️  Migration may need manual intervention"

# ─── 6. Deploy application ────────────────────────────────────────────────────
echo "🚀 Deploying application..."
kubectl apply -f infra/k8s/deployment.yaml

echo "⏳ Waiting for gateway pods..."
kubectl rollout status deployment/agentos-gateway -n agentos --timeout=120s

# ─── 7. Add local host entry ─────────────────────────────────────────────────
echo ""
echo "✅ Deployment complete!"
echo ""
echo "📋 Services:"
kubectl get pods -n agentos
echo ""
echo "🌐 Access:"
echo "  API:      http://agentos.local:8080"
echo "  Docs:     http://agentos.local:8080/docs"
echo "  Grafana:  http://localhost:3001 (admin/admin)"
echo "  Prometheus: http://localhost:9090"
echo ""
echo "⚠️  Add to /etc/hosts:  127.0.0.1  agentos.local"
