import argparse
import os
import subprocess
import tempfile
from pathlib import Path
from unittest import mock, TestCase

import sandbox


class PythonSelectionTests(TestCase):
    def test_select_python_prefers_highest_under_315(self) -> None:
        candidates = [
            (Path("/usr/bin/python3.11"), (3, 11, 5)),
            (Path("/usr/bin/python3.14"), (3, 14, 2)),
            (Path("/usr/bin/python3.15"), (3, 15, 0)),
            (Path("/usr/bin/python3.12"), (3, 12, 0)),
        ]
        picked = sandbox.select_python(candidates)
        self.assertEqual(Path("/usr/bin/python3.14"), picked)


class ActivationTests(TestCase):
    def test_activate_writes_env_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            env_path = Path(td) / ".env"
            playbook_path = Path(td)

            with mock.patch.dict(os.environ, {"UNIT_TESTING": "1"}):
                args = argparse.Namespace(
                    env_file=str(env_path),
                    verbose=0,
                    log_file=None,
                    playbook_path=str(playbook_path),
                    command="activate",
                )
                code = sandbox.activate(args)

            self.assertEqual(sandbox.RETURN_CODES["SUCCESS"], code)
            content = env_path.read_text().splitlines()
            env_map = dict(line.split("=", 1) for line in content if line)
            self.assertEqual(str(playbook_path.resolve()), env_map["PLAYBOOK_PATH"])
            self.assertEqual("podman", env_map["CONTAINER_RUNTIME"])
            self.assertEqual("2222", env_map["CONTAINER_HOST_PORT"])
            self.assertEqual("ansible_target", env_map["CONTAINER_NAME"])
            self.assertTrue(env_map["ANSIBLE_VAULT_PASSWORD_FILE"].endswith("vault-pw.txt"))


class RuntimeDetectionTests(TestCase):
    @mock.patch("sandbox.shutil.which")
    def test_detect_container_runtime_prefers_podman(self, which: mock.MagicMock) -> None:
        which.side_effect = lambda name: "/usr/bin/podman" if name == "podman" else "/usr/bin/docker"
        runtime, volume = sandbox.detect_container_runtime()
        self.assertEqual("podman", runtime)
        self.assertEqual(":ro,z", volume)


class SSHKeyTests(TestCase):
    def test_setup_ssh_keys_creates_key_and_authorized(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)

            def fake_runner(args, *, capture=False, env=None):  # type: ignore[override]
                if args and args[0] == "ssh-keygen":
                    key_path = Path(args[-1])
                    key_path.write_text("PRIVATE")
                    key_path.with_suffix(".pub").write_text("PUBLIC")
                return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

            key_path, auth_path = sandbox.setup_ssh_keys(base, sandbox.DEFAULT_KEY_BASENAME, runner=fake_runner)
            self.assertTrue(key_path.exists())
            self.assertTrue(auth_path.exists())
            self.assertEqual("PUBLIC", auth_path.read_text())


class RolesCollectionsTests(TestCase):
    def test_setup_roles_links_sibling_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            playbook_path = workspace / "ans_dev_sandbox_playbook"
            sibling_role = workspace / "ans_dev_sandbox_role"
            roles_dir = playbook_path / "roles"
            roles_dir.mkdir(parents=True)
            (roles_dir / "requirements.yml").write_text("---\n")
            sibling_role.mkdir()

            calls = []

            def recorder(args, *, capture=False, env=None):  # type: ignore[override]
                calls.append(args)
                return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

            sandbox.setup_roles(playbook_path, runner=recorder)
            link_path = roles_dir / "ans_dev_sandbox_role"
            self.assertTrue(link_path.is_symlink())
            self.assertEqual([], calls)

    def test_setup_collections_installs_when_missing(self) -> None:
        installs: list[list[str]] = []

        def fake_runner(args, *, capture=False, env=None):  # type: ignore[override]
            if args[:3] == ["ansible-galaxy", "collection", "list"]:
                return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
            installs.append(args)
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

        sandbox.setup_collections(runner=fake_runner)
        self.assertIn(["ansible-galaxy", "collection", "install", "ansible.posix"], installs)
        self.assertIn(["ansible-galaxy", "collection", "install", "community.general"], installs)


class RunFlowTests(TestCase):
    @mock.patch("sandbox.run_playbook")
    @mock.patch("sandbox.setup_collections")
    @mock.patch("sandbox.setup_roles")
    @mock.patch("sandbox.setup_container")
    @mock.patch("sandbox.setup_vault")
    @mock.patch("sandbox.setup_ssh_keys")
    @mock.patch("sandbox.detect_ansible")
    @mock.patch("sandbox.detect_container_runtime")
    def test_run_skip_container_defaults_to_localhost_limit(
        self,
        runtime_fn: mock.MagicMock,
        ansible_fn: mock.MagicMock,
        ssh_fn: mock.MagicMock,
        vault_fn: mock.MagicMock,
        container_fn: mock.MagicMock,
        roles_fn: mock.MagicMock,
        collections_fn: mock.MagicMock,
        playbook_fn: mock.MagicMock,
    ) -> None:
        runtime_fn.return_value = ("podman", ":ro,z")
        ansible_fn.return_value = True
        with tempfile.TemporaryDirectory() as td:
            playbook_path = Path(td)
            (playbook_path / "inventory").mkdir()
            (playbook_path / "playbooks").mkdir()
            (playbook_path / "inventory" / "main.yml").write_text("---\n")
            (playbook_path / "playbooks" / "sample_playbook.yml").write_text("---\n")

            ssh_fn.return_value = (playbook_path / "ssh_keys/id", playbook_path / "ssh_keys/authorized_keys")
            vault_fn.return_value = playbook_path / "vault-pw.txt"

            args = argparse.Namespace(
                env_file=str(playbook_path / ".env"),
                verbose=0,
                log_file=None,
                container_runtime=None,
                container_name=None,
                container_host_port=None,
                skip_container=True,
                limit=None,
                playbook_path=str(playbook_path),
                command="run",
            )

            code = sandbox.run(args)

        self.assertEqual(sandbox.RETURN_CODES["SUCCESS"], code)
        playbook_fn.assert_called()
        called_args = playbook_fn.call_args.args
        self.assertEqual("localhost", called_args[3])
        container_fn.assert_not_called()


if __name__ == "__main__":
    import unittest

    unittest.main()
