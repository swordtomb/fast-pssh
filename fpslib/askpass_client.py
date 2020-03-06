import os
import socket
import sys

def askpass_main():

    verbose = os.getenv("PSSH_ASKPASS_VERBOSE")

    if len(sys.argv) > 1:
        prompt = sys.argv[1]
        if verbose:
            sys.stderr.write(f"pssh-askpass received prompt: {prompt}\n")
        if not (
                prompt.strip().lower().endswith("password:") or
                "enter passphrase for key" in prompt.strip().lower()
        ):
            sys.stderr.write(prompt)
            sys.stderr.write('\n')
            sys.exit(1)
    else:
        sys.stderr.write("Error: pass-askpass called without a prompt.\n")
        sys.exit(1)

    address = os.getenv("PSSH_ASKPASS_SOCKET")
    sock = socket.socket(socket.AF_UNIX)
    try:
        sock.connect(address)
    except socket.error:
        _, e, _ = sys.exc_info()
        msg = e.args[1]
        sys.stderr.write(f"Couldn't bind to {address}: {msg}.\n")
        sys.exit(2)

    try:
        password = sock.makefile().read()
    except socket.error:
        sys.stderr.write("Socket error.\n")
        sys.exit(3)

    print(password)

if "__main__" == __name__:
    askpass_main()
