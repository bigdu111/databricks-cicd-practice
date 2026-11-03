# Sales Analytics: Databricks CI/CD Walkthrough

A small Databricks project that practices how a real team changes a production data pipeline **safely**: separate **dev**, **test**, and **prod** environments keep production protected, and a **CI/CD pipeline** on GitHub moves every change through them automatically, checking it at each step.

This guide is written for **Databricks Free Edition**. [Part 10](#part-10-moving-to-a-company-setup) shows how the same project maps to a company setup.

**By the end, you'll be able to:**

- Explain what CI and CD each do, and why they need separate dev, test, and prod environments
- Read a GitHub Actions workflow and say what starts it, what it does, and which environment it touches
- Move a change from a feature branch to prod through two gates, using trunk-based development
- Watch the pipeline **stop** a broken change, and **roll back** a bad release

**Time:** about 2 hours. Parts 1–4 are one-time setup; Parts 5–9 are the everyday loop you'll repeat at work.

### Key terms

| Term | Meaning here |
|---|---|
| **Workflow** | A YAML file in `.github/workflows/` that GitHub runs automatically when an event happens |
| **Trigger** (`on:`) | The event that starts a workflow: a push, a pull request, a release, a branch deletion |
| **Job / step** | A workflow has jobs; a job is a list of steps run in order on one fresh virtual machine (a **runner**) |
| **Status check** | A job's pass/fail result, shown on a pull request. A ruleset can require it before merging |
| **Gate** | A point a change can't pass until something is true: checks green, or a person approves |
| **Bundle / target** | A Databricks Asset Bundle is the project as code; a target (`dev`, `test`, `prod`) is one environment it can be deployed to |
| **GitHub environment** | Repository settings named `dev`, `test`, or `prod`: credentials, approval rules, deployment history |
| **Promotion** | Moving a version to the next environment. Here, by deploying the same commit again, never by copying |

---

## How it works

### The big picture: three roles, five kinds of places

The project lives in at least five places, and each one has one of three roles: **edit**, **store and move**, or **run**.

```
EDIT
  Git folders: one per person per feature
      │
      │ push
      ▼
STORE AND MOVE
  GitHub: back up, check, gate, deploy
      │
      │ deploy
      ▼
RUN
  dev:  each feature while it's built
  test: everything in main, for UAT
  prod: the approved release
```

| Place | Role | How many |
|---|---|---|
| **Git folders** | **Edit** the code | One per person per feature, so often many |
| **GitHub** | **Store and move** the code: back it up, check it, gate it, and deploy it | One repository |
| **dev** | **Run** each feature while it's being built | One copy per feature branch, so also many |
| **test** | **Run** everything merged into `main`, for testing and UAT | One |
| **prod** | **Run** the approved release | One |

Code is never edited where it runs, and never runs where it's edited. GitHub sits in the middle: the single source of the code, and the pipeline that decides when a version is ready to run in each place.

In this guide, everything except GitHub lives in one Databricks workspace. In a company, dev, test, and prod are often separate workspaces, but the roles stay the same.

The next three sections explain each role.

### Run: dev, test, and prod keep production safe

The sales pipeline in **prod** produces results people rely on, so it must keep working. Nobody experiments there. That's why there are three environments: each is a separate place where the project runs, with its own deployed copy of the code, its own jobs, and its own data, so a run in one can never touch another.

| Environment | Why it exists | Runs | Data (schema) | Jobs named |
|---|---|---|---|---|
| **dev** | A safe place to build and break things | Each feature branch, separately | `sales_dev_<branch>`, such as `sales_dev_avg_order` | `[dev <you> avg_order] sales_pipeline_dev` |
| **test** | A safe place to check combined changes before they're trusted | Everything merged into `main`; testing and UAT | `sales_test` | `sales_pipeline_test` |
| **prod** | The real thing | The latest approved release | `sales_prod` | `sales_pipeline_prod` |

A dev schema is named after its branch, with `feature/` dropped, letters lowercased, and every other character that isn't a letter or digit turned into `_` (schema names can't contain `/` or `-`): `feature/avg-order` → `sales_dev_avg_order`. The **Deploy to dev** and **Clean up dev** workflows both work out this name the same way.

In this guide, the three environments share the workspace's serverless compute and stay apart by schema. In a company, they're usually separate workspaces or catalogs, often with separate compute too.

### Edit: one Git folder per person per feature

Code is written in **Git folders**: Git working areas inside Databricks. Each person keeps **one Git folder for each feature** they work on, the same idea as `git worktree`: switching features means opening another folder, so unfinished work is never disturbed.

```
/Workspace/Users/<you>/
├── alice-avg-order     → feature/avg-order
├── alice-dq-checks     → feature/dq-checks
├── bob-segments        → feature/segments
└── bob-forecast        → feature/forecast
```

Unlike real worktrees, each Git folder is a separate clone. Git folders share work only **through GitHub**: push in one, pull in another.

In a Git folder, the **Commit & Push** button combines three Git steps. The Git dialog lists your changed files with checkboxes:

