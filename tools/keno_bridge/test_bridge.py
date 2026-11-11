import contextlib
import copy
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

from . import bridge as b
from .gateway import Gateway

class FakeGitHub:
    def __init__(self):
        self.issue = dict(number=9, state='open', title='Harmless test', body='Verify only')
        self.comments = [dict(id=10, user={'login': b.OWNER}, body='/keno approve ' + b.digest(self.issue))]
        self.posts = []
        self.fail_post = False
        self.prs = []

    def assignment(self, number):
        assert number == self.issue['number']
        return copy.deepcopy(self.issue), copy.deepcopy(self.comments)

    def post(self, number, body):
        if self.fail_post:
            raise b.Blocked('Offline')
        self.posts.append(body)
        self.comments.append(dict(id=len(self.comments)+10, user={'login': b.OWNER}, body=body))

    def api(self, endpoint, payload=None):
        self.prs.append(payload)
        return {'html_url': 'https://github.com/jasahasch/Keno/pull/999'}

class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = b.checked_state(self.root / 'state')
        self.repo = self.root / 'source'
        self.repo.mkdir()
        self.rawgit('init', '-b', 'main', cwd=self.repo)
        self.rawgit('config', 'user.name', 'Test', cwd=self.repo)
        self.rawgit('config', 'user.email', 'test@example.invalid', cwd=self.repo)
        (self.repo / 'docs').mkdir()
        (self.repo / 'docs/test.md').write_text('original\n')
        (self.repo / 'outputs').mkdir()
        (self.repo / 'outputs/certificate.json').write_text('{"evidence":"immutable"}\n')
        self.rawgit('add', '.', cwd=self.repo)
        self.rawgit('commit', '-m', 'fixture', cwd=self.repo)
        self.private = self.root / 'private.sqlite'
        self.private.write_bytes(b'private sentinel')
        self.gh = FakeGitHub()

    def rawgit(self, *args, cwd):
        return subprocess.check_output(['git', *args], cwd=cwd, text=True, stderr=subprocess.DEVNULL)

    def adapter(self, *args, cwd=None):
        if args[0] == 'clone':
            return self.rawgit('clone', '--no-hardlinks', '--no-checkout', str(self.repo), args[-1], cwd=self.root)
        return self.original_git(*args, cwd=cwd)

    @contextlib.contextmanager
    def execution(self, supervise=None):
        self.original_git = b.git
        with patch.object(b, 'git', side_effect=self.adapter), \
             patch.object(b, 'sandbox', side_effect=lambda work, codex, socket: ['sandbox', str(socket)]), \
             patch.object(b, 'Gateway') as gateway, \
             patch.object(b, 'supervise', side_effect=supervise or (lambda *a, **k: 0)):
            gateway.return_value.__enter__.return_value.path = self.state / 'api.sock'
            yield

    def run_fixture(self, **kwargs):
        return b.execute(self.state, self.gh, 9, b.digest(self.gh.issue), Path('/bin/true'), 1, **kwargs)

    def work(self):
        return next(self.state.glob('issue-*/worktree'))

    def test_owner_approval_binds_revision(self):
        self.assertEqual(b.approved(self.gh.issue, self.gh.comments), 10)
        self.gh.issue['body'] += ' new instructions'
        with self.assertRaises(b.Blocked):
            b.approved(self.gh.issue, self.gh.comments)

    def test_nonowner_and_quoted_approvals_rejected(self):
        self.gh.comments[0]['user']['login'] = 'attacker'
        with self.assertRaises(b.Blocked):
            b.approved(self.gh.issue, self.gh.comments)
        self.gh.comments[0]['user']['login'] = b.OWNER
        self.gh.comments[0]['body'] = '> ' + self.gh.comments[0]['body']
        with self.assertRaises(b.Blocked):
            b.approved(self.gh.issue, self.gh.comments)

    def test_legacy_approval_limited_to_initial_issue_and_comment(self):
        issue = dict(self.gh.issue, number=1)
        comment = dict(id=6784188375, user={'login': b.OWNER}, body='**OWNER APPROVAL — EXECUTE ISSUE #1**\nApproved')
        self.assertEqual(b.approved(issue, [comment]), comment['id'])
        with self.assertRaises(b.Blocked):
            b.approved(self.gh.issue, [comment])
        comment['id'] += 1
        with self.assertRaises(b.Blocked):
            b.approved(issue, [comment])

    def test_supervisor_digest_required_before_any_reservation(self):
        with self.assertRaises(b.Blocked):
            b.execute(self.state, self.gh, 9, 'wrong', Path('/bin/true'), 1)
        self.assertFalse((self.state / 'runs.sqlite').exists())

    def test_durable_duplicate_prevention(self):
        with b.ledger(self.state) as first:
            b.reserve(first, 9, 'a'*64)
        with b.ledger(self.state) as second:
            with self.assertRaises(b.Blocked):
                b.reserve(second, 9, 'a'*64)

    def test_concurrent_operation_rejected(self):
        with b.locked(self.state):
            with self.assertRaises(b.Blocked):
                with b.locked(self.state):
                    pass

    def test_state_symlink_and_world_readable_state_rejected(self):
        link = self.root / 'link'
        link.symlink_to(self.state)
        with self.assertRaises(b.Blocked):
            b.checked_state(link)
        self.state.chmod(0o755)
        with self.assertRaises(b.Blocked):
            b.checked_state(self.state)

    def test_state_cannot_reuse_private_directory_or_live_checkout(self):
        private_dir = self.root / 'private-data'
        private_dir.mkdir(mode=0o700)
        evidence = private_dir / 'runs.sqlite'
        evidence.write_bytes(b'private data')
        with self.assertRaises(b.Blocked):
            b.checked_state(private_dir)
        with self.assertRaises(b.Blocked):
            b.checked_state(self.repo / 'bridge-state')
        self.assertEqual(evidence.read_bytes(), b'private data')
        self.assertFalse((self.repo / 'bridge-state').exists())

    def test_timeout_kills_process_group(self):
        sentinel = self.root / 'should-not-exist'
        with self.assertRaises(subprocess.TimeoutExpired):
            b.supervise(['/bin/sh', '-c', 'sleep 0.3; touch "$1"', 'sh', str(sentinel)],
                        self.root / 'timeout.log', 0.03)
        time.sleep(0.4)
        self.assertFalse(sentinel.exists())

    def test_smoke_complete_flow_and_no_duplicate_execution(self):
        before = self.private.read_bytes()
        def check_socket(args, *unused, **kwargs):
            if '/runner/smoke.py' in args:
                self.assertEqual(Path(args[1]).name, 'empty')
            return 0

        with self.execution(check_socket):
            result = self.run_fixture(smoke=True)
            with self.assertRaises(b.Blocked):
                self.run_fixture(smoke=True)
        self.assertEqual(result['status'], 'completed-no-source-changes')
        self.assertTrue(result['smoke_verified'])
        self.assertEqual(len(self.gh.posts), 1)
        self.assertEqual(before, self.private.read_bytes())
        self.assertEqual(self.rawgit('status', '--porcelain', cwd=self.repo), '')

    def test_failed_namespace_probe_never_starts_codex(self):
        calls = []
        def fail(args, *a, **kw):
            calls.append(args)
            return 1
        with self.execution(fail):
            result = self.run_fixture()
        self.assertEqual(result['status'], 'blocked')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][-1], '/bin/true')

    def test_agent_timeout_is_reported(self):
        def timeout(args, *a, **kw):
            if '/bin/true' not in args:
                raise subprocess.TimeoutExpired('agent', 1)
            return 0
        with self.execution(timeout):
            result = self.run_fixture()
        self.assertEqual(result['status'], 'timed-out')
        self.assertIn('timed-out', self.gh.posts[0])

    def test_smoke_rejects_source_edits(self):
        def edit(args, *a, **kw):
            if '/bin/true' not in args:
                (self.work() / 'docs/test.md').write_text('modified')
            return 0
        with self.execution(edit):
            result = self.run_fixture(smoke=True)
        self.assertEqual(result['status'], 'blocked')

    def test_report_retry_does_not_execute_agent(self):
        self.gh.fail_post = True
        with self.execution():
            with self.assertRaises(b.Blocked):
                self.run_fixture()
        self.gh.fail_post = False
        key = next(self.state.glob('issue-*')).name
        with b.ledger(self.state) as db:
            b.publish_report(self.gh, db, key)
            b.publish_report(self.gh, db, key)
        self.assertEqual(len(self.gh.posts), 1)

    def test_report_recovers_remote_acceptance_before_local_ack(self):
        with self.execution():
            result = self.run_fixture()
        with b.ledger(self.state) as db:
            db.execute('UPDATE runs SET posted=0'); db.commit()
            b.publish_report(self.gh, db, result['key'])
        self.assertEqual(len(self.gh.posts), 1)

    def test_public_report_never_contains_logs_paths_or_issue_instructions(self):
        report = dict(key='safe', digest='abc', status='blocked', local_reason='SECRET_PASSWORD',
                      log='private.sqlite', title='injected @everyone')
        body = b.report_text(report)
        for secret in ('SECRET_PASSWORD', 'private.sqlite', '@everyone'):
            self.assertNotIn(secret, body)

    def test_publication_rejects_private_evidence_binary_symlink_and_secret(self):
        baseline = b.source_inventory(self.repo)
        cases = [('outputs/certificate.json', b'changed'), ('docs/private.sqlite', b'private'),
                 ('docs/binary.md', b'\x00binary'), ('docs/secret.md', b'-----BEGIN ' + b'RSA PRIVATE KEY-----')]
        for path, content in cases:
            file = self.repo / path
            old = file.read_bytes() if file.exists() else None
            file.write_bytes(content)
            with self.subTest(path=path), self.assertRaises(b.Blocked):
                b.collect_changes(self.repo, baseline)
            if old is None:
                file.unlink()
            else:
                file.write_bytes(old)
        (self.repo / 'docs/link.md').symlink_to(self.private)
        with self.assertRaises(b.Blocked):
            b.collect_changes(self.repo, baseline)

    def test_changes_are_review_bound(self):
        baseline = b.source_inventory(self.repo)
        (self.repo / 'docs/test.md').write_text('review me\n')
        changes, first = b.collect_changes(self.repo, baseline)
        self.assertEqual(changes, ['docs/test.md'])
        (self.repo / 'docs/test.md').write_text('different\n')
        self.assertNotEqual(first, b.collect_changes(self.repo, baseline)[1])

    def test_source_checkout_rejects_symlinks(self):
        (self.repo / 'docs/link').symlink_to(self.private)
        self.rawgit('add', 'docs/link', cwd=self.repo)
        with self.assertRaises(b.Blocked):
            b.source_inventory(self.repo)

    def test_publish_requires_review_and_never_merges(self):
        def edit(args, *a, **kw):
            if '/bin/true' not in args:
                (self.work() / 'docs/test.md').write_text('source change\n')
            return 0
        with self.execution(edit):
            result = self.run_fixture()
        self.assertEqual(result['status'], 'awaiting-source-review')
        with self.assertRaises(b.Blocked):
            b.publish(self.state, self.gh, result['key'], 'wrong')
        calls = []
        original = b.git
        def git(*args, **kw):
            calls.append(args)
            if 'push' in args:
                return ''
            return original(*args, **kw)
        with patch.object(b, 'git', side_effect=git):
            report = b.publish(self.state, self.gh, result['key'], result['review_sha256'])
        self.assertEqual(report['status'], 'pr-opened')
        self.assertTrue(self.gh.prs[0]['draft'])
        self.assertFalse(any('merge' in args or '--force' in args or 'reset' in args for args in calls))
        self.assertEqual(self.private.read_bytes(), b'private sentinel')

    def test_assignment_edit_blocks_publication(self):
        def edit(args, *a, **kw):
            if '/bin/true' not in args:
                (self.work() / 'docs/test.md').write_text('source change\n')
            return 0
        with self.execution(edit):
            result = self.run_fixture()
        self.gh.issue['body'] = 'changed assignment'
        with self.assertRaises(b.Blocked):
            b.publish(self.state, self.gh, result['key'], result['review_sha256'])

    def test_sandbox_has_no_host_home_git_credentials_or_network(self):
        # Build the actual mount policy, without claiming the kernel executed it.
        work = self.root / 'work'
        work.mkdir(); (work / '.git').touch(); (work / 'outputs').mkdir()
        (work / '.codex').mkdir()
        args = b.sandbox(work, Path('/bin/true'), self.root / 'socket')
        self.assertIn('--unshare-all', args)
        self.assertNotIn('--share-net', args)
        self.assertIn('--clearenv', args)
        self.assertIn('--cap-drop', args)
        self.assertNotIn('GH_TOKEN', ' '.join(args))
        self.assertNotIn('OPENAI_API_KEY', ' '.join(args))
        self.assertNotIn(str(Path.home()), args)
        self.assertIn('/work/outputs', args)
        self.assertIn('/work/.git', args)
        self.assertIn('/work/.codex', args)

    def test_no_unsandboxed_fallback_when_bubblewrap_missing(self):
        with patch.object(b.shutil, 'which', return_value=None), self.assertRaises(b.Blocked):
            b.sandbox(self.repo, Path('/bin/true'), self.root / 'socket')

    def test_gateway_rejects_arbitrary_destination_and_does_not_expose_key(self):
        import http.client
        class Connection(http.client.HTTPConnection):
            def connect(conn):
                conn.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                conn.sock.connect(str(self.state / 'test.sock'))
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'private-sentinel-key'}):
            with Gateway(self.state / 'test.sock'):
                conn = Connection('localhost')
                conn.request('POST', '/https://github.com/steal', b'{}')
                response = conn.getresponse()
                self.assertEqual(response.status, 403)
                self.assertNotIn(b'private-sentinel-key', response.read())
                conn.close()
        self.assertFalse((self.state / 'test.sock').exists())

    def test_api_requests_use_structured_stdin_not_shell(self):
        payload = {'body': '$(touch /tmp/pwned); `malicious`'}
        with patch.object(b, 'command', return_value='{}') as run:
            b.GitHub().api('repos/jasahasch/Keno/issues/9/comments', payload)
        args, kwargs = run.call_args
        self.assertEqual(args[0][-2:], ['--input', '-'])
        self.assertEqual(json.loads(kwargs['input']), payload)

    def test_github_retrieval_rejects_closed_issue_pr_and_wrong_host_identity(self):
        gh = b.GitHub()
        for issue in ({'state': 'closed'}, {'state': 'open', 'pull_request': {'url': 'x'}}):
            with patch.object(gh, 'api', side_effect=[{'login': b.OWNER}, issue]):
                with self.assertRaises(b.Blocked):
                    gh.assignment(9)
        with patch.object(gh, 'api', return_value={'login': 'other-account'}):
            with self.assertRaises(b.Blocked):
                gh.assignment(9)

    def test_gateway_uses_fixed_upstream_and_host_only_oauth(self):
        import http.client
        from . import gateway as g
        auth = self.state / 'auth.json'
        auth.write_text(json.dumps({'tokens': {'access_token': 'oauth-sentinel', 'account_id': 'account-sentinel'}}))
        class Connection(http.client.HTTPConnection):
            def connect(conn):
                conn.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                conn.sock.connect(str(self.state / 'test.sock'))
        class Response:
            status = 200
            headers = {'Content-Type': 'application/json'}
            def __enter__(response):
                response.remaining = b'{}'
                return response
            def __exit__(response, *args):
                pass
            def read1(response, size):
                content, response.remaining = response.remaining, b''
                return content
        with patch.dict(os.environ, {'OPENAI_API_KEY': ''}), patch.object(g.urllib.request, 'build_opener') as factory:
            factory.return_value.open.return_value = Response()
            with Gateway(self.state / 'test.sock', auth):
                conn = Connection('localhost')
                conn.request('POST', '/v1/responses', b'{}', {'Authorization': 'Bearer attacker', 'X-Forwarded-Host': 'evil'})
                response = conn.getresponse()
                self.assertEqual(response.status, 200)
                self.assertEqual(response.read(), b'{}')
                conn.close()
            request = factory.return_value.open.call_args.args[0]
            self.assertEqual(request.full_url, 'https://chatgpt.com/backend-api/codex/responses')
            self.assertEqual(request.get_header('Authorization'), 'Bearer oauth-sentinel')
            self.assertNotIn('evil', str(request.headers))

    def test_gateway_requires_valid_host_credentials(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': ''}):
            with self.assertRaises(ValueError):
                with Gateway(self.state / 'missing.sock', self.state / 'missing-auth.json'):
                    pass

if __name__ == '__main__':
    unittest.main()
