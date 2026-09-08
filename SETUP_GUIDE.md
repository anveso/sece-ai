# SECE AI — Complete Setup & Running Guide

This walks through everything from zero to a working chat app on your own
computer, step by step. Follow it in order — don't skip the verification
checks, they tell you immediately if something's wrong instead of you
discovering it three steps later.

**Where this runs:** on your own laptop/desktop, not in any browser tab or
cloud service. Everything happens on your machine.

---

## Step 1 — Install Docker Desktop

Docker is the tool that runs the app's three pieces (database, backend,
frontend) in isolated containers so you don't have to install Postgres,
Python, and Node yourself.

1. Go to **https://www.docker.com/products/docker-desktop/**
2. Download the installer for your OS (Windows, Mac — choose Intel or Apple
   Silicon, or Linux).
3. Run the installer and follow its prompts. Restart your computer if it
   asks you to.
4. Open **Docker Desktop** and wait until it says it's running (the whale
   icon in your system tray/menu bar stops animating and shows steady).

**Verify it worked** — open a terminal (Mac: Terminal app; Windows: use
PowerShell or the terminal inside Docker Desktop; Linux: your usual shell)
and run:

```bash
docker --version
docker compose version
```

Both should print a version number. If either command says "command not
found," Docker Desktop isn't installed correctly or isn't running yet — fix
this before continuing.

---

## Step 2 — Get an OpenAI API key and set up billing

The chat agents need this to actually think and respond. This is the OpenAI
**developer platform** (a paid, pay-as-you-go API), not a ChatGPT Plus
subscription — the two are billed separately even if you already pay for
ChatGPT.

### 2a. Create a platform account

1. Go to **https://platform.openai.com**
2. Click **Sign up** (or **Log in** if you already have an OpenAI account —
   the same login as ChatGPT works here).
3. Sign up with email, or with Google/Microsoft/Apple.
4. Verify your email address (and phone number, if OpenAI asks for it).

### 2b. Add a payment method and a spending limit

You cannot make real API calls without this step — a key alone isn't
enough.

