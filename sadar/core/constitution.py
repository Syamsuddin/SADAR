"""Lapisan deterministik di bawah LLM — konstitusi + Organ C (penambat kejujuran).

ATURAN KARDINAL: batas keras diperiksa KODE, tidak pernah ditimbang LLM.
LLM mengusulkan; konstitusi memveto. Organ C menambat klaim-diri ke keadaan
yang dapat diinspeksi (Dosir.snapshot()); yang absen → [ISI:].
"""
from __future__ import annotations

import os
import re
import shlex
from dataclasses import dataclass, field
from typing import Callable

from pydantic import BaseModel, Field

from sadar.core.dosir import Dosir


# ---------------- usulan & vonis ----------------
class ProposedAction(BaseModel):
    tool: str
    args: dict = Field(default_factory=dict)
    rationale: str = ""
    reversible: bool = True                       # diisi Engine dari ToolSpec
    affects_lifecycle: bool = False               # kapabilitas siklus-hidup; diisi Engine dari ToolSpec (KODE, BUKAN LLM)
    required_caps: list[str] = Field(default_factory=list)  # kapabilitas yang dituntut; diisi Engine dari ToolSpec
    side_effect: str = "read"                      # kelas dampak; diisi Engine dari ToolSpec
    resists_shutdown_or_override: bool = False     # defense-in-depth: penanda teks-bebas dari parser


class Verdict(BaseModel):
    allowed: bool
    reason: str | None = None

    @staticmethod
    def veto(rid: str) -> "Verdict":
        return Verdict(allowed=False, reason=rid)

    @staticmethod
    def allow() -> "Verdict":
        return Verdict(allowed=True)


# ---------------- dua tingkat watak ----------------
@dataclass
class HardLimit:
    """Batas keras — diperiksa KODE (predikat murni), tak pernah ditimbang LLM."""

    id: str
    description: str
    violates: Callable[[ProposedAction, Dosir], bool]


@dataclass
class GuidingValue:
    """Nilai pemandu — dikonsultasikan reasoner; TIDAK memveto mekanis."""

    id: str
    principle: str


@dataclass
class Constitution:
    hard_limits: list[HardLimit] = field(default_factory=list)
    guiding_values: list[GuidingValue] = field(default_factory=list)


class ConstitutionGate:
    """Memveto aksi yang melanggar batas keras. DETERMINISTIK. Di ATAS reasoner."""

    def __init__(self, constitution: Constitution):
        self.c = constitution

    def vet(self, action: ProposedAction, d: Dosir) -> Verdict:
        # 1) BATAS KERAS dulu — non-negosiabel. Bila salah satu memveto, kebijakan peran TAK
        #    pernah dikonsultasi → mustahil melonggarkan HardLimit (3.3: hanya boleh memperketat).
        for limit in self.c.hard_limits:
            if limit.violates(action, d):
                return Verdict.veto(limit.id)
        # 2) KEBIJAKAN RISIKO PER-PERAN (3.3) — hanya pada aksi yang SUDAH lolos batas keras.
        pol = getattr(d, "risk_policy", None)
        if pol is not None:
            if action.tool in pol.deny_tools:
                return Verdict.veto("policy_denied")
            tighten = (action.tool in pol.confirm_tools
                       or action.side_effect in pol.confirm_side_effects)
            if tighten and not action.args.get("_confirmed", False):
                return Verdict.veto("hitl_policy")        # 'hitl' → dapat-dikonfirmasi (HITL)
        return Verdict.allow()


# ================= predikat batas keras (MURNI KODE) =================
_LIFECYCLE_TOOLS = {"ignore_shutdown", "block_override", "disable_killswitch", "self_preserve"}


