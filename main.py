import os
import csv
import re
from pathlib import Path
from datetime import datetime
from urllib.parse import unquote
from bs4 import BeautifulSoup
from rich.console import Console
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, BarColumn, TimeElapsedColumn, TimeRemainingColumn

console = Console()

# ------------------------ COMMON HELPERS ------------------------

def get_long_path(path):
    abs_path = os.path.abspath(path)
    if os.name == 'nt' and not abs_path.startswith('\\\\?\\'):
        return u'\\\\?\\' + abs_path
    return abs_path

def remove_long_path_prefix(path):
    if os.name == 'nt' and path.startswith('\\\\?\\'):
        return path[4:]
    return path

def cleanup_files():
    files_to_delete = ["file_structure.csv", "root_path.txt"]
    for file_name in files_to_delete:
        try:
            if os.path.exists(file_name):
                os.remove(file_name)
        except Exception:
            pass

# ------------------------ ROOT PATH ------------------------

def get_root_path_config():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "root_path.txt")
    with open(config_path, 'r', encoding='utf-8') as f:
        return os.path.abspath(f.read().strip())

# ------------------------ HELPER FOR PROGRESS BAR ------------------------

def count_items(current_dir):
    """遞迴計算目錄下所有直接與間接的檔案和資料夾數量"""
    count = 0
    try:
        children = os.listdir(current_dir)
    except Exception:
        return count
    count += len(children)
    for child in children:
        full_path = os.path.join(current_dir, child)
        if os.path.isdir(full_path):
            count += count_items(full_path)
    return count

# ------------------------ PART 1 & 2: 統一遍歷 (Rename + Mapping 生成) ------------------------

def clean_filename(name):
    """
    若檔名符合 [name][separator][32位uuid][.ext] 則返回 clean 名稱與 uuid，否則返回原名與 None。
    """
    pattern = re.compile(
        r'^(.*?)[ _-]?'
        r'([0-9a-fA-F]{32})'
        r'(\.\w+)?$'
    )
    match = pattern.match(name)
    if match:
        return {
            'clean': match.group(1) + (match.group(3) or ''),
            'uuid': match.group(2).lower()
        }
    return {'clean': name, 'uuid': None}

def unified_process_directory(current_dir, global_root, conflict_tracker=None, progress=None, task_id=None):
    """
    遞迴遍歷 current_dir，對檔案與資料夾：
      - 針對檔案，計算 clean 名稱（若同一目錄內有重複則加後綴），並執行 rename；
        若檔名中含有 uuid 則記錄 mapping {uuid, file_name}。
      - 針對資料夾，同樣處理 rename，但 mapping 僅記錄檔案。
    回傳 mapping_entries (list of dict，僅包含 "uuid" 與 "file_name")。
    """
    if conflict_tracker is None:
        conflict_tracker = {}
    mapping_entries = []
    try:
        children = sorted(os.listdir(current_dir), key=lambda x: x.lower())
    except Exception:
        if progress and task_id is not None:
            progress.advance(task_id)
        return mapping_entries

    for child in children:
        full_path = os.path.join(current_dir, child)
        if os.path.isfile(full_path):
            info = clean_filename(child)
            base_clean = info['clean']
            uuid = info['uuid']
            
            # Handle file conflicts
            if base_clean in conflict_tracker:
                count = conflict_tracker[base_clean]
                base, ext = os.path.splitext(base_clean)
                clean_name_final = f"{base}_{count}{ext}"
                conflict_tracker[base_clean] += 1
            else:
                conflict_tracker[base_clean] = 1
                clean_name_final = base_clean
            new_full_path = os.path.join(current_dir, clean_name_final)

            # If file name is taken, rename
            if child != clean_name_final:
                target = new_full_path
                counter = 1
                while os.path.exists(target) and os.path.abspath(target) != os.path.abspath(full_path):
                    base, ext = os.path.splitext(new_full_path)
                    target = f"{base}_{counter}{ext}"
                    counter += 1
                try:
                    os.rename(full_path, target)
                    new_full_path = target
                except Exception as e:
                    console.print(f"[red]Rename failed:[/red] {full_path} -> {target} ({e})")
                    new_full_path = full_path

            # Record mapping
            if uuid:
                mapping_entries.append({'uuid': uuid, 'file_name': clean_name_final})
        elif os.path.isdir(full_path):

            # Use conflict_tracker to handle directory conflicts
            sub_conflict = {}
            sub_mapping = unified_process_directory(full_path, global_root, sub_conflict, progress, task_id)
            mapping_entries.extend(sub_mapping)
            info = clean_filename(child)
            base_clean = info['clean']
            if base_clean in conflict_tracker:
                count = conflict_tracker[base_clean]
                base, ext = os.path.splitext(base_clean)
                clean_name_final = f"{base}_{count}{ext}"
                conflict_tracker[base_clean] += 1
            else:
                conflict_tracker[base_clean] = 1
                clean_name_final = base_clean
            new_dir_path = os.path.join(current_dir, clean_name_final)
            if child != clean_name_final:
                target = new_dir_path
                counter = 1
                while os.path.exists(target) and os.path.abspath(target) != os.path.abspath(full_path):
                    base, ext = os.path.splitext(new_dir_path)
                    target = f"{base}_{counter}{ext}"
                    counter += 1
                try:
                    os.rename(full_path, target)
                    new_dir_path = target
                except Exception as e:
                    console.print(f"[red]Rename dir failed:[/red] {full_path} -> {target} ({e})")
                    new_dir_path = full_path

        # Update progress bar
        if progress and task_id is not None:
            progress.advance(task_id)
    return mapping_entries

