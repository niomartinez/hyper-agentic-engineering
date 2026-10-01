"""Reviewed installation plans, owned fragments, and recoverable transactions."""
import base64
import copy
import difflib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import time
import uuid

from . import __version__, fs, memory, commands
from .packaging import resource, runtime_bytes, runtime_command, SKILL_RESOURCES

BEGIN = '<!-- hyper-agentic-engineering:begin -->'
END = '<!-- hyper-agentic-engineering:end -->'
AGENTS = {'claude', 'codex', 'copilot', 'cowork'}


def encode(data):
    return base64.b64encode(data).decode() if data is not None else None


def decode(value):
    if isinstance(value, dict):
        data = fs.read(value['blob'])
        if data is None or fs.digest(data) != value['sha256']:
            raise fs.Conflict('Recovery snapshot missing or changed; preserve the transaction for inspection')
        return data
    return base64.b64decode(value, validate=True) if value is not None else None


def identity(value):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,79}', value):
        raise fs.Conflict('Identifiers must be 1–80 letters, numbers, dots, underscores or hyphens')
    if value.endswith('.') or value.split('.')[0].upper() in {'CON', 'PRN', 'AUX', 'NUL', *('COM'+str(i) for i in range(1,10)), *('LPT'+str(i) for i in range(1,10))}:
        raise fs.Conflict('Choose a portable identifier without reserved Windows names or a trailing dot')
    return value


def state_path(home, explicit=None):
    return fs.checked(explicit or Path(home) / '.local/state/hyper-agentic-engineering')


def active_transactions(state):
    result = []
    for path in sorted((state / 'transactions').glob('*.json')):
        item = fs.load(path)
        if 'operations' not in item:
            plan = fs.load(state / 'plans' / (item['id'] + '.json'))
            if not plan:
                raise fs.Conflict('Transaction plan missing; preserve recovery state')
            item['operations'] = plan['operations']
            for i, op in enumerate(item['operations']):
                op['applied'] = i in item.get('applied_indices', [])
                op['reverted'] = i in item.get('reverted_indices', [])
        if item['status'] not in {'removed', 'rolled-back'}:
            result.append(item)
    return sorted(result, key=lambda t: t.get('started', 0))



def save_transaction(state, transaction):
    # Snapshots stay in the immutable plan. Only the small recovery cursor changes.
    journal = {k: transaction[k] for k in ['id', 'status', 'started']}
    journal['pending'] = transaction.get('pending')
    journal['applied_indices'] = [i for i, op in enumerate(transaction['operations']) if op.get('applied')]
    journal['reverted_indices'] = [i for i, op in enumerate(transaction['operations']) if op.get('reverted')]
    fs.save(state / 'transactions' / (transaction['id'] + '.json'), journal)


def previous_content(state, path):
    for transaction in reversed(active_transactions(state)):
        for op in reversed(transaction['operations']):
            if op['path'] == str(path) and op.get('applied'):
                return decode(op['after'])
    return None


def operation(path, after, kind='file', **extra):
    path = fs.checked(path)
    before = fs.read(path)
    if before == after:
        return None
    return dict(path=str(path), kind=kind, before=encode(before), after=encode(after),
                before_hash=fs.digest(before), after_hash=fs.digest(after), **extra)


def marked(path, text, state):
    before = fs.read(path) or b''
    current = before.decode('utf-8')
    block = '\n\n' + BEGIN + '\n' + text.strip() + '\n' + END + '\n'
    if BEGIN in current or END in current:
        if current.count(BEGIN) != 1 or current.count(END) != 1:
            raise fs.Conflict(f'Ambiguous HAE instruction block: {path}')
        start = current.index(BEGIN)
        end = current.index(END) + len(END)
        existing = current[start:end]
        desired = block.strip()
        normalized = existing.replace('\r\n', '\n')
        if normalized == desired:
            return None
        previous = previous_content(state, path)
        if previous is None or normalized not in previous.decode('utf-8').replace('\r\n', '\n'):
            raise fs.Conflict(f'Edited HAE instruction block; reconcile before upgrading: {path}')
        if '\r\n' in existing:
            desired = desired.replace('\n', '\r\n')
        after = current[:start] + desired + current[end:]
        return operation(path, after.encode(), 'marker', old_fragment=existing, new_fragment=desired)
    return operation(path, before + block.encode(), 'marker', old_fragment='', new_fragment=block)


