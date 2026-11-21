#!/usr/bin/env python3
"""Servidor local para la build de GitHub Actions.

  GET  /health             -> "ok"
  GET  /dump.tar           -> sirve el dump al runner (protegido por X-Token)
  POST /chunk  (X-Chunk: ipa/part_XXX  o  romfs/part_XXX)
                           -> guarda un trozo cifrado
  POST /finish             -> une los trozos en ACNH.ipa.enc y RomFS.img.enc

Escucha solo en 127.0.0.1:8080; cloudflared expone ese puerto al exterior.
"""
import hashlib
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
TOKEN = os.environ.get('RECEIVER_TOKEN') or (sys.argv[2] if len(sys.argv) > 2 else '')
PARTS = ROOT / 'parts'
OUT = ROOT / 'out'
DUMP = ROOT / 'dump.tar'
PORT = int(os.environ.get('PORT', '8080'))
CHUNK = 1024 * 1024


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def _send(self, code, body=b''):
        self.send_response(code)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _auth(self):
        return bool(TOKEN) and self.headers.get('X-Token') == TOKEN

    def do_GET(self):
        if self.path == '/health':
            self._send(200, b'ok\n')
            return
        if not self._auth():
            self._send(403, b'forbidden\n')
            return
        if self.path == '/dump.tar':
            if not DUMP.is_file():
                self._send(404, b'no dump.tar\n')
                return
            self.send_response(200)
            self.send_header('Content-Length', str(DUMP.stat().st_size))
            self.send_header('Content-Type', 'application/x-tar')
            self.end_headers()
            with DUMP.open('rb') as f:
                while True:
                    data = f.read(CHUNK)
                    if not data:
                        break
                    self.wfile.write(data)
            return
        self._send(404, b'not found\n')

    def do_POST(self):
        if not self._auth():
            self._send(403, b'forbidden\n')
            return
        if self.path == '/chunk':
            raw = self.headers.get('X-Chunk', '')
            pieces = raw.split('/')
            if len(pieces) != 2 or pieces[0] not in ('ipa', 'romfs'):
                self._send(400, b'bad chunk name\n')
                return
            group, name = pieces
            if not name or any(c in name for c in '/\\') or '..' in name:
                self._send(400, b'bad chunk name\n')
                return
            length = int(self.headers.get('Content-Length', '0'))
            dest_dir = PARTS / group
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / name
            remaining = length
            with dest.open('wb') as f:
                while remaining > 0:
                    data = self.rfile.read(min(CHUNK, remaining))
                    if not data:
                        break
                    f.write(data)
                    remaining -= len(data)
            self._send(200, f'{group}/{name} {dest.stat().st_size}\n'.encode())
            return
        if self.path == '/finish':
            OUT.mkdir(exist_ok=True)
            reply = []
            for group, filename in (('ipa', 'ACNH.ipa.enc'), ('romfs', 'RomFS.img.enc')):
                # El workflow envia chunks como ipa_* y romfs_* (no part_*).
                files = sorted((PARTS / group).glob(f'{group}_*'))
                if not files:
                    self._send(400, f'no chunks for {group}\n'.encode())
                    return
                digest = hashlib.sha256()
                target = OUT / filename
                with target.open('wb') as out:
                    for part in files:
                        with part.open('rb') as f:
                            while True:
                                data = f.read(CHUNK)
                                if not data:
                                    break
                                out.write(data)
                                digest.update(data)
                line = f'{filename} {target.stat().st_size} bytes sha256={digest.hexdigest()}'
                reply.append(line)
                print('[receiver] ' + line, flush=True)
            self._send(200, ('\n'.join(reply) + '\n').encode())
            return
        self._send(404, b'not found\n')


if __name__ == '__main__':
    ROOT.mkdir(parents=True, exist_ok=True)
    print(f'[receiver] root={ROOT} port={PORT} token={"set" if TOKEN else "EMPTY"}', flush=True)
    ThreadingHTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
