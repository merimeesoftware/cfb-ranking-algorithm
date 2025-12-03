# CFB Ranking Algorithm - Netlify Deployment

This document describes how to deploy the CFB Ranking Algorithm to Netlify with GitHub Actions CI/CD.

## Prerequisites

1. A [Netlify](https://netlify.com) account
2. A [GitHub](https://github.com) repository for this project
3. A CFBD API key from [CollegeFootballData.com](https://collegefootballdata.com/)

## Setup Instructions

### 1. Create Netlify Site

1. Log in to Netlify
2. Click "Add new site" → "Import an existing project"
3. Connect your GitHub repository
4. Configure build settings:
   - **Build command:** `pip install -r requirements.txt`
   - **Publish directory:** `static`
   - **Functions directory:** `netlify/functions`

### 2. Configure Environment Variables

In the Netlify dashboard, go to **Site settings** → **Environment variables** and add:

| Variable | Description |
|----------|-------------|
| `CFBD_API_KEY` | Your College Football Data API key |
| `PYTHON_VERSION` | `3.11` |

### 3. Configure GitHub Secrets

In your GitHub repository, go to **Settings** → **Secrets and variables** → **Actions** and add:

| Secret | Description |
|--------|-------------|
| `NETLIFY_AUTH_TOKEN` | Personal access token from Netlify (User settings → Applications → Personal access tokens) |
| `NETLIFY_SITE_ID` | Your Netlify site ID (Site settings → General → Site information → Site ID) |
| `CFBD_API_KEY` | Your College Football Data API key (for tests) |

### 4. Enable GitHub Actions

The CI/CD pipeline will automatically run when you:
- Push to the `main` branch
- Open a pull request targeting `main`

## Pipeline Overview

The GitHub Actions workflow (`.github/workflows/ci-cd.yml`) runs the following jobs:

### 1. Scan (Code Quality & Security)
- **Flake8**: Python linting for syntax errors and code style
- **Bandit**: Security vulnerability scanning
- **Safety**: Dependency vulnerability checking

### 2. Test
- Runs pytest with coverage reporting
- Uploads coverage reports as artifacts

### 3. Build
- Validates Python syntax
- Verifies required files exist
- Creates build artifact

### 4. Deploy
- **On push to main**: Deploys to production
- **On pull request**: Creates a preview deployment and comments the URL on the PR

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the Flask development server
python app.py

# Access at http://localhost:5001
```

## Project Structure

```
cfb-ranking-algorithm/
├── .github/
│   └── workflows/
│       └── ci-cd.yml          # GitHub Actions workflow
├── netlify/
│   └── functions/
│       └── api.py             # Netlify serverless function
├── static/
│   └── js/
│       └── dashboard.js       # Frontend JavaScript
├── templates/
│   ├── dashboard.html
│   ├── error.html
│   ├── full_view.html
│   └── ...
├── app.py                     # Flask application
├── netlify.toml               # Netlify configuration
├── requirements.txt           # Development dependencies
├── requirements-prod.txt      # Production dependencies
└── ...
```

## Troubleshooting

### Build Failures
- Check that all required environment variables are set
- Verify Python version compatibility
- Review build logs in Netlify dashboard

### Function Errors
- Check the Netlify Functions logs in the dashboard
- Ensure `CFBD_API_KEY` is set correctly
- Verify the API key has proper permissions

### Preview Deploys Not Working
- Ensure `NETLIFY_AUTH_TOKEN` and `NETLIFY_SITE_ID` are set in GitHub secrets
- Check that the workflow has permission to comment on PRs
