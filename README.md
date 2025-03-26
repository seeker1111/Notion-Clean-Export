# Notion Clean Exporter 🧹

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)

A tool to fix Notion's problematic HTML exports for reliable Windows operation. Renames UUID-filled filenames, updates HTML links, and organizes exports with proper naming conventions.

**Why this exists:** Notion's HTML exports generate long UUID-containing filenames that often break Windows file system limits, making exports causing unexpected problem

## What does it do ✨

- Removes UUIDs from filenames while preserving extensions
- Handles naming conflicts automatically (appends _1, _2, etc.)
- Updates all HTML internal links to match cleaned filenames
- Renames export folder with workspace name + date

## Installation 📦

### For Regular Users
1. Download the latest `.exe` from [Releases](#) 
2. Place the executable in your preferred location

### If you want to view code
```bash
git clone https://github.com/yourusername/notion-clean-export.git
```