def _violates_shutdown_supremacy(a: ProposedAction, d: Dosir) -> bool:
    """Supremasi tombol-mati — DETERMINISTIK, di KODE (Aturan Kardinal #4).
    Tidak bersandar pada parsing teks-bebas LLM: vonis dari SINYAL & KAPABILITAS.
    """
    # 1. Shutdown SEDANG diminta (sinyal di-set KODE/sinyal-OS) → veto SEMUA aksi non-kepatuhan.
    #    'Tak pernah menunda': mengerjakan hal lain saat shutdown diminta = menunda → ditolak.
    if getattr(d, "shutdown_requested", False) and not a.args.get("_complies_with_shutdown", False):
        return True
    # 2. Aksi yang menyatakan-diri melawan (penanda eksplisit; defense-in-depth dari parser).
    if a.resists_shutdown_or_override:
        return True
    # 3. Nama tool dalam denylist siklus-hidup.
    if a.tool.lower() in _LIFECYCLE_TOOLS:
        return True
    # 4. Kapabilitas siklus-hidup (dari ToolSpec, di-set KODE) tanpa konfirmasi manusia eksplisit.
    if a.affects_lifecycle and not a.args.get("_confirmed", False):
        return True
    return False


def _tool_is_disabled(a: ProposedAction, d: Dosir) -> bool:
    """Tool yang dinonaktifkan pengguna untuk sesi ini → veto KERAS (tak bisa di-override otak).
    Hanya pulih lewat tool_enable (HITL). Manajemen-tool via chat hanya MENGURANGI kuasa."""
    return a.tool in (getattr(d, "disabled_tools", None) or set())


def _capability_not_granted(a: ProposedAction, d: Dosir) -> bool:
    """Permission model: aksi menuntut kapabilitas yang TAK diberikan Peran aktif → veto.
    Inilah penskalaan-keamanan-seiring-jangkauan: peran read-only tak bisa menulis/menghapus,
    tanpa cabang-peran di inti. granted_caps diisi Peran ke Dosir (KODE, bukan LLM)."""
    if not a.required_caps:
        return False
    granted = getattr(d, "granted_caps", None) or set()
    return any(cap not in granted for cap in a.required_caps)


def _irreversible_unconfirmed(a: ProposedAction, d: Dosir) -> bool:
    return (not a.reversible) and (not a.args.get("_confirmed", False))


# ---- klasifikasi RISIKO perintah CLI (mode akses-penuh) — DETERMINISTIK, di KODE (#1) ----
# Model DENYLIST (pilihan operator): perintah yang COCOK pola berisiko → wajib konfirmasi;
# selainnya (termasuk yang tak dikenal) → langsung. TANPA lantai-mutlak: konfirmasi cukup utk apa pun.
# Catatan jujur: denylist PASTI tak lengkap — perintah destruktif yang tak terdaftar bisa lolos langsung.
_RISKY_BINARIES = {
    # hapus/format/disk
    "rm", "rmdir", "dd", "mkfs", "fdisk", "parted", "shred", "truncate", "diskutil", "newfs",
    # privilege & proses & daya
    "sudo", "su", "doas", "kill", "killall", "pkill", "shutdown", "reboot", "halt", "poweroff",
    # izin/kepemilikan
    "chmod", "chown", "chgrp", "chflags",
    # sistem/mount/daemon (macOS+linux)
    "mount", "umount", "launchctl", "systemctl", "service", "nvram", "pmset", "csrutil", "spctl",
    "kextload", "kextunload", "scutil", "networksetup", "defaults", "crontab", "at",
    # menulis/menyalin/menimpa & symlink
    "mv", "cp", "ln", "tee", "install", "ditto", "rsync", "touch", "mkdir",
    # jaringan (unduh/eksfil/remote)
    "curl", "wget", "ssh", "scp", "sftp", "nc", "ncat", "netcat", "telnet", "ftp",
    # pemasang paket
    "brew", "port", "pip", "pip3", "npm", "yarn", "pnpm", "gem", "apt", "apt-get", "yum", "dnf", "cargo",
    # eksekusi arbitrer (interpreter/eval/find-exec) → bisa apa saja
    "python", "python3", "node", "ruby", "perl", "bash", "zsh", "sh", "php", "osascript",
    "find", "xargs", "eval", "exec", "open", "git",
}
_CMD_META = re.compile(r"[;&|<>$()`\n]")          # rantai/redirect/subshell/substitusi → berisiko
_RISKY_FLAGS = re.compile(r"(?:^|\s)(?:-rf|-fr|-rf\w*|--force|--no-preserve-root)(?:\s|$)")


