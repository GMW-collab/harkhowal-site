# Harkhowal Online

The website for Sant Baba Jagjit Singh Ji Harkhowal Wale. It updates itself every day:

- **Videos**: new uploads on the YouTube channel appear automatically.
- **Audio katha**: new recordings added to Babaji's section on Gurmatveechar appear automatically, with a "Recently added" list.
- **Yatra**: shows Instagram posts automatically once Instagram is connected (optional), otherwise the trips listed in `data/yatra.json`.

Hosting is free on GitHub Pages. The only running cost is the harkhowal.com domain renewal.

---

## One-time setup (about 30 minutes)

### 1. Put the site on GitHub
1. Create a free account at github.com.
2. Click **New repository**, name it `harkhowal-site`, set it to **Public**, and create it.
3. On the new repository page, click **uploading an existing file**. Drag in **everything inside this folder**, including the hidden `.github` folder (on a Mac press Cmd+Shift+. in Finder to show it). Click **Commit changes**.

### 2. Turn on the website
1. In the repository, go to **Settings → Pages**.
2. Under **Source**, choose **Deploy from a branch**, branch **main**, folder **/ (root)**, then **Save**.
3. After a minute the site is live at `https://<your-username>.github.io/harkhowal-site/`.

### 3. Turn on the daily update
1. Go to the **Actions** tab and click **I understand my workflows, go ahead and enable them** if asked.
2. Click **Daily content update → Run workflow** to run it once now. It takes about two minutes and fills in the YouTube videos and every Gurmatveechar recording. After that it runs on its own every morning.

### 4. Point harkhowal.com at the new site
1. In **Settings → Pages → Custom domain**, enter `www.harkhowal.com` and save. Tick **Enforce HTTPS** once it becomes available.
2. Where your domain is managed (Wix, if you bought it through Wix, or your registrar), change the DNS records:
   - `www` → **CNAME** → `<your-username>.github.io`
   - `@` (the bare domain) → four **A** records: `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`
3. DNS changes can take a few hours. Once the new site shows at harkhowal.com, you can cancel the Wix premium plan. Keep the domain itself.

---

## Everyday use

You don't need to edit the website. Upload to YouTube and Gurmatveechar as usual, and the site catches up by the next morning.

**Add a travel post by hand:** open `data/yatra.json` on GitHub, click the pencil icon, copy one of the entries, edit it, and commit. Upload photos into an `images` folder and refer to them as `images/photo-name.jpg`. Delete the three example entries once you have real ones.

**Connect Instagram for the Yatra section (optional):**
1. Sign up at behold.so (it has a free plan) and connect the Instagram account.
2. Create a feed and copy its **JSON feed URL**.
3. Paste it into `config.json` as `"behold_feed_url"`, and add the Instagram profile link under `"social"`.
4. Run the daily update once from the Actions tab.

**Add Facebook and TikTok links:** fill in `"facebook"` and `"tiktok"` under `"social"` in `config.json`. They appear in the footer.

**Play audio on the site instead of linking out:** if Gurmatveechar agrees to you streaming their files, set `"stream_audio_on_site": true` in `config.json` and run the update once. Tracks will then play in a player at the bottom of the page.

**Change how series are grouped:** edit `"audio_categories"` in `config.json`. Each category lists words to match in the Gurmatveechar folder name.

## If something looks wrong
- **Actions tab shows a red cross:** open the run to see which source failed. One source failing never affects the others, and the site keeps the previous day's content.
- **GitHub pauses scheduled jobs** on repositories with no activity for 60 days. If that happens it emails you; click **Enable workflow** in the Actions tab.
