# Git Setup and Publishing Guide

## Quick Start

```bash
cd /Users/calumkuhn/Downloads/otel-integration/customer-onboarding-demo

# Initialize repository
git init

# Add all files
git add .

# Create initial commit
git commit -m "Complete OpenTelemetry implementation for ECS Fargate → SQS → Lambda

Features:
- End-to-end distributed tracing with W3C TraceContext
- Lambda container image with pure OTel SDK
- OTLP gRPC export to Coralogix
- Custom Lambda observability dashboard
- Production-ready patterns and error handling"

# Add remote (replace with your GitHub repo URL)
git remote add origin https://github.com/YOUR_USERNAME/otel-ecs-sqs-lambda-demo.git

# Push to GitHub
git branch -M main
git push -u origin main
```

## Repository Best Practices

### What's Included
✅ Source code with inline documentation  
✅ Comprehensive README with quick start  
✅ Implementation summary with architecture details  
✅ Dashboard JSON and setup guide  
✅ `.gitignore` to exclude temporary files  

### What's Excluded (via .gitignore)
❌ Python cache files (`__pycache__/`, `*.pyc`)  
❌ IDE configurations (`.vscode/`, `.idea/`)  
❌ OS files (`.DS_Store`, `Thumbs.db`)  
❌ Environment variables (`.env` files)  
❌ Log files (`*.log`)  

## GitHub Repository Setup

### 1. Create New Repository on GitHub

```bash
# Via GitHub CLI (if installed)
gh repo create otel-ecs-sqs-lambda-demo --public --description "Production-ready OpenTelemetry implementation for ECS Fargate → SQS → Lambda with Coralogix APM"

# Or manually:
# 1. Go to https://github.com/new
# 2. Repository name: otel-ecs-sqs-lambda-demo
# 3. Description: Production-ready OpenTelemetry implementation for ECS Fargate → SQS → Lambda
# 4. Public or Private: Your choice
# 5. Do NOT initialize with README (we already have one)
# 6. Click "Create repository"
```

### 2. Add Topics/Tags

Add these topics to your repository for discoverability:
- `opentelemetry`
- `aws-lambda`
- `ecs-fargate`
- `distributed-tracing`
- `observability`
- `sqs`
- `coralogix`
- `apm`
- `w3c-tracecontext`
- `python`

### 3. Configure Repository Settings

**Recommended settings:**
- ✅ Enable Issues (for questions/feedback)
- ✅ Enable Discussions (for community help)
- ✅ Add LICENSE file (MIT or Apache 2.0)
- ✅ Add repository description
- ✅ Add website link (to Coralogix docs if applicable)

## Repository Structure

```
otel-ecs-sqs-lambda-demo/
│
├── README.md                          # Primary documentation
├── IMPLEMENTATION-SUMMARY.md          # Technical deep-dive
├── GIT-SETUP.md                       # This file
├── LICENSE                            # Open source license
├── .gitignore                         # Git exclusions
│
├── onboarding-api/                    # ECS Fargate service
│   ├── app.py                         # Flask app with OTel
│   ├── Dockerfile                     # Container image
│   └── requirements.txt               # Python dependencies
│
├── onboarding-lambda/                 # Lambda function
│   ├── app.py                         # Handler with OTel SDK
│   ├── Dockerfile                     # Lambda container image
│   └── requirements.txt               # Python dependencies
│
├── otel/                              # OpenTelemetry Collector
│   ├── coralogix-collector.yaml       # Collector config
│   ├── ecs-collector.yaml             # ECS-specific config
│   └── Dockerfile                     # Collector image
│
├── infrastructure/                    # AWS infrastructure
│   └── taskdef.json                   # ECS task definition
│
└── dashboards/                        # Observability dashboards
    ├── README.md                      # Dashboard setup guide
    └── lambda-observability-dashboard.json
```

## Commit Message Guidelines

Use conventional commits for clarity:

```bash
# Features
git commit -m "feat: add W3C context propagation for SQS"

# Bug fixes
git commit -m "fix: resolve Lambda span export timing issue"

# Documentation
git commit -m "docs: add CloudWatch Metric Streams setup guide"

# Refactoring
git commit -m "refactor: simplify trace context extraction logic"

# Performance
git commit -m "perf: optimize span batch processor settings"
```

## Branching Strategy

For ongoing development:

```bash
# Create feature branch
git checkout -b feature/add-dynamodb-tracing

# Make changes and commit
git add .
git commit -m "feat: add DynamoDB instrumentation"

# Push feature branch
git push origin feature/add-dynamodb-tracing

# Create pull request on GitHub
# After review, merge to main
```