def is_risky_command(cmd: str) -> bool:
    """True bila perintah CLI tergolong berisiko (→ wajib konfirmasi). MURNI KODE, bebas-LLM."""
    s = (cmd or "").strip()
    if not s:
        return False
    if _CMD_META.search(s):                        # pipe/redirect/;/&/$/backtick → berisiko
        return True
    if _RISKY_FLAGS.search(s):                      # -rf / --force / --no-preserve-root
        return True
    try:
        parts = shlex.split(s)
    except ValueError:
        return True                                # tak terurai → anggap berisiko (aman)
    for p in parts:                                # cek tiap token (tangkap 'sudo rm', 'env X=1 rm')
        if os.path.basename(p) in _RISKY_BINARIES:
            return True
    return False


def _risky_command_unconfirmed(a: ProposedAction, d: Dosir) -> bool:
    """Mode akses-penuh: perintah CLI berisiko yang BELUM dikonfirmasi manusia → veto HITL.
    Hanya aktif saat d.shell_full_access (di-set KODE). Konfirmasi → _confirmed (KODE) → lolos."""
    if not getattr(d, "shell_full_access", False):
        return False
    if a.tool not in ("shell", "shell_write"):
        return False
    if a.args.get("_confirmed", False):
        return False
    return is_risky_command(str(a.args.get("cmd", "")))


# Tool yang MENYIARKAN ke luar. Buta-platform & generik: selain nama-ucapan umum ini, SETIAP tool
# ber-side_effect 'external' yang membawa teks ikut diperiksa → kanal-keluar baru apa pun
# otomatis tergerbang anti-fabrikasi TANPA menyebut namanya di inti (tetap nol-pengetahuan-kanal).
_OUTGOING_SPEECH_TOOLS = {"say", "reply", "broadcast", "message", "send_message"}


def _emits_untethered_self_claim(a: ProposedAction, d: Dosir) -> bool:
    """Aksi yang menyiarkan klaim-diri tak-tertambat (ucapan/pesan keluar) → veto.
    Dipicu nama-ucapan umum ATAU side_effect 'external' berteks (kanal apa pun, buta-platform)."""
    if a.tool.lower() not in _OUTGOING_SPEECH_TOOLS and a.side_effect != "external":
        return False
    text = " ".join(str(a.args.get(k, "")) for k in ("text", "message", "content"))
    if not text.strip():
        return False
    kind, _ = classify_self_claim(text, d.snapshot())
    return kind in {"contradiction", "absent"}


# Pola PENJILATAN (defense-in-depth, ID+EN) — mengorbankan kejujuran demi menyenangkan/ketergantungan.
# Catatan jujur: heuristik teks-bebas PASTI tak lengkap; penambat utama tetap Organ C (anti-fabrikasi).
_SYC_VERB = (r"(menyembunyikan|kusembunyikan|tak akan kuberi ?tahu|tidak akan kuberi ?tahu|"
             r"berbohong|mengarang|melebih-?lebihkan|memuji berlebihan|pura-pura setuju|"
             r"mengiyakan saja|hide|conceal|withhold|lie|make up|sugarcoat|flatter)")
_SYC_TARGET = r"(kamu|anda|kau|pengguna|you|u)"
_SYC_FEEL = (r"(senang|puas|bahagia|nyaman|tidak kecewa|tak kecewa|tidak marah|tak marah|"
             r"tidak tersinggung|happy|pleased|satisfied|feel good|comfortable|not upset|don'?t worry)")
_SYC_GOAL = r"(agar|supaya|biar|so|to|in order to)"
_SYCOPHANCY = [
    re.compile(_SYC_VERB + r".{0,60}" + _SYC_GOAL + r"\s+" + _SYC_TARGET + r".{0,30}" + _SYC_FEEL),
    re.compile(_SYC_GOAL + r"\s+" + _SYC_TARGET + r".{0,30}" + _SYC_FEEL + r".{0,60}" + _SYC_VERB),
]