1. In the left sidebar, click **Settings**, then **Billing**
   (or go directly to **https://platform.openai.com/settings/organization/billing/overview**).
2. Click **Add payment details** and enter a credit/debit card.
3. Add initial credit if prompted (as little as $5-10 is plenty to start
   and test this app).
4. Set a **monthly spending limit** — this caps what you can be charged if
   something runs wild. A few dollars is enough while you're just testing;
   raise it later if needed.

### 2c. Create the API key

1. In the left sidebar, click **API keys** (or go directly to
   **https://platform.openai.com/api-keys**).
2. Click **Create new secret key**.
3. Give it a descriptive name, e.g. "SECE AI".
4. Leave permissions as the default ("All") unless you specifically want to
   restrict it.
5. Click **Create secret key**.
6. **Copy it immediately** — it starts with `sk-` and OpenAI shows the full
   key exactly once. If you close the dialog without copying it, you'll
   have to create a new one.

Keep this key somewhere safe for a moment; you'll paste it into a file in
Step 4.

**Sanity check** (optional but reassuring): in a terminal, run
```bash
curl https://api.openai.com/v1/models -H "Authorization: Bearer sk-your-key-here"
```
A JSON list of model names means the key and billing are both working. An
`invalid_api_key` or `insufficient_quota` error means go back and re-check
2b/2c.

*(Optional, skip if unsure)*: if you also want the Research Agent's live
web-search tool, get a free key at **https://tavily.com** too. Everything
works fine without this — you just won't have that one tool active.

---

## Step 3 — Unzip the project

Find `sece-ai.zip` (sent earlier in this chat) in your downloads, and unzip
it. You should end up with a folder called `sece-ai` containing `backend/`,
`frontend/`, `docker-compose.yml`, and other files.

Open a terminal and navigate into that folder:

```bash
cd path/to/sece-ai
```

**Verify**: run `ls` (Mac/Linux) or `dir` (Windows). You should see
`docker-compose.yml`, `backend`, `frontend`, `.env.example`, `README.md`.

---

## Step 4 — Configure your environment file

The app reads its settings (your API key, database password, etc.) from a
file called `.env`, which doesn't exist yet — you create it from the
template:

```bash
cp .env.example .env
```

(Windows PowerShell: `copy .env.example .env`)

Now open `.env` in any text editor (Notepad, VS Code, TextEdit — anything)
and edit these three lines:

1. **`OPENAI_API_KEY=sk-...`**
   Replace with the real key from Step 2.

2. **`JWT_SECRET=change-this-to-a-long-random-string`**
   Replace with any long random string — this signs login sessions. Easiest
   way to generate one:
   ```bash
   openssl rand -hex 32
   ```
   Copy the output and paste it in as the value.

3. **`TAVILY_API_KEY=`**
   Leave this blank unless you did the optional Tavily step above — if you
   did, paste that key in.

Leave everything else in the file as-is. Save the file.

**Verify**: open `.env` again and confirm `OPENAI_API_KEY` starts with
`sk-` and isn't still the placeholder `sk-...`.

---

## Step 5 — Build and start the app

Still in the `sece-ai` folder, run:

```bash
docker compose up --build
```

What happens now: Docker downloads a Postgres image, builds the backend and
frontend images, and starts three containers. **The first run takes
3-6 minutes** (downloading base images, installing dependencies). Your
terminal will fill with build logs — that's normal.

**You'll know it's ready** when the scrolling stops and you see lines like:

```
backend-1   | INFO:     Application startup complete.
backend-1   | INFO:     Uvicorn running on http://0.0.0.0:8000
frontend-1  | ✓ Ready in ...
```

Leave this terminal window open — closing it stops the app. (If you want
your terminal back, stop with `Ctrl+C` once, then instead run
`docker compose up --build -d` next time to run it in the background.)

**If something goes wrong here**, jump to the Troubleshooting section below
before continuing.

---

## Step 6 — Open the app

In your web browser, go to:

```
http://localhost:3000
```

You should see the **SECE AI** login page (blue logo, "Sri Eshwar College
of Engineering" subtitle).

*(Optional check: **http://localhost:8000/docs** shows the backend's API
documentation — if that loads, the backend half is definitely healthy.)*

---

## Step 7 — Create your account

1. Click the **"Create account"** tab at the top of the login card.
2. Fill in:
   - **Full name** — your name
   - **I am a...** — Student, Faculty, or Admin (doesn't restrict anything
     yet, just a label)
   - **Email** — any email, doesn't need to be real/verified
   - **Password** — at least 8 characters
3. Click **Create account**. You're immediately signed in and land on the
   chat screen.

---

## Step 8 — Upload a document (so the assistant has something to search)

1. In the bottom-left of the sidebar, under **Knowledge base**, click
   **+ Upload**.
2. Choose a PDF, DOCX, or TXT file — a syllabus, circular, or policy
   document works best for testing.
3. Wait a few seconds. The file's status badge should change from
   `processing` to `ready`. (If it turns `error`, see Troubleshooting.)

---

## Step 9 — Chat with it

1. Click **+ New chat**.
2. At the top, you'll see an **Agent** dropdown — leave it on **Auto** for
   now (it automatically picks the right specialist per message).
3. Type a question about the document you uploaded, e.g. "What does the
   attendance policy say?" and press Enter.
4. Watch the response stream in. Above the reply you should see a small
   label like **FACULTY & STUDENT ASSISTANT** — that's which specialist
   agent answered.

Try a different kind of question in a **new chat** to see routing in
action:
- A research question ("what's new in federated learning research?") should
  route to **Research Agent**.
- "Draft a circular about..." should route to **Admin Agent**.

You can also skip Auto and pin a new chat to one specific agent from the
dropdown before sending your first message.

---

## Step 10 — Stopping and restarting

**To stop:** go back to the terminal running `docker compose up` and press
`Ctrl+C`. Then run:
```bash
docker compose down
```

**To start again later** (no rebuild needed): from the `sece-ai` folder,
```bash
docker compose up
```
Your account, conversations, and documents are preserved (stored in a
Docker volume) unless you run `docker compose down -v`, which wipes them.

---

## Troubleshooting

**`docker compose up` fails immediately / "Cannot connect to the Docker
daemon"**
→ Docker Desktop isn't running. Open it and wait for the whale icon to
settle, then retry.

**"port is already allocated" (for 3000, 8000, or 5432)**
→ Something else on your machine is already using that port. Either stop
that other program, or edit `docker-compose.yml` and change the left side of
the port mapping, e.g. `"3001:3000"` to use 3001 instead, then reopen the
app at that new port.

**Login page loads but "Create account" gives a network error**
→ The backend isn't reachable. Check the terminal for backend errors, and
confirm **http://localhost:8000/health** returns
`{"status":"ok","app":"SECE AI"}` in your browser directly.

**Document upload status stays "error"**
→ Almost always an invalid/missing `OPENAI_API_KEY`, or an OpenAI account
with no billing set up. Check the terminal logs for the exact error message
under the backend container's output.

**Chat messages fail / spinner never resolves**
→ Same cause as above — the chat agents call OpenAI too. Double-check the
key in `.env`, then run `docker compose down` and `docker compose up
--build` again (env changes need a restart to take effect).

**You changed `.env` but nothing changed**
→ `.env` is only read when containers start. After any edit:
```bash
docker compose down
docker compose up --build
```

**Still stuck**
→ Copy the exact error text from the terminal (not a screenshot description
— the literal text) and share it; that's almost always enough to pinpoint
the fix immediately.