def hooks_for(agent, argv):
    if agent == 'copilot':
        return {'version': 1, 'hooks': {event: [{'type': 'command', 'exec': argv[0], 'args': argv[1:], 'timeoutSec': 3}]
                                      for event in ['agentStop', 'sessionEnd']}}
    hook = {'type': 'command', 'command': argv[0], 'args': argv[1:], 'timeout': 3}
    if agent == 'codex':
        hook = {'type': 'command', 'command': shlex.join(argv), 'timeout': 3}
        if os.name == 'nt':
            hook['commandWindows'] = commands.windows_hook(argv)
    return {'hooks': {event: [{'hooks': [hook]}]
                      for event in ['Stop', 'PreCompact']}}


def merged_hooks(path, additions, state):
    before = fs.read(path)
    data = fs.load(path, {})
    if not isinstance(data, dict) or not isinstance(data.get('hooks', {}), dict):
        raise fs.Conflict(f'Invalid hook configuration: {path}')
    added, removed = {}, {}
    previous = previous_content(state, path)
    previous_data = json.loads(previous) if previous else {}
    for event, entries in additions['hooks'].items():
        original = data.setdefault('hooks', {}).setdefault(event, [])
        if not isinstance(original, list):
            raise fs.Conflict(f'Invalid hook event array: {path}')
        # Replace only commands installed by an earlier successful HAE transaction.
        known = previous_data.get('hooks', {}).get(event, [])
        old = [entry for entry in original if entry in known and 'hae.pyz' in json.dumps(entry)]
        unknown = [entry for entry in original if 'hae.pyz' in json.dumps(entry) and entry not in known and entry not in entries]
        if unknown:
            raise fs.Conflict(f'Unmanaged or edited HAE hook: {path}')
        for entry in old:
            if entry not in entries:
                original.remove(entry)
                removed.setdefault(event, []).append(entry)
        for entry in entries:
            if entry not in original:
                original.append(entry)
                added.setdefault(event, []).append(entry)
    if not added and not removed:
        return None
    if 'version' in additions:
        if data.get('version', 1) != 1:
            raise fs.Conflict(f'Unsupported hooks version: {path}')
        data['version'] = 1
    return operation(path, fs.json_bytes(data), 'hooks', added=added, removed=removed)


def known_memory(home, vault):
    paths = [vault / 'System/memory-config.json', vault / 'System/project-map.json',
             home / '.agents/skills/nio-memory/SKILL.md', home / '.claude/plugins/installed_plugins.json']
    found = []
    for path in paths:
        data = fs.read(path)
        if data and ('installed_plugins' not in path.name or b'claude-mem' in data):
            found.append(str(path))
    for path in [home / '.claude/CLAUDE.md', home / '.codex/AGENTS.md', home / '.copilot/copilot-instructions.md']:
        data = fs.read(path)
        if data:
            # HAE-owned instructions are excluded from overlap warnings.
            text = re.sub(re.escape(BEGIN) + r'.*?' + re.escape(END), '', data.decode(), flags=re.S)
            if re.search(r'(?i)\b(memory|vault|memories)\b', text):
                found.append(str(path))
    return found


