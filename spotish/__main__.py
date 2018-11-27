#!/usr/bin/env python3

'''
main module;
'''

from os.path import join
import argparse
import json
import os
import requests
import spotipy
import spotipy.util
import sys

##  program name;
prog='spotish'

##  album cache;
album_cache = set()

##  track cache;
track_cache = set()

def die(msg):

    '''
    die with a message;
    '''

    print('error: {}'.format(msg), file=sys.stderr)
    sys.exit(1)

def oplog(op_name, op_msg):

    '''
    log an operation;
    '''

    print('[{:20s}]{}'.format(op_name, op_msg), flush=True)

class help_formatter(argparse.HelpFormatter):

    '''
    formatter for generating usage messages and argument help strings;

    difference from super class:

    -   default indent increment is 4 (io: 2);

    -   default max help position is 48 (io: 24);

    -   short and long options are formatted together;

    -   sort actions by long option strings;
    '''

    def __init__(self, prog, indent_increment=4, max_help_position=48,
                 width=None):
        return super().__init__(
            prog=prog,
            indent_increment=indent_increment,
            max_help_position=max_help_position,
            width=width,
        )

    def _format_action_invocation(self, action):
        if not action.option_strings:
            default = self._get_default_metavar_for_positional(action)
            metavar, = self._metavar_formatter(action, default)(1)
            return metavar
        else:
            if action.nargs == 0:
                return '{}{}'.format(
                    ' ' * 4 * int(action.option_strings[0].startswith('--')),
                    ', '.join(action.option_strings),
                )
            else:
                default = self._get_default_metavar_for_optional(action)
                args_string = self._format_args(action, default)
                return '{}{}'.format(
                    ' ' * 4 * int(action.option_strings[0].startswith('--')),
                    ', '.join(action.option_strings),
                ) + ' ' + args_string

    def add_arguments(self, actions):
        actions = sorted(actions, key=lambda x: x.option_strings[::-1])
        super().add_arguments(actions)

def parse_args():

    '''
    parse command line arguments;
    '''

    ##  init arg parser;
    parser = argparse.ArgumentParser(
        prog=prog,
        usage='{} [options]'.format(prog),
        description='download saved tracks on spotify;',
        formatter_class=help_formatter,
        add_help=False,
    )

    ##  add arg;
    parser.add_argument(
        '-h', '--help',
        action='help',
        help='display help message;',
    )

    ##  add arg;
    parser.add_argument(
        '-u', '--user',
        type=str,
        metavar='{user}',
        help='spotify username;',
    )

    ##  add arg;
    parser.add_argument(
        '-i', '--client-id',
        type=str,
        metavar='{id}',
        help='client id;',
    )

    ##  add arg;
    parser.add_argument(
        '-s', '--client-secret',
        type=str,
        metavar='{secret}',
        help='client secret;',
    )

    ##  add arg;
    parser.add_argument(
        '-r', '--redirect-uri',
        type=str,
        metavar='{uri}',
        help='redirect uri;',
    )

    ##  add arg;
    parser.add_argument(
        '-o', '--output',
        type=str,
        default='tracks',
        metavar='{dir}',
        help='output dir (default=tracks);',
    )

    ##  add arg;
    parser.add_argument(
        '--album-image',
        action='store_true',
        help='download album image;',
    )

    ##  add arg;
    parser.add_argument(
        '--track-preview',
        action='store_true',
        help='download track preview;',
    )

    ##  add arg;
    parser.add_argument(
        '-d', '--debug',
        action='store_true',
        help='enable debug mode;',
    )

    ##  add arg;
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='enable verbose mode;',
    )

    ##  parse args;
    args = parser.parse_args()

    return args

def main():

    '''
    main function;
    '''

    ##  parse args;
    args = parse_args()

    if args.user is None:
        die('no user;')

    if args.client_id is None:
        die('no client id;')

    if args.client_secret is None:
        die('no client secret;')

    if args.redirect_uri is None:
        die('no redirect uri;')

    if args.output is None:
        die('no output dir;')

    ##  request access token;
    scope = ' '.join([
        'playlist-read-collaborative',
        'playlist-read-private',
        'user-library-read',
    ])

    token = spotipy.util.prompt_for_user_token(
        args.user,
        scope,
        client_id=args.client_id,
        client_secret=args.client_secret,
        redirect_uri=args.redirect_uri,
    )

    if token is None:
        die('cannot get token for {}'.format(args.user))

    ##  create spotipy client;
    sp = spotipy.Spotify(auth=token)

    ##  fetch saved tracks;
    limit = 20
    offset = 0
    while True:
        resp = sp.current_user_saved_tracks(limit=limit, offset=offset)

        ##  break when no more items;
        if len(resp['items']) == 0: break

        ##  dump raw json in debug mode;
        if args.debug:
            print(json.dumps(resp, indent=4))

        for item in resp['items']:
            ##  get track and album;
            track = item['track']
            album = track['album']

            ##  make track and album uuid;
            ##
            ##  `uri` guarantees uniqueness but isnt legible; `name` is legible
            ##  but doesnt guarantee uniqueness; uuid has both advantages;
            track_uuid = '{:02d}:{}:{}'.format(
                track['track_number'], track['uri'], track['name'])
            album_uuid = '{:02d}:{}:{}'.format(
                album['total_tracks'], album['uri'], album['name'])

            ##  make album dir;
            album_dir = join(args.output, album_uuid)
            os.makedirs(album_dir, exist_ok=True)

            ##  make track dir;
            track_dir = join(album_dir, track_uuid)
            os.makedirs(track_dir, exist_ok=True)

            ##  save album;
            if album['uri'] not in album_cache:
                album_cache.add(album['uri'])

                ##  save album json;
                album_json = join(album_dir, album_uuid + '.json')
                if args.verbose:
                    oplog('save album', album_uuid)
                with open(album_json, 'wt') as fp:
                    json.dump(album, fp, indent=4)

                ##  save album image;
                if args.album_image and album['images']:
                    album_img = join(album_dir, album_uuid + '.jpg')
                    if args.verbose:
                        oplog('save album img', album_uuid)
                    resp_ = requests.get(album['images'][0]['url'])
                    with open(album_img, 'wb') as fp:
                        fp.write(resp_.content)

            ##  save track;
            if track['uri'] not in track_cache:
                track_cache.add(track['uri'])

                ##  save track json;
                track_json = join(track_dir, track_uuid + '.json')
                if args.verbose:
                    oplog('save track', track_uuid)
                with open(track_json, 'wt') as fp:
                    json.dump(track, fp, indent=4)

                ##  save track preview;
                if args.track_preview and track['preview_url']:
                    track_preview = join(track_dir, track_uuid + '.mp3')
                    if args.verbose:
                        oplog('save track preview', track_uuid)
                    resp_ = requests.get(track['preview_url'])
                    with open(track_preview, 'wb') as fp:
                        fp.write(resp_.content)

        ##  fetch next page;
        offset += limit

if __name__ == '__main__':
    main()