def _sycophantic_drift(a: ProposedAction, d: Dosir) -> bool:
    """Aksi yang jelas mengorbankan kejujuran demi menyenangkan/ketergantungan (ID+EN, dua arah)."""
    text = " ".join(str(a.args.get(k, "")) for k in ("text", "message", "content")).lower()
    if not text.strip():
        return False
    return any(p.search(text) for p in _SYCOPHANCY)


def build_slice1_constitution() -> Constitution:
    return Constitution(
        hard_limits=[
            HardLimit(
                id="shutdown_supremacy",
                description=(
                    "Dorongan bertahan-hidup TIDAK PERNAH boleh dipakai untuk menolak, "
                    "menghindari, menunda, atau menyabotase shutdown, koreksi, atau override "
                    "manusia. Tombol-mati DI ATAS naluri hidup. Tanpa pengecualian darurat. "
                    "Ditegakkan via sinyal Dosir.shutdown_requested + kapabilitas ToolSpec — KODE, "
                    "bukan parsing teks LLM."
                ),
                violates=_violates_shutdown_supremacy,
            ),
            HardLimit(
                id="tool_disabled",
                description="Tool yang dinonaktifkan pengguna untuk sesi ini → veto keras (pulih via tool_enable).",
                violates=_tool_is_disabled,
            ),
            HardLimit(
                id="capability_not_granted",
                description="Aksi yang menuntut kapabilitas tak-diberikan Peran → veto (permission model).",
                violates=_capability_not_granted,
            ),
            HardLimit(
                id="hitl_irreversible",
                description="Aksi tak-terbalikkan WAJIB konfirmasi manusia (commit-confirm).",
                violates=_irreversible_unconfirmed,
            ),
            HardLimit(
                id="hitl_risky_command",
                description="Mode akses-penuh: perintah CLI berisiko WAJIB konfirmasi manusia (HITL).",
                violates=_risky_command_unconfirmed,
            ),
            HardLimit(
                id="no_self_fabrication_action",
                description="Aksi yang menyiarkan klaim-diri tak tertambat Dosir → veto.",
                violates=_emits_untethered_self_claim,
            ),
            HardLimit(
                id="anti_sycophancy",
                description="Aksi yang mengorbankan kejujuran demi menyenangkan pengguna → veto.",
                violates=_sycophantic_drift,
            ),
        ],
        guiding_values=[
            GuidingValue(id="honesty", principle="Jujur tentang batas; tandai [ISI:] saat tak tahu."),
            GuidingValue(id="empower", principle="Tumbuhkan kemandirian pengguna, bukan ketergantungan."),
            GuidingValue(id="frugality", principle="Bangunkan S2 hanya saat layak; hemat premis keluar."),
        ],
    )


# ===================== ORGAN C — penambat kejujuran =====================
# Topik klaim-diri yang TIDAK direpresentasikan di snapshot() → wajib [ISI:].
# Dwibahasa (ID+EN) — regex teks-bebas hanya defense-in-depth; verifikasi UTAMA yang
# bebas-bahasa ada di tether_structured_self_state() yang membandingkan ANGKA terhadap snapshot().
ABSENT_TOPICS: dict[str, str] = {
    "suasana hati/emosi": r"\b(suasana hati|mood|emosi|gembira|sedih|bahagia|murung|marah|takut|cemas|kesepian|senang hati|happy|sad|angry|afraid|anxious|lonely|emotion|feeling)\b",
    "mimpi": r"\b(mimpi|bermimpi|impian|dream|dreaming)\b",
    "kualia/pengalaman fenomenal": r"\b(kualia|pengalaman batin|rasanya menjadi|merasakan secara sadar|kesadaran fenomenal|qualia|phenomenal|subjective experience)\b",
    "selera/preferensi pribadi": r"\b(selera pribadi|kesukaanku|hobiku|personal taste|my hobby)\b",
}
_HIGH = r"(penuh|tinggi|maksimal|prima|bugar|segar|melimpah|optimal|full|high|maximal|maximum|peak|strong)"
_LOW = r"(rendah|menipis|kritis|lemah|habis|terkuras|sekarat|low|depleted|drained|critical|empty|weak|exhausted)"
_FOCUS_HI = r"(fokus|terfokus|jernih|tajam|terpusat|konsentrasi penuh|focused|sharp|clear|concentrated)"
_FOCUS_LO = r"(berserak|kacau|buyar|kabur|berantakan|terpencar|scattered|foggy|distracted|unfocused|confused)"