| In the Git dialog | Command-line equivalent |
|---|---|
| Leave a file checked | `git add <file>` |
| Uncheck a file | Leave it out: it stays an uncommitted change |
| Click **Commit & Push** | `git commit` + `git push` |

Like `git commit -- <file>`, the checked files are taken straight from the working area. Every commit reaches GitHub right away, which is what starts the pipeline. For full command-line Git, see [Optional: CLI-enabled Git folders](#optional-cli-enabled-git-folders).

### Store and move: GitHub

#### One repository; the code moves, not the environments

One project has **one repository**. It holds the code once, plus the definitions of all three environments. Every Git folder pushes to it, and every environment is deployed from it.

Nothing is ever copied from dev to test, or from test to prod. Instead, the **same commit is deployed to each environment in turn**: a feature branch's commits go to dev; once merged, that code is in `main`, which goes to test; a release tag on that commit goes to prod. Only configuration differs (which schema, which mode), so what passed in test is exactly what runs in prod.

#### Branches: trunk-based

This project uses **trunk-based development**, the simplest common branching strategy:

| Branch or tag | Lives for | Purpose | Deployed to |
|---|---|---|---|
| `feature/*` | Days: deleted when merged | One new feature or fix | dev, its own copy |
| `main` (the "trunk") | Forever | Everything finished and merged | test |
| Release tag, such as `v1.0.0` | Forever: a fixed label | A version of `main` approved for production | prod |

There's **one long-lived branch, `main`**. Environments are reached by **events** (a push, a merge, a release), not by branches of their own, and a **release is a tag**: a permanent label on the exact `main` commit that was tested.

**Why there's no `dev`, `test`, or `prod` branch:** separate environment branches tend to **drift**. A quick fix made directly on one, or a promotion that carries unfinished work along, and soon `test` and `prod` differ in ways nobody intended. With one trunk, the release tag points at exactly the commit that passed in test, and nothing is merged on the way to prod.

To see what's in each environment, look at **Deployments** on the repository page (dev, test, and prod each have a history), plus the `feature/*` branches for dev, `main` for test, and **Releases** for prod.

**Urgent fixes** take the normal path, just faster: a `feature/fix-...` branch, a pull request into `main`, a check in test, then a release such as `v1.0.1`.

Other strategies you'll meet at work keep the same idea, but use more long-lived branches:

| Strategy | Branches | Promotion | Main trade-off |
|---|---|---|---|
| **Trunk-based** (this project) | `main` + `feature/*`; releases are tags | Merge → test; tag → prod | Simplest; the same commit reaches test and prod |
| **Environment branches** | `dev`, `test`, `prod` + `feature/*` | Pull requests `dev` → `test` → `prod` | Each environment visible as a branch, but branches drift |
| **GitFlow** | `main`, `develop`, `release/*`, `hotfix/*`, `feature/*` | `develop` → `release/x` → `main` | Suits scheduled releases, but more merging |

#### CI/CD: checking and moving the code automatically

Teams used separate environments long before CI/CD, deploying to each by hand with scripts and checklists. That was slow and error-prone. CI/CD makes the journey **automatic, repeatable, and checked**:

- **CI (continuous integration)** automatically **checks** every change: unit tests and configuration validation.
- **CD (continuous delivery)** automatically **deploys** checked changes: to dev on every push, and to test on every merge. Prod is deployed automatically too, but only after a person approves.

> **Continuous delivery vs. continuous deployment.** Both are "CD". With continuous **delivery** (this project), every change is *ready* to release, but a person decides when it goes to prod. With continuous **deployment**, there's no human gate: every change that passes test goes straight to prod. That needs very strong automated tests, so data teams usually start with delivery.

Between the environments are two **gates**, where a change must prove itself before moving on:

```
feature branch
   │ push: CI checks, CD deploys ──► dev
   │
pull request: CI checks
   │
✔ GATE 1: checks passed (+ review in a team)
   │ merge
   ▼
main: CD deploys ──► test (testing, UAT)
   │
   │ release tag
   ▼
✔ GATE 2: a person approves
   │
   ▼
CD deploys ──► prod
```

Without separate environments, CI could still run checks like unit tests, but every deploy would go straight to production. There'd be no safe place to run the whole pipeline on realistic data, or for users to check results, before production depends on it. Without CI/CD, the environments would rely on slow, manual deploys. Together, they let you change things often **and** safely.

#### How GitHub is wired to each environment

Each environment has one bundle target that defines it, one GitHub environment that holds the settings for deploying to it, and the workflows that act on it:

| Side | Piece | What it is | Where it lives |
|---|---|---|---|
| **Databricks** | The environment itself | The deployed copy, jobs, and schema: where the project runs | Databricks |
| **Repository** | Bundle target | The definition of the environment: schema, mode | `databricks.yml` |
| **GitHub** | GitHub environment | Settings for deploying to it: credentials and approval rules, plus its deployment history | Repository settings (not in the code) |
| **GitHub** | Workflows | The actions that check, deploy to, or clean up the environment, and when they run | `.github/workflows/` (versioned like code) |

---

## What's in the project

The project files do two jobs at once. Pushed to GitHub, they **set up the pipeline**. Deployed by that pipeline, they **set up and run the environments** in Databricks. Together with a few settings made by hand in GitHub, they fall into four groups:

```
databricks-cicd-practice/
│
├── databricks.yml          1. ENVIRONMENTS
├── resources/
│   └── sales_job.yml
│
│   2. GITHUB SETTINGS: made by hand
│      in GitHub, not in this folder
│
├── tests/                  3. CI CHECKS
│   └── test_transforms.py
├── .github/workflows/
│   ├── ci.yml              3. CI CHECKS
│   ├── deploy-dev.yml      4. CD
│   ├── deploy-test.yml     4. CD
│   ├── deploy-prod.yml     4. CD
│   └── cleanup-dev.yml     4. CD
│
└── src/                    4. CD: code that's
    ├── ingest.py              deployed and run
    ├── build_report.py
    ├── integration_checks.py
    └── transforms.py
```

### 1. The environments: bundle targets

Read by **Databricks**, through the bundle commands the workflows run (`databricks bundle deploy -t <target>`). These files define what each environment is and what gets deployed into it.

| File | Defines |
|---|---|
| `databricks.yml` | The three environments, as **bundle targets**: `dev` (one copy per branch, schema `sales_dev_<branch>`), `test` (schema `sales_test`), and `prod` (schema `sales_prod`, production mode) |
| `resources/sales_job.yml` | The **jobs** deployed into every environment: `sales_pipeline` (ingest, then build the report) and `integration_tests`. Each target fills in its own schema |

The first deploy to a target creates that environment's deployed copy and jobs. That's why the setup starts with the repository: see [Part 1](#part-1-what-you-need-and-the-setup-order).

### 2. The rules of the pipeline: GitHub settings (not in the folder)

Some parts of the CI/CD setup are **settings you make by hand in GitHub**, not files. They hold credentials, which must never be in the code, and the rules that guard each step:

| Setting | Where in GitHub | Holds | Set up in |
|---|---|---|---|
| GitHub environments `dev`, `test`, `prod` | Settings → Environments | `DATABRICKS_HOST` (variable) and `DATABRICKS_TOKEN` (secret) for deploying to each environment. `prod` also requires a reviewer: **gate 2** | Part 3 |
| Ruleset `protect-main` | Settings → Rules → Rulesets | Merges into `main` need a pull request whose CI passed: **gate 1** | Part 3 and Part 6 |

The workflows refer to these by name, such as `environment: test`, so the files and the settings work together.

### 3. The CI checks

Run by **GitHub**, on its own virtual machine, on each pull request and **before** anything is merged. They don't change the environments: CI borrows the `test` GitHub environment's credentials only so `databricks bundle validate -t test` can check the configuration against the workspace. (That's also why CI runs show up in test's deployment history.)

| File | Does |
|---|---|
| `tests/test_transforms.py` | The **unit tests**: check the functions in `src/transforms.py` give the expected results, without Databricks |
| `.github/workflows/ci.yml` | The **CI** workflow: on each pull request into `main`, runs the unit tests and validates the bundle. Its result is what **gate 1** checks |

The unit tests also run first in **Deploy to dev**, so a broken change isn't deployed even to dev.

### 4. The CD workflows, and the code they deploy

The CD workflows are read by **GitHub**, and they move the code in `src/` into the environments.

| Workflow file | Runs when | Does |
|---|---|---|
| `deploy-dev.yml` | Push to a `feature/*` branch | Unit tests, then deploy that branch to dev and run the pipeline and checks |
| `deploy-test.yml` | Merge into `main` | Deploy to test, run the pipeline and checks |
| `deploy-prod.yml` | Release published and approved (gate 2) | Deploy to prod, run the pipeline |
| `cleanup-dev.yml` | `feature/*` branch deleted | Remove that branch's dev copy |

The code in `src/` is what actually **runs** in each environment. The same files run in dev, test, and prod; only the schema they're given differs.

| File | Does |
|---|---|
| `src/ingest.py` | Notebook: creates the schema if needed, and loads sample orders into `<schema>.orders` |
| `src/build_report.py` | Notebook: builds `<schema>.sales_report`, total sales per region |
| `src/integration_checks.py` | Notebook: fails if the tables are wrong. Run after each deploy to dev and test, as the `integration_tests` job |
| `src/transforms.py` | Plain Python logic, imported by the notebooks and unit tested |

The project also has a `.gitignore`, which keeps local clutter (such as Python caches and the bundle's `.databricks/` folder) out of the repository.

---

## Part 1: What you need, and the setup order

- A **GitHub** account, with Git on your computer set up to push (your SSH key from the Git practice project).
- Your **Databricks Free Edition** workspace.

You'll use your computer only once, to put the project on GitHub. Everything after that happens in Databricks and on the GitHub website.

**Why the setup starts with the repository, not the environments.** You might expect to create dev, test, and prod in Databricks first. This project works the other way around: **the environments are defined in the repository, and the pipeline creates them.** This is called **infrastructure as code**:

- **The definition is code.** Each environment is a target in `databricks.yml`, so environments are versioned and reviewed like any other change.
- **The first deploy creates the environment.** Deploying to a target creates its deployed copy and jobs, and the pipeline's first run creates its schema (`ingest.py` runs `CREATE SCHEMA IF NOT EXISTS`). There's nothing to create by hand.
- **No manual drift.** Built by the pipeline from one definition, the environments stay consistent, and any of them can be rebuilt from the repository.

So the setup follows what each step depends on:

| Part | Sets up | Why in this order | Environment created |
|---|---|---|---|
| 2 | The repository, with the environment definitions | Everything else is built from it | |
| 3 | GitHub → Databricks connection | So the pipeline can deploy | test: its first deploy |
| 4 | Databricks → GitHub connection | So people can develop in Databricks and push | |
| 5–8 | Git folders and features | The team's everyday work | dev: each branch's first push |
| 9 | A release | Passing gate 2 | prod: the first approved release |
| Practice, Rolling back | A broken change, and a way back | Seeing the gates work, and recovering when one isn't enough | |

> **In a company,** an admin first creates what the pipeline isn't allowed to create: the separate workspaces or catalogs, the service principals, and the permissions that let only the pipeline write to test and prod. Everything inside them is created by the pipeline, as here. See [Part 10](#part-10-moving-to-a-company-setup).

## Part 2: Create the repository

**1. Point the environment definitions at your workspace.** Unzip the project somewhere outside your Git practice folder. The unzipped folder is called `databricks-cicd-example`; the repository you'll create can have a different name. Open `databricks.yml` and replace:

- `<your-workspace-url>` (three places) with your **workspace URL**: the address in your browser when you're signed in to Databricks, up to `.com`, such as `https://dbc-1234abcd-5678.cloud.databricks.com`
- `<your-databricks-email>` (two places, in `prod`) with the email you sign in to Databricks with

**2. Create the repository on GitHub.** Make a **new public repository** named `databricks-cicd-practice`, with nothing checked (no README, `.gitignore`, or license).

> **Why public?** On a free GitHub account, the approval gate before prod ("required reviewers") only works on public repositories. Nothing secret lives in the code: tokens go into encrypted settings in Parts 3 and 4. A private repository works too, but prod then deploys without waiting for approval.

**3. Push the project.** In the project folder:

```bash
git init
git add .
git commit -m "Initial project"
git branch -M main
git remote add origin git@github.com:<your-username>/databricks-cicd-practice.git
git push -u origin main
```

The push starts **Deploy to test**, which fails because GitHub can't reach Databricks yet. That's expected; you'll fix it in Part 3.

**4. Look at the Actions tab.** It lists the five workflows. You didn't create them in GitHub: GitHub treats every `.yml` file in `.github/workflows/` as a workflow. Each file's `name:` line sets the name shown, and its `on:` section sets the event it waits for. Each run starts a fresh virtual machine, runs the file's steps in order, and goes green if all succeed or red at the first failure.

**5. Read one workflow.** Open `.github/workflows/deploy-test.yml` on GitHub and find these four parts. Every workflow in this project, and most you'll meet at work, has the same shape:

| Part | Answers | Look for |
|---|---|---|
| `on:` | **When** does it run? | The event, such as a push to `main` |
| `jobs:` | **What** runs? | One job, named `deploy`, on `ubuntu-latest` |
| `environment:` | **Where** does it deploy, with whose credentials? | The GitHub environment name, such as `test` |
| `env:` | With **which credentials**? | `vars.DATABRICKS_HOST` and `secrets.DATABRICKS_TOKEN`, read from that GitHub environment |
| `steps:` | **How**, step by step? | Check out the code, install the Databricks CLI, `databricks bundle deploy -t test`, then `databricks bundle run` for the pipeline and for the integration tests |

Then skim the other four files and fill in the "When" and "Where" for each. Comparing them with the table in [What's in the project](#4-the-cd-workflows-and-the-code-they-deploy) is the quickest way to see how the pipeline fits together.

## Part 3: Connect GitHub to Databricks, and create test

This gives the pipeline the keys and gates to reach dev, test, and prod, then lets it create the test environment.

**1. Create a Databricks token.** In Databricks, click your username → **Settings** → **Developer** → **Access tokens** → **Manage** → **Generate new token**. Name it `github-actions`, set an expiration, and copy the token.

**2. Create three GitHub environments.** In your GitHub repository → **Settings** → **Environments** → **New environment**:

| GitHub environment | Variable | Secret | Protection |
|---|---|---|---|
| `dev` | `DATABRICKS_HOST` = your workspace URL | `DATABRICKS_TOKEN` = the Databricks token | None |
| `test` | `DATABRICKS_HOST` = your workspace URL | `DATABRICKS_TOKEN` = the Databricks token | None |
| `prod` | `DATABRICKS_HOST` = your workspace URL | `DATABRICKS_TOKEN` = the Databricks token | **Required reviewers**: add yourself |

For each: under **Environment variables** click **Add variable**, and under **Environment secrets** click **Add secret**. Names must match exactly, in capitals: `DATABRICKS_HOST` is a **variable**, and `DATABRICKS_TOKEN` is a **secret**. For `prod`, check **Required reviewers**, add yourself, and click **Save protection rules**. Leave "Prevent self-review" unchecked, since you're the only person.

**3. Let the pipeline create test.** Go to **Actions** → **Deploy to test** → the failed run → **Re-run jobs** → **Re-run all jobs**. When it's green, the test environment exists: the job `sales_pipeline_test`, its deployed copy, and the schema `workspace.sales_test` with the tables `orders` and `sales_report`. You never created any of it by hand.

**4. Add gate 1.** In the repository → **Settings** → **Rules** → **Rulesets** → **New ruleset** → **New branch ruleset**:

- Name: `protect-main`; Enforcement status: **Active**
- Target branches: **Add target** → **Include default branch**
- Check **Require a pull request before merging**. Set required approvals to **0**, since you're working alone. In a team, use at least 1.
- Check **Require status checks to pass**. The check to require, `checks`, appears only after CI has run once, so you'll add it in Part 6, step 6.
- Click **Create**.

From now on, nobody pushes straight to `main`. Every change arrives through a pull request.

## Part 4: Connect Databricks to GitHub

Part 3 let GitHub reach Databricks. This part lets Databricks push to GitHub, so there's one token for each direction:

| Token | Created in | Stored in | Lets |
|---|---|---|---|
| Databricks token | Databricks | GitHub environments (Part 3) | **GitHub Actions** deploy to Databricks |
| GitHub token | GitHub | Databricks Linked accounts (this part) | **Git folders** push commits to GitHub |

**1. Create a GitHub token.** On GitHub: your profile picture → **Settings** → **Developer settings** → **Personal access tokens** → **Fine-grained tokens** → **Generate new token**.

- Name: `databricks-git-folders`; set an expiration
- Repository access: **Only select repositories** → `databricks-cicd-practice`
- Permissions → Repository permissions → **Contents: Read and write**
- Click **Generate token** and copy it

**2. Add it to Databricks.** Click your username → **Settings** → **Linked accounts** → **Add Git credential**:

- Git provider: **GitHub**
- Git provider email: your GitHub email
- Token: paste the token
- Click **Save**

Use the token rather than the GitHub app option: on Free Edition, the token is more reliable for pushing.

The setup is done. Everything from here on is a team's everyday work.

## Part 5: The scenario, and one Git folder per feature

Two people, Alice and Bob, work on four features at the same time. You'll play both.

| Feature | Owner | Git folder | Branch | Goes to prod in |
|---|---|---|---|---|
| 1. Average order value in the report | Alice | `alice-avg-order` | `feature/avg-order` | v1.0.0 |
| 2. Data quality checks | Alice | `alice-dq-checks` | `feature/dq-checks` | v1.1.0 |
| 3. Customer segments | Bob | `bob-segments` | `feature/segments` | v1.0.0 |
| 4. Sales forecast | Bob | `bob-forecast` | `feature/forecast` | Not yet (still in progress) |

Create all four Git folders now, the way a team starts several features at once. **For each row of the table:**

1. In the sidebar, click **Workspace** → your user folder.
2. Click **Create** → **Git folder**.
3. Git repository URL: `https://github.com/<your-username>/databricks-cicd-practice.git`. Git folders use the HTTPS form, not SSH.
4. Git folder name: for example `alice-avg-order`. Click **Create Git folder**. It starts as a clone of `main`.
5. Click **Git** next to the folder name to open the Git dialog. Click **Create Branch**, name it for example `feature/avg-order`, base it on `main`, and click **Create**.

You now have four Git folders, each on its own feature branch. Nothing has been pushed yet, so no dev environment exists yet.

> In a real team, Alice creates her two folders in her own user folder, and Bob his two in his.

## Part 6: Alice builds Feature 1

Work in `alice-avg-order`.

**1. Make the change.** Open `src/build_report.py`. In the cell that builds the report, replace the `.agg(...)` line with:

```python
    .agg(
        F.sum("amount").alias("total_amount"),
        F.round(F.avg("amount"), 2).alias("avg_amount"),
        F.count("*").alias("order_count"),
    )
```

**2. Try it interactively, in the branch's own schema.** Open `src/ingest.py` and attach it to **Serverless**. Run the cell that defines the widgets (the first code cell, under the comment cell) to show them at the top, set **schema** to `sales_dev_avg_order`, then click **Run all**. Do the same in `src/build_report.py`. Check that `workspace.sales_dev_avg_order.sales_report` has `avg_amount` and `order_count`.

**3. Commit & Push.** Open the Git dialog. `src/build_report.py` is listed and checked. Write the message `Add average order value and order count to report`, and click **Commit & Push**.

**4. Watch CD deploy to dev.** On GitHub → **Actions**, **Deploy to dev** is running for `feature/avg-order`. When it's green, Databricks has the job `[dev <you> avg_order] sales_pipeline_dev`. This is the branch's official dev deployment, done the same way test and prod are deployed. Each Commit & Push to this branch redeploys it.

**5. Open a pull request.** On GitHub, a banner shows **feature/avg-order had recent pushes**. Click **Compare & pull request**, check that the base is `main`, and click **Create pull request**. **CI** runs.

**6. Pass gate 1.** Wait for CI's green check. Then finish the ruleset from Part 3, step 4: open **protect-main**, under **Require status checks to pass** click **Add checks**, type `checks`, select it, and save. In a team, a reviewer approves here too.

> `checks` is the **job name** in `ci.yml`. GitHub only offers a check in the list once a job with that name has run, which is why this step waits until now. If you rename the job, update the ruleset too, or every pull request will wait forever for a check that never comes.

**7. Merge and delete the branch.** Click **Merge pull request** → **Confirm merge** → **Delete branch**. Two workflows start:

- **Deploy to test:** test is redeployed from `main`. Check `workspace.sales_test.sales_report`: it has the new columns. This is where UAT happens.
- **Clean up dev:** the branch's dev jobs are removed. The schema `sales_dev_avg_order` stays; you can drop it later.

**8. Remove the Git folder.** The feature is finished, so delete `alice-avg-order` (right-click it → **Delete**). Its work is safe in `main`.

## Part 7: Bob builds Feature 3 at the same time

Work in `bob-segments`. Bob started from the same `main` as Alice, in parallel.

**1. Add the logic.** Open `src/transforms.py` and add at the end:

```python


def segment(amount):
    """Label an order 'large', 'medium', or 'small' by amount."""
    if amount is None:
        return "unknown"
    if amount >= 1000:
        return "large"
    if amount >= 300:
        return "medium"
    return "small"
```

**2. Add its tests.** Open `tests/test_transforms.py` and add at the end:

```python


def test_segment_boundaries():
    from transforms import segment

    assert segment(1000) == "large"
    assert segment(300) == "medium"
    assert segment(299.99) == "small"
    assert segment(None) == "unknown"
```

**3. Use it in the pipeline.** In `src/ingest.py`, change the import, the line that builds `rows`, and the schema string:

```python
from transforms import clean_amount, segment
```

```python
rows = [
    (order_id, region, clean_amount(amount), segment(clean_amount(amount)))
    for order_id, region, amount in raw_orders
]
```

```python
df = spark.createDataFrame(rows, "order_id string, region string, amount double, segment string")
```

**4. Try it.** As in Part 6, set the **schema** widget, this time to `sales_dev_segments`, and run `src/ingest.py`. If the notebook was already open, restart its session first (from the compute drop-down at the top), so it picks up the new `segment` function.

**5. Commit & Push.** The Git dialog lists all three changed files, checked. Message: `Add customer segments`. Click **Commit & Push**.

**6. Watch dev deploy.** **Deploy to dev** runs for `feature/segments`, including the new unit test. When it's green, `workspace.sales_dev_segments.orders` has a `segment` column.

**7. Pull request, merge, delete the branch, and remove the Git folder**, as in Part 6, steps 5 to 8.

Alice changed `build_report.py`, and Bob changed `ingest.py` and `transforms.py`, so the two features merge without conflicts. Test now has both.

> **What CI didn't check.** Bob's pull request was tested against the `main` he started from, *before* Alice's change. The combination of both features was first run in **test**. That's exactly why test exists: it's the first place every merged change runs together. Teams that want CI to check the combination too turn on **Require branches to be up to date before merging** in the ruleset, so each pull request must first take in the latest `main` and pass CI again.

## Part 8: Features 2 and 4 stay in progress

Real projects always have unfinished work. Push both features, but don't merge them yet.

**Feature 2 (Alice), in `alice-dq-checks`.** In `src/integration_checks.py`, before the final `print`, add:

```python
null_amounts = orders.filter("amount IS NULL").count()
assert null_amounts == 0, f"{null_amounts} orders have no amount"
```

**Commit & Push** with the message `Check for orders with no amount`.

**Feature 4 (Bob), in `bob-forecast`.** In the `src` folder, click **Create** → **Notebook**, name it `forecast`, and add one cell:

```python
print("Forecast coming soon")
```

**Commit & Push** with the message `Start forecast notebook`.

Both deploy to their own dev copies (`sales_dev_dq_checks` and `sales_dev_forecast`). Neither is in `main`, so neither reaches test or prod. And because each feature has its own Git folder, Alice had Features 1 and 2 open at the same time, without one disturbing the other.

## Part 9: Release v1.0.0 to prod

`main` has Features 1 and 3, and test is green. Time to pass gate 2.

**0. Check what you're about to release.** In **Actions** → **Deploy to test**, the latest run should be green **and** be for the latest commit on `main`. A release tags whatever `main` is when you publish, so if someone merged after the last green test run, you'd be releasing something test hasn't seen. Wait for that run first.

> **Version numbers** follow [semantic versioning](https://semver.org/): `MAJOR.MINOR.PATCH`. A new feature raises MINOR (`v1.0.0` → `v1.1.0`), a fix raises PATCH (`v1.1.0` → `v1.1.1`), and a change that breaks people who use the output (such as renaming a column) raises MAJOR (`v2.0.0`).

**1. Publish a release.** On GitHub → **Releases** → **Draft a new release**:

- **Choose a tag** → type `v1.0.0` → **Create new tag: v1.0.0 on publish**
- Target: `main`
- Title: `v1.0.0`. Click **Generate release notes** to list the merged pull requests.
- Click **Publish release**.

**2. Approve.** In **Actions**, **Deploy to prod** is **Waiting**. Open it → **Review deployments** → check `prod` → **Approve and deploy**. (**Reject** would stop the run, and prod would keep its current version.)

**3. Check prod.** When the run is green, Databricks has `sales_pipeline_prod`, `workspace.sales_prod.sales_report` has `avg_amount` and `order_count`, and `workspace.sales_prod.orders` has the `segment` column. The forecast notebook and the new quality check aren't there: they're still on feature branches.

> **Why prod doesn't run the integration checks.** `deploy-prod.yml` validates, deploys, and runs the pipeline, but not `integration_tests`. The checks already passed in test on this exact commit, so running them again in prod adds little. Some teams still run a quick "smoke test" after a prod deploy, to catch problems that only prod's data or permissions would show.

**4. See all three environments on GitHub.** On the repository's main page, the right sidebar has **Deployments**, listing `dev`, `test`, and `prod`. Click it to see which branch or commit went where, and when.

| Environment | Has now | Updated by |
|---|---|---|
| dev | Features 2 and 4, each in its own copy | Each Commit & Push on a feature branch |
| test | Everything in `main`: Features 1 and 3 | Each merge into `main` |
| prod | Release v1.0.0: Features 1 and 3 | Each published, approved release |

**5. Ship Feature 2 later.** Open a pull request for `feature/dq-checks`. `main` has moved on since the branch started, so bring it in first: if the pull request shows **Update branch**, click it. GitHub merges the latest `main` into the feature branch, so CI runs again on the combination, and the push redeploys its dev copy. In `alice-dq-checks`, click **Pull** to bring that update into the Git folder. When CI is green, merge, check test, then publish `v1.1.0` and approve it.

## Practice: watch the gates stop a bad change

So far everything has passed. A pipeline is only worth having if it **stops** bad changes, so break one on purpose.

**1. Make a breaking change.** Create a Git folder `alice-break-it` on a new branch `feature/break-it`, as in Part 5. In `src/transforms.py`, change the `medium` threshold in `segment` from `300` to `500`, as if someone "tidied up" the rule without telling anyone. **Commit & Push** with the message `Change medium threshold`.

**2. Watch CD refuse to deploy.** **Deploy to dev** goes red at the unit-test step: `test_segment_boundaries` expects `segment(300)` to be `"medium"`. The deploy steps after it never run, so not even dev gets the broken code. Open the failed step to read the test output: this is how you'll debug real failures.

**3. Watch gate 1 hold.** Open a pull request for `feature/break-it`. CI goes red, and the **Merge pull request** button is blocked by `protect-main`. Nothing reaches `main`, test, or prod.

**4. Clean up.** Close the pull request without merging, delete the branch on GitHub, and delete the Git folder. **Clean up dev** still runs; since this branch was never deployed, it has little or nothing to remove.

> **The lesson:** the tests encoded a business rule (300 is medium), and CI enforced it automatically. If the rule really should change, the fix is to change the **test and the code together**, in one reviewed pull request. Tests only protect what they check: a change the tests don't cover would sail through to test, which is why integration checks and UAT come after.

## Rolling back prod

Sooner or later a release turns out to be wrong. There are two ways back, and both go through the pipeline, never by editing prod by hand:

| Way | How | Use when |
|---|---|---|
| **Redeploy the previous release** | **Actions** → **Deploy to prod** → the run for the last good release (such as `v1.0.0`) → **Re-run all jobs** → approve | Prod must be fixed **now**. It reruns the same commit that worked before (GitHub keeps runs available for re-run for a limited time) |
| **Roll forward** | A `feature/fix-...` branch that reverts or fixes the change → pull request → test → release `v1.1.1` | The normal fix. `main` and prod end up agreeing again |

Redeploying puts the old **code** back, but not old **data**: tables the bad version wrote stay as they are until the pipeline's next run rebuilds them. Because `ingest.py` and `build_report.py` rewrite their tables on every run, columns included (`overwriteSchema`), here the redeploy's own run is enough. In pipelines that append or update data, rollback needs a plan for the data too, such as Delta Lake's `RESTORE TABLE ... TO VERSION AS OF`.

After a redeploy, `main` still holds the bad change, so the next release would bring it back. Always follow a redeploy with a roll-forward fix.

## Part 10: Moving to a company setup

The process stays the same. What changes is how strongly the environments are separated:

1. **Separate environments.** Three workspaces, or one workspace with three catalogs, so test and prod data can't be touched from dev. Each target in `databricks.yml` gets its own `host` or catalog.
2. **Separate compute.** For example, small compute for dev and larger, reliable compute for prod, set per target.
3. **Service principals.** Deployments and jobs run as non-human identities: in `databricks.yml`, `run_as: service_principal_name: <application-id>` for test and prod.
4. **No stored tokens.** Each GitHub environment signs in as its own service principal through workload identity federation. In each workflow, add `permissions: id-token: write` and replace the token with:

   ```yaml
   env:
     DATABRICKS_AUTH_TYPE: github-oidc
     DATABRICKS_HOST: ${{ vars.DATABRICKS_HOST }}
     DATABRICKS_CLIENT_ID: ${{ secrets.DATABRICKS_CLIENT_ID }}   # service principal ID
   ```

5. **Real people at the gates.** Each developer links their own GitHub token in Databricks. `main` requires at least one approving review, and prod approval comes from someone other than the person releasing, with **Prevent self-review** checked.
6. **Only release tags can reach prod.** In the `prod` GitHub environment, set **Deployment branches and tags** to **Selected branches and tags** and add a tag rule `v*`. Then even a mistaken or edited workflow can't deploy a feature branch to prod. Tag rulesets can also stop anyone from moving or deleting a release tag once it's published.
7. **Stricter gate 1.** Turn on **Require branches to be up to date before merging**, so CI always checks the change combined with the latest `main` (see the note at the end of Part 7).

## Clean up

- **Git folders:** delete each one when its feature is merged.
- **Dev copies:** removed automatically when a feature branch is deleted (**Clean up dev**).
- **Schemas** are kept. Drop the ones you don't need in the SQL editor, for example `DROP SCHEMA workspace.sales_dev_avg_order CASCADE`.
- **Test and prod deployments:** delete the jobs in **Jobs & Pipelines**, or from your computer with the Databricks CLI: `databricks bundle destroy -t test`.

## Troubleshooting

| Problem | Likely cause |
|---|---|
| `401` / "Credential was not sent" in Actions | `DATABRICKS_TOKEN` is missing from that GitHub environment, misspelled, or added as a variable instead of a secret |
| `403` or "Invalid access token" in Actions | The Databricks token expired or was deleted. Generate a new one and update all three GitHub environments |
| Commit & Push fails in Databricks ("Resolver error" or similar) | The GitHub token in Linked accounts is missing, expired, or lacks **Contents: Read and write** on this repository |
| Deploy to dev didn't run after Commit & Push | The branch name doesn't start with `feature/` |
| Prod deploy doesn't wait for approval | The repository is private on a free GitHub plan, or required reviewers isn't saved on `prod` |
| Can't merge: "Required status check is expected" | CI hasn't run on this pull request. Push a commit to the branch to trigger it |
| No **schema** widget to set | Widgets appear after the cell that defines them runs (the first code cell). Run it, then set the widget |
| `ModuleNotFoundError: transforms`, or a new function isn't found | `transforms.py` must stay in `src/` with the notebooks. After editing it, restart the notebook's session |
| Prod validate error about `run_as` or `permissions` | Fill in `<your-databricks-email>` in both places in the `prod` target |
| Pull request waits forever: "Waiting for status to be reported" for `checks` | The required check name in `protect-main` doesn't match the job name in `ci.yml`, or the pull request's base isn't `main` |
| Deploy to dev is red at the unit tests | Working as intended: open the failed step to see which test failed and why. Fix the code (or the test, if the rule really changed) and push again |
| Deploy to test is red after a merge | A combination of merged changes broke the pipeline. Fix it with a new feature branch and pull request, never by pushing to `main`; don't release until test is green again |

## Optional: CLI-enabled Git folders

Ordinary Git folders hide the stage behind **Commit & Push**. For full Git (partial staging, several local commits before pushing, `git stash`), Databricks offers **Git CLI support for Git folders**, in Public Preview:

1. A workspace admin enables it on the **Previews** page. On Free Edition, that's you, if it's offered.
2. Create a **new** Git folder with Git CLI access. Existing Git folders don't gain it.
3. Use Git from the web terminal or a `%sh` cell, on serverless environment version 5 or later:

   ```bash
   cd /Workspace/Users/<you>/alice-avg-order
   git add -p src/build_report.py
   git commit -m "Add average order value"
   git push
   ```

Pushes from a CLI-enabled Git folder start the same pipeline.

## Optional: deploy dev from your computer

With the [Databricks CLI](https://docs.databricks.com/dev-tools/cli/install.html) installed and signed in (`databricks auth login --host <your-workspace-url>`), you can create a branch's dev copy by hand, exactly as **Deploy to dev** does:

```bash
databricks bundle deploy -t dev --var="branch=avg_order"
databricks bundle run -t dev --var="branch=avg_order" sales_pipeline
```
