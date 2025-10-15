# Vercel Deployment Guide - HorseRacingML

Complete guide to deploying HorseRacingML with Vercel (Frontend) + Railway (Backend)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│  Vercel (Frontend - Next.js UI)         │
│  https://horseracingml.vercel.app       │
└────────────────┬────────────────────────┘
                 │
                 │ API Calls
                 ▼
┌─────────────────────────────────────────┐
│  Railway (Backend - FastAPI)            │
│  https://horseracingml-api.railway.app  │
│                                          │
│  ┌────────────────────────────────┐     │
│  │  Betfair API                   │     │
│  │  PuntingForm API               │     │
│  │  LightGBM Model                │     │
│  └────────────────────────────────┘     │
└──────────────────────────────────────────┘
```

---

## 📋 Environment Variables Summary

### **Vercel (Frontend) - 1 variable**
```bash
NEXT_PUBLIC_API_BASE=https://your-backend-url.railway.app
```

### **Railway (Backend) - 5 variables**
```bash
BETFAIR_APP_KEY=qkXksbzX9pMJfLCp
BETFAIR_USERNAME=jryan1810
BETFAIR_PASSWORD=Kn2Y9s3aRh.h8q!
PUNTINGFORM_API_KEY=5b0df8bf-da9a-4d1e-995d-9b7a002aa836
PF_MODE=starter
```

---

## 🚀 Step-by-Step Deployment

### **PART 1: Deploy Backend API to Railway**

#### 1. Create Railway Account
- Go to: https://railway.app
- Click "Login with GitHub"
- Authorize Railway

#### 2. Create New Project
- Click "New Project"
- Select "Deploy from GitHub repo"
- Choose: `juggajay/HorseRacingML`
- Railway will detect your project

#### 3. Configure Service
- Railway will create a service
- Click on the service card
- Go to **"Settings"** tab

#### 4. Set Root Directory
- Find **"Root Directory"**
- Set to: `services/api`
- This tells Railway where the API code is

#### 5. Add Environment Variables
Click **"Variables"** tab, add these:

```
BETFAIR_APP_KEY = qkXksbzX9pMJfLCp
BETFAIR_USERNAME = jryan1810
BETFAIR_PASSWORD = Kn2Y9s3aRh.h8q!
PUNTINGFORM_API_KEY = 5b0df8bf-da9a-4d1e-995d-9b7a002aa836
PF_MODE = starter
```

#### 6. Generate Domain
- Go to **"Settings"** → **"Networking"**
- Click **"Generate Domain"**
- Copy the URL (e.g., `https://horseracingml-production.up.railway.app`)
- **Save this URL** - you'll need it for Vercel!

#### 7. Deploy
- Railway will auto-deploy
- Wait for build to complete (2-3 minutes)
- Check logs for any errors

#### 8. Test API
```bash
curl https://your-railway-url.railway.app/health
```

Should return: `{"status":"ok"}`

---

### **PART 2: Deploy Frontend UI to Vercel**

#### 1. Install Vercel CLI (Optional)
```bash
npm install -g vercel
```

#### 2. Go to Vercel Dashboard
- Go to: https://vercel.com
- Click "Login with GitHub"
- Authorize Vercel

#### 3. Import Project
- Click **"Add New..."** → **"Project"**
- Select: `juggajay/HorseRacingML`
- Click **"Import"**

#### 4. Configure Build Settings

**Framework Preset:** Next.js

**Root Directory:**
- Click **"Edit"**
- Set to: `web`
- This tells Vercel where the UI code is

**Build Command:** (auto-detected)
```
npm run build
```

**Output Directory:** (auto-detected)
```
.next
```

#### 5. Add Environment Variables

Click **"Environment Variables"**, add:

**Variable Name:**
```
NEXT_PUBLIC_API_BASE
```

**Value:** (Use your Railway URL from Part 1)
```
https://your-railway-url.railway.app
```

**Environments:** Check all (Production, Preview, Development)

#### 6. Deploy
- Click **"Deploy"**
- Vercel will build and deploy (2-3 minutes)
- You'll get a URL like: `https://horseracingml.vercel.app`

#### 7. Test Frontend
- Open your Vercel URL in browser
- You should see the HorseRacingML UI
- It should connect to your Railway API

---

## ✅ Verification Checklist

### Backend (Railway)
- [ ] Service deployed successfully
- [ ] Health endpoint working: `/health`
- [ ] Environment variables set correctly
- [ ] Domain generated and accessible
- [ ] Logs show no errors

### Frontend (Vercel)
- [ ] Build completed successfully
- [ ] Site loads in browser
- [ ] API connection working
- [ ] No console errors
- [ ] Data loads correctly

---

## 🔧 Troubleshooting

### **Frontend can't connect to API**

**Symptom:** UI loads but no data

