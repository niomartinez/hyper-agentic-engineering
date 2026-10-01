"""Observable memory behavior. Temporary vaults, deterministic provider, no paid calls."""
import json
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from hae import provider as j
from hae import recall as jm
from hae import memory as m


class JevMemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()
        for folder in ['System','Projects','Sessions','Practices','Inbox/Captures']:(self.root/folder).mkdir(parents=True)
        self.cfg={'backend':'jev','model':'jev-1.13.0','daily_budget_usd':0.25,'lifetime_budget_usd':24,
                  'timeout_seconds':1,'capture_enabled':True,'cloud_scopes':['personal'],'batch_captures':12,'cooldown_seconds':120,'recall_candidates':12}
        (self.root/'System/hae-config.json').write_text(json.dumps(self.cfg))
        self.projects=[{'id':'test','name':'Test project','scope':'personal','paths':[str(self.root/'repo')],'note':'Projects/Test.md','capture_enabled':True},
                       {'id':'client','name':'Client','scope':'client-acme','paths':[str(self.root/'client')],'note':'Projects/Client.md','capture_enabled':True}]
        (self.root/'System/hae-projects.json').write_text(json.dumps(self.projects))
        (self.root/'Projects/Test.md').write_text(m.frontmatter({'scope':'personal','project':'test'})+'# Test\nProject baseline.\n')
        (self.root/'Projects/Client.md').write_text(m.frontmatter({'scope':'client-acme','project':'client'})+'# Client\nPrivate client database.\n')
        self.patcher=patch.object(jm,'launch');self.patcher.start();self.addCleanup(self.patcher.stop)

    def capture(self,text,turn='1',project='test'):
        cwd=self.root/('repo' if project=='test' else 'client');cwd.mkdir(exist_ok=True)
        m.capture(self.root,'codex',{'last-assistant-message':text,'thread-id':'session-a','turn-id':turn,'cwd':str(cwd)})
        return sorted((self.root/'Inbox/Captures').glob('capture-*'),key=lambda p:p.stat().st_mtime)[-1]

    def decide(self,state,questions,purpose,root=None,choice='retain',confidence=1):
        answers={}
        for name,q in questions.items():
            if q['type']=='noul':answers[name]={'type':'noul','noul':0.9}
            else:answers[name]={'type':'choice','choice':choice,'confidence':confidence,
                               'probabilities':{k:1 if k==choice else 0 for k in q['criteria']}}
        return {'model':'jev-1.13.0','answers':answers,'usage':{'input_tokens':100},'cached':False}

    def test_nested_repository_does_not_inherit_parent_scope(self):
        import subprocess
        parent = self.root / 'repo'; parent.mkdir()
        child = parent / 'nested'; child.mkdir()
        for folder in [parent, child]:
            subprocess.run(['git', 'init', '-q', str(folder)], check=True)
        self.assertEqual(m.context(self.root, str(child))['status'], 'unresolved')

    def test_linked_worktree_resolves_canonical_project(self):
        import subprocess
        repo = self.root / 'repo'; repo.mkdir()
        def git(*args):
            subprocess.run(['git', '-C', str(repo), '-c', 'core.hooksPath=' + str(self.root/'empty-hooks'),
                '-c', 'commit.gpgsign=false', '-c', 'user.name=Fixture',
                '-c', 'user.email=fixture@example.invalid', *args], check=True, capture_output=True)
        git('init', '-q')
        git('commit', '--allow-empty', '-m', 'Synthetic test')
        worktree = self.root / 'linked'
        git('worktree', 'add', '-b', 'fixture', str(worktree))
        result = m.context(self.root, str(worktree))
        self.assertEqual(result['project_id'], 'test')
        self.assertEqual(result['resolved_via'], 'git-common-dir')

    def test_retains_exact_evidence_with_unverified_status(self):
        text='Fixed database retries. Five integration checks passed; deployment remains pending.'
        self.capture(text)
        result=jm.drain(self.root,force=True,decide=self.decide)
        self.assertEqual(len(result['saved_paths']),1)
        note=(self.root/result['saved_paths'][0]).read_text()
        self.assertIn('> '+text,note);self.assertEqual(jm.metadata(note)['status'],'unverified')

    def test_session_rollup_and_dedup(self):
        self.capture('Fixed database retries; five integration checks passed.')
        first=jm.drain(self.root,True,self.decide)
        self.capture('Fixed database retries; five integration checks passed.','2')
        second=jm.drain(self.root,True,self.decide)
        self.assertEqual(second['calls'],0)
        self.capture('The remaining blocker is a missing deployment approval.','3')
        third=jm.drain(self.root,True,self.decide)
        self.assertEqual(first['saved_paths'],third['saved_paths'])
        self.assertEqual(len(list((self.root/'Sessions').glob('*.md'))),1)

    def test_other_edits_are_not_overwritten(self):
        self.capture('Fixed database retries; five integration checks passed.')
        first=jm.drain(self.root,True,self.decide);path=self.root/first['saved_paths'][0]
        path.write_text(path.read_text()+'\nHuman correction.\n');before=path.read_text()
        self.capture('Deployment completed and service health was verified.','2')
        second=jm.drain(self.root,True,self.decide)
        self.assertNotEqual(first['saved_paths'],second['saved_paths']);self.assertEqual(path.read_text(),before)

    def test_provider_failure_keeps_pending_and_calls_no_worker(self):
        p=self.capture('Fixed database retries; five integration checks passed.')
        with patch.object(jm.subprocess,'Popen') as spawn:
            result=jm.drain(self.root,True,lambda *a,**k:(_ for _ in ()).throw(j.JevError('provider unavailable')))
        self.assertEqual(result['status'],'deferred');self.assertEqual(jm.metadata(p.read_text())['capture_status'],'pending');spawn.assert_not_called()

    def test_uncertain_evidence_preserved_for_review(self):
        p=self.capture('We changed the database configuration after investigating failures.')
        result=jm.drain(self.root,True,lambda *a,**k:self.decide(*a,**k,confidence=0.4))
        self.assertEqual(result['review_needed'],1);self.assertEqual(jm.metadata(p.read_text())['capture_status'],'review-needed');self.assertFalse(result['saved_paths'])

    def test_requirements_cannot_be_skipped_by_high_confidence(self):
        self.capture('The cache key must include the account identifier.')
        result=jm.drain(self.root,True,lambda *a,**k:self.decide(*a,**k,choice='skip'))
        self.assertEqual(result['review_needed'],1);self.assertEqual(result['skipped'],0)

    def test_short_decision_is_not_lost_by_local_filter(self):
        self.capture('Use pnpm.')
        result=jm.drain(self.root,True,self.decide)
        self.assertEqual(len(result['saved_paths']),1)
        self.assertIn('Use pnpm.',(self.root/result['saved_paths'][0]).read_text())

    def test_uncertain_capture_is_locally_retrievable_without_upload(self):
        self.capture('We chose a local SQLite database for offline support.')
        jm.drain(self.root,True,lambda *a,**k:self.decide(*a,**k,choice='review'))
        with patch.object(j,'evaluate') as provider:
            result=jm.recall(self.root,'test','SQLite database offline')
        provider.assert_not_called()
        self.assertIn('SQLite',result['local_evidence'][0]['excerpt'])
        self.assertEqual(result['capture_status']['review-needed'],1)

    def test_scope_is_filtered_before_provider(self):
        p=self.capture('A private client database migration completed.',project='client')
        with patch.object(j,'evaluate') as provider:jm.drain(self.root,True)
        provider.assert_not_called();self.assertEqual(jm.metadata(p.read_text())['capture_status'],'review-needed')

    def test_trivial_response_makes_no_model_call(self):
        self.capture('Thanks!')
        with patch.object(j,'evaluate') as provider:result=jm.drain(self.root,True)
        provider.assert_not_called();self.assertEqual(result['skipped'],1)

    def test_secret_redaction_covers_typesafe_format(self):
        fake='apikey_'+'a'*35+'_'+'b'*64
        clean,count=m.redact_text('credential '+fake)
        self.assertEqual(count,1);self.assertNotIn(fake,clean)
        with patch.object(j,'transport') as send:
            with self.assertRaises(j.JevError):j.evaluate(fake,{'q':{'type':'noul','instructions':'Is this a key?'}},'verification',self.root)
        send.assert_not_called()

    def test_explicit_save_is_model_free_and_idempotent(self):
        packet={'approved':True,'job_id':'manual-1','mode':'remember','project':'test','scope':'personal','source':'user directive',
                'records':[{'title':'Offline requirement','summary':'The app must work offline.','next':'Keep SQLite.'}]}
        with patch.object(j,'evaluate') as provider:
            first=jm.save_packet(self.root,packet);second=jm.save_packet(self.root,packet)
        self.assertEqual(first['saved_paths'],second['saved_paths']);self.assertTrue(second['duplicate']);provider.assert_not_called()
        self.assertEqual(len(list((self.root/'Sessions').glob('*.md'))),1)

    def test_changed_manual_job_rejected(self):
        packet={'approved':True,'job_id':'manual-1','mode':'remember','project':'test','scope':'personal','records':[{'summary':'The app must work offline.'}]}
        jm.save_packet(self.root,packet);packet['records'][0]['summary']='Use cloud only.'
        with self.assertRaises(m.MemoryError):jm.save_packet(self.root,packet)

    def test_record_recovers_after_file_write_before_receipt(self):
        packet={'approved':True,'job_id':'crash-1','mode':'checkpoint','project':'test','scope':'personal','records':[{'summary':'The app must work offline.'}]}
        original=m.record
        def crash(*args):
            original(*args)
            raise RuntimeError('simulated crash after file write')
        with patch.object(m,'record',side_effect=crash):
            with self.assertRaises(RuntimeError):jm.save_packet(self.root,packet)
        result=jm.save_packet(self.root,packet)
        self.assertEqual(len(result['saved_paths']),1)
        self.assertEqual(len(list((self.root/'Sessions').glob('*.md'))),1)

    def test_partial_update_and_record_retry(self):
        path='Practices/Test.md';old=m.frontmatter({'scope':'global'})+'# Test\nOriginal rule.\n';(self.root/path).write_bytes(old.encode('utf-8'))
        packet={'approved':True,'job_id':'partial-1','mode':'override','project':'test','scope':'global',
                'updates':[{'path':path,'content':old+'New rule.\n','expected_sha256':jm.sha(old)}],
                'records':[{'summary':'The global rule changed as explicitly requested.'}]}
        with patch.object(m,'record',side_effect=RuntimeError('crash')):
            with self.assertRaises(RuntimeError):jm.save_packet(self.root,packet)
        result=jm.save_packet(self.root,packet)
        self.assertEqual(len(result['saved_paths']),2)
        self.assertEqual((self.root/path).read_text(),old+'New rule.\n')
        with j.database(self.root) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM receipts').fetchone()[0],2)

    def test_manual_update_checks_hash_and_scope(self):
        path='Practices/Test.md';old=m.frontmatter({'scope':'global'})+'# Test\nOriginal rule.\n';(self.root/path).write_bytes(old.encode('utf-8'))
        packet={'approved':True,'job_id':'update-1','mode':'override','project':'test','scope':'global','updates':[{'path':path,'content':old+'New rule.\n','expected_sha256':jm.sha(old)}]}
        jm.save_packet(self.root,packet)
        packet['job_id']='update-2'
        with self.assertRaises(m.MemoryError):jm.save_packet(self.root,packet)

    def test_recall_never_sends_other_project(self):
        (self.root/'Sessions/personal.md').write_text(m.frontmatter({'project':'test','scope':'personal'})+'# Database\nUse local SQLite database for offline support.')
        (self.root/'Sessions/client.md').write_text(m.frontmatter({'project':'client','scope':'client-acme'})+'# Database\nCLIENT-PRIVATE-CONTENT database.')
        received=[]
        def decide(state,*a,**kw):received.append(json.dumps(state));return self.decide(state,*a,**kw)
        result=jm.recall(self.root,'test','database offline',decide=decide)
        self.assertNotIn('CLIENT-PRIVATE-CONTENT',''.join(received));self.assertTrue(result['matches'])
        self.assertTrue(all(r['path']!='Sessions/client.md' for r in result['matches']))

    def test_recall_falls_back_on_provider_failure(self):
        (self.root/'Sessions/personal.md').write_text(m.frontmatter({'project':'test','scope':'personal'})+'# Database\nOffline database investigation.')
        def fail(*a,**kw):raise j.JevError('provider unavailable')
        result=jm.recall(self.root,'test','database',decide=fail)
        self.assertEqual(result['backend'],'local-search');self.assertTrue(result['matches'])

    def test_strong_curated_match_does_not_pull_in_weaker_raw_noise(self):
        (self.root/'Sessions/personal.md').write_text(m.frontmatter({'project':'test','scope':'personal'})+'# Storage\nSQLite database supports offline operation.')
        self.capture('We discussed SQLite in an old conversation.')
        jm.drain(self.root,True,lambda *a,**k:self.decide(*a,**k,choice='review'))
        result=jm.recall(self.root,'test','SQLite database offline',decide=self.decide)
        self.assertTrue(result['matches']);self.assertFalse(result['local_evidence'])

    def test_low_relevance_is_not_returned_as_context(self):
        (self.root/'Sessions/personal.md').write_text(m.frontmatter({'project':'test','scope':'personal'})+'# Database\nDatabase discussion without the requested information.')
        def irrelevant(state,questions,purpose,root=None):
            return {'answers':{name:{'type':'noul','noul':0.01} for name in questions},'cached':False}
        result=jm.recall(self.root,'test','database',decide=irrelevant)
        self.assertFalse(result['matches']);self.assertIn('Projects/Test.md',result['required_context'])

    def test_read_cache_refreshes_edits_without_reopening_unchanged_files(self):
        paths=['Projects/Test.md'];first=jm.indexed_texts(self.root,paths)
        with patch.object(jm,'read_note',side_effect=AssertionError('unchanged files should stay cached')):
            self.assertEqual(jm.indexed_texts(self.root,paths),first)
        (self.root/paths[0]).write_text('Updated local requirement.')
        self.assertEqual(jm.indexed_texts(self.root,paths)[paths[0]],'Updated local requirement.')
        (self.root/paths[0]).unlink()
        self.assertFalse(jm.indexed_texts(self.root,paths))

    def test_read_cache_never_stores_recognizable_secrets(self):
        path='Projects/Test.md';fake='apikey_'+'a'*35+'_'+'b'*64
        (self.root/path).write_text(fake)
        jm.indexed_texts(self.root,[path])
        with j.database(self.root) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM read_cache').fetchone()[0],0)

    def test_mode_rollback_preserves_notes(self):
        self.capture('Fixed database retries; five integration checks passed.');jm.drain(self.root,True,self.decide)
        before={str(p):p.read_bytes() for p in (self.root/'Sessions').glob('*.md')}
        jm.set_backend(self.root,'local');self.assertEqual(j.config(self.root)['backend'],'local')
        self.assertEqual(before,{str(p):p.read_bytes() for p in (self.root/'Sessions').glob('*.md')})
        with patch.object(j,'evaluate') as provider:result=jm.drain(self.root,True)
        provider.assert_not_called();self.assertEqual(result['status'],'deferred')

    def test_recall_rejects_mismatched_scope_even_with_matching_project_id(self):
        (self.root/'Sessions/mismatch.md').write_text(m.frontmatter({'project':'test','scope':'client-acme'})+'# Private\nCLIENT-PRIVATE-CONTENT database.')
        result=jm.recall(self.root,'test','database')
        self.assertFalse(any(r['path']=='Sessions/mismatch.md' for r in result['matches']))

    def test_request_cache_avoids_second_api_call(self):
        sent=[];q={'q':{'type':'noul','instructions':'Is this a durable project decision?'}}
        def send(body,key,timeout):sent.append(body);return {'model':'jev-1.13.0','answers':{'q':{'type':'noul','noul':0.9}},'usage':{'input_tokens':99}}
        a=j.evaluate('Use local SQLite.',q,'verification',self.root,send,lambda:'fixture')
        b=j.evaluate('Use local SQLite.',q,'verification',self.root,send,lambda:'fixture')
        self.assertEqual(len(sent),1);self.assertFalse(a['cached']);self.assertTrue(b['cached'])
        self.assertEqual(j.usage(self.root)['calls'][0]['input_tokens'],99)

    def test_spending_cap_blocks_before_network(self):
        self.cfg['daily_budget_usd']=0;(self.root/'System/hae-config.json').write_text(json.dumps(self.cfg))
        with patch.object(j,'transport') as send:
            with self.assertRaises(j.JevError):j.evaluate('test',{'q':{'type':'noul','instructions':'Is this relevant?'}},'verification',self.root)
        send.assert_not_called()

    def test_schema_failure_keeps_conservative_reserve(self):
        def send(*a):return {'model':'jev-1.13.0','answers':{'q':{'type':'noul','noul':float('nan')}},'usage':{'input_tokens':10}}
        with self.assertRaises(j.JevError):j.evaluate('test',{'q':{'type':'noul','instructions':'Is this relevant?'}},'verification',self.root,send,lambda:'fixture')
        row=j.usage(self.root)['calls'][0];self.assertEqual(row['status'],'failed');self.assertGreater(row['estimated_usd'],0)

    def test_large_request_rejected_before_network(self):
        with patch.object(j,'transport') as send:
            with self.assertRaises(j.JevError):j.evaluate('x'*33000,{'q':{'type':'noul','instructions':'Relevant?'}},'verification',self.root)
        send.assert_not_called()

    def test_oversize_capture_retains_review_evidence(self):
        p=self.capture('A'*2500)
        with patch.object(j,'evaluate') as send:result=jm.drain(self.root,True)
        send.assert_not_called();self.assertEqual(result['review_needed'],1);self.assertIn('A'*2500,p.read_text())


if __name__=='__main__':unittest.main()
