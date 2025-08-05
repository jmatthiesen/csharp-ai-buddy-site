# C# AI Buddy Deployment Guide

This guide covers deploying both the frontend and backend components of the C# AI Buddy application.

## Backend Deployment (Render)

### Prerequisites
- GitHub account
- Render account (free tier available)

### Steps

1. **Push code to GitHub**
   ```bash
   git add .
   git commit -m "Initial commit"
   git push origin main
   ```

2. **Create Render Web Service**
   - Go to [Render Dashboard](https://dashboard.render.com/)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Configure the service:
     - **Name**: `csharp-ai-buddy-api`
     - **Runtime**: Python 3
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `python main.py`
     - **Root Directory**: `src/api`

3. **Set Environment Variables**
   - `PORT`: (auto-set by Render)
   - `PYTHON_VERSION`: `3.11.0`

4. **Deploy**
   - Click "Create Web Service"
   - Wait for deployment to complete
   - Note your service URL: `https://your-app-name.onrender.com`

### Health Check
Visit `https://your-app-name.onrender.com/health` to verify deployment.

## Frontend Deployment Options

### Option 1: Netlify (Recommended)

1. **Build for production**
   - Update the API URL in `src/frontend/index.html`:
     ```html
     <meta name="api-url" content="https://your-render-app.onrender.com">
     ```

2. **Deploy to Netlify**
   - Go to [Netlify](https://www.netlify.com/)
   - Drag and drop the `src/frontend` folder
   - Or connect your GitHub repository with build settings:
     - **Build command**: (none needed)
     - **Publish directory**: `src/frontend`

### Option 2: Vercel

1. **Install Vercel CLI**
   ```bash
   npm i -g vercel
   ```

2. **Deploy**
   ```bash
   cd src/frontend
   vercel --prod
   ```

### Option 3: GitHub Pages

1. **Create a deployment branch**
   ```bash
   git checkout -b gh-pages
   cp -r src/frontend/* .
   git add .
   git commit -m "Deploy to GitHub Pages"
   git push origin gh-pages
   ```

2. **Enable GitHub Pages**
   - Go to repository Settings → Pages
   - Source: Deploy from branch `gh-pages`

## Local Development

### Backend
```bash
cd src/api
pip install -r requirements.txt
python main.py
```
Backend runs on http://localhost:8000

### Frontend
```bash
cd src/frontend
# Serve with any static file server
python -m http.server 3000
# or
npx serve .
```
Frontend runs on http://localhost:3000

### Development URLs
- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Configuration

### API URL Configuration
The frontend automatically detects the API URL:
1. **Development**: Uses `http://localhost:8000`
2. **Production**: Uses the URL in `<meta name="api-url" content="...">` tag
3. **Fallback**: Uses hardcoded production URL in JavaScript

### CORS Configuration
The backend is configured to allow all origins by default. For production, update the CORS settings in `src/api/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend-domain.com"],  # Specify exact origins
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

## Monitoring

### Health Checks
- Backend health: `GET /health`
- Response: `{"status": "healthy", "timestamp": "...", "version": "1.0.0"}`

### Logs
- **Render**: View logs in the Render dashboard
- **Local**: Console output for both frontend and backend

## Scaling Considerations

### Backend (Render)
- Free tier: 750 hours/month, sleeps after 15 minutes of inactivity
- Paid tiers: Always-on with auto-scaling
- Consider implementing caching for better performance

### Frontend
- Static hosting scales automatically
- Consider using a CDN for global distribution
- Optimize images and assets for faster loading

## Troubleshooting

### Common Issues

1. **CORS Errors**
   - Ensure backend CORS is configured correctly
   - Check that frontend is using the correct API URL

2. **Backend Sleeping (Render Free Tier)**
   - First request after inactivity may be slow
   - Consider using a cron job to keep service warm

3. **API URL Configuration**
   - Verify the meta tag has the correct backend URL
   - Check browser developer tools for network requests

### Debug Commands
```bash
# Test backend locally
curl http://localhost:8000/health

# Test production backend
curl https://your-app.onrender.com/health

# Check API URL in frontend
console.log(new ChatApp().apiBaseUrl)
```