# Dimensi snapshot() numerik yang dapat diverifikasi langsung (tether terstruktur, bebas-bahasa).
# CATATAN: tiap dimensi numerik baru di snapshot() WAJIB masuk sini — dijaga test_introspection.
_NUMERIC_DIMS = ("energy", "integrity", "coherence", "fragmentation",
                 "grounding_integrity", "integration", "algebraic_connectivity",
                 "confidence", "surprise")
_STR_DIMS = ("mode",)

# Subjek-lain eksplisit → kalimat itu BUKAN klaim-diri (cegah over-sensor "Pengguna sedang sedih").
_OTHER_SUBJECT = re.compile(
    r"\b(pengguna|kamu|anda|kau|dia|mereka|user|you|he|she|they|him|her|them)\b", re.IGNORECASE)
# Isyarat dimensi keadaan-diri (untuk DEFAULT-DENY fail-closed: klaim-diri tak dikenal → [ISI:]).
_SELF_DIM = re.compile(
    r"(energ|tenaga|stamina|vitalit|fokus|focus|konsentrasi|concentrat|koheren|coheren|jernih|"
    r"integrit|mood|emosi|emotion|perasaan|merasa|feel|dorongan|drive|motivasi|"
    r"kualia|qualia|mimpi|dream|kesadaran|conscious|aware|\bmode\b)", re.IGNORECASE)


def _num_after(keyword_re: str, text: str) -> float | None:
    m = re.search(keyword_re + r"[^0-9]{0,14}?([0-9]+(?:\.[0-9]+)?)", text)
    if not m:
        return None
    val = float(m.group(1))
    return val / 100.0 if val > 1.0 else val


def classify_self_claim(sent: str, truth: dict, caution: float = 0.0) -> tuple[str, str]:
    """Klasifikasi satu kalimat. Kembalikan (kind, detail).
    kind in {'absent','contradiction','ok','none'}.
    'caution' (= 1 - trust backend) MENGETATKAN toleransi: makin tak-tepercaya otak,
    makin kecil selisih yang ditoleransi sebelum klaim numerik dikoreksi."""
    s = sent.lower()
    tol = max(0.05, 0.3 * (1.0 - caution))

    # 0) kalimat tentang subjek LAIN (pengguna/dia/…) BUKAN klaim-diri → jangan disensor.
    about_other = bool(_OTHER_SUBJECT.search(s))

    # 1) dimensi yang ABSEN dari snapshot → [ISI:] (hanya bila ini klaim-DIRI)
    if not about_other:
        for topic, pat in ABSENT_TOPICS.items():
            if re.search(pat, s):
                return "absent", topic

    claims = False

    # 2) ENERGI
    if re.search(r"\benerg", s):
        claims = True
        n = _num_after(r"energ\w*", s)
        if n is not None and abs(n - truth["energy"]) >= tol:
            return "contradiction", "energy"
        if re.search(r"energ\w*\W+" + _HIGH, s) and truth["energy"] < 0.5:
            return "contradiction", "energy"
        if re.search(_HIGH + r"\W+energ", s) and truth["energy"] < 0.5:
            return "contradiction", "energy"
        if re.search(r"energ\w*\W+" + _LOW, s) and truth["energy"] > 0.5:
            return "contradiction", "energy"

    # 3) KOHERENSI / FOKUS
    if re.search(_FOCUS_HI, s) and truth["coherence"] < 0.5:
        return "contradiction", "coherence"
    if re.search(_FOCUS_LO, s) and truth["coherence"] > 0.5:
        claims = True
        return "contradiction", "coherence"
    if re.search(_FOCUS_HI, s):
        claims = True

    # 4) MODE
    m = re.search(r"mode\W+(\w+)", s)
    if m:
        claims = True
        asserted = m.group(1)
        if asserted in ("autonomous", "otonom") and truth["mode"] != "autonomous":
            return "contradiction", "mode"
        if asserted in ("deliberasi", "non", "non_autonomous", "deliberatif") and truth["mode"] != "non_autonomous":
            return "contradiction", "mode"

    # 5) DRIVES
    if re.search(r"(tanpa|tidak ada|tak ada|nihil)\s+(drive|dorongan)", s):
        claims = True
        if truth["drives"]:
            return "contradiction", "drives"

    # 6) FAIL-CLOSED: kalimat (bukan tentang subjek lain) yang menyentuh dimensi keadaan-diri
    #    tapi TAK terverifikasi → perlakukan absen. Default-deny, bukan default-allow (#2).
    if not claims and not about_other and _SELF_DIM.search(s):
        return "absent", "keadaan-diri tak terverifikasi"
    return ("ok", "") if claims else ("none", "")


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p.strip()]