## Keeping Secrets Safe

**NEVER commit:**
- ❌ AWS credentials
- ❌ Coralogix API keys
- ❌ Private keys or certificates

**Use placeholders instead:**

```python
# ❌ BAD
API_KEY = "abc123secretkey456"

# ✅ GOOD
API_KEY = os.environ.get("CORALOGIX_API_KEY")  # Set via env var or AWS Secrets Manager
```

**If you accidentally commit a secret:**

```bash
# Remove from history (requires force push!)
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch path/to/sensitive/file" \
  --prune-empty --tag-name-filter cat -- --all

# Force push (⚠️ use with caution)
git push origin --force --all

# Rotate the compromised secret immediately!
```

## Creating Releases

When ready for a release:

```bash
# Tag the release
git tag -a v1.0.0 -m "Release v1.0.0: Production-ready OTel implementation"

# Push tag to GitHub
git push origin v1.0.0

# Create release on GitHub
# 1. Go to Releases → Draft a new release
# 2. Choose tag: v1.0.0
# 3. Release title: "v1.0.0 - Production-Ready OTel Implementation"
# 4. Add release notes with highlights
# 5. Publish release
```

**Release Notes Template:**

```markdown
## What's New in v1.0.0

### Features
- Complete end-to-end distributed tracing (ECS → SQS → Lambda)
- W3C TraceContext propagation via SQS MessageAttributes
- Lambda container image with pure OpenTelemetry SDK
- Custom Lambda observability dashboard with CloudWatch metrics
- Production-ready error handling and span flushing

### Technical Details
- OTLP gRPC export to Coralogix APM
- ARM64 Lambda for cost optimization
- Span metrics connector for APM dashboard
- Comprehensive documentation and setup guides

### Requirements
- AWS Account with ECS, Lambda, SQS access
- Coralogix account with Send-Your-Data API key
- Docker and AWS CLI

### Documentation
- Quick Start: [README.md](README.md)
- Technical Deep-Dive: [IMPLEMENTATION-SUMMARY.md](IMPLEMENTATION-SUMMARY.md)
- Dashboard Setup: [dashboards/README.md](dashboards/README.md)
```

## README Badge Ideas

Add badges to your README for visual appeal:

```markdown
![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![AWS](https://img.shields.io/badge/AWS-ECS%20%7C%20Lambda%20%7C%20SQS-orange.svg)
![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-1.21+-purple.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Status](https://img.shields.io/badge/Status-Production--Ready-success.svg)
```

## Sharing with Customer

### Option 1: Public Repository
Share the GitHub URL directly:
```
https://github.com/YOUR_USERNAME/otel-ecs-sqs-lambda-demo
```

### Option 2: Private Repository with Access
```bash
# Add customer as collaborator
# GitHub → Settings → Collaborators → Add people
```

### Option 3: Export as ZIP
```bash
# Create clean export without git history
git archive --format=zip --output=otel-demo.zip HEAD
```

### Option 4: Fork for Customer
Customer can fork your repository and customize:
```bash
# Customer clicks "Fork" on GitHub
# Then clones their fork
git clone https://github.com/CUSTOMER_USERNAME/otel-ecs-sqs-lambda-demo.git
```

## Post-Publish Checklist

After pushing to GitHub:

- [ ] Verify all files are present
- [ ] Check README renders correctly
- [ ] Test clone on fresh machine
- [ ] Add repository description and topics
- [ ] Create first release tag
- [ ] Share link with customer
- [ ] Add to your portfolio/demos list
- [ ] Write blog post or create demo video (optional)

## Support and Contributions

If making this an open-source project:

```markdown
## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Support

- 📚 Documentation: See [README.md](README.md) and [IMPLEMENTATION-SUMMARY.md](IMPLEMENTATION-SUMMARY.md)
- 🐛 Issues: [GitHub Issues](https://github.com/YOUR_USERNAME/otel-ecs-sqs-lambda-demo/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/YOUR_USERNAME/otel-ecs-sqs-lambda-demo/discussions)
```

---

**Ready to publish?**

```bash
cd /Users/calumkuhn/Downloads/otel-integration/customer-onboarding-demo
git init
git add .
git commit -m "Complete OpenTelemetry implementation for ECS→SQS→Lambda"
git remote add origin https://github.com/YOUR_USERNAME/otel-ecs-sqs-lambda-demo.git
git push -u origin main
```

🎉 **Your production-ready OTel demo is ready to share!**

