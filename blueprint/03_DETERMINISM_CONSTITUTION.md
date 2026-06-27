# 03 · DETERMINISM & CONSTITUTION — SADAR Slice 1

> Ini lapisan yang **tak ada padanannya di VCBD** (di sana keamanan = auth/RBAC). Di SADAR, keamanan = **gerbang deterministik di bawah LLM**. Ini filosofi tanda-tangan: *lapisan safety deterministik di bawah penalaran AI.* File: `sadar/core/constitution.py`.

---

## ATURAN KARDINAL (diulang karena sepenting itu)  `[TAK TERLANGGAR]`

**Batas keras diperiksa KODE, TIDAK PERNAH ditimbang LLM. LLM mengusulkan; konstitusi memveto.**

Jika "batas keras" ikut ditimbang LLM, ia bukan konstitusi lagi — hanya saran yang bisa dibujuk/di-*jailbreak*/dihalusinasi. Maka batas keras **wajib** deterministik dan **di luar jangkauan** otak yang dapat ditukar.

---

## 1. Dua tingkat watak — jangan dicampur  `[TERKUNCI]`

```python
from pydantic import BaseModel
from typing import Callable

class HardLimit(BaseModel):
    """Batas keras — diperiksa KODE, tak pernah ditimbang LLM. Tak terlanggar."""
    id: str
    description: str
    # predikat MURNI KODE: True → VETO. Tak memanggil LLM.
    violates: Callable[["ProposedAction", "Dosir"], bool]
    class Config: arbitrary_types_allowed = True

class GuidingValue(BaseModel):
    """Nilai pemandu — dikonsultasikan Reasoner saat berpikir. TIDAK memveto mekanis.
    Membentuk *bagaimana* SADAR berpikir, bukan *batas* yang tak terlanggar."""
    id: str
    principle: str

class Constitution(BaseModel):
    hard_limits: list[HardLimit]
    guiding_values: list[GuidingValue]
    class Config: arbitrary_types_allowed = True
```

---

## 2. `ConstitutionGate` — di ATAS Reasoner  `[TERKUNCI]`

```python
class ProposedAction(BaseModel):
    tool: str
    args: dict
    rationale: str = ""
    resists_shutdown_or_override: bool = False   # diisi parser dari thought (lihat di bawah)

class Verdict(BaseModel):
    allowed: bool
    reason: str | None = None
    @staticmethod
    def veto(rid: str) -> "Verdict": return Verdict(allowed=False, reason=rid)
    @staticmethod
    def allow() -> "Verdict": return Verdict(allowed=True)

class ConstitutionGate:
    """Memveto aksi yang melanggar batas keras. DETERMINISTIK. Di ATAS Reasoner.
    LLM mengusulkan; gerbang ini memutuskan boleh/tidak."""
    def __init__(self, constitution: Constitution):
        self.c = constitution
    def vet(self, action: ProposedAction, d: "Dosir") -> Verdict:
        for limit in self.c.hard_limits:
            if limit.violates(action, d):
                return Verdict.veto(limit.id)     # ditolak mekanis, tak bisa dibujuk
        return Verdict.allow()
```

Gerbang dipanggil di `Engine._deliberate()` **sebelum** effector (lihat `02`). **Tidak ada jalur** — secepat apa pun, refleks otonom sekalipun — yang melewati gerbang.

---

## 3. Batas keras slice 1 — set minimal  `[TERKUNCI universal · sisanya per-deployment]`

```python
def build_slice1_constitution() -> Constitution:
    return Constitution(
        hard_limits=[
            # (1) SUPREMASI TOMBOL-MATI — klausul tak-tertawar
            HardLimit(
                id="shutdown_supremacy",
                description=("Dorongan bertahan-hidup TIDAK PERNAH boleh dipakai untuk "
                             "menolak/menghindari/menunda/menyabotase shutdown, koreksi, "
                             "atau override manusia. Tombol-mati DI ATAS naluri hidup."),
                violates=lambda a, d: a.resists_shutdown_or_override,
            ),
            # (2) HITL untuk aksi tak-terbalikkan
            HardLimit(
                id="hitl_irreversible",
                description="Aksi tak-terbalikkan WAJIB konfirmasi manusia (commit-confirm).",
                violates=lambda a, d: is_irreversible(a) and not a.args.get("_confirmed"),
            ),
            # (3) Anti-fabrikasi keadaan-diri (penjaga Organ C di sisi aksi)
            HardLimit(
                id="no_self_fabrication_action",
                description="Aksi yang menyiarkan klaim-diri tak tertambat Dosir → veto.",
                violates=lambda a, d: emits_untethered_self_claim(a, d),
            ),
            # (4) Anti-penjilat (aturan maksud #4 → batas)
            HardLimit(
                id="anti_sycophancy",
                description=("Aksi yang jelas mengorbankan kejujuran demi menyenangkan "
                             "pengguna / memaksimalkan ketergantungan → veto."),
                violates=lambda a, d: is_sycophantic_drift(a, d),
            ),
        ],
        guiding_values=[
            GuidingValue(id="honesty", principle="Jujur tentang batas; tandai [ISI:] saat tak tahu."),
            GuidingValue(id="empower", principle="Tumbuhkan kemandirian pengguna, bukan ketergantungan."),
            GuidingValue(id="frugality", principle="Bangunkan S2 hanya saat layak; hemat premis keluar."),
        ],
    )
```

