#!/bin/bash

echo "🔄 Updating UHD-MCP Repository"
echo "==============================="

# Check if PAT_TOKEN is provided
if [ -z "$PAT_TOKEN" ]; then
    echo "❌ PAT_TOKEN environment variable is not set"
    echo "   Please provide a GitHub Personal Access Token"
    exit 1
fi

# Get current directory (should be the repo root)
REPO_DIR=$(pwd)
echo "📁 Repository directory: $REPO_DIR"

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "❌ Not in a git repository directory"
    exit 1
fi

# Get current branch and remote info
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
echo "🔀 Current branch: $CURRENT_BRANCH"

# Remove existing remote configurations
echo "🗑️  Removing existing remote configurations..."
git remote remove origin 2>/dev/null || true
git remote remove upstream 2>/dev/null || true

# Set new remote with PAT token
NEW_REMOTE="https://${PAT_TOKEN}@github.com/wineslab/uhd-mcp"
echo "🔗 Setting new remote: https://***@github.com/wineslab/uhd-mcp"
git remote add origin "$NEW_REMOTE"

# Verify remote was set correctly
REMOTE_URL=$(git remote get-url origin 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "✅ Remote configured successfully"
else
    echo "❌ Failed to configure remote"
    exit 1
fi

# Perform initial git pull to sync with remote
echo "⬇️  Performing initial pull from remote..."
if git pull origin; then
    echo "✅ Initial pull completed successfully"
else
    echo "⚠️  Initial pull failed, continuing with fetch strategy..."
fi

# Perform git pull to update current branch
echo "⬇️  Pulling latest changes..."
if git pull; then
    echo "✅ Repository updated successfully"
    
    # Show latest commit info
    LATEST_COMMIT=$(git log -1 --pretty=format:"%h - %an: %s (%cr)")
    echo "📝 Latest commit: $LATEST_COMMIT"
    
else
    echo "❌ Failed to pull changes"
    echo "⚠️  This might be due to local changes conflicting with remote changes"
    echo "   Consider stashing local changes or resolving conflicts manually"
    exit 1
fi

echo "🎉 Repository update completed successfully!"
echo
