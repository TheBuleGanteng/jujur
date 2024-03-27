#!/bin/bash

# Replace these placeholders with your actual values
GIT_REPO_URL="git@github.com:TheBuleGanteng/jujur_private.git"
PROJECT_DIR="."  # Assuming your project directory is the current working directory

# Forcefully add all files (including ignored ones)
git add -f -A

# Get a descriptive commit message from the user
read -r -p "Enter a descriptive commit message (careful, bypassing .gitignore): " COMMIT_MESSAGE

# Commit all changes with the provided message
if [[ ! -z "$COMMIT_MESSAGE" ]]; then
  git commit -m "$COMMIT_MESSAGE"
  echo "Committed changes with message: '$COMMIT_MESSAGE'"
fi

# Get the actual remote branch name (assuming 'origin')
REMOTE_BRANCH=$(git config --get branch.main.remote | sed 's/\./origin/')
REMOTE_BRANCH_NAME=$(git config --get branch.main.merge | sed 's/refs\/heads\///')

# Push the committed changes to the remote branch (force push)
git push -f "$GIT_REPO_URL" "$REMOTE_BRANCH_NAME"

echo "Project pushed successfully to $GIT_REPO_URL (**WARNING: Bypassed .gitignore**)"