def create_plan(*, home, state, vault, project, project_id, name, scope, mode='engineering',
                agents=('codex', 'claude', 'copilot'), hooks=False, style='existing',
                authority=None, memory_enabled=True, delivery='standalone'):
    home, state, vault, project = map(fs.checked, [home, state, vault, project])
    identity(project_id)
    identity(scope)
    if scope.lower() in {'unresolved', 'unknown'}:
        raise fs.Conflict('Choose the verified project scope before setup')
    if not name.strip() or len(name) > 100 or any(ord(c) < 32 for c in name):
        raise fs.Conflict('Project name must be 1–100 printable characters')
    if mode not in {'engineering', 'general'} or style not in {'existing', 'lean'}:
        raise fs.Conflict('Unsupported mode or style')
    if not set(agents) <= AGENTS or not agents:
        raise fs.Conflict('Select claude, codex, copilot or cowork')
    if delivery not in {'standalone', 'plugin'}:
        raise fs.Conflict('Select standalone or plugin delivery')
    if not project.is_dir():
        raise fs.Conflict('Select an existing project folder')
    if vault == project or memory.within(vault, project):
        raise fs.Conflict('Keep the private memory folder outside the source project')
    operations, warnings, conflicts = [], [], []
    def add(op):
        if op:
            operations.append(op)
    def owned(path, data):
        existing = fs.read(path)
        if existing is not None and existing != data and previous_content(state, path) != existing:
            raise fs.Conflict(f'Existing unowned or edited file: {path}')
        add(operation(path, data))
    def data_file(path, data):
        if fs.read(path) is None:
            add(operation(path, data, 'data'))

    with fs.lock(state):
        unfinished = [t for t in active_transactions(state) if t['status'] != 'installed']
        if unfinished:
            raise fs.Conflict('Recover the incomplete transaction with rollback before making another plan')
        overlap = known_memory(home, vault)
        prior_mapping = fs.load(vault / memory.MAP_NOTE, [])
        already_selected = isinstance(prior_mapping, list) and any(
            p.get('id') == project_id and p.get('scope') == scope and str(project) in p.get('paths', [])
            for p in prior_mapping if isinstance(p, dict))
        if memory_enabled and overlap and authority != 'hae' and not already_selected:
            conflicts.append('Existing memory detected. Choose --memory-authority hae for this project, or --no-memory to preserve the current authority.')
        if overlap:
            warnings.append({'existing_memory': overlap, 'settings_preserved': True})
        config_path = state / 'config.json'
        config = fs.load(config_path, {})
        if config and config.get('vault') != str(vault):
            conflicts.append('This profile already uses another vault. Use its current vault or a separate --state-dir.')
        if config and config.get('delivery', 'standalone') != delivery:
            conflicts.append('Changing delivery requires uninstalling the current integrations first; notes are preserved.')
        if config and config.get('memory_enabled', True) != memory_enabled:
            conflicts.append('Changing profile memory authority requires uninstalling the current integrations first; notes are preserved. Use a separate profile for a different setup.')
        zipdata = runtime_bytes()
        runtime = state / 'runtime' / fs.digest(zipdata)[:16] / 'hae.pyz'
        owned(runtime, zipdata)
        argv = [sys.executable, str(runtime), '--state-dir', str(state)]
        command = commands.display(argv)
        mode_config = {'version': 1, 'vault': str(vault), 'runtime': str(runtime), 'home': str(home),
                       'agents': sorted(set(config.get('agents', [])) | set(agents)), 'memory_enabled': memory_enabled,
                       'delivery': delivery}
        owned(config_path, fs.json_bytes(mode_config))
        if memory_enabled:
            cfg_path = vault / 'System/hae-config.json'
            cfg = fs.load(cfg_path, {'backend': 'local', 'model': 'jev-1.13.0', 'cloud_scopes': [],
                'daily_budget_usd': 0, 'lifetime_budget_usd': 0, 'batch_captures': 12,
                'recall_candidates': 12, 'cooldown_seconds': 120, 'timeout_seconds': 5, 'capture_enabled': False})
            if not isinstance(cfg, dict):
                raise fs.Conflict('Invalid HAE memory configuration')
            cfg['capture_enabled'] = bool(cfg.get('capture_enabled') or hooks)
            add(operation(cfg_path, fs.json_bytes(cfg), 'data'))
            map_path = vault / memory.MAP_NOTE
            mapping = fs.load(map_path, [])
            if not isinstance(mapping, list):
                raise fs.Conflict('Invalid HAE project map')
            existing = next((p for p in mapping if p.get('id') == project_id), None)
            entry = {'id': project_id, 'name': name, 'scope': scope, 'paths': [str(project)],
                     'note': f'Projects/{project_id}.md', 'mode': mode,
                     'practice': f'Practices/HAE {mode.title()}.md',
                     'capture_enabled': bool(hooks or (existing and existing.get('capture_enabled')))}
            if existing:
                comparable = dict(existing, capture_enabled=entry['capture_enabled'])
                if comparable != entry:
                    conflicts.append('Project ID already mapped differently; review the existing System/hae-projects.json mapping before changing ownership, paths or mode.')
                else:
                    existing['capture_enabled'] = entry['capture_enabled']
            else:
                if any(str(project) in p.get('paths', []) for p in mapping):
                    conflicts.append('Folder already belongs to another mapped project')
                mapping.append(entry)
            add(operation(map_path, fs.json_bytes(mapping), 'data'))
            # Never overwrite an existing note when attaching a vault.
            note = vault / entry['note']
            existing_note = fs.read(note)
            if existing_note is not None:
                meta = memory.parse_frontmatter(existing_note)
                if meta.get('project') != project_id or meta.get('scope') != scope:
                    conflicts.append(f'Existing note has different or unknown ownership: {entry["note"]}')
            data_file(note, (memory.frontmatter({'project': project_id, 'scope': scope, 'status': 'needs-verification'})
                            + f'# {name}\n\nRecord verified decisions and current work here.\n').encode())
            practice = vault / entry['practice']
            practice_text = (memory.frontmatter({'scope': 'global', 'status': 'practice'}) + resource(mode + '.md')).encode()
            current_practice = fs.read(practice)
            if current_practice is None or current_practice == previous_content(state, practice):
                add(operation(practice, practice_text, 'data'))
            elif current_practice != practice_text:
                warnings.append('Existing practice edits are preserved; the current engineering pack is available in hae-engineering references.')
            data_file(vault / 'HAE.md', resource('vault.md').encode())
            ignore_path = vault / '.gitignore'
            ignored = '.hae-state/\nSystem/hae-projects.json\nSystem/hae-config.json\nInbox/\n.obsidian/\n.DS_Store'
            ignore = marked(ignore_path, ignored, state)
            if ignore:
                ignore['kind'] = 'data'
            add(ignore)
        # Skills are standalone: each includes the full reviewed runtime zipapp.
        roots = set()
        if delivery == 'standalone' and {'codex', 'copilot'} & set(agents):
            roots.add(home / '.agents/skills')
        if delivery == 'standalone' and 'claude' in agents:
            roots.add(home / '.claude/skills')
        for root in sorted(roots):
            for skill, files in SKILL_RESOURCES.items():
                if skill == 'hae-memory' and not memory_enabled:
                    continue
                if skill == 'hae-engineering' and mode != 'engineering':
                    continue
                for relative, source in files.items():
                    owned(root / skill / relative, resource(source).encode())
                owned(root / skill / 'scripts/hae.pyz', zipdata)
        # context already defaults to the process cwd, avoiding shell-specific variables.
        instructions = f'HAE continuity: run `{command} context` at task start. Load only the matched project note and relevant practice. For engineering tasks use hae-engineering and select relevant installed skills. Follow current repository/user instructions. Save explicit memories, decisions and cutoff state with hae-memory; ordinary replies need no note. Keep client scopes separate, verify historical status and use project handoffs. Never infer ownership from the AI login.'
        if not memory_enabled:
            instructions = 'HAE handoffs: preserve the existing memory authority. At a meaningful milestone or cutoff, use the project’s existing handoff convention to record verified results, evidence, remaining work and owner. Do not infer authorship or ownership from the AI login.'
            if mode == 'engineering':
                instructions += ' Use hae-engineering for coding practices and relevant installed-skill routing.'
        if style == 'lean':
            instructions += ' Prefer concise replies, selective context reads and the smallest complete change; keep validation and safety intact. Documents and handoffs use normal prose.'
        targets = {'claude': home / '.claude/CLAUDE.md', 'codex': home / '.codex/AGENTS.md',
                   'copilot': home / '.copilot/copilot-instructions.md'}
        for agent in agents:
            if agent == 'cowork':
                warnings.append('Cowork uses the generated plugin package; install and select the folder in Cowork. Its live runtime support is not yet verified.')
                continue
            add(marked(targets[agent], instructions, state))
            if hooks and memory_enabled:
                # Native hooks compose with existing handlers; notify/config.toml are untouched.
                hook_path = {'claude': home / '.claude/settings.json', 'codex': home / '.codex/hooks.json',
                             'copilot': home / '.copilot/hooks/hae.json'}[agent]
                add(merged_hooks(hook_path, hooks_for(agent, argv + ['hook', '--agent', agent]), state))
                if agent == 'codex':
                    warnings.append('Codex hooks require review/trust through /hooks. Installation does not grant trust.')
        if not hooks:
            warnings.append('Automatic capture is off for new integrations. Use explicit milestone checkpoints.')
        # Store each large snapshot once. Journaling must not rewrite several
        # copies of the runtime archive for every single filesystem operation.
        for op in operations:
            for field in ['before', 'after']:
                content = decode(op[field])
                if content is not None and len(content) > 2048:
                    digest = fs.digest(content)
                    blob = state / 'blobs' / digest
                    existing_blob = fs.read(blob)
                    if existing_blob is None:
                        fs.write(blob, content, None)
                    elif fs.digest(existing_blob) != digest:
                        raise fs.Conflict('Recovery snapshot hash collision or modified snapshot')
                    op[field] = {'blob': str(blob), 'sha256': digest}
        plan_id = uuid.uuid4().hex
        value = {'schema': 1, 'id': plan_id, 'version': __version__, 'created': time.time(),
                 'home': str(home), 'state': str(state), 'vault': str(vault), 'project': str(project),
                 'mode': mode, 'agents': list(agents), 'operations': operations, 'warnings': warnings,
                 'conflicts': conflicts, 'provider_calls': 0, 'status': 'planned'}
        fs.save(state / 'plans' / (plan_id + '.json'), value)
        return preview(value)


