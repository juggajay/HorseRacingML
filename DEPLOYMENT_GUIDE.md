# Deployment Guide - HorseRacingML

Complete guide to deploying your HorseRacingML project to production.

---

## 📦 Step 1: Create GitHub Repository

### Option A: Via GitHub Website (Easiest)

1. **Go to GitHub**: https://github.com/new

2. **Repository Details:**
   - **Name**: `HorseRacingML` (or your preferred name)
   - **Description**: `AI-powered horse racing predictions using Betfair & PuntingForm APIs`
   - **Visibility**:
     - ⚠️ **Private** (recommended - contains trading strategy)
     - OR Public (if you want to share)
   - **DO NOT** initialize with README (we already have one)

3. **Click "Create repository"**

4. **Copy the repository URL** (shown on next page)
   - Example: `https://github.com/yourusername/HorseRacingML.git`

### Option B: Via GitHub CLI

```bash
gh repo create HorseRacingML --private --source=. --remote=origin
```

---

## 🔗 Step 2: Connect Local Repository to GitHub

### From your project directory:

```bash
cd /mnt/c/Users/jayso/Documents/HorseRacingML

# Add GitHub as remote (replace with YOUR repository URL)
git remote add origin https://github.com/YOUR_USERNAME/HorseRacingML.git

# Rename branch to main (modern convention)
git branch -M main

# Push to GitHub
git push -u origin main
```

**Example** (replace with your actual username):
```bash
git remote add origin https://github.com/jryan1810/HorseRacingML.git
git branch -M main
git push -u origin main
```

---

## 🔐 Step 3: Set Up GitHub Secrets (for CI/CD)

If you plan to use GitHub Actions for deployment:

1. Go to your repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Add these secrets:

```
BETFAIR_APP_KEY = your_delayed_or_live_key
BETFAIR_USERNAME = your_username
BETFAIR_PASSWORD = your_password
PUNTINGFORM_API_KEY = your_pf_key
```

---

## 🚀 Step 4: Choose Your Deployment Platform

### Option 1: AWS ECS/Fargate (Recommended for Production)

**Pros:**
- Auto-scaling
- Managed containers
- High reliability
- Good for production loads

**Setup:**

1. **Install AWS CLI:**
   ```bash
   pip install awscli
   aws configure
   ```

2. **Push Docker images to ECR:**
   ```bash
   # Login to ECR
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com

   # Tag and push API
   docker tag horseracingml-api:latest YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/horseracingml-api:latest
   docker push YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/horseracingml-api:latest

   # Tag and push UI
   docker tag horseracingml-ui:latest YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/horseracingml-ui:latest
   docker push YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/horseracingml-ui:latest
   ```

3. **Create ECS Task Definition** (use AWS Console or CLI)

4. **Deploy to ECS Fargate**

**Cost estimate:** ~$20-50/month for small instance

---

### Option 2: Google Cloud Run (Easiest)

**Pros:**
- Serverless (pay only when running)
- Very easy setup
- Auto-scaling
- Free tier available

**Setup:**

1. **Install gcloud CLI:**
   ```bash
   curl https://sdk.cloud.google.com | bash
   gcloud init
   ```

2. **Deploy API:**
   ```bash
   cd services/api
   gcloud run deploy horseracingml-api \
     --source . \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --set-env-vars BETFAIR_APP_KEY=$BETFAIR_APP_KEY,BETFAIR_USERNAME=$BETFAIR_USERNAME,BETFAIR_PASSWORD=$BETFAIR_PASSWORD
   ```

3. **Deploy UI:**
   ```bash
   cd ../../web
   gcloud run deploy horseracingml-ui \
     --source . \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --set-env-vars NEXT_PUBLIC_API_BASE=https://your-api-url
   ```

**Cost estimate:** Free tier covers most small workloads

---

### Option 3: DigitalOcean App Platform (Simple)

**Pros:**
- Simple pricing
- Easy setup
- Good for small-medium projects

**Setup:**

1. **Go to**: https://cloud.digitalocean.com/apps

2. **Click "Create App"**

3. **Connect GitHub repository**

4. **Configure:**
   - **API Service**:
     - Build command: `docker build -f services/api/Dockerfile`
     - HTTP port: 8000
     - Environment variables: Add your secrets

   - **UI Service**:
     - Build command: `docker build -f web/Dockerfile`
     - HTTP port: 3000

5. **Deploy**

**Cost estimate:** ~$12-24/month

---

### Option 4: Railway.app (Very Easy)

**Pros:**
- GitHub integration
- Automatic deployments
- Free tier

**Setup:**

1. Go to: https://railway.app
2. Sign in with GitHub
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your HorseRacingML repository
5. Add environment variables in dashboard
6. Deploy!

**Cost estimate:** Free tier → ~$5-20/month

---

### Option 5: Render.com (Free Tier Available)

