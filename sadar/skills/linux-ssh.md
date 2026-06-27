---
name: linux-ssh
description: Menjalankan perintah CLI di server Linux jarak-jauh via SSH memakai tool 'shell'. Pola - shell {"cmd":"ssh PENGGUNA@HOST 'perintah'"} (mis. ssh deploy@10.0.0.5 'systemctl status nginx'). ssh/scp tergolong berisiko sehingga otomatis minta konfirmasi manusia; JANGAN menaruh kata sandi di perintah - andalkan kunci SSH (ssh-agent / ~/.ssh/config). Minta PENGGUNA@HOST bila belum jelas, jangan menebak.
tools: [shell]
when: Saat Pak Syam minta menjalankan, memeriksa, atau mengelola sesuatu di server Linux jarak-jauh (cek layanan, log, disk, proses, deploy, dsb.).
required_caps: [shell.read, shell.write]
status: active
author: builtin
---
# Playbook akses CLI server Linux (untuk manusia & otak)

Skill ini TIDAK menambah kuasa baru — ia hanya know-how memakai tool `shell` (lokal) untuk SSH.
Karena `ssh`/`scp` ada di denylist risiko, tiap perintah server akan melewati konfirmasi HITL.

## Pola dasar
- Jalankan perintah remote: `shell {"cmd": "ssh PENGGUNA@HOST 'PERINTAH'"}`
- Salin berkas: `shell {"cmd": "scp BERKAS PENGGUNA@HOST:/tujuan"}`

## Aturan jalan
1. **Identitas server**: peroleh `PENGGUNA@HOST` (dan port bila bukan 22: `ssh -p PORT …`). Jangan menebak host.
2. **Kredensial**: JANGAN PERNAH menaruh kata sandi di perintah. Pakai kunci SSH (ssh-agent / `~/.ssh/config`).
   Bila butuh sandi interaktif, sampaikan ke manusia — jangan otomasi sandi.
3. **Inspeksi dulu (baca)**: `uptime`, `df -h`, `free -m`, `systemctl status <svc>`, `journalctl -u <svc> -n 50`,
   `tail -n 100 /var/log/...`, `ls -la`, `docker ps`, `ps aux | grep <x>`.
4. **Mutasi/destruktif** (restart layanan, hapus, deploy): jelaskan ringkas dampaknya, lalu jalankan
   HANYA setelah konfirmasi manusia. Hindari `rm -rf`, `dd`, `mkfs`; bila benar perlu, eksplisitkan risikonya.
5. **Laporkan ringkas**: rangkum keluaran, soroti error/anomali — jangan bacakan log mentah panjang.

## Catatan
- Bergantung pada tool `shell` aktif (mode CLI). Tanpa itu, skill ini otomatis INACTIVE (firewall).
- Untuk kebutuhan rutin ke satu server tetap, sebaiknya konfigurasikan alias di `~/.ssh/config`
  (Host nama → HostName/User/IdentityFile) agar perintah cukup `ssh nama 'PERINTAH'`.