def preview(plan):
    changes = []
    for op in plan['operations']:
        before, after = decode(op['before']) or b'', decode(op['after']) or b''
        diff = None
        if not op['path'].endswith('.pyz'):
            diff = ''.join(difflib.unified_diff(before.decode().splitlines(True), after.decode().splitlines(True),
                                               fromfile='before', tofile='after', n=2))
            diff = memory.redact_text(diff)[0]
        changes.append({'path': op['path'], 'kind': op['kind'], 'action': 'create' if op['before'] is None else 'modify',
                        'after_sha256': op['after_hash'], 'diff': diff})
    return {k: plan[k] for k in ['id', 'mode', 'warnings', 'conflicts', 'provider_calls']} | {
        'status': 'conflict' if plan['conflicts'] else 'ready', 'changes': changes,
        'apply': commands.display(runtime_command() + ['--state-dir', plan['state'], 'apply', plan['id']]),
        'rollback': commands.display(runtime_command() + ['--state-dir', plan['state'], 'rollback'])}


def apply(state, plan_id):
    identity(plan_id)
    state = fs.checked(state)
    with fs.lock(state):
        plan = fs.load(state / 'plans' / (plan_id + '.json'))
        if not plan or plan['state'] != str(state):
            raise fs.Conflict('Plan not found in this profile')
        if plan['conflicts']:
            raise fs.Conflict('Resolve the reported plan conflicts before applying')
        transaction_path = state / 'transactions' / (plan_id + '.json')
        prior = fs.load(transaction_path)
        if prior and prior['status'] == 'installed':
            return {'status': 'unchanged', 'id': plan_id}
        if prior:
            raise fs.Conflict('This transaction has already started; inspect doctor and rollback before retrying')
        if any(t['status'] != 'installed' for t in active_transactions(state)):
            raise fs.Conflict('Recover the incomplete transaction first')
        # All hashes are checked before the first mutation; each write also rechecks.
        for op in plan['operations']:
            if fs.digest(fs.read(op['path'])) != op['before_hash']:
                raise fs.Conflict(f'Stale plan; file changed: {op["path"]}')
            if fs.digest(decode(op['after'])) != op['after_hash']:
                raise fs.Conflict('Planned content changed; make a new plan')
        if not plan['operations']:
            return {'status': 'unchanged', 'id': plan_id}
        transaction = dict(plan, status='applying', started=time.time())
        save_transaction(state, transaction)
        try:
            for index, op in enumerate(transaction['operations']):
                # Journal the intent before the filesystem mutation for crash recovery.
                transaction['pending'] = index
                save_transaction(state, transaction)
                fs.write(op['path'], decode(op['after']), op['before_hash'])
                op['applied'] = True
                transaction['pending'] = None
                save_transaction(state, transaction)
            transaction['status'] = 'installed'
            save_transaction(state, transaction)
        except Exception:
            transaction['status'] = 'interrupted'
            save_transaction(state, transaction)
            raise
        return {'status': 'installed', 'id': plan_id, 'files_changed': len(plan['operations']),
                'warnings': plan['warnings'], 'notes_preserved_on_removal': True}


