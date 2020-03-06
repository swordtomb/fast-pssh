import argparse
import os
import shlex
import sys

_DEFAULT_PARALLELISM = 32
# infinity 其实超时设置0是无限大
_DEFAULT_TIMEOUT = 0

def common_parser():

    parser = argparse.ArgumentParser(description="fast-pssh",
                                     conflict_handler="resolve")

    parser.epilog = "Example: fpssh -h nodes.txt -l irb2 -o /tmp/foo uptime"
    parser.add_argument("-h", "--hosts", dest="host_files", action="append",
                        metavar="HOST_FILE",
                        help="hosts file (each line '[user@]host[:port]')")
    parser.add_argument("-H", "--host",
                        dest="host_strings",
                        action="append",
                        help="additional host entries ('[user@]host[:port]')",
                        metavar="HOST_STRING")
    parser.add_argument("-l", "--user", dest="user",
                        help="username (OPTIONAL)")

    parser.add_argument("-p", "--par", dest="par", type=int,
                        help="max number of parallel threads (OPTIONAL)")
    parser.add_argument("-o", "--outdir", dest="outdir", 
                        help="output directory for stdout files (OPTIONAL)")
    parser.add_argument("-e", "--errdir", dest="errdir",
                        help="output directory for stderr files (OPTIONAL)")

    parser.add_argument("-t", "--timeout", dest="timeout", type=int,
                        help="timeout (secs) (0 = no timeout) per host (OPTIONAL)")
    parser.add_argument("-O", "--option", dest="options", action="append",
                        metavar="OPTION", help="SSH option (OPTIONAL)")
    parser.add_argument("-v", "--verbose", dest="verbose", action="store_true",
                        help="turn on warning and diagnostic messages (OPTIONAL)")
    parser.add_argument("-A", "--askpass", dest="askpass", action="store_true",
                        help="Ask for a password (OPTIONAL)")

    parser.add_argument('-x', '--extra-args', type=str,
                        metavar='ARGS', dest='extra',
                        help='Extra command-line arguments, with processing for '
                        'spaces, quotes, and backslashes')
    parser.add_argument('-X', '--extra-arg', dest='extra', action='append',
                        metavar='ARG', help='Extra command-line argument')

    parser.add_argument("-g", "--host-glob", dest="host_glob", type=str,
                        help="Shell-style glob to filter hosts (OPTIONAL)")

    return parser


def shlex_append(option, opt_str, value, parser):
    """An optparse callback similar to the append action.

    The given value is processed with shlex, and the resulting list is
    concatenated to the option's dest list.
    """
    lst = getattr(parser.values, option.dest)
    if lst is None:
        lst = []
        setattr(parser.values, option.dest, lst)
    lst.extend(shlex.split(value))


def common_defaults(**kwargs):
    defaults = dict(par=_DEFAULT_PARALLELISM, timeout=_DEFAULT_TIMEOUT)
    defaults.update(**kwargs)
    env_vars = [
        ('user', 'PSSH_USER'),
        ('par', 'PSSH_PAR'),
        ('outdir', 'PSSH_OUTDIR'),
        ('errdir', 'PSSH_ERRDIR'),
        ('timeout', 'PSSH_TIMEOUT'),
        ('verbose', 'PSSH_VERBOSE'),
        ('print_out', 'PSSH_PRINT'),
        ('askpass', 'PSSH_ASKPASS'),
        ('inline', 'PSSH_INLINE'),
        ('recursive', 'PSSH_RECURSIVE'),
        ('archive', 'PSSH_ARCHIVE'),
        ('compress', 'PSSH_COMPRESS'),
        ('localdir', 'PSSH_LOCALDIR'),
    ]

    for option, var in env_vars:
        value = os.getenv(var)
        if value:
            defaults[option] = value

    opt_env = os.getenv("PSSH_OPTIONS")
    if opt_env:
        defaults["options"] = [opt_env]

    # deprecated
    hosts_env = os.getenv("PSSH_HOSTS")
    if hosts_env:
        msg1 = ("deprecated")
        msg2 = ""

        sys.stderr.write('\n')
        sys.stderr.write('\n')

        defaults["host_files"] = [hosts_env]

    return defaults


if __name__ == "__main__":
    parser = common_parser()
    args = parser.parse_args(["-H", "foo"])
    print(args)