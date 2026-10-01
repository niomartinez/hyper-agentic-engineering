"""Shell-specific rendering of trusted argument vectors; no user text is executed."""
import base64
import os
import shlex


def powershell(argv):
    return '& ' + ' '.join("'" + str(arg).replace("'", "''") + "'" for arg in argv)


def display(argv):
    return powershell(argv) if os.name == 'nt' else shlex.join([str(a) for a in argv])


def windows_hook(argv):
    # Works when the host launches through cmd, PowerShell or Git Bash. The
    # encoded script contains literal quoted argv; %, $, ` and & in paths stay data.
    script = powershell(argv) + '; exit $LASTEXITCODE'
    encoded = base64.b64encode(script.encode('utf-16-le')).decode('ascii')
    return 'powershell.exe -NoLogo -NoProfile -NonInteractive -EncodedCommand ' + encoded
