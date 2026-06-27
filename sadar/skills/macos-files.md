---
name: macos-files
description: Mengelola berkas & folder di Mac (lokal) memakai tool 'shell'. Lihat (ls -la, find, du -sh, stat) = langsung. Buat/susun (mkdir -p, touch, cp -R, mv untuk pindah/ganti-nama), buka di Finder (open). HAPUS AMAN - utamakan pindahkan ke Tempat Sampah (mv TARGET ~/.Trash/) yang reversibel, bukan rm permanen. Operasi mutasi otomatis minta konfirmasi; selalu pastikan path dulu, jangan menebak lokasi.
tools: [shell]
when: Saat Pak Syam minta mengelola berkas/folder di Mac-nya - membuat, mencari, menyusun, menyalin, memindah, merapikan, atau menghapus.
required_caps: [shell.read, shell.write]
status: active
author: builtin
---
# Playbook manajemen berkas & folder macOS (untuk manusia & otak)

Skill ini TIDAK menambah kuasa baru — hanya know-how memakai tool `shell` (lokal) untuk operasi berkas.

## Lihat (baca — jalan langsung)
- Daftar isi: `ls -la <dir>`
- Cari: `find <dir> -name '*.pdf'` · `find <dir> -type d`
- Ukuran: `du -sh <dir>` · `du -sh <dir>/*` (per-isi) · ruang disk `df -h`
- Detail: `stat <file>` · jenis `file <file>` · awal/akhir `head`/`tail`

## Buat & susun (mutasi → konfirmasi HITL)
- Folder: `mkdir -p <dir>`  · Berkas kosong: `touch <file>`
- Salin: `cp -R <sumber> <tujuan>`  · Pindah / ganti nama: `mv <sumber> <tujuan>`

## Hapus — UTAMAKAN yang reversibel
- **Pindahkan ke Tempat Sampah** (reversibel, bisa dipulihkan): `mv <target> ~/.Trash/`
- `rm` permanen HANYA bila Pak Syam eksplisit memintanya & paham tak bisa dipulihkan → konfirmasi tegas.
  Hindari `rm -rf`; jangan pernah ke direktori sistem.

## macOS
- Buka di Finder/aplikasi: `open <path>` · folder ini: `open .`

## Aturan jalan
1. **Pastikan path** (absolut atau relatif terhadap workdir) sebelum bertindak — jangan menebak lokasi.
2. **Inspeksi dulu** (`ls`/`du`) sebelum operasi massal atau penghapusan.
3. **Default hapus = ke Trash**, bukan `rm` permanen.
4. Laporkan hasil ringkas; soroti bila ada yang tertimpa/terhapus.
