"""
Revit Journal File Parser
Parses Revit journal files and extracts session info, errors, performance data, and workflow events.
Uses XML pattern file for error matching with Autodesk KB article links.
"""

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple


class JournalParser:
    """Main parser class for Revit journal files."""

    def __init__(self, xml_pattern_file: Optional[str] = None):
        """Initialize parser with optional XML pattern file."""
        self.patterns = []
        if xml_pattern_file:
            self.load_patterns(xml_pattern_file)
        else:
            # Try to load default pattern file
            default_path = Path(__file__).parent / "Search_v8_b.xml"
            if default_path.exists():
                self.load_patterns(str(default_path))

    def load_patterns(self, xml_file: str) -> None:
        """Load error patterns from XML file."""
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()

            for search_text in root.findall('SearchText'):
                pattern = {
                    'text': search_text.text or '',
                    'search_type': search_text.get('searchType', 'text'),
                    'color': search_text.get('color', 'gray'),
                    'comment': search_text.get('comment', ''),
                    'group': search_text.get('group', 'Other'),
                    'do_search': search_text.get('doSearch', 'true') != 'false'
                }
                if pattern['do_search'] and pattern['text']:
                    self.patterns.append(pattern)
        except Exception as e:
            print(f"Warning: Could not load patterns from {xml_file}: {e}")

    def parse(self, content: str) -> Dict[str, Any]:
        """Parse journal file content and return structured data."""
        lines = content.splitlines()

        result = {
            'session_info': self._extract_session_info(content),
            'errors': self._extract_errors(lines),
            'performance': self._extract_performance(lines),
            'workflow': self._extract_workflow(lines),
            'addins': self._extract_addins(lines, content),
            'kb_articles': self._match_known_issues(lines),  # FIXED: Renamed for clarity
            'timeline': self._extract_timeline(lines),
            'summary': {}
        }

        # Build summary
        result['summary'] = self._build_summary(result)

        return result

    def _extract_session_info(self, content: str) -> Dict[str, Any]:
        """Extract session and system information from journal content."""
        info = {
            'revit_version': '',
            'build_number': '',
            'computer_name': '',
            'username': '',
            'operating_system': '',
            'ram': '',
            'graphics_card': '',
            'graphics_driver': '',
            'processor': '',
            'journal_name': '',  # Journal filename
            'session_start': '',
            'session_end': '',
            'session_duration': '',
            'models_opened': [],
            'primary_model': '',  # Main model being worked on
            'session_status': 'Active',  # Active, Closed, or Crashed
            'journal_file': '',
            'unsaved_work': '',  # Time of unsaved work
            'unsaved_work_duration': '',  # Duration of unsaved work
            'views': [],          # Unique views activated
            'sheets': [],         # Unique sheets activated
            'views_count': 0,
            'sheets_count': 0
        }

        models = set()
        linked_files = set()
        primary_model = ''
        session_start_time = None
        session_end_time = None
        
        # Split content into lines for line-by-line processing
        lines = content.split('\n')

        # === SESSION START ===
        # Pattern: 'C dd-Mon-YYYY HH:MM:SS.sss; 0:< 'C' (Clock.  [hh:mm:ss.000])
        m = re.search(r"'C\s+(\d{1,2}-\w{3}-\d{4}\s+\d{2}:\d{2}:\d{2}\.\d+);", content)
        if m:
            session_start_time = self._parse_timestamp(m.group(1))
            # Store formatted timestamp without milliseconds
            info['session_start'] = session_start_time.strftime('%d-%b-%Y %H:%M:%S') if session_start_time else m.group(1)
        else:
            session_start_time = None
        # === BUILD NUMBER ===
        # Pattern: ' Build: 20230308_1635(x64)
        m = re.search(r"'\s*Build:\s*(\S+)", content)
        if m:
            info['build_number'] = m.group(1).strip()

        # === REVIT VERSION ===
        # Pattern: ' 0:< Autodesk Revit 2024
        m = re.search(r"'\s*\d+:\s*<?\s*Autodesk Revit\s+(\d{4})", content)
        if m:
            info['revit_version'] = f"Revit {m.group(1)}"
        else:
            # Alternative: Branch: RELEASE_2024
            m = re.search(r"Branch:\s*RELEASE_(\d{4})", content)
            if m:
                info['revit_version'] = f"Revit {m.group(1)}"

        # === JOURNAL FILE PATH ===
        # Pattern: ' 0:< this journal = C:\Users\...
        m = re.search(r"'\s*\d+:\s*<?\s*this journal\s*=\s*(.+?)[\r\n]", content)
        if m:
            info['journal_file'] = m.group(1).strip()
            # Extract journal name from path
            journal_path = info['journal_file']
            info['journal_name'] = journal_path.split('\\')[-1].split('/')[-1]

        # === USERNAME ===
        # Pattern: Jrn.Directive  _\n        "Username"  , "Jenish"
        m = re.search(r'Jrn\.Directive\s+_\s*[\r\n]+\s*"Username"\s*,\s*"([^"]+)"', content)
        if m:
            info['username'] = m.group(1)
        else:
            # Alternative: extract from path C:\Users\USERNAME\
            m = re.search(r'C:\\Users\\([^\\]+)\\', content, re.IGNORECASE)
            if m:
                info['username'] = m.group(1)

        # === RAM ===
        # Pattern: ' 0:< Initial VM: Avail 134213198 MB, Used 35 MB, Peak 35; RAM: Avail 35501 MB
        m = re.search(r"Initial VM:.*?RAM:\s*Avail\s+(\d+)\s*MB", content)
        if m:
            ram_mb = int(m.group(1))
            ram_gb = round(ram_mb / 1024, 1)
            info['ram'] = f"{ram_gb} GB ({ram_mb} MB)"

        # === GRAPHICS CARD ===
        # Best pattern: VIDEO CARD ENVIRONMENT: CARD="NVIDIA Quadro K1200"
        m = re.search(r'VIDEO CARD ENVIRONMENT:.*?CARD="([^"]+)"', content, re.IGNORECASE)
        if m:
            info['graphics_card'] = m.group(1).strip()
        else:
            # Alternative: Look for NVIDIA/AMD in Caption lines (avoid Intel integrated)
            m = re.search(r"'\s*\d+:\s*<?\s*Caption\s*:\s*(NVIDIA[^'\r\n]+|AMD[^'\r\n]+Radeon[^'\r\n]*)", content, re.IGNORECASE)
            if m:
                info['graphics_card'] = m.group(1).strip()
            else:
                # Fallback: Any graphics Caption
                m = re.search(r"'\s*\d+:\s*<?\s*Caption\s*:\s*((?:Intel|NVIDIA|AMD)[^'\r\n]*(?:Graphics|GPU|Radeon|GeForce|Quadro)[^'\r\n]*)", content, re.IGNORECASE)
                if m:
                    info['graphics_card'] = m.group(1).strip()

        # === GRAPHICS DRIVER ===
        # Best pattern: VIDEO CARD ENVIRONMENT: ... DRIVER="32.0.15.6603"
        m = re.search(r'VIDEO CARD ENVIRONMENT:.*?DRIVER="([^"]+)"', content, re.IGNORECASE)
        if m:
            info['graphics_driver'] = m.group(1).strip()
        else:
            # Fallback: DriverVersion : xx.xx.xx.xx
            m = re.search(r"DriverVersion\s*:\s*(\d+[\d.]+)", content)
            if m:
                info['graphics_driver'] = m.group(1).strip()

        # === PROCESSOR ===
        # Pattern: ' 1:<    Name : Intel(R) Core(TM) i7-9700 CPU @ 3.00GHz
        # Look for Name with CPU/Processor in it to avoid matching graphics cards
        m = re.search(r"'\s*\d+:\s*<?\s*Name\s*:\s*((?:Intel|AMD)[^'\r\n]*(?:CPU|Core|Processor|Ryzen|EPYC)[^'\r\n]*)", content, re.IGNORECASE)
        if m:
            info['processor'] = m.group(1).strip()
        else:
            # Alternative: Caption in processor section
            m = re.search(r"'\s*\d+:\s*<?\s*Caption\s*:\s*(Intel64 Family[^'\r\n]+)", content)
            if m:
                info['processor'] = m.group(1).strip()

        # === OPERATING SYSTEM ===
        # Pattern: ' OS Version : or Caption : Microsoft Windows
        m = re.search(r"'\s*\d+:\s*<?\s*Caption\s*:\s*(Microsoft Windows[^'\r\n]*)", content, re.IGNORECASE)
        if m:
            info['operating_system'] = m.group(1).strip()

        # === SESSION END / FINISHED ===
        # Pattern: 'C dd-Mon-YYYY HH:MM:SS.sss;  finished recording journal file
        m = re.search(r"'C\s+(\d{1,2}-\w{3}-\d{4}\s+\d{2}:\d{2}:\d{2}\.\d+);\s*finished recording journal file", content)
        if m:
            session_end_time = self._parse_timestamp(m.group(1))
            # Store formatted timestamp without milliseconds
            info['session_end'] = session_end_time.strftime('%d-%b-%Y %H:%M:%S') if session_end_time else m.group(1)
        else:
            # If no finish marker (crashed or active session), find the last timestamp in the file
            # Look for any 'C or 'E timestamp markers
            all_timestamps = list(re.finditer(r"'[CE]\s+(\d{1,2}-\w{3}-\d{4}\s+\d{2}:\d{2}:\d{2}\.\d+)", content))
            if all_timestamps:
                last_timestamp_str = all_timestamps[-1].group(1)
                session_end_time = self._parse_timestamp(last_timestamp_str)
                # Store formatted timestamp without milliseconds
                info['session_end'] = session_end_time.strftime('%d-%b-%Y %H:%M:%S') if session_end_time else last_timestamp_str

        # === MODELS OPENED ===
        # FIXED: Extract ONLY clean model filenames, no paths or technical data
        models = set()
        model_matches = []
        
        # Pattern 1: Jrn.Data "File Name" - extract just the filename
        for m in re.finditer(r'Jrn\.Data\s+"File Name"\s*,\s*"[^"]*?([^\\\/]+\.rvt)"', content, re.IGNORECASE):
            model_name = m.group(1).strip()
            if model_name and model_name.lower().endswith('.rvt'):
                # Skip if it looks like a temp file (all hex digits)
                if not re.match(r'^[0-9a-f]{32,}', model_name.replace('.rvt', '').replace('-', '')):
                    models.add(model_name)
                    model_matches.append((m.start(), model_name))
        
        # Pattern 2: Cloud models (BIM 360/ACC) - extract just filename
        for m in re.finditer(r'BIM 360://[^/]+/([^\\\/"]+\.rvt)', content, re.IGNORECASE):
            model_name = m.group(1).strip()
            if model_name:
                models.add(model_name)
                model_matches.append((m.start(), model_name))
        
        # Pattern 3: File open command - extract just filename
        for m in re.finditer(r'ID_REVIT_FILE_OPEN[^"]*"[^"]*?([^\\\/]+\.rvt)"', content, re.IGNORECASE):
            model_name = m.group(1).strip()
            if model_name and model_name.lower().endswith('.rvt'):
                if not re.match(r'^[0-9a-f]{32,}', model_name.replace('.rvt', '').replace('-', '')):
                    models.add(model_name)
                    model_matches.append((m.start(), model_name))

        # Set primary model as the first model opened
        if model_matches:
            model_matches.sort(key=lambda x: x[0])
            primary_model = model_matches[0][1]
            info['primary_model'] = primary_model
        else:
            if models:
                info['primary_model'] = list(models)[0]

        info['models_opened'] = sorted(list(models))  # Sort alphabetically

        # === LINKED MODELS ===
        # Extract linked RVT files (now primary_model is set, so we can filter it out)
        for m in re.finditer(r'(?:Link|Linked|OpenLink).*?"([^"]*\.rvt)"', content, re.IGNORECASE):
            full_path = m.group(1)
            link_name = full_path.split('\\')[-1].split('/')[-1]
            if link_name and link_name != primary_model:  # Don't include primary model as link
                linked_files.add(('RVT Link', link_name))

        # Extract DWG links
        for m in re.finditer(r'(?:Link|Import|CAD).*?"([^"]*\.dwg)"', content, re.IGNORECASE):
            full_path = m.group(1)
            link_name = full_path.split('\\')[-1].split('/')[-1]
            if link_name:
                linked_files.add(('DWG Link', link_name))

        # Extract IFC links
        for m in re.finditer(r'(?:Link|Import).*?"([^"]*\.ifc)"', content, re.IGNORECASE):
            full_path = m.group(1)
            link_name = full_path.split('\\')[-1].split('/')[-1]
            if link_name:
                linked_files.add(('IFC Link', link_name))

        # Extract NWC links (Navisworks)
        for m in re.finditer(r'(?:Link|Import).*?"([^"]*\.nwc)"', content, re.IGNORECASE):
            full_path = m.group(1)
            link_name = full_path.split('\\')[-1].split('/')[-1]
            if link_name:
                linked_files.add(('NWC Link', link_name))

        # Convert to list of dicts for better JSON structure
        info['linked_models'] = [{'type': link_type, 'name': name} for link_type, name in sorted(linked_files)]
        
        # FIXED: Remove linked model names from models_opened list
        # Extract just the names from linked_files
        linked_model_names = {name for link_type, name in linked_files if link_type == 'RVT Link'}
        # Filter out linked models from models_opened, keeping only primary and directly opened models
        info['models_opened'] = [model for model in info['models_opened'] if model not in linked_model_names]

        # === SESSION STATUS ===
        # FIXED: Only detect crash when "FATAL" keyword is present
        # Determine session status: Closed, Active, or Crashed
        has_finish_marker = 'finished recording journal file' in content.lower()

        # Check for FATAL errors only (as requested by user)
        has_fatal = re.search(r'\bFATAL\b', content, re.IGNORECASE) is not None

        # Set session status based on conditions
        if has_fatal:
            info['session_status'] = 'Crashed'
        elif has_finish_marker:
            info['session_status'] = 'Closed'
        else:
            info['session_status'] = 'Active'

        # === SESSION DURATION ===
        if session_start_time and session_end_time:
            try:
                duration = session_end_time - session_start_time
                total_seconds = int(duration.total_seconds())
                if total_seconds >= 0:
                    hours, remainder = divmod(total_seconds, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    if hours > 0:
                        info['session_duration'] = f"{hours}h {minutes}m {seconds}s"
                    elif minutes > 0:
                        info['session_duration'] = f"{minutes}m {seconds}s"
                    else:
                        info['session_duration'] = f"{seconds}s"
            except Exception as e:
                # If calculation fails, try to provide some info
                pass
        
        # If duration still not set, try alternative calculation
        if not info.get('session_duration') and info.get('session_start') and info.get('session_end'):
            info['session_duration'] = 'Unable to calculate'

        # === UNSAVED WORK TRACKING ===
        # Find the last save/sync operation and extract all actions after it
        last_save_time = None
        last_save_line = 0
        
        # Patterns for save/sync operations
        save_patterns = [
            r'>STC',  # Sync to Central marker
            r'ID_FILE_SAVE_TO_MASTER',  # Sync command
            r'<<<Save Document',  # Document save
            r'ID_REVIT_FILE_SAVE',  # File save command
            r'SYNCHRONIZE WITH CENTRAL',  # Sync dialog
            r'Jrn\.Command.*Save',  # Any save command
        ]
        
        # Find last save operation
        for i, line in enumerate(lines):
            for pattern in save_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # Try to extract timestamp from this line or nearby lines (strip milliseconds)
                    for j in range(max(0, i-2), min(len(lines), i+3)):
                        ts_match = re.search(r"'[CE]\s+(\d{1,2}-\w{3}-\d{4}\s+\d{2}:\d{2}:\d{2})", lines[j])
                        if ts_match:
                            last_save_time = ts_match.group(1)
                            last_save_line = i
                            break
                    break
        
        if last_save_time and session_end_time:
            try:
                last_save_dt = self._parse_timestamp(last_save_time)
                if last_save_dt and session_end_time:
                    duration = session_end_time - last_save_dt
                    hours = int(duration.total_seconds() // 3600)
                    minutes = int((duration.total_seconds() % 3600) // 60)
                    info['unsaved_work_duration'] = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
                    info['unsaved_work'] = last_save_time
            except:
                pass
        
        # Extract ALL actions after last save
        unsaved_actions = []
        if last_save_line > 0:
            # OPTIMIZED: Focus on most important action patterns only
            action_patterns = [
                # Commands (most important)
                (r'Jrn\.Command\s+"[^"]*"\s*,\s*"([^"]+)"', 'Command'),
                # Ribbon actions (user interactions)
                (r'Jrn\.RibbonEvent\s+"[^"]*:\s*([^"]+)"', 'Ribbon Action'),
                # Data changes
                (r'Jrn\.Data\s+"[^"]+"\s*,\s*"([^"]+)"', 'Data'),
                # Directives
                (r'Jrn\.Directive\s+"[^"]*"\s*,\s*"([^"]+)"', 'Directive'),
                # View changes
                (r'Jrn\.ViewActivate\s+"([^"]+)"', 'View Change'),
                # Transactions
                (r'Transaction\s+"([^"]+)"', 'Transaction'),
            ]
            
            # PERFORMANCE: Reduced from 10k to 2k lines for faster processing
            max_lines_to_process = min(len(lines) - last_save_line - 1, 2000)  # Process max 2k lines
            
            for i in range(last_save_line + 1, last_save_line + 1 + max_lines_to_process):
                if i >= len(lines):
                    break
                    
                line = lines[i]
                
                # Extract timestamp if available (strip milliseconds)
                ts_match = re.search(r"'[CE]\s+(\d{1,2}-\w{3}-\d{4}\s+\d{2}:\d{2}:\d{2})", line)
                timestamp = ts_match.group(1) if ts_match else ''
                
                # Check each action pattern
                for pattern, category in action_patterns:
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match:
                        action_text = match.group(1).strip()
                        # Filter out very generic or empty actions
                        if action_text and len(action_text) > 1 and action_text not in ['_', '-', '0', '1']:
                            unsaved_actions.append({
                                'timestamp': timestamp,
                                'category': category,
                                'action': action_text[:100],  # Limit length
                                'line': i + 1
                            })
                        break  # Only match first pattern per line
                
                # Stop early if we have enough actions
                if len(unsaved_actions) >= 500:
                    break
            
            # Limit to reasonable number
            info['unsaved_actions'] = unsaved_actions[:500]
            info['unsaved_actions_count'] = len(unsaved_actions)
        else:
            info['unsaved_actions'] = []
            info['unsaved_actions_count'] = 0

        # === VIEWS & SHEETS ===
        # Extract views and sheets activated during the session from Jrn.ViewActivate entries
        # Pattern: Jrn.ViewActivate "docname" , "ViewFamilyType: Floor Plan, ViewName: Level 1"
        # views_map: name -> {'count': N, 'type': 'Floor Plan'}
        views_map = {}
        sheets_map = {}

        for m in re.finditer(
            r'Jrn\.ViewActivate\s+"[^"]*"\s*,\s*"([^"]+)"',
            content, re.IGNORECASE
        ):
            raw = m.group(1).strip()

            # Try to extract ViewFamilyType and ViewName from structured format
            vft_match = re.search(r'ViewFamilyType:\s*([^,]+)', raw, re.IGNORECASE)
            vn_match = re.search(r'ViewName:\s*(.+)$', raw, re.IGNORECASE)

            if vft_match and vn_match:
                view_family_type = vft_match.group(1).strip()
                name = vn_match.group(1).strip()
            else:
                # Fallback: take last comma-separated segment, strip key prefix
                parts = raw.split(',')
                name = re.sub(r'^[\w\s]+:\s*', '', parts[-1].strip()).strip()
                view_family_type = ''

            if not name or len(name) < 2:
                continue

            # Classify as Sheet if ViewFamilyType contains "sheet", or fallback heuristic
            is_sheet = (
                'sheet' in view_family_type.lower()
                or (not view_family_type and (
                    re.match(r'^[A-Za-z]{0,3}[\d]', name) or 'sheet' in name.lower()
                ))
            )

            if is_sheet:
                if name not in sheets_map:
                    sheets_map[name] = {'count': 0, 'type': view_family_type}
                sheets_map[name]['count'] += 1
            else:
                if name not in views_map:
                    views_map[name] = {'count': 0, 'type': view_family_type}
                views_map[name]['count'] += 1

        info['views'] = [
            {'name': k, 'count': v['count'], 'type': v['type']}
            for k, v in sorted(views_map.items())
        ]
        info['sheets'] = [
            {'name': k, 'count': v['count'], 'type': v['type']}
            for k, v in sorted(sheets_map.items())
        ]
        info['views_count'] = len(views_map)
        info['sheets_count'] = len(sheets_map)

        return info

    def _parse_timestamp(self, timestamp_str: str):
        """Parse timestamp and return datetime object, stripping milliseconds."""
        if not timestamp_str:
            return None

        timestamp_str = timestamp_str.strip()
        
        # Remove milliseconds if present
        if '.' in timestamp_str:
            timestamp_str = timestamp_str.split('.')[0]

        formats = [
            '%d-%b-%Y %H:%M:%S',          # 28-Jan-2025 10:30:15
            '%Y-%m-%d %H:%M:%S',          # 2025-01-28 10:30:15
            '%m/%d/%Y %H:%M:%S',          # 01/28/2025 10:30:15
            '%d/%m/%Y %H:%M:%S',          # 28/01/2025 10:30:15
        ]

        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue
        return None

    def _extract_errors(self, lines: List[str]) -> Dict[str, List[Dict]]:
        """Extract errors, warnings, and info messages."""
        errors = {
            'fatal': [],
            'errors': [],
            'warnings': [],
            'info': [],
            'exceptions': []
        }

        for i, line in enumerate(lines):
            upper = line.upper()
            clean = line.strip()

            # Skip empty lines
            if not clean:
                continue

            entry = {'line': i + 1, 'text': clean}  # Show full line
            
            # Add context from next 2-3 lines for better error understanding
            context_lines = []
            for j in range(i + 1, min(i + 4, len(lines))):
                next_line = lines[j].strip()
                if next_line and not next_line.startswith("'"):  # Skip timestamp lines
                    context_lines.append(next_line)
            
            if context_lines:
                entry['text'] = clean + ' | ' + ' '.join(context_lines)

            # Fatal errors - be specific
            if 'FATAL' in upper and 'ERROR' in upper:
                errors['fatal'].append(entry)
            elif 'UNRECOVERABLE' in upper:
                errors['fatal'].append(entry)
            elif 'APPLICATION WILL BE TERMINATED' in upper:
                errors['fatal'].append(entry)
            elif 'TASKDIALOG_SERIOUS_ERROR' in upper:
                errors['fatal'].append(entry)
            # Exceptions
            elif 'EXCEPTION' in upper and ('THROWN' in upper or 'CAUGHT' in upper or ':' in line):
                errors['exceptions'].append(entry)
            # DBG_WARN warnings
            elif 'DBG_WARN' in upper:
                errors['warnings'].append(entry)
            # Other warnings - be more specific
            elif re.search(r'\bWARNING\b', line, re.IGNORECASE):
                errors['warnings'].append(entry)
            # Errors
            elif 'DBG_ERROR' in upper:
                errors['errors'].append(entry)
            elif re.search(r'Error\s*(?:posted|:)', line, re.IGNORECASE):
                errors['errors'].append(entry)
            # DBG_INFO - only if specifically DBG_INFO
            elif 'DBG_INFO' in upper:
                errors['info'].append(entry)

        # === XML PATTERN MATCHING ===
        # Also surface lines that match the XML pattern file in the Fault Log
        if self.patterns:
            content = '\n'.join(lines)
            max_patterns = min(len(self.patterns), 100)
            for pattern in self.patterns[:max_patterns]:
                try:
                    if pattern['search_type'] == 'regex':
                        regex = re.compile(pattern['text'], re.IGNORECASE | re.MULTILINE)
                    elif pattern['search_type'] == 'escaped':
                        escaped_text = pattern['text'].replace('\\r\\n', '\r\n').replace('\\n', '\n')
                        regex = re.compile(re.escape(escaped_text), re.IGNORECASE)
                    else:
                        regex = re.compile(re.escape(pattern['text']), re.IGNORECASE)

                    match_count = 0
                    for match in regex.finditer(content):
                        line_num = content[:match.start()].count('\n') + 1
                        entry = {'line': line_num, 'text': match.group(0)[:200]}
                        color = pattern.get('color', '')
                        if color in ('red', 'darkRed'):
                            errors['fatal'].append(entry)
                        elif color in ('purple', 'deepPurple', 'pink', 'litePink'):
                            errors['errors'].append(entry)
                        else:
                            errors['warnings'].append(entry)
                        match_count += 1
                        if match_count >= 5:
                            break
                except re.error:
                    continue

        # Deduplicate each list to avoid showing the same line twice
        for key in errors:
            seen = set()
            unique = []
            for e in errors[key]:
                k = (e['line'], e['text'][:50])
                if k not in seen:
                    seen.add(k)
                    unique.append(e)
            errors[key] = unique

        return errors

    def _extract_performance(self, lines: List[str]) -> Dict[str, Any]:
        """Extract performance metrics."""
        perf = {
            'memory_usage': [],
            'load_times': [],
            'save_times': [],
            'sync_times': [],
            'regeneration_times': []
        }

        for i, line in enumerate(lines):
            # Look for memory stats
            # Pattern: RAM: Avail 35501 MB, Used 86 MB
            m = re.search(r"RAM:\s*Avail\s+(\d+)\s*MB,\s*Used\s+(\d+)\s*MB", line)
            if m:
                perf['memory_usage'].append({
                    'line': i + 1,
                    'available': int(m.group(1)),
                    'used': int(m.group(2)),
                    'unit': 'MB'
                })

        return perf

    def _extract_workflow(self, lines: List[str]) -> Dict[str, List[Dict]]:
        """Extract workflow events like sync, save, open operations."""
        workflow = {
            'file_operations': [],
            'sync_operations': [],
            'link_operations': [],
            'print_operations': [],
            'export_operations': [],
            'commands': [],
            'longest_delays': []  # NEW: Track longest delays
        }

        # Track timestamps for delay calculation
        timeline_events = []

        for i, line in enumerate(lines):
            clean = line.strip()
            upper = clean.upper()

            # Skip empty or very short lines
            if len(clean) < 10:
                continue

            entry = {'line': i + 1, 'text': clean[:200]}
            
            # Extract timestamp if present (strip milliseconds)
            ts_match = re.search(r"'[CE]\s+(\d{1,2}-\w{3}-\d{4}\s+\d{2}:\d{2}:\d{2})", line)
            if ts_match:
                timestamp = ts_match.group(1)
                timeline_events.append((i + 1, timestamp, clean[:100]))

            # Sync operations - specific patterns
            if '>STC' in line or '<STC' in line:
                workflow['sync_operations'].append(entry)
            elif 'ID_FILE_SAVE_TO_MASTER' in upper:
                workflow['sync_operations'].append(entry)
            elif 'SYNCHRONIZE WITH CENTRAL' in upper:
                workflow['sync_operations'].append(entry)

            # File operations
            if 'JRN.DATA' in upper and ('FILE NAME' in upper or 'MRUFILENAME' in upper):
                workflow['file_operations'].append(entry)
            elif 'ID_REVIT_FILE_OPEN' in upper or 'ID_REVIT_FILE_SAVE' in upper:
                workflow['file_operations'].append(entry)

            # Link operations
            if 'OPENLINK' in upper or 'LOAD LINKED FILE' in upper:
                workflow['link_operations'].append(entry)
            elif '.RVT' in upper and 'LINK' in upper:
                workflow['link_operations'].append(entry)

            # Export operations
            if 'EXPORT' in upper and any(fmt in upper for fmt in ['DWG', 'IFC', 'NWC', 'FBX', 'PDF']):
                workflow['export_operations'].append(entry)

            # Print operations
            if 'PRINT' in upper and ('DIALOG' in upper or 'COMMAND' in upper):
                workflow['print_operations'].append(entry)

            # Commands
            m = re.search(r'Jrn\.Command\s+"[^"]*"\s*,\s*"([^"]+)"', line, re.IGNORECASE)
            if m:
                workflow['commands'].append({
                    'line': i + 1,
                    'command': m.group(1)[:100]
                })

        # Calculate longest delays between consecutive events
        delays = []
        
        # Limit timeline events to avoid performance issues
        max_events = min(len(timeline_events), 2000)  # Process max 2000 events
        limited_events = timeline_events[:max_events]
        
        for i in range(1, len(limited_events)):
            prev_line, prev_ts, prev_action = limited_events[i-1]
            curr_line, curr_ts, curr_action = limited_events[i]
            
            try:
                prev_time = self._parse_timestamp(prev_ts)
                curr_time = self._parse_timestamp(curr_ts)
                
                if prev_time and curr_time:
                    delay_seconds = (curr_time - prev_time).total_seconds()
                    
                    # Mark delays over 5 seconds as significant
                    if delay_seconds >= 5:
                        delays.append({
                            'duration_seconds': int(delay_seconds),
                            'duration_formatted': self._format_duration(delay_seconds),
                            'from_line': prev_line,
                            'to_line': curr_line,
                            'from_action': prev_action,
                            'to_action': curr_action,
                            'timestamp': prev_ts
                        })
                        
                        # Stop early if we have enough delays
                        if len(delays) >= 50:
                            break
            except:
                pass
        
        # Sort by duration (longest first) and keep top 20
        delays.sort(key=lambda x: x['duration_seconds'], reverse=True)
        workflow['longest_delays'] = delays[:20]

        return workflow
    
    def _extract_timeline(self, lines: List[str]) -> List[Dict[str, Any]]:
        """STRICT: Extract ONLY requested 6 event types."""
        timeline = []
        content = '\n'.join(lines)
        
        # PERFORMANCE: Pre-calculate cumulative line positions (O(n) instead of O(n²))
        line_positions = [0]
        for line in lines:
            line_positions.append(line_positions[-1] + len(line) + 1)
        
        # Build model position tracking
        model_positions = []  # List of (position, model_name)
        
        # Pattern 1: Jrn.Data with continuation (multi-line)
        for m in re.finditer(r'Jrn\.Data\s+_\s*[\r\n]+\s*"(?:File Name|MRUFileName)"\s*,\s*"([^"]+\.rvt)"', content, re.IGNORECASE):
            filename = m.group(1).split('\\')[-1].split('/')[-1]
            if filename:
                model_positions.append((m.start(), filename))
        
        # Pattern 2: Cloud models
        for m in re.finditer(r'BIM 360://[^/]+/([^"]+\.rvt)', content, re.IGNORECASE):
            filename = m.group(1)
            if filename:
                model_positions.append((m.start(), filename))
        
        # Sort by position
        model_positions.sort(key=lambda x: x[0])
        
        def get_current_model(position: int) -> str:
            """Get the current model name at a given position in the file."""
            current = ''
            for pos, name in model_positions:
                if pos <= position:
                    current = name
                else:
                    break
            if current:
               match = re.search(r'([^\\\/\s]+\.rvt)', current, re.IGNORECASE)
               if match:
                   return match.group(1)

            return ''
        
        # PERFORMANCE: Limit timeline events to avoid processing huge files
        max_timeline_events = 200
        events_found = 0
        
        for i, line in enumerate(lines):
            # Stop if we have enough events
            if events_found >= max_timeline_events:
                break
                
            event = None
            timestamp = None
            position = line_positions[i]  # O(1) lookup instead of O(n) sum
            
            # Extract timestamp from line (without microseconds)
            ts_match = re.search(r'(\d{1,2}-\w{3}-\d{4}\s+\d{2}:\d{2}:\d{2})', line)
            if ts_match:
                timestamp = ts_match.group(1)
            else:
                # If no timestamp on current line, look at previous 3 lines
                for j in range(max(0, i-3), i):
                    ts_match = re.search(r'(\d{1,2}-\w{3}-\d{4}\s+\d{2}:\d{2}:\d{2})', lines[j])
                    if ts_match:
                        timestamp = ts_match.group(1)
                        break
            
            # === USER REQUESTED EVENTS ONLY ===
            
            # 1. Session Started
            if 'Jrn.Directive "Username"' in line:
                event = {
                    'type': 'session_start',
                    'description': 'Session Started',
                    'timestamp': timestamp,
                    'line': i + 1
                }
            
            # 2. Model Opened (Model Name) - ONLY actual file opens, not linked models
            elif 'Jrn.Data' in line and i + 1 < len(lines):

                 next_line = lines[i + 1]

                 if 'File Name' in next_line:

                    search_area = '\n'.join(lines[i:i+4])
                    match = re.search(r'([^\\\/\s]+\.rvt)', search_area, re.IGNORECASE)

                    model_name = match.group(1) if match else ''
 
                    if model_name and not self._is_temp_file(model_name):
                        event = {
                           'type': 'model_open',
                           'description': f'Model Opened ({model_name})',
                           'timestamp': timestamp,
                           'line': i + 1,
                           'model_name': model_name
                        }
            # 3. File Saved (Model Name) - Only when we have a valid model
            elif 'ID_REVIT_FILE_SAVE' in line and 'SAVE_AS' not in line:
                model_name = get_current_model(position)
                if model_name:  # Only add if we have a valid model
                    event = {
                        'type': 'save',
                        'description': f'File Saved ({model_name})' if model_name else 'File Saved',
                        'timestamp': timestamp,
                        'line': i + 1,
                        'model_name': model_name
                    }
            
            # 4. Sync with Central (Model Name) - Only actual sync operations
            elif 'ID_FILE_SAVE_TO_MASTER' in line:
                model_name = get_current_model(position)
                if model_name:  # Only add if we have a valid model
                    event = {
                        'type': 'sync',
                        'description': f'Sync with Central ({model_name})' if model_name else 'Sync with Central',
                        'timestamp': timestamp,
                        'line': i + 1,
                        'model_name': model_name
                    }
            
            # 5. Model Closed (Model Name) - Only when we have a valid model
            elif 'ID_REVIT_FILE_CLOSE' in line or 'Jrn.CloseDocumentFile' in line:

                 search_area = '\n'.join(lines[max(0, i-5):i+5])
                 match = re.search(r'([^\\\/\s]+\.rvt)', search_area, re.IGNORECASE)

                 model_name = match.group(1) if match else ''
    
                 if model_name:
                    event = {
                        'type': 'model_close',
                        'description': f'Model Closed ({model_name})',
                        'timestamp': timestamp,
                        'line': i + 1,
                        'model_name': model_name
        }

            # 6. Error that caused the crash - Name of the Error
            if event:
                timeline.append(event)
                events_found += 1
        
        return timeline
    
    def _is_temp_file(self, filename: str) -> bool:
        """Check if filename looks like a temp/cache file (GUID or hash)."""
        if not filename:
            return True
        
        # Remove .rvt extension for checking
        name = filename.lower().replace('.rvt', '')
        
        # Check for GUID patterns
        if '{' in filename or '}' in filename:
            return True
        
        # Check if starts with GUID pattern (8-4-4-4-12 hex digits)
        if re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', name):
            return True
        
        # Check if mostly hexadecimal (cache file)
        if re.match(r'^[0-9a-f]{32,}', name.replace('-', '')):
            return True
        
        return False # Corrected from `return Falsetimeline`
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format."""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"

    def _extract_addins(self, lines: List[str], content: str) -> Dict[str, Any]:
        """Extract add-in information - plugin names and versions."""
        addins = {
            'autodesk': [],
            'third_party': [],
            'failed': []
        }

        seen_plugins = set()
        pyrevit_detected = False
        
        # Generic menu items to exclude (these are not plugin names)
        excluded_items = {
            # Generic UI elements
            'help', 'about', 'toggle', 'settings', 'options', 'preferences',
            'close', 'exit', 'open', 'save', 'new', 'delete', 'remove',
            'add', 'edit', 'view', 'tools', 'window', 'file', 'home',
            'untangle', 'transmit', 'grow', 'auto', 'section box',
            
            # Common tab/panel names
            'modify', 'annotate', 'structure', 'systems', 'insert', 'manage',
            'collaborate', 'massing', 'site', 'analyze', 'architecture',
            'create', 'model', 'place', 'draw', 'component', 'datum',
            'work plane', 'measure', 'project', 'selection', 'clipboard',
            
            # Common button names
            'properties', 'filter', 'visibility', 'graphics', 'display',
            'render', 'view', 'sheet', 'schedule', 'legend', 'detail',
            'section', 'elevation', 'plan', 'callout', 'scope box',
            
            # PyRevit common UI items
            'extensions', 'commands', 'scripts', 'config', 'update',
            
            # Additional common UI terms
            'panel', 'tab', 'ribbon', 'toolbar', 'menu', 'dialog',
            'browser', 'navigator', 'explorer', 'manager', 'editor'
        }
        
        def is_likely_ui_element(name):
            """Check if name is likely a UI element rather than a plugin."""
            name_lower = name.lower().strip()
            
            # Too short (likely a button/tab)
            if len(name_lower) < 4:
                return True
            
            # Common UI patterns
            ui_patterns = [
                'panel', 'tab', 'button', 'menu', 'ribbon',
                'toolbar', 'command', 'tool', 'dialog', 'bar'
            ]
            if any(pattern in name_lower for pattern in ui_patterns):
                return True
            
            # Single word without version (likely UI element)
            if ' ' not in name and not any(char.isdigit() for char in name):
                if len(name) < 15:  # Short single words are usually UI
                    return True
            
            return False
        
        # Known Autodesk add-ins whitelist
        AUTODESK_ADDINS = {
            'revit model review', 'a360', 'collaboration for revit',
            'insight', 'formit converter', 'dynamo', 'structural analysis',
            'energy analysis', 'robot structural analysis', 'navisworks',
            'bim 360', 'docs', 'glue', 'point cloud', 'green building studio',
            'autodesk', 'adsk'
        }

        # === METHOD 1: Extract from External Application entries ===
        # Pattern: API_SUCCESS { Starting External DB Application: Name, Class: xxx, Vendor : ADSK
        # FIXED: Capture full multi-word names by using [^,]+ instead of limiting to single words
        for m in re.finditer(
            r"Starting External (?:DB )?Application:\s*([^,]+),.*?Vendor\s*:\s*(\w+)",
            content, re.IGNORECASE
        ):
            name = m.group(1).strip()[:100]  # Capture full name, limit to 100 chars
            vendor = m.group(2).strip().upper()

            # Check if this is PyRevit
            if 'pyrevit' in name.lower():
                pyrevit_detected = True

            # Filter out UI elements and excluded items
            if (name and name not in seen_plugins and 
                name.lower() not in excluded_items and 
                not is_likely_ui_element(name)):
                
                seen_plugins.add(name)
                line_num = content[:m.start()].count('\n') + 1
                
                # Try to find version info nearby (search in next 1000 chars)
                version = ''
                context = content[m.start():m.start()+1000]
                version_match = re.search(r'version[:\s]+([0-9.]+)', context, re.IGNORECASE)
                if version_match:
                    version = version_match.group(1)
                
                entry = {'line': line_num, 'name': name, 'version': version}

                # IMPROVED: Better Autodesk classification with whitelist
                is_autodesk = False
                name_lower = name.lower()
                
                # Check whitelist first (highest priority)
                if any(known in name_lower for known in AUTODESK_ADDINS):
                    is_autodesk = True
                # Then check vendor tag
                elif vendor in ['ADSK', 'RPCA', 'AUTODESK']:
                    is_autodesk = True
                
                # PyRevit always goes to third-party
                if 'pyrevit' in name_lower:
                    is_autodesk = False
                
                if is_autodesk:
                    addins['autodesk'].append(entry)
                else:
                    addins['third_party'].append(entry)

        # === METHOD 2: Extract plugin names from assembly paths ===
        # Pattern: assembly: C:\...\PluginName.dll or assembly: PluginName
        plugin_assemblies = {}  # Track assembly -> (plugin name, version) mapping
        
        for m in re.finditer(
            r"assembly:\s*([^,\}\s]+(?:\.dll)?)",
            content, re.IGNORECASE
        ):
            assembly_path = m.group(1).strip()
            
            # Check if this is PyRevit
            if 'pyrevit' in assembly_path.lower():
                pyrevit_detected = True
            
            # IMPROVED: Skip Autodesk's core Revit assemblies (not add-ins)
            if 'Autodesk\\Revit\\' in assembly_path and '\\AddIns\\' not in assembly_path:
                continue
            
            # Extract plugin name from path - FIXED to capture multi-word names
            # Example: C:\ProgramData\Autodesk\Revit\Addins\2024\My Plugin Name\MyPlugin.dll -> My Plugin Name
            if '\\' in assembly_path or '/' in assembly_path:
                # Get the directory name (often the plugin name for multi-word plugins)
                path_parts = assembly_path.replace('/', '\\').split('\\')
                # Try to get plugin name from directory or filename
                plugin_name = path_parts[-2] if len(path_parts) > 1 and path_parts[-2] not in ['Addins', 'AddIns', '2024', '2023', '2022', '2021', '2020'] else path_parts[-1]
                plugin_name = plugin_name.replace('.dll', '').replace('.addin', '')
            else:
                plugin_name = assembly_path.replace('.dll', '').replace('.addin', '')
            
            # Clean up the name
            plugin_name = plugin_name.strip()
            
            # Try to extract version from assembly path or nearby context
            version = ''
            
            # Method 1: Version in path (e.g., MyPlugin.2.5.0.dll or MyPlugin_v2.5 or MyPlugin-1.0.0)
            version_in_path = re.search(r'[._-]v?(\d+\.\d+(?:\.\d+)?(?:\.\d+)?)', assembly_path)
            if version_in_path:
                version = version_in_path.group(1)
            
            # Method 2: Search nearby context for version info
            if not version:
                context = content[max(0, m.start()-500):m.start()+1000]
                version_match = re.search(r'version[:\s]+([0-9.]+)', context, re.IGNORECASE)
                if version_match:
                    version = version_match.group(1)
            
            # Method 3: Look for AssemblyVersion attribute
            if not version:
                context = content[max(0, m.start()-200):m.start()+500]
                assembly_version = re.search(r'AssemblyVersion[:\s\(]+["\']?([0-9.]+)', context, re.IGNORECASE)
                if assembly_version:
                    version = assembly_version.group(1)
            
            # Skip if it's a generic menu item, too short, or UI element
            if (plugin_name.lower() not in excluded_items and 
                len(plugin_name) > 2 and 
                plugin_name not in seen_plugins and
                not is_likely_ui_element(plugin_name)):
                
                plugin_assemblies[assembly_path] = (plugin_name, version)

        # Add unique plugins from assemblies
        for assembly_path, (plugin_name, version) in plugin_assemblies.items():
            if plugin_name not in seen_plugins:
                seen_plugins.add(plugin_name)
                # Find line number
                match_pos = content.find(f'assembly: {assembly_path}')
                if match_pos != -1:
                    line_num = content[:match_pos].count('\n') + 1
                else:
                    line_num = 0
                
                # IMPROVED: Better classification logic with whitelist
                is_autodesk = False
                plugin_name_lower = plugin_name.lower()
                
                # Check whitelist first (highest priority)
                if any(known in plugin_name_lower for known in AUTODESK_ADDINS):
                    is_autodesk = True
                # Only Autodesk-owned paths OUTSIDE the shared AddIns folder
                elif 'Autodesk\\Revit\\' in assembly_path and '\\AddIns\\' not in assembly_path:
                    is_autodesk = True
                # ADSK in path is a reliable Autodesk vendor indicator
                elif 'ADSK' in assembly_path:
                    is_autodesk = True
                
                # PyRevit and other third-party plugins go to third_party
                if 'pyrevit' in plugin_name_lower or 'pyrevit' in assembly_path.lower():
                    is_autodesk = False
                
                entry = {'line': line_num, 'name': plugin_name, 'version': version}
                
                if is_autodesk:
                    addins['autodesk'].append(entry)
                else:
                    addins['third_party'].append(entry)

        # === METHOD 3: Look for add-in failures ===
        for i, line in enumerate(lines):
            upper = line.upper()
            if ('ADDIN' in upper or 'ADD-IN' in upper) and ('FAIL' in upper or 'ERROR' in upper or 'COULD NOT' in upper):
                # Extract name if possible - FIXED to capture full names
                m = re.search(r'application[:\s]+([^,\n]+)', line, re.IGNORECASE)
                name = m.group(1).strip()[:100] if m else line.strip()[:100]
                
                # Clean up the name
                name = name.replace('"', '').replace("'", '').strip()
                
                if name and name not in seen_plugins and len(name) > 2 and name.lower() not in excluded_items:
                    seen_plugins.add(name)
                    addins['failed'].append({'line': i + 1, 'name': name, 'version': ''})

        # === METHOD 4: Extract PyRevit plugins if PyRevit is detected ===
        # NEW: Create hierarchical structure with PyRevitLoader as parent
        pyrevit_plugins = []
        pyrevit_loader_info = None
        
        if pyrevit_detected:
            # Look for PyRevit extension loading patterns
            # Pattern 1: Extension loaded: ExtensionName
            for m in re.finditer(r'(?:Extension|extension)\s+(?:loaded|Loading):\s*([^\n\r,]+)', content, re.IGNORECASE):
                plugin_name = m.group(1).strip()
                if plugin_name and len(plugin_name) > 2 and plugin_name not in seen_plugins:
                    line_num = content[:m.start()].count('\n') + 1
                    seen_plugins.add(plugin_name)
                    
                    # Try to find version info nearby
                    version = ''
                    context = content[m.start():m.start()+500]
                    version_match = re.search(r'version[:\s]+([0-9.]+)', context, re.IGNORECASE)
                    if version_match:
                        version = version_match.group(1)
                    
                    # Add to pyrevit_plugins list
                    pyrevit_plugins.append({
                        'line': line_num,
                        'name': plugin_name,
                        'version': version
                    })
            
            # Pattern 2: Look for pyRevit command execution
            for m in re.finditer(r'pyRevit[^%]*%([A-Za-z0-9_\s]+)', content):
                plugin_name = m.group(1).strip()
                if plugin_name and len(plugin_name) > 2 and plugin_name.lower() not in excluded_items:
                    if plugin_name not in seen_plugins:
                        seen_plugins.add(plugin_name)
                        line_num = content[:m.start()].count('\n') + 1
                        pyrevit_plugins.append({
                            'line': line_num,
                            'name': plugin_name,
                            'version': ''
                        })
            
            # Pattern 3: Look for assembly paths containing extension names
            for m in re.finditer(r'pyRevit[/\\]Extensions[/\\]([^/\\]+)[/\\]', content, re.IGNORECASE):
                extension_name = m.group(1).strip()
                if extension_name and len(extension_name) > 2 and extension_name not in seen_plugins:
                    seen_plugins.add(extension_name)
                    line_num = content[:m.start()].count('\n') + 1
                    
                    # Try to find version
                    version = ''
                    context = content[m.start():m.start()+1000]
                    version_match = re.search(r'version[:\s]+([0-9.]+)', context, re.IGNORECASE)
                    if version_match:
                        version = version_match.group(1)
                    
                    pyrevit_plugins.append({
                        'line': line_num,
                        'name': extension_name,
                        'version': version
                    })
            
            # Find PyRevitLoader info from third_party list
            for i, addon in enumerate(addins['third_party']):
                if 'pyrevit' in addon['name'].lower():
                    pyrevit_loader_info = addon.copy()
                    # Remove from third_party as we'll add it back with children
                    addins['third_party'].pop(i)
                    break
            
            # If PyRevitLoader found, add it with children
            if pyrevit_loader_info:
                pyrevit_loader_info['children'] = pyrevit_plugins
                pyrevit_loader_info['is_parent'] = True
                addins['third_party'].insert(0, pyrevit_loader_info)
            elif pyrevit_plugins:
                # If no PyRevitLoader found but plugins exist, create a parent entry
                addins['third_party'].insert(0, {
                    'line': 0,
                    'name': 'PyRevitLoader',
                    'version': '',
                    'children': pyrevit_plugins,
                    'is_parent': True
                })

        return addins

    def _extract_kb_articles(self, lines: List[str], content: str) -> List[Dict[str, Any]]:

        
        # Generic menu items to exclude (these are not plugin names)
        excluded_items = {
            'help', 'about', 'toggle', 'settings', 'options', 'preferences',
            'close', 'exit', 'open', 'save', 'new', 'delete', 'remove',
            'add', 'edit', 'view', 'tools', 'window', 'file', 'home',
            'untangle', 'transmit', 'grow', 'auto', 'section box'
        }

        # === METHOD 1: Extract from External Application entries ===
        # Pattern: API_SUCCESS { Starting External DB Application: Name, Class: xxx, Vendor : ADSK
        for m in re.finditer(
            r"Starting External (?:DB )?Application:\s*([^,]+),.*?Vendor\s*:\s*(\w+)",
            content, re.IGNORECASE
        ):
            name = m.group(1).strip()[:100]
            vendor = m.group(2).strip().upper()

            # Check if this is PyRevit
            if 'pyrevit' in name.lower():
                pyrevit_detected = True

            if name and name not in seen_plugins:
                seen_plugins.add(name)
                line_num = content[:m.start()].count('\n') + 1
                
                # Try to find version info nearby (search in next 1000 chars)
                version = ''
                context = content[m.start():m.start()+1000]
                version_match = re.search(r'version[:\s]+([0-9.]+)', context, re.IGNORECASE)
                if version_match:
                    version = version_match.group(1)
                
                entry = {'line': line_num, 'name': name, 'version': version}

                if vendor in ['ADSK', 'RPCA', 'AUTODESK']:
                    addins['autodesk'].append(entry)
                else:
                    addins['third_party'].append(entry)

        # === METHOD 2: Extract plugin names from assembly paths ===
        # Pattern: assembly: C:\...\PluginName.dll or assembly: PluginName
        plugin_assemblies = {}  # Track assembly -> (plugin name, version) mapping
        
        for m in re.finditer(
            r"assembly:\s*([^,\}\s]+(?:\.dll)?)",
            content, re.IGNORECASE
        ):
            assembly_path = m.group(1).strip()
            
            # Check if this is PyRevit
            if 'pyrevit' in assembly_path.lower():
                pyrevit_detected = True
            
            # Skip Autodesk's own assemblies
            if 'Autodesk\\Revit\\' in assembly_path and '\\AddIns\\' in assembly_path:
                continue
            
            # Extract plugin name from path
            # Example: C:\ProgramData\Autodesk\Revit\Addins\2024\MyPlugin\MyPlugin.dll -> MyPlugin
            if '\\' in assembly_path or '/' in assembly_path:
                plugin_name = assembly_path.split('\\')[-1].split('/')[-1]
                plugin_name = plugin_name.replace('.dll', '').replace('.addin', '')
            else:
                plugin_name = assembly_path.replace('.dll', '').replace('.addin', '')
            
            # Clean up the name
            plugin_name = plugin_name.strip()
            
            # Try to extract version from assembly path or nearby context
            version = ''
            
            # Method 1: Version in path (e.g., MyPlugin.2.5.0.dll or MyPlugin_v2.5 or MyPlugin-1.0.0)
            version_in_path = re.search(r'[._-]v?(\d+\.\d+(?:\.\d+)?(?:\.\d+)?)', assembly_path)
            if version_in_path:
                version = version_in_path.group(1)
            
            # Method 2: Search nearby context for version info
            if not version:
                context = content[max(0, m.start()-500):m.start()+1000]
                version_match = re.search(r'version[:\s]+([0-9.]+)', context, re.IGNORECASE)
                if version_match:
                    version = version_match.group(1)
            
            # Method 3: Look for AssemblyVersion attribute
            if not version:
                context = content[max(0, m.start()-200):m.start()+500]
                assembly_version = re.search(r'AssemblyVersion[:\s\(]+["\']?([0-9.]+)', context, re.IGNORECASE)
                if assembly_version:
                    version = assembly_version.group(1)
            
            # Skip if it's a generic menu item or too short
            if (plugin_name.lower() not in excluded_items and 
                len(plugin_name) > 2 and 
                plugin_name not in seen_plugins):
                
                plugin_assemblies[assembly_path] = (plugin_name, version)

        # Add unique plugins from assemblies to third_party
        for assembly_path, (plugin_name, version) in plugin_assemblies.items():
            if plugin_name not in seen_plugins:
                seen_plugins.add(plugin_name)
                # Find line number
                match_pos = content.find(f'assembly: {assembly_path}')
                if match_pos != -1:
                    line_num = content[:match_pos].count('\n') + 1
                else:
                    line_num = 0
                
                # Determine if Autodesk or third-party based on path
                is_autodesk = ('Autodesk' in assembly_path or 
                              'ADSK' in assembly_path or
                              'Revit' in assembly_path)
                
                entry = {'line': line_num, 'name': plugin_name, 'version': version}
                
                if is_autodesk:
                    addins['autodesk'].append(entry)
                else:
                    addins['third_party'].append(entry)

        # === METHOD 3: Look for add-in failures ===
        for i, line in enumerate(lines):
            upper = line.upper()
            if ('ADDIN' in upper or 'ADD-IN' in upper) and ('FAIL' in upper or 'ERROR' in upper or 'COULD NOT' in upper):
                # Extract name if possible
                m = re.search(r'application[:\s]+([^,\n]+)', line, re.IGNORECASE)
                name = m.group(1).strip()[:100] if m else line.strip()[:100]
                
                # Clean up the name
                name = name.replace('"', '').replace("'", '').strip()
                
                if name and name not in seen_plugins and len(name) > 2:
                    seen_plugins.add(name)
                    addins['failed'].append({'line': i + 1, 'name': name, 'version': ''})

        # === METHOD 4: Extract PyRevit plugins if PyRevit is detected ===
        if pyrevit_detected:
            # Look for PyRevit extension loading patterns
            # Pattern 1: Extension loaded: ExtensionName
            for m in re.finditer(r'(?:Extension|extension)\s+(?:loaded|Loading):\s*([^\n\r,]+)', content, re.IGNORECASE):
                plugin_name = m.group(1).strip()
                if plugin_name and len(plugin_name) > 2:
                    line_num = content[:m.start()].count('\n') + 1
                    
                    # Try to find version info nearby
                    version = ''
                    # Look for version pattern in next 500 characters
                    context = content[m.start():m.start()+500]
                    version_match = re.search(r'version[:\s]+([0-9.]+)', context, re.IGNORECASE)
                    if version_match:
                        version = version_match.group(1)
                    
                    addins['pyrevit_plugins'].append({
                        'line': line_num,
                        'name': plugin_name,
                        'version': version
                    })
            
            # Pattern 2: Look for pyRevit command execution which might indicate loaded extensions
            # Pattern: Jrn.RibbonEvent "Execute external command:CustomCtrl_%CustomCtrl_%pyRevit%...%CBOX
            for m in re.finditer(r'pyRevit[^%]*%([A-Za-z0-9_]+)', content):
                plugin_name = m.group(1).strip()
                if plugin_name and len(plugin_name) > 2 and plugin_name.lower() not in excluded_items:
                    # Check if already added
                    if not any(p['name'] == plugin_name for p in addins['pyrevit_plugins']):
                        line_num = content[:m.start()].count('\n') + 1
                        addins['pyrevit_plugins'].append({
                            'line': line_num,
                            'name': plugin_name,
                            'version': ''
                        })
            
            # Pattern 3: Look for assembly paths containing extension names
            for m in re.finditer(r'pyRevit[/\\]Extensions[/\\]([^/\\]+)[/\\]', content, re.IGNORECASE):
                extension_name = m.group(1).strip()
                if extension_name and len(extension_name) > 2:
                    # Check if already added
                    if not any(p['name'] == extension_name for p in addins['pyrevit_plugins']):
                        line_num = content[:m.start()].count('\n') + 1
                        
                        # Try to find version
                        version = ''
                        context = content[m.start():m.start()+1000]
                        version_match = re.search(r'version[:\s]+([0-9.]+)', context, re.IGNORECASE)
                        if version_match:
                            version = version_match.group(1)
                        
                        addins['pyrevit_plugins'].append({
                            'line': line_num,
                            'name': extension_name,
                            'version': version
                        })

        return addins



    def _match_known_issues(self, lines: List[str]) -> List[Dict[str, Any]]:
        """Match journal content against known issue patterns from XML."""
        matches = []
        content = '\n'.join(lines)
        
        # OPTIMIZATION: Limit patterns to avoid performance issues
        max_patterns = min(len(self.patterns), 100)  # Process max 100 patterns
        limited_patterns = self.patterns[:max_patterns]

        for pattern in limited_patterns:
            try:
                if pattern['search_type'] == 'regex':
                    regex = re.compile(pattern['text'], re.IGNORECASE | re.MULTILINE)
                elif pattern['search_type'] == 'escaped':
                    # Handle escaped patterns (literal newlines, etc.)
                    escaped_text = pattern['text'].replace('\\r\\n', '\r\n').replace('\\n', '\n')
                    regex = re.compile(re.escape(escaped_text), re.IGNORECASE)
                else:
                    # Plain text search
                    regex = re.compile(re.escape(pattern['text']), re.IGNORECASE)

                # OPTIMIZATION: Limit matches per pattern
                match_count = 0
                for match in regex.finditer(content):
                    # Find line number
                    line_num = content[:match.start()].count('\n') + 1

                    matches.append({
                        'pattern': pattern['text'][:100],
                        'line': line_num,
                        'group': pattern['group'],
                        'severity': self._color_to_severity(pattern['color']),
                        'kb_article': pattern['comment'] if pattern['comment'].startswith('http') else '',
                        'description': pattern['comment'] if not pattern['comment'].startswith('http') else '',
                        'matched_text': match.group(0)[:200]
                    })
                    
                    match_count += 1
                    # Stop after 5 matches per pattern
                    if match_count >= 5:
                        break
                
                # OPTIMIZATION: Stop early if we have enough total matches
                if len(matches) >= 50:
                    break
                    
            except re.error:
                continue

        # Remove duplicates - keep only one instance per unique issue pattern
        seen = set()
        unique_matches = []
        for m in matches:
            key = m['pattern']  # Deduplicate by pattern only (one reference per issue type)
            if key not in seen:
                seen.add(key)
                unique_matches.append(m)

        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3, 'info': 4}
        unique_matches.sort(key=lambda x: (severity_order.get(x['severity'], 5), x['line']))

        return unique_matches

    def _color_to_severity(self, color: str) -> str:
        """Convert XML color to severity level."""
        color_map = {
            'red': 'critical',
            'darkRed': 'critical',
            'purple': 'high',
            'deepPurple': 'high',
            'pink': 'medium',
            'litePink': 'medium',
            'brown': 'low',
            'beige': 'low',
            'blueGreen': 'info',
            'liteGreen': 'info',
            'darkGreen': 'info',
            'gray': 'info',
            'liteGrey': 'info'
        }
        return color_map.get(color, 'info')

    def _find_nearest_timestamp(self, content: str, position: int) -> str:
        """Find the nearest timestamp before the given position."""
        # Look backwards for a timestamp pattern like 'C or 'E followed by timestamp
        search_area = content[:position]
        # Find all timestamps in the area before position
        timestamps = list(re.finditer(
            r"'[CE]\s+(\d{1,2}-\w{3}-\d{4}\s+\d{2}:\d{2}:\d{2}\.\d+)",
            search_area
        ))
        if timestamps:
            # Return the last (nearest) timestamp
            return timestamps[-1].group(1)
        return ''

    def _extract_model_name_from_context(self, content: str, position: int, search_range: int = 2000) -> str:
        """Extract the model name from the context around a given position."""
        # Search backwards and forwards from the position
        start = max(0, position - search_range)
        end = min(len(content), position + search_range)
        context = content[start:end]
        
        # Look for .rvt file references
        # Pattern 1: "File Name" or "MRUFileName" with .rvt
        matches = list(re.finditer(r'"(?:File Name|MRUFileName)"\s*,\s*"([^"]*\.rvt)"', context, re.IGNORECASE))
        if matches:
            # Get the closest match to our position
            closest_match = min(matches, key=lambda m: abs((start + m.start()) - position))
            full_path = closest_match.group(1)
            model_name = full_path.split('\\')[-1].split('/')[-1]
            return model_name
        
        # Pattern 2: Direct .rvt file path
        matches = list(re.finditer(r'([^\\/\s]+\.rvt)', context, re.IGNORECASE))
        if matches:
            closest_match = min(matches, key=lambda m: abs((start + m.start()) - position))
            return closest_match.group(1)
        
        return ''

    def _build_timeline(self, lines: List[str], content: str) -> List[Dict[str, Any]]:
        """Build a timeline of significant events with timestamps and model names."""
        timeline = []

        # === SESSION START ===
        m = re.search(r"'C\s+(\d{1,2}-\w{3}-\d{4}\s+\d{2}:\d{2}:\d{2}\.\d+);\s*started recording journal file", content)
        if m:
            line_num = content[:m.start()].count('\n') + 1
            timeline.append({
                "type": "save_as",
                "description": "File Saved",
                "model": model_name,
                "timestamp": timestamp,
                "line": line_no
            })



        # === MODEL OPEN ===
        # Pattern 1: Jrn.Data "File Name" or "MRUFileName" with .rvt
        for m in re.finditer(r'Jrn\.Data\s+_\s*[\r\n]+\s*"(?:File Name|MRUFileName)"\s*,\s*"([^"]+\.rvt)"', content, re.IGNORECASE):
            line_num = content[:m.start()].count('\n') + 1
            filename = m.group(1).split('\\')[-1].split('/')[-1]
            timestamp = self._find_nearest_timestamp(content, m.start())
            if filename:
                timeline.append({
                    'line': line_num,
                    'timestamp': timestamp,
                    'type': 'model_open',
                    'description': f'Model Opened ({filename})',
                    'text': filename[:100]
                })

        # Pattern 2: ModelBrowserIsOpenChangedEvent:Open (model browser open)
        for m in re.finditer(r'ModelBrowserIsOpenChangedEvent:Open', content):
            line_num = content[:m.start()].count('\n') + 1
            timestamp = self._find_nearest_timestamp(content, m.start())
            model_name = self._extract_model_name_from_context(content, m.start())
            description = f'Model Browser Opened ({model_name})' if model_name else 'Model Browser Opened'
            timeline.append({
                'line': line_num,
                'timestamp': timestamp,
                'type': 'model_open',
                'description': description
            })

        # === SAVE OPERATIONS ===
        # Save command
        for m in re.finditer(r'Jrn\.Command[^,]*,\s*"[^"]*,\s*ID_REVIT_FILE_SAVE"', content):
            line_num = content[:m.start()].count('\n') + 1
            timestamp = self._find_nearest_timestamp(content, m.start())
            model_name = self._extract_model_name_from_context(content, m.start())
            description = f'File Saved ({model_name})' if model_name else 'File Saved'
            timeline.append({
                'line': line_num,
                'timestamp': timestamp,
                'type': 'save',
                'description': description
            })

        # Save As command
        for m in re.finditer(r'Jrn\.Command[^,]*,\s*"[^"]*,\s*ID_REVIT_FILE_SAVE_AS"', content):
            line_num = content[:m.start()].count('\n') + 1
            timestamp = self._find_nearest_timestamp(content, m.start())
            model_name = self._extract_model_name_from_context(content, m.start())
            description = f'File Saved As ({model_name})' if model_name else 'File Saved As'
            timeline.append({
                'line': line_num,
                'timestamp': timestamp,
                'type': 'save_as',
                'description': description
            })

        # <<<Save Document pattern
        for m in re.finditer(r'<<<Save Document', content):
            line_num = content[:m.start()].count('\n') + 1
            timestamp = self._find_nearest_timestamp(content, m.start())
            model_name = self._extract_model_name_from_context(content, m.start())
            description = f'Document Saved ({model_name})' if model_name else 'Document Saved'
            timeline.append({
                'line': line_num,
                'timestamp': timestamp,
                'type': 'save',
                'description': description
            })

        # === SYNC WITH CENTRAL ===
        # >STC pattern
        for m in re.finditer(r"'[^\n]*>STC[^\n]*", content):
            line_num = content[:m.start()].count('\n') + 1
            timestamp = self._find_nearest_timestamp(content, m.start())
            model_name = self._extract_model_name_from_context(content, m.start())
            description = f'Sync with Central ({model_name})' if model_name else 'Sync with Central'
            timeline.append({
                'line': line_num,
                'timestamp': timestamp,
                'type': 'sync',
                'description': description
            })

        # ID_FILE_SAVE_TO_MASTER command
        for m in re.finditer(r'ID_FILE_SAVE_TO_MASTER', content):
            line_num = content[:m.start()].count('\n') + 1
            timestamp = self._find_nearest_timestamp(content, m.start())
            model_name = self._extract_model_name_from_context(content, m.start())
            description = f'Sync to Central ({model_name})' if model_name else 'Sync to Central'
            timeline.append({
                'line': line_num,
                'timestamp': timestamp,
                'type': 'sync',
                'description': description
            })

        # === RELOAD LATEST ===
        for m in re.finditer(r'Jrn\.Command[^,]*,\s*"[^"]*,\s*ID_WORKSETS_RELOAD_LATEST"', content):
            line_num = content[:m.start()].count('\n') + 1
            timestamp = self._find_nearest_timestamp(content, m.start())
            model_name = self._extract_model_name_from_context(content, m.start())
            description = f'Reload Latest ({model_name})' if model_name else 'Reload Latest'
            timeline.append({
                'line': line_num,
                'timestamp': timestamp,
                'type': 'reload',
                'description': description
            })

        # === DOCUMENT CLOSE ===
        for m in re.finditer(r'\[Jrn\.CloseDocumentFile\]', content):
            line_num = content[:m.start()].count('\n') + 1
            timestamp = self._find_nearest_timestamp(content, m.start())
            model_name = self._extract_model_name_from_context(content, m.start())
            description = f'Document Closed ({model_name})' if model_name else 'Document Closed'
            timeline.append({
                'line': line_num,
                'timestamp': timestamp,
                'type': 'document_close',
                'description': description
            })

        # === REVIT CLOSE ===
        # [Jrn.CloseRevitMainFrame] pattern
        for m in re.finditer(r'\[Jrn\.CloseRevitMainFrame\]', content):
            line_num = content[:m.start()].count('\n') + 1
            timestamp = self._find_nearest_timestamp(content, m.start())
            timeline.append({
                'line': line_num,
                'timestamp': timestamp,
                'type': 'revit_close',
                'description': 'Revit Closing'
            })


        # ID_APP_EXIT command
        for m in re.finditer(r'Jrn\.Command[^,]*,\s*"[^"]*,\s*ID_APP_EXIT"', content):
            line_num = content[:m.start()].count('\n') + 1
            timestamp = self._find_nearest_timestamp(content, m.start())
            timeline.append({
                'line': line_num,
                'timestamp': timestamp,
                'type': 'revit_close',
                'description': 'Application Exit'
            })

        # === FATAL ERRORS ===
        # Exclude "Crash Notify" which is a plugin action, not a real crash
        for m in re.finditer(r'(?:FATAL\s+ERROR|Unrecoverable|TaskDialog_Serious_Error)[^\n]*', content, re.IGNORECASE):
            # Skip if this is just a "Crash Notify" plugin action
            if 'Crash Notify' in m.group(0) or 'CrashNotify' in m.group(0):
                continue
            line_num = content[:m.start()].count('\n') + 1
            timestamp = self._find_nearest_timestamp(content, m.start())
            timeline.append({
                'line': line_num,
                'timestamp': timestamp,
                'type': 'crash',
                'description': 'Fatal Error',
                'text': m.group(0)[:100]
            })

        # === SESSION END ===
        m = re.search(r"'C\s+(\d{1,2}-\w{3}-\d{4}\s+\d{2}:\d{2}:\d{2}\.\d+);\s*finished recording journal file", content)
        if m:
            line_num = content[:m.start()].count('\n') + 1
            timeline.append({
                'line': line_num,
                'timestamp': m.group(1),
                'type': 'session_end',
                'description': 'Session Ended'
            })

        # Sort by line number (chronological order)
        timeline.sort(key=lambda x: x['line'])

        # Remove duplicates based on line number and type
        seen = set()
        unique_timeline = []
        for event in timeline:
            key = (event['line'], event['type'])
            if key not in seen:
                seen.add(key)
                unique_timeline.append(event)

        return unique_timeline

    def _build_summary(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Build summary statistics."""
        errors = result['errors']
        matched = result['kb_articles']
        session = result['session_info']

        return {
            'total_errors': len(errors['fatal']) + len(errors['errors']),
            'total_exceptions': len(errors['exceptions']),
            'session_status': session['session_status'],
            'unsaved_work_duration': session.get('unsaved_work_duration', ''),
            'unsaved_work': session.get('unsaved_work', ''),
            'critical_issues': len([m for m in matched if m['severity'] == 'critical']),
            'high_issues': len([m for m in matched if m['severity'] == 'high']),
            'medium_issues': len([m for m in matched if m['severity'] == 'medium']),
            'models_count': len(session['models_opened']),
            'sync_operations': len(result['workflow']['sync_operations']),
            'addins_count': len(result['addins']['autodesk']) + len(result['addins']['third_party']),
            'failed_addins': len(result['addins']['failed'])
        }


def parse_journal(content: str, xml_pattern_file: Optional[str] = None) -> Dict[str, Any]:
    """Convenience function to parse journal content."""
    parser = JournalParser(xml_pattern_file)
    return parser.parse(content)
