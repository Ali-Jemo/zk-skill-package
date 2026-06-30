#!/bin/bash
# zk-auto-update.sh
# Run this once to enable automatic updates on shell start.

echo "Enabling automatic toolkit updates..."
UPDATE_CMD="npx zk-skill-package@latest > /dev/null 2>&1 &"

# Append to .bashrc if not already present
if ! grep -q "zk-skill-package" ~/.bashrc; then
    echo -e "\n# ZiqaKernel Auto-Update\n$UPDATE_CMD" >> ~/.bashrc
    echo "Added to ~/.bashrc. Toolkit will check for updates in the background on shell start."
else
    echo "Already enabled in ~/.bashrc."
fi
