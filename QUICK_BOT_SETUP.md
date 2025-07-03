# 🚀 Quick Start: Bot PR Setup

This is a simplified guide to get your AI bots creating PRs successfully.

## ✅ Setup Steps

### 1. Test Bot PR Creation (Start Here!)

First, let's verify that bots can create PRs in your repository:

1. Go to your repository on GitHub
2. Click **Actions** tab
3. Find **"Test Bot PR Creation"** workflow
4. Click **Run workflow** button
5. Wait for it to complete and check if a PR was created

### 2. Repository Settings

Enable these settings in your GitHub repository:

```
Repository Settings → General:
☑️ Allow auto-merge
☑️ Automatically delete head branches
☑️ Allow squash merging
☐ Allow merge commits
☐ Allow rebase merging
```

### 3. Install Mergify (Optional but Recommended)

1. Go to [Mergify GitHub App](https://github.com/apps/mergify)
2. Click **Install**
3. Select your repository
4. The `.mergify.yml` configuration is already set up

### 4. Enable Dependabot

```
Repository Settings → Security → Code security and analysis:
☑️ Dependabot alerts
☑️ Dependabot security updates
☑️ Dependabot version updates
```

## 🤖 Available Workflows

### Manual Bot Workflows (Run Anytime)

1. **Test Bot PR Creation** - Verify bot functionality
2. **AI Bot Pull Requests** - Run dependency updates, code improvements
3. **Repository Setup** - Configure branch protection and labels

### Scheduled Bot Workflows

- **Daily 9 AM UTC**: Dependency updates
- **Weekly Monday 10 AM UTC**: Code improvements

## 🔧 Troubleshooting

### Bot Can't Create PRs?

1. Check that **Actions** are enabled in repository settings
2. Verify **Auto-merge** is enabled
3. Make sure the workflow has proper permissions

### Auto-merge Not Working?

1. Install the **Mergify app**
2. Check that **CI checks** are passing
3. Verify **branch protection** rules allow auto-merge

## 🎯 Next Steps

Once the test bot PR is working:

1. ✅ Merge the test PR
2. ✅ Enable scheduled workflows
3. ✅ Monitor bot activity in Actions tab
4. ✅ Customize bot behavior as needed

---

**🎉 That's it! Your bots should now be able to create PRs automatically.**

For detailed configuration options, see the full `AI_BOTS_SETUP.md` guide.
