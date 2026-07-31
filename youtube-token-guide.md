# YouTube Token Kaise Nikale 🎬

Yeh guide aapko step-by-step batayegi ki **YouTube API Token** (OAuth Access Token / Refresh Token / API Key) kaise generate karein.

---

## 🔑 Method 1: YouTube Data API Key (Sabse Aasan)

API Key simple read-only operations ke liye use hota hai (jaise video search, channel info fetch karna).

### Steps:
1. **Google Cloud Console** kholein: [https://console.cloud.google.com/](https://console.cloud.google.com/)
2. Naya project banayein ya existing select karein.
3. Left menu me **APIs & Services → Library** par jayein.
4. Search karein **"YouTube Data API v3"** aur usse **Enable** karein.
5. **APIs & Services → Credentials** par jayein.
6. **+ Create Credentials → API Key** par click karein.
7. Ek popup me aapki **API Key** dikhegi — usse copy karke safely rakh lein.

> ⚠️ API Key ko public me share mat karein. Production me **HTTP Referrer** ya **IP Address** restriction lagayein.

---

## 🔐 Method 2: OAuth 2.0 Access Token (User Data ke liye)

Yeh method tab use hota hai jab aap user ki behalf par action lena chahte hain (upload, comment, playlist create, etc.)

### Prerequisites:
- Google Cloud Console account
- OAuth 2.0 Client ID configured

### Steps:
1. **Google Cloud Console** me jayein.
2. **APIs & Services → OAuth consent screen** setup karein.
   - User Type: **External** (testing ke liye)
   - App name, support email, developer email bharein.
   - **Scopes** me `https://www.googleapis.com/auth/youtube` add karein.
3. **Credentials → Create Credentials → OAuth 2.0 Client IDs** par click karein.
   - Application type: **Web application** ya **Desktop app**
   - **Authorized redirect URIs** me apna redirect URL daalein (e.g., `http://localhost:8080/oauth2callback` ya `https://oauth.pstmn.io/v1/callback` agar Postman use kar rahe ho).
4. **Client ID** aur **Client Secret** milega — save karein.

### Token lene ka process (Authorization Code Flow):
1. Browser me yeh URL kholein (apna `CLIENT_ID` aur `REDIRECT_URI` replace karein):

```
https://accounts.google.com/o/oauth2/v2/auth?
client_id=YOUR_CLIENT_ID&
redirect_uri=YOUR_REDIRECT_URI&
response_type=code&
scope=https://www.googleapis.com/auth/youtube&
access_type=offline&
prompt=consent
```

2. Google account se login karein aur permissions allow karein.
3. Aapko redirect URL me ek `code=...` milega.
4. Ab `curl` ya Postman se token exchange karein:

```bash
curl -X POST https://oauth2.googleapis.com/token \
  -d "code=PASTE_CODE_HERE" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "redirect_uri=YOUR_REDIRECT_URI" \
  -d "grant_type=authorization_code"
```

5. Response me aapko milega:
   - `access_token` (1 ghante ke liye valid)
   - `refresh_token` (long-term, refresh karne ke liye)
   - `expires_in`

### Refresh Token se naya Access Token:
```bash
curl -X POST https://oauth2.googleapis.com/token \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "refresh_token=YOUR_REFRESH_TOKEN" \
  -d "grant_type=refresh_token"
```

---

## 🛠️ Method 3: Postman se Token lena (Beginners ke liye easy)

1. **Postman** kholein → New Request → Authorization tab.
2. Type: **OAuth 2.0**
3. **Get New Access Token** par click karein.
4. Details bharein:
   - Auth URL: `https://accounts.google.com/o/oauth2/v2/auth`
   - Access Token URL: `https://oauth2.googleapis.com/token`
   - Client ID & Client Secret (upar wale)
   - Scope: `https://www.googleapis.com/auth/youtube`
5. **Request Token** → Login → Allow.
6. Postman me **access token** mil jayega.

---

## 🧪 Token test kaise karein?

```bash
curl "https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Agar sahi response aaye, token kaam kar raha hai ✅

---

## ⚠️ Security Tips

- **Token ko kabhi public Git repo me commit mat karein.**
- `.env` file me store karein aur `.gitignore` me add karein.
- Production me **Refresh Token rotation** enable karein.
- Sirf required **scopes** request karein.

---

## 📚 Useful Links

- Google Cloud Console: [https://console.cloud.google.com/](https://console.cloud.google.com/)
- YouTube Data API Docs: [https://developers.google.com/youtube/v3](https://developers.google.com/youtube/v3)
- OAuth 2.0 Playground: [https://developers.google.com/oauthplayground/](https://developers.google.com/oauthplayground/)
