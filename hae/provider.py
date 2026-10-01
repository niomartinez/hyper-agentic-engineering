#!/usr/bin/env python3
"""Bounded TypeSafe decisions, environment credentials and content-free usage accounting."""
import contextlib
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
from . import fs
import sqlite3
import subprocess
import time
import urllib.error
import urllib.request

ENDPOINT = 'https://api.typesafe.ai/v1/systemone'
DEFAULT_PRICE_PER_MILLION = 0.042
MAX_REQUEST_BYTES = 32000


class JevError(Exception):
    """Messages are fixed strings; never include request, credential or response bodies."""


def config(root):
    path = root / 'System/hae-config.json'
    if not path.exists():
        return {'backend': 'local'}
    from .memory import safe_path, read_bytes
    value = json.loads(read_bytes(safe_path(root, 'System/hae-config.json'), 12000))
    if value.get('backend') not in {'jev', 'local'}:
        raise JevError('invalid memory backend')
    if value.get('backend') == 'jev':
        for field in ['daily_budget_usd', 'lifetime_budget_usd']:
            amount = value.get(field)
            if not isinstance(amount, (int, float)) or isinstance(amount, bool) or not math.isfinite(amount) or amount < 0:
                raise JevError('Jev requires finite nonnegative spending limits')
        scopes = value.get('cloud_scopes')
        if not isinstance(scopes, list) or any(not isinstance(s, str) or not s for s in scopes):
            raise JevError('Jev requires an explicit scope list')
    return value


def state_dir(root):
    from .memory import safe_path
    path = safe_path(root, '.hae-state')
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)
    return path


@contextlib.contextmanager
def database(root):
    path = state_dir(root) / 'decisions.sqlite3'
    if fs.is_link(path):
        raise JevError('unsafe database path')
    with contextlib.closing(sqlite3.connect(str(path), timeout=10)) as db:
        path.chmod(0o600)
        db.execute('CREATE TABLE IF NOT EXISTS calls (id INTEGER PRIMARY KEY, request_hash TEXT, created REAL, day TEXT, purpose TEXT, status TEXT, input_tokens INTEGER, cost REAL, latency_ms INTEGER, model TEXT)')
        db.execute('CREATE TABLE IF NOT EXISTS cache (hash TEXT PRIMARY KEY, expires REAL, result TEXT)')
        db.execute('CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT)')
        db.execute('CREATE TABLE IF NOT EXISTS facts (project TEXT, hash TEXT, path TEXT, PRIMARY KEY(project,hash))')
        db.execute('CREATE TABLE IF NOT EXISTS notes (group_id TEXT PRIMARY KEY, path TEXT, hash TEXT)')
        db.execute('CREATE TABLE IF NOT EXISTS receipts (path TEXT PRIMARY KEY, hash TEXT)')
        db.execute('CREATE TABLE IF NOT EXISTS read_cache (path TEXT PRIMARY KEY, signature TEXT, content TEXT)')
        db.commit()
        with db:
            yield db


def credential():
    value = os.environ.get('HAE_JEV_API_KEY', '').strip()
    if not value:
        raise JevError('HAE_JEV_API_KEY unavailable; evidence kept locally')
    return value


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise JevError('provider redirect refused')


