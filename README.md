# ACNH → IPA desde Linux usando GitHub Actions (gratis)

El runner `xcode-27` es una Mac en la nube. Desde tu Linux solo haces de "servidor de archivos":
el runner baja tu dump, compila con nxnative y te devuelve el IPA cifrado por chunks.
**No se usa `upload-artifact`**, así que no gastas los 500 MB gratis de artefactos.

## Antes de empezar

- Cuenta de GitHub.
- Tus `prod.keys` (guárdalos en `~/keys/prod.keys`; no los pegues en ningún chat).
- **Importante:** tienes solo la base v0. nxnative está probado en **3.0.3 + Happy Home Paradise**.
  Si tienes el update y el DLC, ponlos en la misma carpeta antes del paso 4. Si no, se compilará la v0.

## 1. Login de GitHub (lo haces tú, yo no veo tus credenciales)

```bash
~/.local/bin/gh auth login -h github.com -p https -w -s repo,workflow
```

## 2. Crear el repo público y subir el workflow

```bash
cd /home/alioli/acnh-actions
git init -b main
git add .
git commit -m "ACNH Actions workflow"
~/.local/bin/gh repo create acnh-actions --public --source=. --remote=origin --push
```

## 3. Preparar el dump (solo si cambias los archivos del juego)

```bash
cd /home/alioli/acnh-actions
./server/prepare_dump.sh
```

Genera `server/dump.tar` (~6,3 GB). Vuelve a ejecutarlo si añades update o DLC.

## 4. Arrancar el túnel (terminal 1, déjala abierta)

```bash
cd /home/alioli/acnh-actions
./server/start_tunnel.sh
```

Aparecerá una URL tipo `https://abc-def.trycloudflare.com`. Cópiala.

## 5. Poner los secretos (terminal 2)

```bash
cd /home/alioli/acnh-actions
GH=~/.local/bin/gh

# token local (el workflow y el receiver deben usar el mismo)
$GH secret set TOKEN < server/token.txt

# contraseña para cifrar el IPA (te la pedirá sin mostrarla)
read -srp 'Passphrase: ' P; echo; printf '%s' "$P" | $GH secret set IPA_PASS; unset P

# tus claves, codificadas; no se muestran
$GH secret set PROD_KEYS_B64 < <(base64 -w0 ~/keys/prod.keys)

# URL del túnel del paso 4
read -rp 'URL de cloudflared (sin /): ' U
printf '%s/dump.tar' "$U" | $GH secret set DUMP_URL
printf '%s' "$U" | $GH secret set UPLOAD_URL
```

## 6. Lanzar la build

```bash
cd /home/alioli/acnh-actions
~/.local/bin/gh workflow run build-acnh.yml
~/.local/bin/gh run watch
```

Tarda 1–2 h. Al terminar, el receiver guarda `server/out/ACNH.ipa.enc` y
`server/out/RomFS.img.enc` y muestra sus SHA-256.

## 7. Descifrar

```bash
cd /home/alioli/acnh-actions
read -srp 'Passphrase: ' P; echo
export P
openssl enc -d -aes-256-cbc -pbkdf2 -pass env:P -in server/out/ACNH.ipa.enc -out ACNH.ipa
openssl enc -d -aes-256-cbc -pbkdf2 -pass env:P -in server/out/RomFS.img.enc -out RomFS.img
unset P
ls -lh ACNH.ipa RomFS.img
```

## 8. Instalar

- Firma `ACNH.ipa` con AltStore Classic / SideStore / LiveContainer (con *Increased Memory Limit*).
- Como se usó `--romfs separate`, copia `RomFS.img` una vez a la carpeta `Documents` de la app
  siguiendo el comando `scripts/push_romfs.sh` que imprime el build (o con la app de archivos).
- El IPA no incluye el juego completo sin ese `RomFS.img`.

## Notas

- Repo público = runner gratis. Por eso el IPA viaja cifrado y con token.
- Cierra el túnel (Ctrl+C en la terminal 1) cuando acabes.
- No subas nunca `dump.tar`, `prod.keys`, `ACNH.ipa` ni `RomFS.img` al repo (ya están en `.gitignore`).
