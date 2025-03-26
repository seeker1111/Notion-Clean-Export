# Notion Clean Exporter

[![Windows EXE](https://img.shields.io/badge/Download-Windows_EXE-0078d7?logo=windows)](https://github.com/seeker1111/Notion-Clean-Export/releases/download/1.0/Notion.HTML.Clean.Export.exe)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)

Fix Notion HTML exports for Windows operation.

### Why this exists
Notion's HTML exports generate long UUID-containing filenames that break Windows path limits, causing extraction failures and broken links. This fixes This fixes the issue..

### What it does ✨

- Remove UUIDs from filenames
- Resolve naming conflicts (appends _1, _2, etc.)
- Update HTML internal links to match cleaned filenames
- Rename export folder with workspace name + date


## 📦Installation  (One-Click Download)

⚙️ **From Notion**:  
   - Go to `Settings` → `General`
   - Choose `Export entire workspace` as HTML  
   - Check `Include subpages`

📦 **Extract Files**:  
   - Small exports: Use built-in Windows unzip  
   - Large exports: If Windows can't unzip, Use 7-Zip (https://www.7-zip.org/)

▶️ **Run the Cleaner**

[![Download EXE](https://github.com/seeker1111/Notion-Clean-Export/releases/download/1.0.0/Notion.CleanExport.exe)
1. Click the button above to download
2. Launch
3. Enter the path of your Notion export  