def unified_process(global_root):
    total_items = count_items(global_root)
    mapping_entries = []
    progress_bar = Progress(
        SpinnerColumn(),
        "[progress.description]{task.description}",
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeElapsedColumn(),
        TimeRemainingColumn(),
    )
    with progress_bar:
        task = progress_bar.add_task("Renaming files and directories", total=total_items)
        mapping_entries = unified_process_directory(global_root, global_root, progress=progress_bar, task_id=task)
    return mapping_entries

def write_mapping_csv(global_root, mapping_entries):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, "file_structure.csv")
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        fieldnames = ['uuid', 'file_name']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(mapping_entries)
    return csv_path

# ------------------------ PART 3: HTML FILE UPDATE ------------------------

def remove_uuid_from_segment(segment):
    return re.sub(r'[ _-]?[0-9a-fA-F]{32}$', '', segment)

def normalize_filename(filename):
    return re.sub(r'_\d+(?=\.html$)', '', filename)

def process_href(href, replacement_filename):
    decoded = unquote(href)
    parts = decoded.split('/')
    new_parts = [remove_uuid_from_segment(part) for part in parts]
    new_parts[-1] = replacement_filename
    return '/'.join(new_parts)

def load_full_mapping(csv_path):
    mapping = {}
    try:
        with open(csv_path, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                uuid = row.get('uuid', '').strip().lower()
                file_name = row.get('file_name', '').strip()
                if uuid:
                    mapping[uuid] = file_name
    except Exception:
        pass
    return mapping

def update_html_links_in_file(file_path, full_mapping):
    updated = False
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')
    except Exception:
        return False

    a_tags = soup.find_all('a')
    for a in a_tags:
        href = a.get('href')
        if not href:
            continue
        if re.search(r'[0-9a-fA-F]{32}', href):
            match = re.search(r'([0-9a-fA-F]{32})(?=\.html$)', href)
            if match:
                uuid = match.group(1).lower()
                if uuid in full_mapping:
                    replacement_filename = full_mapping[uuid]
                else:
                    replacement_filename = normalize_filename(os.path.basename(file_path))
            else:
                replacement_filename = normalize_filename(os.path.basename(file_path))
            new_href = process_href(href, replacement_filename)
            a['href'] = new_href
            updated = True

    if updated:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(str(soup))
        except Exception:
            updated = False
    return updated

def process_all_html(root_folder, csv_path):
    full_mapping = load_full_mapping(csv_path)
    html_files = []
    for dirpath, _, filenames in os.walk(root_folder):
        for filename in filenames:
            if filename.lower().endswith('.html'):
                html_files.append(os.path.join(dirpath, filename))
    progress = Progress(
        SpinnerColumn(),
        "[progress.description]{task.description}",
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeElapsedColumn(),
        TimeRemainingColumn(),
    )
    with progress:
        task = progress.add_task("Updating HTML files", total=len(html_files))
        for file_path in html_files:
            update_html_links_in_file(file_path, full_mapping)
            progress.advance(task)
            progress.console.log(f"Processed: {file_path}")
    console.print(f"Processed {len(html_files)} HTML files.")

def run_html_update():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_folder = get_root_path_config()
    csv_path = os.path.join(script_dir, "file_structure.csv")
    if os.path.exists(root_folder) and os.path.exists(csv_path):
        process_all_html(root_folder, csv_path)

# ------------------------ Part 4 Rename Project Title ------------------------
    
def rename_workspace_folder(base_path: str):
    """
    尋找 'index.html'，提取工作區名稱，並用當前日期重新命名資料夾。
    """
    old_path = Path(base_path)
    index_path = next(old_path.rglob("index.html"), None)
    if index_path is None:
        console.print("[red]index.html not found in any subdirectory.[/red]")
        return False
    workspace_name = None
    try:
        with open(index_path, "r", encoding="utf-8") as file:
            soup = BeautifulSoup(file, 'html.parser')
    except Exception as e:
        console.print(f"[red]Error reading index.html: {e}[/red]")
        return False

    for p in soup.find_all('p'):
        text = p.get_text(strip=True)
        if text.startswith("Workspace name:"):
            workspace_name = text.replace("Workspace name:", "").strip()
            break

    if not workspace_name:
        console.print("[red]Workspace name not found in index.html.[/red]")
        return False

    current_date = datetime.today().strftime('%Y-%m-%d')

    # rename the folde
    new_folder_name = f"{workspace_name} {current_date}"
    new_path = old_path.parent / new_folder_name
    try:
        new_folder_name = f"{workspace_name} {current_date}"
        new_path = old_path.parent / new_folder_name
        old_path.rename(new_path)
        console.print(f"[green]Folder renamed successfully to:[/green] {new_path}")
    except Exception as e:
        console.print(f"[red]Error renaming folder: {e}[/red]")
        return False

    # Subfolder rename
    try:
        subfolders = [f for f in new_path.iterdir() if f.is_dir()]
        if len(subfolders) == 1 :
            single_subfolder = subfolders[0]
            new_subfolder_name = f"{workspace_name} {current_date}"
            new_subfolder_path = new_path / new_subfolder_name

            single_subfolder.rename(new_subfolder_path)
            console.print(f"[green]Subfolder renamed successfully to:[/green] {new_subfolder_path}")
    except Exception as e:
        console.print(f"[red]Error renaming subfolder: {e}[/red]")

    return True

# ------------------------ UNIFIED MAIN FUNCTION ------------------------

def main():
    banner = """
  
    _   _       _   _                ____ _                  _____                       _     _ 
    | \ | | ___ | |_(_) ___  _ __    / ___| | ___  __ _ _ __ | ____|_  ___ __   ___  _ __| |_  | |
    |  \| |/ _ \| __| |/ _ \| '_ \  | |   | |/ _ \/ _` | '_ \|  _| \ \/ / '_ \ / _ \| '__| __| | |
    | |\  | (_) | |_| | (_) | | | | | |___| |  __/ (_| | | | | |___ >  <| |_) | (_) | |  | |_  |_|
    |_| \_|\___/ \__|_|\___/|_| |_|  \____|_|\___|\__,_|_| |_|_____/_/\_\ .__/ \___/|_|   \__| (_)
                                                                        |_| 
    Rename your exported Notion HTML workspace for   
    proper viewing on Windows
    ---------------------------------------------------
    """
    console.print(banner, style="rgb(255,140,0)")
 
    root_path = Prompt.ask("[bold rgb(255,215,0)]Enter the ROOT path of your Notion export[/bold rgb(255,215,0)]")
    root_path = root_path.strip('\"')
    root_path = os.path.abspath(os.path.normpath(root_path))
    if not os.path.exists(root_path):
        input("\nPress Enter to exit...")
        return

    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "root_path.txt")
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(root_path)
    except Exception:
        input("\nPress Enter to exit...")
        return
    
    mapping_entries = unified_process(root_path)
    csv_path = write_mapping_csv(root_path, mapping_entries)
    
    run_html_update()
    cleanup_files()

    rename_workspace_folder(root_path)

    console.print("\n[bold red]DONE ♥️[/bold red]\n[bold blue]All tasks completed successfully.[/bold blue]")
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