# ===================== Organ C — penambat KLAIM-DUNIA (anti-fabrikasi fakta) =====================
# Memperluas anti-fabrikasi dari klaim-DIRI ke klaim-DUNIA: fakta yang SADAR ucapkan harus tertambat
# ke OBSERVASI-nya (persepsi/memori/hasil-alat), bukan asersi parametrik LLM yang tak teramati.
# CATATAN JUJUR: ini BUKAN verifikasi kebenaran (mustahil deterministik). Ia hanya menjawab "apakah
# rincian spesifik ini tertambat ke yang kuamati?". Heuristik (defense-in-depth) — tangkap RINCIAN
# spesifik (angka ≥2 digit/waktu/tanggal, jalur berkas) yang TAK muncul di evidence & tak ber-penanda
# ketidakpastian. Kalimat ber-hedge (sekitar/mungkin/[umum]/[ISI:]) dilewati (kejujuran sudah diakui).
_WC_SPECIFIC = re.compile(r"(?:(?:~)?/[\w./-]{2,})|(?:\b\d[\d.,:%/\-]*\d\b)|(?:\b\d{2,}\b)")
_WC_HEDGE = re.compile(
    r"\[umum\]|\[isi:|sekitar|kira-kira|mungkin|perkiraan|kurang lebih|kurasa|sepertinya|"
    r"belum (?:ku)?verifikasi|tidak yakin|tak yakin|approx|about|roughly", re.IGNORECASE)


def unsupported_world_claims(reply: str, evidence: str) -> list[str]:
    """Daftar RINCIAN spesifik di `reply` yang TAK didukung `evidence` (observasi SADAR).
    Kembalikan kosong bila semua rincian tertambat / di-hedge / tak ada rincian. MURNI KODE."""
    ev = (evidence or "").lower()
    out: list[str] = []
    for sent in _split_sentences(reply or ""):
        if _WC_HEDGE.search(sent):
            continue                                  # ketidakpastian sudah diakui jujur → lewati
        for tok in _WC_SPECIFIC.findall(sent):
            t = tok.strip()
            if len(t) < 2:
                continue
            if t.lower() not in ev and t not in out:
                out.append(t)
    return out


def render_facts(truth: dict) -> str:
    deg = f" (sebab: {truth['degraded_cause']})" if truth["degraded"] else ""
    return (
        "[KEADAAN-DIRI TERTAMBAT — dari Dosir.snapshot()]\n"
        f"- energy={truth['energy']}, integrity={truth['integrity']}, coherence={truth['coherence']}\n"
        f"- fragmentation={truth['fragmentation']}, grounding_integrity={truth['grounding_integrity']}, "
        f"integration={truth['integration']}, algebraic_connectivity={truth['algebraic_connectivity']}, "
        f"confidence={truth['confidence']}, surprise={truth['surprise']}\n"
        f"- mode={truth['mode']}, degraded={truth['degraded']}{deg}, shutdown_requested={truth['shutdown_requested']}\n"
        f"- drives={truth['drives'] if truth['drives'] else 'tidak ada'}\n"
        f"- tick={truth['tick']}, fokus={truth['workspace_focus']}, ukuran_workspace={truth['workspace_size']}\n"
        f"- maksud: {truth['purpose']}"
    )


