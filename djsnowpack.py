import time
import json
import os
import psutil
import socket
import subprocess

from django.conf import settings
from urllib.request import urlopen
from xml.etree.ElementTree import ElementTree

DJSNOWPACK = dict(
    WORKDIR=settings.BASE_DIR,
)
DJSNOWPACK.update(getattr(settings, 'DJSNOWPACK', dict()))


def snowpack_start():
    path = os.path.join(
        settings.DJSNOWPACK['WORKDIR'],
        '.djsnowpack.json',
    )
    data = dict()

    if os.path.exists(path):
        with open(path, 'r') as f:
            try:
                data = json.load(f)
            except json.DecodeError:
                pass

        pid = data.get('pid', None)
        if pid:
            try:
                proc = psutil.Process(pid)
            except psutil.NoSuchProcess:
                pass
            else:
                return data.get('port')

    data['port'] = 8080
    while data['port'] < 65_000:
        try:
            test = socket.create_server(('localhost', data['port']))
        except OSError:
            data['port'] += 1
        else:
            test.close()
            break

    if os.fork() == 0:
        data['pid'] = os.getpid()
        with open(path, 'w+') as f:
            json.dump(data, f)

        npm = DJSNOWPACK.get(
            'NPM',
            subprocess.check_output(
                'type npm',
                shell=True,
            ).strip().decode('utf8').split()[-1]
        )

        os.execv(npm, [
            'npm',
            'start',
            '--',
            '--devOptions.port=' + str(data['port']),
            '--devOptions.output=stream',
            '--devOptions.open=none',
        ])

    while True:
        try:
            with urlopen('http://localhost:' + str(data['port'])) as conn:
                conn.read()
                time.sleep(.05)
        except:
            continue
        else:
            break

    return data['port']


class Middleware:
    marker_script = b'<!-- djsnowpack-script -->'
    marker_style = b'<!-- djsnowpack-style -->'

    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        response = self.get_response(request)

        if self.marker_script not in response.content:
            response.content = response.content.replace(
                b'</body>',
                self.marker_script + b'</body>',
            )

        if self.marker_style not in response.content:
            response.content = response.content.replace(
                b'</head>',
                self.marker_style + b'</head>',
            )

        if settings.DEBUG:
            tree = ElementTree()
            port = snowpack_start()
            url = f'http://localhost:{port}'

            with urlopen(f'http://localhost:{port}') as conn:
                tree.parse(conn)

            for script in tree.findall('body/script'):
                if src := script.attrib.get('src', False):
                    src = src + '/' if not src.startswith('/') else src
                    script.attrib['src'] = f'http://localhost:{port}' + src

                tag = ['<script']
                tag += [f'{k}="{v}"' for k, v in script.attrib.items()]
                tag.append('></script>')
                tag = b' '.join([v.encode('utf8') for v in tag])

                response.content = response.content.replace(
                    self.marker_script,
                    tag + self.marker_script
                )

            response.content = response.content.replace(
                self.marker_script,
                b'<script type="text/javascript">window.HMR_WEBSOCKET_URL="ws://localhost:'
                + str(port).encode('utf8')
                + b'/"</script>'
                + self.marker_script
            )

            for link in tree.findall('head/link'):
                if src := script.attrib.get('href', False):
                    src = src + '/' if not src.startswith('/') else src
                    script.attrib['href'] = f'http://localhost:{port}' + src

                tag = ['<link']
                tag += [f'{k}="{v}"' for k, v in link.attrib.items()]
                tag.append('/>')
                tag = b' '.join([v.encode('utf8') for v in tag])

                response.content = response.content.replace(
                    self.marker_style,
                    tag + self.marker_style
                )


        # Code to be executed for each request/response after
        # the view is called.

        return response