def inverse(op):
    path = Path(op['path'])
    current = fs.read(path)
    before, after = decode(op['before']), decode(op['after'])
    if op['kind'] == 'data':
        return current  # Memory, project mappings, and local provider configuration survive removal.
    if current == before:
        return current
    if current == after:
        return before
    if current is None:
        raise fs.Conflict(f'Installed file was removed: {path}')
    if op['kind'] == 'marker':
        text = current.decode()
        fragment = op['new_fragment']
        normalized = fragment.replace('\r\n', '\n')
        variants = set([fragment, normalized, normalized.replace('\n', '\r\n')])
        matches = [variant for variant in variants if text.count(variant)]
        if len(matches) != 1 or text.count(matches[0]) != 1:
            raise fs.Conflict(f'Owned instruction fragment changed: {path}')
        actual = matches[0]
        restored = op['old_fragment'].replace('\r\n', '\n')
        if '\r\n' in actual:
            restored = restored.replace('\n', '\r\n')
        result = text.replace(actual, restored, 1).encode()
        return result if result or before is not None else None
    if op['kind'] == 'hooks':
        data = json.loads(current)
        for event, entries in op['added'].items():
            current_entries = data.get('hooks', {}).get(event, [])
            for entry in entries:
                if current_entries.count(entry) != 1:
                    raise fs.Conflict(f'Owned hook changed: {path}')
                current_entries.remove(entry)
        for event, entries in op['removed'].items():
            data.setdefault('hooks', {}).setdefault(event, []).extend(entries)
        return fs.json_bytes(data)
    raise fs.Conflict(f'Installed file edited; preserved: {path}')


