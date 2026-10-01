"""HAE command line: reviewed setup and bounded, local-first memory."""
import argparse
import json
import os
from pathlib import Path
import re
import sys

from . import __version__, fs, install, memory, provider, recall, skills


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--version', action='version', version=__version__)
    p.add_argument('--home', type=Path, default=Path.home(), help='Profile home (use a disposable directory for testing)')
    p.add_argument('--state-dir', type=Path, default=os.environ.get('HAE_STATE_DIR'))
    p.add_argument('--vault', type=Path, default=os.environ.get('HAE_VAULT'))
    commands = p.add_subparsers(dest='command', required=True)
    plan = commands.add_parser('plan', help='Inspect setup and generate exact changes without applying them')
    plan.add_argument('--project', type=Path, required=True)
    plan.add_argument('--project-id', required=True)
    plan.add_argument('--name', required=True)
    plan.add_argument('--scope', required=True, help='Verified owner/client boundary, e.g. personal or client-acme')
    plan.add_argument('--mode', choices=['engineering', 'general'], default='engineering')
    plan.add_argument('--agents', default='codex,claude,copilot')
    plan.add_argument('--hooks', action='store_true', help='Opt in to bounded automatic evidence capture')
    plan.add_argument('--style', choices=['existing', 'lean'], default='existing')
    plan.add_argument('--delivery', choices=['standalone', 'plugin'], default='standalone',
                      help='Plugin delivery uses the already-installed plugin skills, avoiding duplicate discovery')
    plan.add_argument('--memory-authority', choices=['hae'])
    plan.add_argument('--no-memory', action='store_true', help='Use handoff guidance and preserve existing memory authority')
    commands.add_parser('apply').add_argument('plan_id')
    commands.add_parser('doctor')
    commands.add_parser('rollback').add_argument('transaction_id', nargs='?')
    commands.add_parser('uninstall')
    ctx = commands.add_parser('context')
    ctx.add_argument('--cwd', default=os.getcwd())
    mem = commands.add_parser('memory').add_subparsers(dest='action', required=True)
    mem.add_parser('save').add_argument('--packet', required=True, help='Approved JSON packet file or - for stdin')
    search = mem.add_parser('recall')
    search.add_argument('--project', required=True)
    search.add_argument('--query', required=True)
    search.add_argument('--limit', type=int, default=5)
    mem.add_parser('status')
    mem.add_parser('health')
    capture = mem.add_parser('capture', help='Enable or disable automatic evidence for one mapped project')
    capture.add_argument('enabled', choices=['on', 'off'])
    capture.add_argument('--project', required=True)
    drain = mem.add_parser('drain')
    drain.add_argument('--force', action='store_true', help='Bypass cooldown, never budget or scope checks')
    mode = mem.add_parser('backend')
    mode.add_argument('backend', choices=['local', 'jev'])
    mode.add_argument('--scopes', help='Explicit comma-separated scopes allowed to reach Jev')
    mode.add_argument('--daily-budget', type=float)
    mode.add_argument('--lifetime-budget', type=float)
    mode.add_argument('--price-per-million', type=float, default=provider.DEFAULT_PRICE_PER_MILLION)
    hook = commands.add_parser('hook')
    hook.add_argument('--agent', choices=['claude', 'codex', 'copilot', 'cowork'], required=True)
    handoff = commands.add_parser('handoff', help='Create an approved portable project handoff without importing private memory')
    handoff.add_argument('--project', required=True)
    handoff.add_argument('--packet', required=True)
    handoff.add_argument('--output', type=Path, required=True)
    backup = commands.add_parser('backup', help='Explicit local text-only backup; never pushes automatically')
    backup.add_argument('--dest', type=Path, required=True)
    commands.add_parser('catalog', help='Show optional pinned upstream sources; installs nothing')
    routing = commands.add_parser('skills').add_subparsers(dest='skill_action', required=True)
    route = routing.add_parser('route', help='Find a relevant installed skill without loading the whole library')
    route.add_argument('--task', choices=sorted(skills.routes()), required=True)
    route.add_argument('--explicit', action='store_true', help='Only for an explicit user request for an opt-in skill')
    return p


def packet(path):
    raw = sys.stdin.buffer.read(24001) if path == '-' else fs.read(path, 24000)
    if raw is None or len(raw) > 24000:
        raise fs.Conflict('Packet missing or exceeds 24000 bytes')
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise fs.Conflict('Packet must be a JSON object')
    return value


def vault_for(args, state):
    cfg = fs.load(state / 'config.json', {})
    value = args.vault or cfg.get('vault')
    if not value:
        raise fs.Conflict('No vault configured; pass --vault or apply a setup plan')
    return memory.vault_root(fs.checked(value))


def handoff(root, project_id, data, output):
    project = next((p for p in memory.load_map(root) if p['id'] == project_id), None)
    if not project or data.get('approved') is not True:
        raise fs.Conflict('A known project and approved handoff packet are required')
    fields = ['task', 'completed', 'evidence', 'remaining', 'owner', 'references']
    if project.get('mode', 'engineering') == 'engineering':
        fields += ['branch_commit']
    if any(not isinstance(data.get(f, ''), str) or len(data.get(f, '')) > 4000 for f in fields):
        raise fs.Conflict('Handoff fields must be bounded text')
    if not data.get('task', '').strip() or not data.get('remaining', '').strip():
        raise fs.Conflict('Handoff needs a task and remaining work (or explicitly none)')
    text = '# ' + project['name'] + ' — Handoff\n\n'
    for field in fields:
        if data.get(field):
            text += '## ' + field.replace('_', ' ').title() + '\n\n' + data[field] + '\n\n'
    if memory.redact_text(text)[1]:
        raise fs.Conflict('Possible credential in handoff; no write')
    output = fs.checked(output)
    if not any(memory.within(output, Path(p).expanduser().resolve()) for p in project['paths']):
        raise fs.Conflict('Handoff output must be inside the selected project folder')
    if output.suffix != '.md':
        raise fs.Conflict('Handoff output must be Markdown')
    fs.write(output, text.encode(), None)
    return {'status': 'saved', 'path': str(output), 'model_calls': 0}