def transport(body, key, timeout):
    request = urllib.request.Request(ENDPOINT, data=body, method='POST', headers={
        'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key})
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=timeout) as reply:
            raw = reply.read(256001)
        if len(raw) > 256000:
            raise JevError('provider response exceeds limit')
        return json.loads(raw)
    except urllib.error.HTTPError as error:
        raise JevError('provider HTTP ' + str(error.code)) from None
    except JevError:
        raise
    except Exception:
        raise JevError('provider unavailable or invalid response; evidence kept locally') from None


def probability(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and 0 <= value <= 1


def validate(result, questions, model):
    if not isinstance(result, dict) or result.get('model') != model:
        raise JevError('provider model mismatch')
    answers = result.get('answers')
    if not isinstance(answers, dict) or set(answers) != set(questions):
        raise JevError('provider answer schema mismatch')
    for name, question in questions.items():
        answer = answers[name]
        if not isinstance(answer, dict) or answer.get('type') != question['type']:
            raise JevError('provider answer type mismatch')
        if question['type'] == 'noul':
            if not probability(answer.get('noul')):
                raise JevError('invalid probability')
        elif question['type'] == 'choice':
            options = question['criteria']
            values = answer.get('probabilities', {})
            if (answer.get('choice') not in options or set(values) != set(options)
                    or not probability(answer.get('confidence'))
                    or not all(probability(p) for p in values.values())
                    or abs(sum(values.values()) - 1) > 0.025):
                raise JevError('invalid choice distribution')
        else:
            raise JevError('unsupported question type')
    return answers


def evaluate(state, questions, purpose, root, send=None, get_key=None):
    cfg = config(root)
    price = cfg.get('price_per_million_usd', DEFAULT_PRICE_PER_MILLION)
    if not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 0:
        raise JevError('invalid provider price estimate')
    if cfg['backend'] != 'jev':
        raise JevError('Jev backend is not enabled')
    if purpose not in {'write', 'recall', 'verification'} or not 1 <= len(questions) <= 24:
        raise JevError('invalid bounded decision request')
    from .memory import redact_text
    model = cfg['model']
    payload = {'model': model, 'state': state, 'questions': questions}
    body = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode()
    clean, redactions = redact_text(body.decode())
    if redactions:
        raise JevError('request contains possible secret material; not transmitted')
    if len(body) > MAX_REQUEST_BYTES:
        raise JevError('request exceeds byte budget')
    digest = hashlib.sha256(body).hexdigest()
    now = time.time()
    day = dt.datetime.now(dt.timezone.utc).date().isoformat()
    # Reserve a deliberately conservative byte-based token estimate before any call.
    reserve = (len(body) + 1000) * price / 1000000
    with database(root) as db:
        db.execute('BEGIN IMMEDIATE')
        cached = db.execute('SELECT result FROM cache WHERE hash=? AND expires>?', (digest, now)).fetchone()
        if cached:
            result = json.loads(cached[0])
            validate(result, questions, model)
            return dict(result, cached=True, estimated_cost_usd=0, latency_ms=0)
        backoff = db.execute('SELECT value FROM kv WHERE ?=key', ('backoff_until',)).fetchone()
        if backoff and now < float(backoff[0]):
            raise JevError('provider retry deferred; evidence kept locally')
        spent = db.execute('SELECT COALESCE(SUM(cost),0) FROM calls').fetchone()[0]
        daily = db.execute('SELECT COALESCE(SUM(cost),0) FROM calls WHERE day=?', (day,)).fetchone()[0]
        if spent + reserve > cfg['lifetime_budget_usd'] or daily + reserve > cfg['daily_budget_usd']:
            raise JevError('local Jev spending limit reached; evidence kept locally')
        row = db.execute('INSERT INTO calls(request_hash,created,day,purpose,status,input_tokens,cost,latency_ms,model) VALUES(?,?,?,?,?,?,?,?,?)',
                         (digest, now, day, purpose, 'reserved', 0, reserve, 0, model)).lastrowid
        db.commit()
    started = time.monotonic()
    try:
        result = (send or transport)(body, (get_key or credential)(), cfg.get('timeout_seconds', 5))
        validate(result, questions, model)
        tokens = result.get('usage', {}).get('input_tokens')
        if not isinstance(tokens, int) or isinstance(tokens, bool) or not 0 < tokens <= 64000:
            raise JevError('provider usage missing or invalid')
        cost = tokens * price / 1000000
        latency = round((time.monotonic() - started) * 1000)
        with database(root) as db:
            db.execute('UPDATE calls SET status=?,input_tokens=?,cost=?,latency_ms=? WHERE id=?', ('ok', tokens, cost, latency, row))
            db.execute('INSERT OR REPLACE INTO cache VALUES(?,?,?)', (digest, now + 7 * 86400, json.dumps(result)))
        return dict(result, cached=False, estimated_cost_usd=cost, latency_ms=latency)
    except Exception as error:
        with database(root) as db:
            # Failed/unknown calls retain the reserve rather than claim zero spend.
            db.execute('UPDATE calls SET status=?,latency_ms=? WHERE id=?', ('failed', round((time.monotonic()-started)*1000), row))
            db.execute('INSERT OR REPLACE INTO kv VALUES(?,?)', ('backoff_until', str(time.time()+60)))
        if isinstance(error, JevError):
            raise
        raise JevError('decision unavailable; evidence kept locally') from None


def usage(root):
    with database(root) as db:
        counts = db.execute('SELECT status,COUNT(*),SUM(input_tokens),SUM(cost) FROM calls GROUP BY status').fetchall()
    return {'backend': config(root)['backend'], 'model': config(root).get('model'),
            'calls': [{'status': s, 'count': n, 'input_tokens': t, 'estimated_usd': round(c, 8)} for s,n,t,c in counts],
            'daily_budget_usd': config(root).get('daily_budget_usd'),
            'lifetime_budget_usd': config(root).get('lifetime_budget_usd'),
            'account_balance': 'not queried; local accounting only'}