def rollback(state, transaction_id=None, uninstall=False):
    state = fs.checked(state)
    with fs.lock(state):
        transactions = sorted(active_transactions(state), key=lambda t: t.get('started', 0), reverse=True)
        if transaction_id:
            identity(transaction_id)
            if not transactions or transactions[0]['id'] != transaction_id:
                raise fs.Conflict('Rollback must start with the latest active transaction')
        if not uninstall:
            transactions = transactions[:1]
        changed, preserved = [], []
        for transaction in transactions:
            ops = transaction['operations']
            pending = transaction.get('pending')
            if pending is not None:
                op = ops[pending]
                actual = fs.digest(fs.read(op['path']))
                if actual == op['after_hash']:
                    op['applied'] = True
                elif actual != op['before_hash']:
                    raise fs.Conflict('Interrupted write changed externally; preserve and inspect the journal')
            reversals = []
            for op in reversed(ops):
                if not op.get('applied') or op.get('reverted'):
                    continue
                if op['kind'] == 'data':
                    preserved.append(op['path'])
                    continue
                reversals.append((op, fs.read(op['path']), inverse(op)))
            transaction['status'] = 'removing'
            journal = state / 'transactions' / (transaction['id'] + '.json')
            save_transaction(state, transaction)
            for op, current, target in reversals:
                if target != current:
                    if target is None:
                        if fs.read(op['path']) != current:
                            raise fs.Conflict('File changed during removal')
                        Path(op['path']).unlink()
                    else:
                        fs.write(op['path'], target, fs.digest(current))
                    changed.append(op['path'])
                op['reverted'] = True
                save_transaction(state, transaction)
            transaction['status'] = 'removed' if uninstall else 'rolled-back'
            save_transaction(state, transaction)
        return {'status': 'removed' if uninstall else 'rolled-back', 'changed': changed,
                'memory_preserved': True, 'retained_data_files': preserved}


def doctor(state):
    config = fs.load(state / 'config.json', {})
    transactions = active_transactions(state)
    issues = []
    newest = {}
    for transaction in sorted(transactions, key=lambda t: t.get('started', 0)):
        if transaction['status'] != 'installed':
            issues.append({'transaction': transaction['id'], 'status': transaction['status'], 'action': 'rollback'})
        for op in transaction['operations']:
            if op.get('applied') and op['kind'] != 'data':
                newest[op['path']] = op
    for path, op in newest.items():
        if fs.digest(fs.read(path)) != op['after_hash']:
            issues.append({'path': path, 'status': 'changed-since-install', 'action': 'inspect; later user edits may be intentional'})
    versions = {}
    for name in ['claude', 'codex', 'copilot']:
        executable = shutil.which(name)
        if not executable:
            versions[name] = 'not-found'
            continue
        try:
            output = subprocess.run([executable, '--version'], capture_output=True, text=True, timeout=5)
            versions[name] = output.stdout.splitlines()[0][:120] if output.stdout else 'unavailable'
        except (OSError, subprocess.TimeoutExpired):
            versions[name] = 'unavailable'
    return {'version': __version__, 'status': 'needs-attention' if issues else ('installed' if config else 'not-installed'),
            'state': str(state), 'vault': config.get('vault'), 'issues': issues, 'tools': versions,
            'hook_trust': 'not verified; review native host hooks UI', 'automatic_support': 'requires live host verification',
            'platform': sys.platform, 'python': sys.version.split()[0]}
