import argparse


def base_parser():

    parser = argparse.ArgumentParser(description='fast-pssh',
                                     epilog='Thank you for your use.')

    parser.add_argument('-H', '--host',
                        dest='host',
                        action='append',
                        help='host name',
                        metavar='HOST_STRING')
    parser.add_argument("-p", '--par', dest="par")
    parser.add_argument("-o", "--outdir", dest="outdir")
    parser.add_argument("-i", "--inline", dest="inline")
    parser.add_argument("-c", dest="cmd", action="store")

    return parser


if __name__ == '__main__':
    parser = base_parser()
    args = parser.parse_args(['-H', 'foo'])
    print(args)