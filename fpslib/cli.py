import argparse


def base_parser():

    parser = argparse.ArgumentParser(description='fast-pssh',
                                     epilog='Thank you for your use.')

    parser.add_argument('-H', '--host',
                        dest='host',
                        action='append',
                        help='host name',
                        metavar='HOST_STRING')

    return parser


if __name__ == '__main__':
    parser = base_parser()
    args = parser.parse_args(['-H', 'foo'])
    print(args)