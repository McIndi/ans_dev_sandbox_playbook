import unittest
import sys
import os
import tempfile
import shutil
import base64
from unittest.mock import patch, MagicMock
from io import StringIO
from subprocess import CalledProcessError

# Add parent directory to path to import DECRYPT_VAULTED_ITEMS module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the module to be tested
# Mock pygments if not available
try:
    import pygments
except ImportError:
    sys.modules["pygments"] = MagicMock()
    sys.modules["pygments.formatters"] = MagicMock()
    sys.modules["pygments.lexers"] = MagicMock()

import DECRYPT_VAULTED_ITEMS

class TestDecryptVaultedItems(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_extract_vault_content_success(self):
        """Test extracting vault content successfully."""
        vault_id = "my_secret"
        vault_content = "$ANSIBLE_VAULT;1.1;AES256\n36373839...\n"
        file_content = f"""
other_stuff: value
{vault_id}: !vault |
    {vault_content.replace(chr(10), chr(10) + '    ')}
more_stuff: value
"""
        file_path = os.path.join(self.test_dir, "test_vault.yml")
        with open(file_path, "w") as f:
            f.write(file_content)

        extracted = DECRYPT_VAULTED_ITEMS.extract_vault_content(file_path, vault_id)
        # The extraction logic dedents, so we expect the original vault content
        # Note: The logic in extract_vault_content appends dedent(line).
        # If the vault content in the file is indented, dedent removes common leading whitespace.
        # Let's check what we expect.
        # In the file:
        #     $ANSIBLE_VAULT...
        #     3637...
        # dedent should remove the 4 spaces.
        
        # Re-constructing expected content based on how we wrote it
        expected_lines = [line for line in vault_content.splitlines(keepends=True)]
        expected = "".join(expected_lines)
        
        self.assertEqual(extracted.strip(), expected.strip())

    def test_extract_vault_content_id_not_found(self):
        """Test extracting vault content when ID is not found."""
        file_path = os.path.join(self.test_dir, "test_vault.yml")
        with open(file_path, "w") as f:
            f.write("some_other_id: value\n")

        with self.assertRaises(ValueError) as cm:
            DECRYPT_VAULTED_ITEMS.extract_vault_content(file_path, "missing_id")
        self.assertIn("missing_id id not found", str(cm.exception))

    def test_extract_vault_content_file_not_found(self):
        """Test extracting vault content when file does not exist."""
        with self.assertRaises(FileNotFoundError):
            DECRYPT_VAULTED_ITEMS.extract_vault_content("non_existent_file.yml", "some_id")

    @patch("DECRYPT_VAULTED_ITEMS.run")
    def test_decrypt_vault_success(self, mock_run):
        """Test decrypting vault content successfully."""
        mock_result = MagicMock()
        mock_result.stdout = b"decrypted_secret"
        mock_result.stderr = b""
        mock_run.return_value = mock_result

        stdout, stderr = DECRYPT_VAULTED_ITEMS.decrypt_vault("encrypted_data")
        
        self.assertEqual(stdout, b"decrypted_secret")
        self.assertEqual(stderr, b"")
        mock_run.assert_called_once()

    @patch("DECRYPT_VAULTED_ITEMS.run")
    def test_decrypt_vault_failure(self, mock_run):
        """Test decrypting vault content failure."""
        mock_error = CalledProcessError(1, "cmd", output=b"", stderr=b"decryption failed")
        mock_run.side_effect = mock_error

        stdout, stderr = DECRYPT_VAULTED_ITEMS.decrypt_vault("encrypted_data")
        
        self.assertEqual(stdout, b"") # CalledProcessError.stdout is usually output
        self.assertEqual(stderr, b"decryption failed")

    def test_attempt_base64_decode_valid(self):
        """Test base64 decoding valid data."""
        original = "hello world"
        encoded = base64.b64encode(original.encode()).decode()
        
        decoded, status, encoding = DECRYPT_VAULTED_ITEMS.attempt_base64_decode(encoded)
        
        self.assertEqual(decoded, original)
        self.assertTrue(status)
        self.assertEqual(encoding, "base64")

    def test_attempt_base64_decode_invalid(self):
        """Test base64 decoding invalid data."""
        invalid_data = "not base64 encoded string"
        
        decoded, status, encoding = DECRYPT_VAULTED_ITEMS.attempt_base64_decode(invalid_data)
        
        self.assertEqual(decoded, invalid_data)
        self.assertFalse(status)
        self.assertEqual(encoding, "none")

    def test_attempt_base64_decode_bytes(self):
        """Test base64 decoding with bytes input."""
        # If input is bytes and not valid base64, it should be decoded to string
        data = b"some bytes"
        decoded, status, encoding = DECRYPT_VAULTED_ITEMS.attempt_base64_decode(data)
        
        self.assertEqual(decoded, "some bytes")
        self.assertFalse(status)
        self.assertEqual(encoding, "none")

    @patch("sys.stdout", new_callable=StringIO)
    def test_format_output_no_color(self, mock_stdout):
        """Test formatting output without color."""
        data = {"key": "value"}
        DECRYPT_VAULTED_ITEMS.format_output(data, use_color=False)
        
        output = mock_stdout.getvalue()
        self.assertIn("key: value", output)

    @patch("sys.stdout", new_callable=StringIO)
    @patch("DECRYPT_VAULTED_ITEMS.pygments")
    def test_format_output_color(self, mock_pygments, mock_stdout):
        """Test formatting output with color."""
        # We need to mock pygments to avoid actual coloring codes in this test if we want simple verification,
        # or we can just verify that pygments.highlight was called.
        mock_pygments.highlight.return_value = "colored_output"
        
        data = {"key": "value"}
        DECRYPT_VAULTED_ITEMS.format_output(data, use_color=True)
        
        # Since we mocked print in the original code? No, the original code uses print().
        # But wait, format_output uses print(pygments.highlight(...))
        # So we capture stdout.
        
        output = mock_stdout.getvalue()
        self.assertIn("colored_output", output)
        mock_pygments.highlight.assert_called()

if __name__ == "__main__":
    unittest.main()
