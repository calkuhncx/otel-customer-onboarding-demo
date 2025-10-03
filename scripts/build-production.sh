#!/bin/bash
set -e

echo "🏗️ Building production-ready demo for customer..."

# Copy clean files into place
echo "📁 Preparing clean files..."
cp onboarding-api/app.clean.py onboarding-api/app.py
cp onboarding-lambda/app.simple.py onboarding-lambda/app.py
cp otel/production-collector.yaml otel/ecs-collector.yaml

# Build Lambda container image (standard approach)
echo "📦 Building Lambda container image..."
docker build --platform linux/amd64 \
  -t 104013952213.dkr.ecr.us-west-2.amazonaws.com/cal-onboarding-lambda:production \
  -f onboarding-lambda/Dockerfile.simple .

# Build clean API image
echo "📦 Building ECS API image..."
docker build --platform linux/amd64 \
  -t 104013952213.dkr.ecr.us-west-2.amazonaws.com/cal-onboarding-api:production \
  -f onboarding-api/Dockerfile .

# Build production collector
echo "📦 Building production collector..."
docker build --platform linux/amd64 \
  -t 104013952213.dkr.ecr.us-west-2.amazonaws.com/cal-otel-collector:production \
  -f otel/Dockerfile .

echo "✅ All images built successfully!"

# Push images
echo "🚀 Pushing images to ECR..."
docker push 104013952213.dkr.ecr.us-west-2.amazonaws.com/cal-onboarding-lambda:production
docker push 104013952213.dkr.ecr.us-west-2.amazonaws.com/cal-onboarding-api:production  
docker push 104013952213.dkr.ecr.us-west-2.amazonaws.com/cal-otel-collector:production

echo "✅ All images pushed successfully!"
echo "🎯 Ready for customer demo!"
