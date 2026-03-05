#!/bin/bash

# Ensure we are in the project root
echo "🚀 Starting Hugging Face Deployment..."

# 1. Delete the old orphan branch if it exists
git branch -D hf-deploy 2>/dev/null

# 2. Create a fresh orphan branch with no history (wipes tracking)
echo "🌿 Creating fresh orphan branch..."
git checkout --orphan hf-deploy

# 3. Clear all tracked files from the Git index (keeps files on disk)
git rm -rf --cached .

# 4. Add all current files (the tracked .gitignore will block assets)
echo "➕ Staging files..."
git add .

# 5. Commit
git commit -m "Automated deployment to Hugging Face"

# 6. Force push this single, clean commit to Hugging Face
echo "☁️ Pushing to Hugging Face..."
git push -f hf hf-deploy:main

# 7. Return safely to the main branch
echo "🏠 Returning to main branch..."
git checkout main

echo "✅ Deployment Complete!"