**Solutions:**
1. Check `NEXT_PUBLIC_API_BASE` is set correctly
2. Verify Railway URL is accessible
3. Check CORS settings in API
4. Look at browser console for errors

**Fix CORS (if needed):**

Edit `services/api/main.py`:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://horseracingml.vercel.app"],  # Your Vercel URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Then commit and push:
```bash
git add services/api/main.py
git commit -m "Add CORS for Vercel frontend"
git push origin main
```

### **Railway API not starting**

**Check logs:**
- Go to Railway dashboard
- Click on service
- Click "Deployments"
- Click latest deployment
- Check logs for errors

**Common issues:**
- Missing environment variables
- Wrong root directory (`services/api`)
- Missing dependencies in `requirements.txt`

### **Vercel build fails**

**Check:**
- Root directory set to `web`
- `package.json` exists in `web/` directory
- Node.js version compatible

**View build logs:**
- Vercel dashboard → Deployments → Click deployment → View logs

---

## 💰 Cost Estimate

### **Free Tier (For Testing)**
- **Railway**: $5 free credit/month → ~$5-10/month after
- **Vercel**: Free for hobby projects
- **Total**: FREE to start, then ~$5-10/month

### **Production**
- **Railway**: ~$10-20/month (API backend)
- **Vercel**: FREE (or $20/month Pro for team features)
- **Betfair Live Key**: £299 one-time (optional upgrade)
- **Total**: ~$10-20/month + optional £299 one-time

---

## 🔄 Continuous Deployment

### Auto-Deploy on Git Push

**Already configured!** Both Vercel and Railway watch your GitHub repo:

1. Make changes locally
2. Commit and push:
   ```bash
   git add .
   git commit -m "Your changes"
   git push origin main
   ```
3. **Vercel** auto-deploys UI
4. **Railway** auto-deploys API
5. Changes live in ~2-3 minutes!

---

## 📊 Monitoring & Logs

### **Vercel Logs**
- Dashboard → Your Project → Deployments → Click deployment
- Real-time function logs
- Performance analytics

### **Railway Logs**
- Dashboard → Your Service → Deployments
- Real-time application logs
- Resource usage metrics

---

## 🔐 Security Best Practices

### **Environment Variables**
- ✅ Never commit `.env` files
- ✅ Use Vercel/Railway secret management
- ✅ Rotate credentials regularly

### **API Keys**
- ✅ Start with Betfair Delayed key (FREE)
- ✅ Upgrade to Live key only when ready
- ✅ Keep PuntingForm key in backend only

### **CORS**
- ✅ Whitelist only your Vercel domain
- ✅ Don't use `allow_origins=["*"]` in production

---

## 🚀 Quick Commands Reference

### **Deploy Backend to Railway**
```bash
# Railway will auto-deploy from GitHub
# Or use CLI:
railway login
railway link
railway up
```

### **Deploy Frontend to Vercel**
```bash
# From web/ directory:
cd web
vercel
# Follow prompts
```

### **Update Environment Variables**

**Vercel:**
```bash
vercel env add NEXT_PUBLIC_API_BASE
# Enter value when prompted
```

**Railway:**
- Use dashboard → Variables tab
- Or CLI: `railway variables set KEY=value`

---

## 📈 Scaling

### **When Traffic Grows:**

**Railway:**
- Upgrade plan for more resources
- Add Redis for caching
- Horizontal scaling available

**Vercel:**
- Automatically scales
- Upgrade to Pro for more bandwidth
- Add Edge Functions for speed

---

## 🆘 Need Help?

### **Vercel Support:**
- Docs: https://vercel.com/docs
- Community: https://github.com/vercel/vercel/discussions

### **Railway Support:**
- Docs: https://docs.railway.app
- Discord: https://discord.gg/railway

### **Project Issues:**
- GitHub: https://github.com/juggajay/HorseRacingML/issues

---

## ✅ Final Checklist

Before going live:

- [ ] Railway API deployed and tested
- [ ] Environment variables set on Railway
- [ ] Railway domain generated
- [ ] Vercel UI deployed
- [ ] `NEXT_PUBLIC_API_BASE` set on Vercel
- [ ] Frontend connects to API successfully
- [ ] Health check passes
- [ ] Model predictions working
- [ ] CORS configured correctly
- [ ] Both services auto-deploying from GitHub

---

## 🎯 Quick Start Commands

```bash
# 1. Deploy backend to Railway (via dashboard)
# Visit: https://railway.app
# Import: juggajay/HorseRacingML
# Root: services/api
# Add environment variables

# 2. Deploy frontend to Vercel (via dashboard)
# Visit: https://vercel.com
# Import: juggajay/HorseRacingML
# Root: web
# Add NEXT_PUBLIC_API_BASE

# 3. Test
curl https://your-railway-url/health
open https://your-vercel-url
```

---

**You're ready to deploy!** 🚀

Start with Railway (backend), then Vercel (frontend). Both platforms have generous free tiers perfect for testing.
