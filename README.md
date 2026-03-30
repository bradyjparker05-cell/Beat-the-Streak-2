# MLB Daily Hit Predictor

Automated system that analyzes all MLB games daily and texts the top 5 hit predictions via SMS.

## Features

- ✅ Analyzes all games every day (not just ones with posted lineups)
- ✅ Hot streak detection (last 7/14 days heavily weighted)
- ✅ Early season stat blending (2025 + 2026 combined)
- ✅ Away team bias (guaranteed extra at-bat)
- ✅ Batting order position scoring
- ✅ Pitcher matchup analysis (ERA, batting avg against)
- ✅ Duplicate prevention (only texts when picks change)
- ✅ Free SMS via Gmail SMTP → T-Mobile email gateway

## How It Works

**Algorithm scores each player based on:**
- Season batting average, OBP, OPS (max ~45 points)
- Hot streak bonuses (max 40 points)
- Away team bonus (+5 points for guaranteed 9th inning AB)
- Batting order position (leadoff +4, #2 +3, #3 +2)
- Pitcher matchup (ERA >5.00 = +15, AVG against >.280 = +10)

**Runs automatically via GitHub Actions:**
- Every 30 minutes from 8 AM - 5 PM ET during baseball season
- Sends SMS only when picks change (duplicate prevention)
- Uses free GitHub Actions (2000 min/month free tier)

## Setup Instructions

### 1. Gmail App Password Setup
1. Go to https://myaccount.google.com/apppasswords
2. Create an app password for "Mail"
3. Save the 16-character password

### 2. GitHub Secrets Setup
In your repo: Settings → Secrets and variables → Actions → New repository secret

Add these 3 secrets:
- `GMAIL_ADDRESS` - Your Gmail address
- `GMAIL_APP_PASSWORD` - The 16-character app password from step 1
- `PHONE_NUMBER` - Your T-Mobile phone number (10 digits, no dashes)

### 3. File Structure
```
Beat-The-Streak/
├── .github/
│   └── workflows/
│       └── daily_picks.yml
├── mlb_hit_predictor.py
├── sms_sender.py
├── main.py
├── requirements.txt
└── .gitignore
```

### 4. Run It
- **Manual:** Actions → Daily MLB Hit Picks → Run workflow
- **Automatic:** Runs every 30 min from 8 AM-5 PM ET (Mon-Sat, Apr-Oct)

## SMS Message Format

```
TOP 5 HIT PICKS - Saturday, Mar 28 (01:27 PM ET)

1. Aaron Judge (New)
   vs Tyler Mahle
   AVG: 0.318 (6% '25) | L7: 0.111 
   Away | #1 | Score: 27.42

2. Roman Anthony (Bos)
   vs Brady Singer
   AVG: 0.304 (2% '25) | L7: 0.750 🔥🔥🔥
   Away | #1 | Score: 26.55

🔥 = Hot last 7 days
(X% '25) = Blended with 2025 stats
Good luck!
```

## Cost

**$0/month**
- MLB Stats API: Free
- GitHub Actions: Free (2000 min/month, uses ~2 min/day)
- SMS: Free (Gmail SMTP → T-Mobile email gateway)

## Technical Notes

- **API:** statsapi.mlb.com (no key required)
- **Timezone:** Converts UTC to ET automatically
- **Caching:** All API responses cached to reduce redundant calls
- **Rate limiting:** 0.5 second delays between API calls

## Known Limitations

- Injury endpoint returns 404 errors (harmless, code handles gracefully)
- Scheduled workflows reliable only on public repos
- T-Mobile email gateway only (other carriers have similar gateways)

## License

MIT
