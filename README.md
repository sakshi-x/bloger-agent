# Blogger Agent 🤖

Automatically writes and publishes blog posts to Google Blogger using AI. Runs daily via GitHub Actions.

## Features

- ✅ Generates 800-1200 word blog posts using Groq (Llama 3.3 70B)
- ✅ Searches web for latest info using Serper API
- ✅ Adds relevant free images from Pixabay (optional)
- ✅ Publishes directly to Blogger as live posts
- ✅ Tracks used topics (no duplicates)
- ✅ Runs automatically daily + manual trigger
- ✅ All secrets stored securely in GitHub Actions

---

## Quick Start

### 1. Fork/Clone This Repo

```bash
git clone https://github.com/YOUR_USERNAME/blogger-agent.git
cd blogger-agent
```

### 2. Get All API Keys

You need **6 required API keys/secrets** + **1 optional** (Pixabay). Follow each section below.

---

### 🔑 1. Groq API Key (Content Generation)

1. Go to [console.groq.com](https://console.groq.com/)
2. Sign up / log in
3. Click **API Keys** → **Create API Key**
4. Copy the key → Save as `GROQ_API_KEY`

**Model used:** `llama-3.3-70b-versatile` (free tier available)

---

### 🔑 2. Serper API Key (Web Search)

1. Go to [serper.dev](https://serper.dev/)
2. Sign up (free tier: 2,500 searches/month)
3. Get API key from dashboard
4. Save as `SEARCH_API_KEY`

---

### 🔑 3. Pixabay API Key (Images - Optional)

1. Go to [pixabay.com/api/docs](https://pixabay.com/api/docs/)
2. Create account → Get API key
3. Save as `PIXABAY_API_KEY`

**Note:** This is optional. If not provided, blog posts will be published without images.

---

### 🔑 4. Google Blogger Setup (Most Complex)

#### Step A: Google Cloud Console

1. Go to [console.cloud.google.com](https://console.cloud.google.com/)
2. Create new project (or select existing)
3. **Enable Blogger API v3:**
   - APIs & Services → Library → Search "Blogger API" → Enable
4. **Create OAuth Credentials:**
   - APIs & Services → Credentials → Create Credentials → OAuth Client ID
   - Application type: **Desktop app**
   - Name: "Blogger Agent"
   - Download JSON → Save as `credentials.json` in project root
5. **OAuth Consent Screen:**
   - APIs & Services → OAuth consent screen
   - User Type: **External**
   - Add your email as **Test user**
   - Save

#### Step B: Get Blog ID

1. Go to [blogger.com](https://blogger.com/)
2. Select your blog
3. Look at URL: `https://www.blogger.com/blog/posts/123456789`
4. The number `123456789` is your **BLOGGER_BLOG_ID**

#### Step C: Get Refresh Token (Run Once Locally)

```bash
# Install dependencies
pip install -r requirements.txt

# Run the helper script
python get_refresh_token.py
```

- Browser opens → Sign in with your Google account
- Grant Blogger permission
- Script outputs:
  - `GOOGLE_CLIENT_ID`
  - `GOOGLE_CLIENT_SECRET`
  - `GOOGLE_REFRESH_TOKEN`

**Save all three!**

---

### 3. Add GitHub Secrets

1. Go to your repo on GitHub
2. Settings → Secrets and variables → Actions → **New repository secret**
3. Add all **6 required** secrets + **1 optional**:

| Secret Name | Required? | Value |
|-------------|-----------|-------|
| `GROQ_API_KEY` | Yes | From Groq console |
| `SEARCH_API_KEY` | Yes | From Serper dashboard |
| `PIXABAY_API_KEY` | **No (optional)** | From Pixabay |
| `BLOGGER_BLOG_ID` | Yes | Number from Blogger URL |
| `GOOGLE_CLIENT_ID` | Yes | From OAuth credentials |
| `GOOGLE_CLIENT_SECRET` | Yes | From OAuth credentials |
| `GOOGLE_REFRESH_TOKEN` | Yes | From `get_refresh_token.py` |

---

### 4. Configure Topics

Edit `topics.txt` - one topic per line (30 included for Digital Marketing + AI).

The agent picks the first unused topic each run.

---

### 5. Test Locally (Optional)

```bash
# Create .env file with your keys (NEVER commit this!)
cp .env.example .env  # If example exists, or create manually
# Edit .env with your keys

# Run
python main.py
```

---

### 6. Push and Enable Workflow

```bash
git add .
git commit -m "Initial setup"
git push origin main
```

1. Go to **Actions** tab in GitHub
2. Click "Daily Blog Post" workflow
3. Click **Run workflow** → **Run workflow** (green button)
4. Watch the logs!

---

## How It Works

### Flow Diagram

```
┌─────────────┐
│ 1. Pick     │
│    Topic    │
└──────┬──────┘
       ▼
┌─────────────┐
│ 2. Search   │── Serper API
│    Web      │
└──────┬──────┘
       ▼
┌─────────────┐
│ 3. Generate │── Groq (Llama 3.3 70B)
│    Post     │
└──────┬──────┘
       ▼
┌─────────────┐
│ 4. Get      │── Pixabay API
│    Image    │
└──────┬──────┘
       ▼
┌─────────────┐
│ 5. Publish  │── Blogger API v3
│    to       │
│    Blogger  │
└──────┬──────┘
       ▼
┌─────────────┐
│ 6. Save     │── Git commit
│    Topic    │
└─────────────┘
```

### File Structure

```
blogger-agent/
├── main.py                 # Main script (runs full flow)
├── topics.txt              # 30 topics (edit this)
├── used_topics.txt         # Auto-updated (don't edit)
├── requirements.txt        # Python dependencies
├── get_refresh_token.py    # Run once locally for Google OAuth
├── .github/workflows/
│   └── blog.yml           # GitHub Actions workflow
├── .gitignore             # Excludes .env, credentials.json
└── README.md              # This file
```

---

## Customization

### Change Schedule

Edit `.github/workflows/blog.yml`:

```yaml
schedule:
  - cron: "0 9 * * *"  # Daily 9 AM UTC
```

Cron format: `minute hour day month weekday`

Examples:
- `"0 14 * * 1-5"` = Weekdays 2 PM UTC
- `"0 0 * * 0"` = Weekly Sunday midnight

### Change Post Style

Edit the prompt in `main.py` → `generate_blog_post()` function.

### Change Number of Labels

Edit `generate_blog_post()` prompt: "4-5 relevant labels"

### Add More Topics

Just add lines to `topics.txt` (one per line).

---

## Troubleshooting

### "No unused topics found"
Add more topics to `topics.txt`.

### "Missing required environment variable"
Check all 7 secrets are added in GitHub Settings → Secrets.

### "Blog post failed to publish"
- Verify Blogger API is enabled in Google Cloud
- Check Blog ID is correct
- Ensure refresh token hasn't expired (re-run `get_refresh_token.py`)

### "Pixabay: No images found"
Try broader topics in `topics.txt` or check Pixabay API key. **This is optional** - posts will publish without images if Pixabay fails.

### "Groq: Rate limited"
Free tier has limits. Wait or upgrade at console.groq.com.

### Git push fails in workflow
- Ensure workflow has `contents: write` permission
- Check `GITHUB_TOKEN` is passed (automatic)

---

## Security Notes

- **Never commit** `.env`, `credentials.json`, `token.json`
- All secrets in GitHub Actions (encrypted)
- Public repo = secrets stay secret
- Rotate keys periodically

---

## Costs (Monthly Estimates)

| Service | Free Tier | Paid |
|---------|-----------|------|
| Groq | 14,400 req/day | ~$0.50/1M tokens |
| Serper | 2,500 searches | $50/mo for 10k |
| Pixabay | Unlimited | Free |
| Blogger | Free | Free |
| GitHub Actions | 2,000 min/mo | Free for public |

---

## License

MIT License - Feel free to use and modify!

---

## Support

If something breaks:
1. Check Actions logs for error details
2. Verify all 6 required secrets are set (Pixabay is optional)
3. Re-run `get_refresh_token.py` if Google auth fails
4. Open an issue on GitHub