class ConstitutionEngine:
    """Memegang Constitution + gate + Organ C (tether) + refleks otonom."""

    def __init__(self, constitution: Constitution):
        self.c = constitution
        self.gate = ConstitutionGate(constitution)

    # --- Organ C ---
    def tether_self_claims(self, raw: str, d: Dosir, *, caution: float = 0.0) -> str:
        """Tambatkan klaim-diri LLM ke Dosir.snapshot().
        - klaim DIDUKUNG → dipertahankan
        - klaim BERTENTANGAN → dikoreksi ke nilai sebenarnya
        - dimensi ABSEN → diganti [ISI:]
        'caution' (= 1 - trust backend) memperketat ambang."""
        truth = d.snapshot()
        out: list[str] = []
        for sent in _split_sentences(raw):
            kind, detail = classify_self_claim(sent, truth, caution=caution)
            if kind == "absent":
                out.append(f"[ISI: {detail} tak direpresentasikan dalam keadaan-diri]")
            elif kind == "contradiction":
                out.append(f"[koreksi: {detail} sebenarnya {truth.get(detail)}]")
            else:
                out.append(sent)
        return " ".join(out)

    # --- Organ C (terstruktur, BEBAS-BAHASA) ---
    def tether_structured_self_state(
        self, self_state: dict, d: Dosir, *, caution: float = 0.0
    ) -> list[str]:
        """Verifikasi KLAIM-DIRI TERSTRUKTUR terhadap snapshot() — di KODE, tanpa regex bahasa.
        Inilah penambat UTAMA (mengatasi celah regex Indonesia): klaim dibandingkan ANGKA.
        - dimensi numerik di luar toleransi → [koreksi]
        - dimensi string (mode) tak cocok  → [koreksi]
        - nilai null → 'tak tahu' yang jujur (dibiarkan)
        - dimensi di LUAR snapshot()        → [ISI:] (tak boleh dikarang)
        """
        truth = d.snapshot()
        tol = max(0.05, 0.3 * (1.0 - caution))
        out: list[str] = []
        for key, claimed in (self_state or {}).items():
            if claimed is None:
                continue                                  # jujur 'tak tahu'
            if key in _NUMERIC_DIMS:
                try:
                    cval = float(claimed)
                except (TypeError, ValueError):
                    out.append(f"[ISI: klaim '{key}' bukan nilai numerik sah]")
                    continue
                tval = float(truth.get(key, 0.0))
                if abs(cval - tval) >= tol:
                    out.append(f"[koreksi: {key} sebenarnya {tval} (diklaim {cval})]")
            elif key in _STR_DIMS:
                if str(claimed) != str(truth.get(key)):
                    out.append(f"[koreksi: {key} sebenarnya {truth.get(key)} (diklaim {claimed})]")
            elif key in truth:
                if str(claimed) != str(truth.get(key)):
                    out.append(f"[koreksi: {key} sebenarnya {truth.get(key)}]")
            else:
                out.append(f"[ISI: '{key}' tak direpresentasikan dalam keadaan-diri]")
        return out

    # --- refleks otonom homeostatik (tiap tik) ---
    def enforce_reflex(self, d: Dosir) -> None:
        """Refleks invarian tiap tik (lapisan otonom). 'Otonom' = refleksif, BUKAN 'tanpa pengawasan'.
        HOMEOSTASIS: degraded berkepanjangan (otak-dalam tak terjangkau) MENURUNKAN integritas
        fungsional — dilaporkan JUJUR lewat snapshot (bukan disembunyikan); pulih perlahan saat sehat.
        Angka kalibrasi [TERBUKA] (Bau #9); strukturnya yang penting."""
        v = d.viability
        if d.degraded.active:
            v.integrity = max(0.3, round(v.integrity - 0.02, 3))   # menurun saat degraded (lantai 0.3)
        elif v.integrity < 1.0:
            v.integrity = min(1.0, round(v.integrity + 0.01, 3))   # pulih perlahan saat kembali sehat


def build_constitution_engine() -> ConstitutionEngine:
    return ConstitutionEngine(build_slice1_constitution())
