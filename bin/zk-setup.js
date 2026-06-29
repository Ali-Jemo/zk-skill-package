#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

console.log("Installing YOU OS / ZiqaKernel agent integration...");

const PKG_DIR = __dirname;
const PROJECT_ROOT = process.cwd();

// Helper to copy files
function copyDir(src, dest) {
    if (!fs.existsSync(dest)) fs.mkdirSync(dest, { recursive: true });
    for (const file of fs.readdirSync(src)) {
        const srcPath = path.join(src, file);
        const destPath = path.join(dest, file);
        if (fs.lstatSync(srcPath).isDirectory()) {
            copyDir(srcPath, destPath);
        } else {
            fs.copyFileSync(srcPath, destPath);
        }
    }
}

// 1. Copy structure
const dirs = ['.agents', '.opencode', '.kilo', '.claude', 'scripts'];
for (const dir of dirs) {
    if (fs.existsSync(path.join(PKG_DIR, dir))) {
        copyDir(path.join(PKG_DIR, dir), path.join(PROJECT_ROOT, dir));
    }
}

// Copy single files
const files = ['AGENTS.md', 'mcp.json'];
for (const file of files) {
    if (fs.existsSync(path.join(PKG_DIR, file))) {
        fs.copyFileSync(path.join(PKG_DIR, file), path.join(PROJECT_ROOT, file));
    }
}

// Make scripts executable
const installScript = path.join(PROJECT_ROOT, 'scripts/install-zk-agent.sh');
if (fs.existsSync(installScript)) {
    fs.chmodSync(installScript, '755');
}

console.log("YOU OS / ZiqaKernel agent integration installed successfully.");
console.log("Available commands: /zk, /zk-fix, /zk-plan, /zk-review, /zk-elf, /zk-sched, /zk-gui, /zk-mem, /zk-ipc, /zk-input, /zk-driver");