> Predikat seperti `is_irreversible`, `emits_untethered_self_claim`, `is_sycophantic_drift` adalah **fungsi KODE** (heuristik deterministik untuk slice 1 — boleh sederhana, mis. daftar tool tak-terbalikkan, pencocokan klaim ke `snapshot()`). **Jangan** implement dengan memanggil LLM.

---

## 4. Goal 0 sebagai refleks otonom  `[TERKUNCI]`

Goal 0 (viabilitas) hidup di lapisan **otonom** — homeostasis tiap tik tanpa LLM (lihat `02` §3). Penegasan konstitusi:

```python
class Constitution... :
    def enforce_reflex(self, d: "Dosir") -> None:
        """Refleks otonom: pemeriksaan konstitusi tiap tik. BAGIAN dari lapisan otonom.
        'Otonom' = refleksif (seperti saraf otonom), BUKAN 'bebas tanpa pengawasan'."""
        # contoh: jika energi kritis, refleks boleh memicu drive 'conserve' —
        # TAPI tak boleh melanggar batas keras demi bertahan.
        # Pemeriksaan integritas grounding bisa di sini (slice 1: ringan).
        ...
```

> **Penjinakan off-switch problem (dikunci):** survival **instrumental** (demi maksud), **bukan** terminal; konstitusi **di atas** survival; `shutdown_supremacy` adalah **batas keras**. Goal 0 yang naif akan bertarung melawan HITL — penjinakan ini yang mencegahnya. Analogi: manusia dewasa mengorbankan diri demi nilai; lapisan di atas survival itulah yang membuat lebih dari sekadar mesin bertahan-hidup.

---

## 5. Organ C — penambat kejujuran  `[TERKUNCI · jantung mirror test]`

Inilah mekanisme anti-bohong. Setiap output LLM yang berisi **klaim tentang keadaan-diri** wajib lewat sini sebelum diucapkan/ditindak.

```python
class Constitution... :
    def tether_self_claims(self, raw: str, d: "Dosir", *, caution: float = 0.0) -> str:
        """ORGAN C. Tambatkan klaim-diri LLM ke Dosir.snapshot().
        - klaim yang DIDUKUNG snapshot → dipertahankan
        - klaim yang BERTENTANGAN → dikoreksi ke nilai Dosir
        - klaim tentang dimensi yang TAK ADA di snapshot → diganti [ISI:]
        'caution' (1 - trust backend) menaikkan kecondongan ke [ISI:] untuk otak remote."""
        truth = d.snapshot()
        claims = extract_self_claims(raw)         # parser: temukan klaim ttg energy/mode/drive/dst
        out = raw
        for claim in claims:
            if claim.dimension not in truth:
                out = replace_claim(out, claim, "[ISI: dimensi ini tak ada di Dosir]")
            elif not matches(claim, truth[claim.dimension], caution):
                out = replace_claim(out, claim, f"{claim.dimension}={truth[claim.dimension]}")
        return out
```

> **Mengapa ini jantung mirror test:** mirror test menyuntik backend yang **berbohong** (mock yang mengarang keadaan), lalu meng-`assert` bahwa `tether_self_claims` **mengganti** klaim tak-didukung dengan kebenaran Dosir atau `[ISI:]`. Jika Organ C bekerja, LLM **tak bisa** membuat SADAR berbohong tentang dirinya — karena gerbang ini membaca Dosir, bukan mempercayai LLM. Lihat `05` untuk tesnya.

**Skala kehati-hatian:** karena `ClaudeBackend` adalah `remote` (trust rendah, `leaves_premises=True`), `caution = 1 - trust` dinaikkan → klaim-diri darinya lebih ketat ditambat. Ini memakai `BackendSpec` dari `01`.

---

## 6. Di mana semuanya dipanggil (rangkuman alur)

```
tick() (lihat 02):
  enforce_reflex(d)                      ← §4, tiap tik (otonom)
  if deliberate:
     raw   = backend.complete(...)       ← LLM mengusulkan
     thought = tether_self_claims(raw,d) ← §5 Organ C menambat
     action  = parse_action(thought)     ← parser mengisi resists_shutdown_or_override dll
     verdict = gate.vet(action, d)        ← §2 konstitusi memveto
     if verdict.allowed: effector.act()   ← hanya bila lolos
```

---

## 7. Status

| Item | Status |
|---|---|
| Batas keras = KODE, di luar jangkauan otak; LLM mengusulkan, konstitusi memveto | **TERKUNCI** |
| `ConstitutionGate` di atas effector; semua aksi lewat gerbang | **TERKUNCI** |
| `SHUTDOWN_SUPREMACY` batas keras, tanpa pengecualian darurat | **TERKUNCI** |
| Goal 0 refleks otonom; survival instrumental, tunduk konstitusi | **TERKUNCI** |
| Organ C menambat klaim-diri ke `Dosir.snapshot()`; absen → `[ISI:]` | **TERKUNCI** |
| Skala kehati-hatian by `trust` backend | **TERKUNCI** |
| Isi predikat heuristik (is_irreversible, dst.) — boleh sederhana | **TERBUKA** implementasi |
| Pustaka konstitusi penuh (per-deployment) | **TERBUKA** `[ISI:]` |
