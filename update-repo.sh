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

# Get current branch name before modifying remotes
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "main")
echo "🔀 Current branch: $CURRENT_BRANCH"

# Remove existing remote configurations
echo "🗑️  Removing existing remote configurations..."
git remote remove origin 2>/dev/null || true
git remote remove upstream 2>/dev/null || true

# Set new remote with PAT token
NEW_REMOTE="https://${PAT_TOKEN}@github.com/wineslab/uhd-mcp"
echo "🔗 Setting new remote: https://***@github.com/wineslab/uhd-mcp"
git remote add origin "$NEW_REMOTE"

# Fetch latest information from new remote
echo "📥 Fetching latest information from remote..."
if git fetch origin; then
    echo "✅ Fetch completed successfully"
else
    echo "❌ Failed to fetch from remote"
    exit 1
fi

# Pull latest changes from current branch
echo "⬇️  Pulling latest changes..."
if git pull origin "$CURRENT_BRANCH"; then
    echo "✅ Repository updated successfully"
    
    # Show latest commit info
    LATEST_COMMIT=$(git log -1 --pretty=format:"%h - %an: %s (%cr)")
    echo "📝 Latest commit: $LATEST_COMMIT"
    
else
    echo "❌ Failed to pull changes"
    exit 1
fi

echo "🎉 Repository update completed successfully!"
echo