**Pros:**
- Free tier for small projects
- Auto-deploy from GitHub
- Simple setup

**Setup:**

1. Go to: https://render.com
2. Sign up/Login
3. Click "New +" → "Web Service"
4. Connect GitHub repository
5. Configure services (API & UI separately)
6. Add environment variables
7. Deploy!

**Cost estimate:** Free tier → ~$7-21/month

---

## 📊 Step 5: Production Checklist

### Before Going Live:

- [ ] **Test with delayed API key first**
- [ ] **Verify model predictions are accurate**
- [ ] **Set up monitoring/logging**
- [ ] **Configure auto-backups for models**
- [ ] **Set up alerting for errors**
- [ ] **Document deployment process**
- [ ] **Set up SSL/HTTPS**
- [ ] **Configure domain name (optional)**

### Security:

- [ ] **All secrets in environment variables**
- [ ] **Never commit `.env` file**
- [ ] **Enable HTTPS only**
- [ ] **Set up firewall rules**
- [ ] **Regular security updates**
- [ ] **API rate limiting enabled**

### Monitoring:

- [ ] **Health check endpoints working**
- [ ] **Error tracking (Sentry, etc.)**
- [ ] **Performance monitoring**
- [ ] **Cost monitoring**
- [ ] **API usage tracking**

---

## 🔄 Step 6: Continuous Deployment (Optional)

### GitHub Actions Workflow

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Production

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build and Deploy
        env:
          BETFAIR_APP_KEY: ${{ secrets.BETFAIR_APP_KEY }}
          BETFAIR_USERNAME: ${{ secrets.BETFAIR_USERNAME }}
          BETFAIR_PASSWORD: ${{ secrets.BETFAIR_PASSWORD }}
        run: |
          # Your deployment commands here
          echo "Deploying to production..."
```

---

## 📈 Step 7: Scaling Considerations

### When to Upgrade to Live Betfair Key (£299)

Upgrade when:
- ✅ Model proven profitable in backtesting
- ✅ Ready for live trading
- ✅ Need real-time data (no delay)
- ✅ Automated betting system

### Performance Optimization

- **API Caching**: Cache market data for 5-10 seconds
- **Database**: Add PostgreSQL for historical tracking
- **CDN**: Use CloudFlare for UI
- **Load Balancer**: For high traffic
- **Redis**: For session management

---

## 💰 Cost Estimates (Monthly)

| Platform | Free Tier | Small | Medium | Large |
|----------|-----------|-------|--------|-------|
| **Railway** | ✅ $5 | $10-20 | $30-50 | $100+ |
| **Render** | ✅ Free | $7-21 | $50-100 | $200+ |
| **DigitalOcean** | ❌ | $12-24 | $40-80 | $150+ |
| **Google Cloud Run** | ✅ Free | $5-15 | $20-50 | $100+ |
| **AWS ECS** | ❌ | $20-40 | $80-150 | $300+ |

**Plus:**
- Betfair Live Key: £299 one-time (optional)
- Domain name: ~$12/year (optional)

---

## 🆘 Troubleshooting

### Common Issues:

**Build fails:**
- Check Docker logs
- Verify all dependencies in requirements.txt
- Ensure Node.js version matches

**Environment variables not working:**
- Check platform-specific syntax
- Verify secrets are set correctly
- Restart services after adding

**API connection issues:**
- Check firewall/security groups
- Verify CORS settings
- Test endpoints with curl

**Out of memory:**
- Increase container memory limit
- Optimize model loading
- Enable pagination for large datasets

---

## 📞 Support Resources

- **GitHub Issues**: For project-specific problems
- **Platform Support**:
  - AWS: https://aws.amazon.com/support/
  - Google Cloud: https://cloud.google.com/support
  - DigitalOcean: https://www.digitalocean.com/support/
  - Railway: https://railway.app/help
  - Render: https://render.com/docs

- **Betfair**: automation@betfair.com.au
- **PuntingForm**: support@puntingform.com.au

---

## 🎯 Quick Start Commands

### Initial Setup (Run Once):

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/HorseRacingML.git
cd HorseRacingML

# Set up environment
cp .env.example .env
# Edit .env with your credentials

# Test locally
docker-compose up -d

# Verify
curl http://localhost:8000/health
```

### Update and Deploy:

```bash
# Make changes to code
git add .
git commit -m "Your commit message"
git push origin main

# Platform will auto-deploy (if CD enabled)
# Or manually trigger deployment on platform dashboard
```

---

## ✅ You're Ready!

Your repository is now ready for deployment. Choose a platform above and follow the setup instructions.

**Recommended for beginners:** Start with Render.com or Railway.app (free tiers available)

**Recommended for production:** Google Cloud Run or AWS ECS

---

**Need help?** Check the platform-specific documentation or create a GitHub issue.

Good luck with your deployment! 🚀🏇