def backend(root, args):
    relative = 'System/hae-config.json'
    original = recall.read_note(root, relative)
    cfg = json.loads(original)
    if args.backend == 'jev':
        if args.scopes is None or args.daily_budget is None or args.lifetime_budget is None:
            raise fs.Conflict('Enabling Jev requires --scopes, --daily-budget and --lifetime-budget; use your own limits')
        scopes = [s.strip().lower() for s in args.scopes.split(',') if s.strip()]
        known = {p['scope'].lower() for p in memory.load_map(root)}
        if not scopes or not set(scopes) <= known or {'unknown', 'unresolved'} & set(scopes):
            raise fs.Conflict('Cloud scopes must explicitly name known mapped scopes')
        import math
        if any(not math.isfinite(v) or v <= 0 for v in [args.daily_budget, args.lifetime_budget, args.price_per_million]):
            raise fs.Conflict('Budgets and price estimate must be finite positive numbers')
        cfg.update(cloud_scopes=scopes, daily_budget_usd=args.daily_budget,
                   lifetime_budget_usd=args.lifetime_budget, price_per_million_usd=args.price_per_million)
    cfg['backend'] = args.backend
    with recall.lock(root, 'config'):
        recall.replace_text(root, relative, recall.sha(original), fs.json_bytes(cfg).decode())
    return {'backend': args.backend, 'cloud_scopes': cfg.get('cloud_scopes', []), 'model_calls': 0,
            'credential': 'read from HAE_JEV_API_KEY only when a call is needed',
            'limits': 'local estimates; not the provider account balance'}


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        state = install.state_path(args.home, args.state_dir)
        if sys.version_info < (3, 11):
            raise fs.Conflict('Python 3.11 or newer is required')
        if args.command == 'plan':
            result = install.create_plan(home=args.home, state=state,
                vault=args.vault or args.home / 'Documents/Agent Memory', project=args.project,
                project_id=args.project_id, name=args.name, scope=args.scope, mode=args.mode,
                agents=args.agents.split(','), hooks=args.hooks, style=args.style,
                authority=args.memory_authority, memory_enabled=not args.no_memory, delivery=args.delivery)
        elif args.command == 'apply':
            result = install.apply(state, args.plan_id)
        elif args.command == 'doctor':
            result = install.doctor(state)
        elif args.command in {'rollback', 'uninstall'}:
            result = install.rollback(state, getattr(args, 'transaction_id', None), args.command == 'uninstall')
        elif args.command == 'catalog':
            from .packaging import resource
            result = json.loads(resource('integrations.lock.json'))
        elif args.command == 'skills':
            result = skills.route(args.home, args.task, args.explicit)
        else:
            root = vault_for(args, state)
            if args.command == 'context':
                result = memory.context(root, args.cwd)
            elif args.command == 'hook':
                # Neutral output only. Never block completion or request another model turn.
                memory.capture(root, args.agent, memory.bounded_input())
                result = {}
            elif args.command == 'handoff':
                result = handoff(root, args.project, packet(args.packet), args.output)
            elif args.command == 'backup':
                result = memory.backup(root, args.dest)
            elif args.action == 'save':
                result = recall.save_packet(root, packet(args.packet))
            elif args.action == 'recall':
                result = recall.recall(root, args.project, args.query, args.limit)
            elif args.action == 'status':
                result = recall.status(root)
            elif args.action == 'health':
                result = memory.maintenance(root)
            elif args.action == 'capture':
                path = root / memory.MAP_NOTE
                with recall.lock(root, 'config'):
                    original = fs.read(path)
                    projects = memory.load_map(root)
                    selected = next((p for p in projects if p['id'] == args.project), None)
                    if selected is None:
                        raise fs.Conflict('Capture requires a known project')
                    selected['capture_enabled'] = args.enabled == 'on'
                    if selected['capture_enabled']:
                        cfg_path = root / 'System/hae-config.json'
                        previous_cfg = fs.read(cfg_path)
                        cfg = json.loads(previous_cfg)
                        cfg['capture_enabled'] = True
                        fs.write(cfg_path, fs.json_bytes(cfg), fs.digest(previous_cfg))
                    fs.write(path, fs.json_bytes(projects), fs.digest(original))
                result = {'project': args.project, 'capture_enabled': selected['capture_enabled'],
                          'hook_dispatch': 'requires a configured and trusted native host hook'}
            elif args.action == 'drain':
                result = recall.drain(root, args.force)
            else:
                result = backend(root, args)
        # ASCII JSON remains parseable under Windows legacy pipe encodings too.
        print(json.dumps(result, ensure_ascii=True))
        return 2 if result.get('status') == 'conflict' else 0
    except Exception as error:
        if args.command == 'hook':
            print('{}')
            # No payloads or credentials in diagnostic output.
            print('HAE capture unavailable; use an explicit checkpoint.', file=sys.stderr)
            return 0
        reason = str(error) if isinstance(error, (fs.Conflict, memory.MemoryError, provider.JevError)) else 'Operation failed; original inputs preserved. Check configuration and packet format.'
        print(json.dumps({'status': 'blocked', 'reason': reason}))
        return 1
