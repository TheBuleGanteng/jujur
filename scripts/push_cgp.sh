#!/bin/bash

# Step 1: Pull the latest version of the repository
git -C ~/01.Repos/05.MyFin50d pull https://github.com/TheBuleGanteng/jujur.git

# Step 2: Import files specified in .gitignore using SCP
# List of files/folders to import, adjust as necessary based on .gitignore content
FILES=(
    "gitignored/cert.pem"
    "gitignored/key.pem"
)

for file in "${FILES[@]}"; do
    scp -r ~/01.Repos/05.MyFin50d/$file matt@<VM_IP>:~/05.MyFin50d/${file%/*}/
done
