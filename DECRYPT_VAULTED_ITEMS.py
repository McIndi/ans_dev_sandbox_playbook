"""Decrypt Ansible vault items from a YAML file."""

import argparse
import base64
import sys
import yaml
from io import StringIO
from subprocess import run, CalledProcessError
from textwrap import dedent

import pygments
import pygments.formatters
import pygments.lexers


def parse_arguments():
    """Parse and return command-line arguments."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
        prog="DECRYPT_VAULTED_ITEMS.py",
        epilog="Sample Command: python DECRYPT_VAULTED_ITEMS.py --color --decode --file foo.yml --id bar"
    )

    parser.add_argument(
        "-c",
        "--color",
        action="store_true",
        help="colorize the output for more readability",
    )

    parser.add_argument(
        "-d",
        "--decode",
        action="store_true",
        help="attempt to base64 decode the output",
    )

    parser.add_argument(
        "-f",
        "--file",
        required=True,
        help="the file used to store the ansible vault",
    )

    parser.add_argument(
        "-i",
        "--id",
        required=True,
        help="the ansible vault id to read and decrypt",
    )

    return parser.parse_args()

def extract_vault_content(file_path, vault_id):
    """Extract and return the vault content from the YAML file."""
    vault_marker = f"{vault_id}: !vault |"
    
    with open(file_path, "r") as fin:
        for line in fin:
            if line.startswith(vault_marker):
                break
        else:
            raise ValueError(f"{vault_id} id not found in {file_path} file")
        
        # Collect indented lines (vault content)
        content_lines = []
        for line in fin:
            if dedent(line) == line:  # Line is not indented
                break
            content_lines.append(dedent(line))
    
    return "".join(content_lines)


def decrypt_vault(vault_content):
    """Decrypt vault content using ansible-vault."""
    try:
        result = run(
            "ansible-vault decrypt",
            shell=True,
            input=vault_content.encode(),
            capture_output=True,
            check=True,
        )
        return result.stdout, result.stderr
    except CalledProcessError as e:
        return e.stdout, e.stderr


def attempt_base64_decode(data):
    """Attempt to base64 decode data. Return decoded data and status."""
    try:
        decoded = base64.b64decode(data).decode()
        return decoded, True, "base64"
    except (ValueError, UnicodeDecodeError):
        return data.decode() if isinstance(data, bytes) else data, False, "none"


def format_output(data, use_color=False):
    """Format and print output as YAML, optionally with syntax highlighting."""
    if use_color:
        fp = StringIO()
        yaml.dump(data, fp)
        fp.seek(0)
        s = fp.read()
        lexer = pygments.lexers.get_lexer_by_name("yaml")
        formatter = pygments.formatters.Terminal256Formatter()
        print(pygments.highlight(s, lexer, formatter))
    else:
        yaml.dump(data, sys.stdout)


def main():
    """Main entry point."""
    args = parse_arguments()
    
    try:
        vault_content = extract_vault_content(args.file, args.id)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    stdout, stderr = decrypt_vault(vault_content)
    
    if args.decode:
        output, decoded, encoding = attempt_base64_decode(stdout)
    else:
        output = stdout.decode()
        decoded = False
        encoding = "none"
    
    try:
        error_msg = stderr.decode()
    except (UnicodeDecodeError, AttributeError):
        error_msg = str(stderr)
    
    result = {
        "decrypted_vault": {
            "decoded": decoded,
            "encoding": encoding,
            "error": error_msg,
            "file": args.file,
            "id": args.id,
            "output": output,
        }
    }
    
    format_output(result, args.color)


if __name__ == "__main__":
    main()

