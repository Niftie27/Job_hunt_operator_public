# JH Operator — Setup Guide (Step by Step)

**Who this is for:** You, Tomáš, sitting at your local machine, setting this up from scratch.

**Reminder:** Browser chats (GPT, Claude) are for *thinking* about the project. This local folder is the *real home*. Git is the orchestrator of files. You are the orchestrator of decisions.

---

## Step 1: Create the local project folder

Open your terminal (PowerShell on Windows, Terminal on Mac/Linux) and run:

```bash
mkdir job-hunt-operator
cd job-hunt-operator
mkdir data output
```

That's it. You now have:

```
job-hunt-operator/
├── data/
└── output/
```

---

## Step 2: Put these exact files in the folder

### Files you BUILD WITH (the code — from Claude browser):

| Filename        | What it does                                      | Where to get it          |
|----------------|---------------------------------------------------|--------------------------|
| `config.py`    | Sources list, keywords, scoring weights            | Download from Claude chat |
| `fetchers.py`  | Talks to Greenhouse/Ashby/Lever/web3.career APIs   | Download from Claude chat |
| `pipeline.py`  | Dedupe, scoring, report generation                 | Download from Claude chat |
| `run.py`       | The one script you actually run                    | Download from Claude chat |
| `README.md`    | How to use everything                              | Download from Claude chat |

### Files you OPERATE WITH (your data — from your existing files):

| Filename                       | What it does                              | Where to get it                    |
|-------------------------------|-------------------------------------------|------------------------------------|
| `data/tracker.csv`            | Your outreach history (67 entries)         | Copy your `JH_Outreach_Tracker.csv` and rename it |

### Files you REFERENCE (canon — the important ones only):

| Filename                       | What it does                              | Where to get it                    |
|-------------------------------|-------------------------------------------|------------------------------------|
| `docs/master-file.md`         | Your candidate dossier + safe claims       | Copy your `JH_Master_File_v2.md` and rename it    |
| `docs/system-prompt.md`       | OpenClaw operator behavior rules           | Copy your `OpenClaw_JH_System_Prompt.md`          |
| `docs/roles-and-alerts.md`    | Role keywords + LinkedIn alert setup       | Copy your `JH_operator_roles_and_LinkedIn_alerts.md` |
| `docs/source-library.md`      | All 300+ source URLs                       | Copy your `JH_Jobs_links.md`                       |

### Files you DO NOT need in this repo:

- `Job_Hunt_Operator_Grand_System_Blueprint.md` — stays in browser chat as reference
- `JH_Conversation_Batch_Summary_Review.md` — stays in browser chat as reference
- `Job_Hunt_Operator_Short_System_Overview.md` — stays in browser chat as reference
- `JH_Agentic_Workflow_Playbook.md` — stays in browser chat as reference
- `OpenClaw_Research_for_JH.md` — stays in browser chat as reference
- `Structured_Chat_Transcript.md` — archive only
- `Optional_ClawHub_Skills_for_JH_Operator_Adopt_Sandbox_Avoid.md` — archive only
- Any other planning/architecture doc — archive only

**These are advisory files, not operational files. They helped you think. They don't run anything.**

---

## Step 3: Create the docs folder and copy reference files

```bash
mkdir docs
```

Then copy the 4 reference files listed above into `docs/`.

Your folder should now look like this:

```
job-hunt-operator/
├── config.py
├── fetchers.py
├── pipeline.py
├── run.py
├── README.md
├── data/
│   └── tracker.csv
├── docs/
│   ├── master-file.md
│   ├── system-prompt.md
│   ├── roles-and-alerts.md
│   └── source-library.md
└── output/
    (empty — reports will appear here after you run the script)
```

---

## Step 4: Open in VS Code

```bash
code .
```

This opens the whole project folder in VS Code. You can now browse all files in the sidebar.

---

## Step 5: Test locally

In VS Code's terminal (or any terminal inside the folder):

```bash
python3 run.py
```

**What should happen:**
- You'll see it try to fetch from ~20 sources
- Some will return jobs, some might fail (that's normal — we fix those)
- A report will appear in `output/daily-brief-YYYY-MM-DD.md`
- A CSV of all leads will appear in `output/leads-YYYY-MM-DD.csv`

**If Python isn't installed:** Install Python 3.10+ from https://www.python.org/downloads/

**If you get errors:** Copy the full error message and paste it to me (in this browser Claude chat) or to your VS Code Claude extension. We'll fix it.

---

## Step 6: Initialize Git

```bash
git init
```

Create a `.gitignore` file so you don't commit output files or junk:

```bash
# Create .gitignore with these contents:
output/
__pycache__/
*.pyc
.DS_Store
```

(You can create this file manually in VS Code — just make a new file called `.gitignore` and paste those 4 lines.)

---

## Step 7: First commit

```bash
git add .
git commit -m "v0.5: first working intake loop"
```

---

## Step 8: Create private GitHub repo and push

1. Go to https://github.com/new
2. Name: `job-hunt-operator`
3. Set to **Private**
4. Do NOT add README (you already have one)
5. Click "Create repository"
6. GitHub will show you commands. Run these:

```bash
git remote add origin https://github.com/YOUR_USERNAME/job-hunt-operator.git
git branch -M main
git push -u origin main
```

Replace `YOUR_USERNAME` with your actual GitHub username.

---

## Step 9: Deploy to VPS (OpenClaw)

SSH into your VPS:

```bash
ssh your-user@your-vps-ip
```

Clone the repo:

```bash
cd ~
git clone https://github.com/YOUR_USERNAME/job-hunt-operator.git
cd job-hunt-operator
```

Copy your tracker if it's not in git (or if the VPS has a newer version):

```bash
# If needed:
cp /path/to/your/tracker.csv data/tracker.csv
```

Test it:

```bash
python3 run.py
```

---

## Step 10: Set up daily cron (optional, after testing)

```bash
crontab -e
```

Add this line (runs every day at 8:00 AM server time):

```
0 8 * * * cd ~/job-hunt-operator && python3 run.py >> output/cron.log 2>&1
```

Save and exit.

---

## When you make changes later

The workflow is always:

1. Edit files locally in VS Code
2. Test: `python3 run.py`
3. Commit: `git add . && git commit -m "description of change"`
4. Push: `git push`
5. On VPS: `cd ~/job-hunt-operator && git pull`

That's the whole development cycle.

---

## The 3-lane reminder

Whenever you feel confused about "where does this go":

| Lane        | Tool                        | Purpose                    |
|------------|-----------------------------|-----------------------------|
| **Build**  | VS Code + local repo + git  | Write code, edit, test, commit |
| **Run**    | OpenClaw VPS                | Cron jobs, daily reports, runtime |
| **Advice** | Browser GPT / Browser Claude | Review, debug, explain, plan |

**Browser chats are for thinking about the project. The local repo is the real home.**
