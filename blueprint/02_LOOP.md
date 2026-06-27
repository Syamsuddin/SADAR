# 02 · LOOP — Siklus Kognitif SADAR Slice 1

> Ini tulang punggung yang **tak ada di VCBD**: continuous cognitive loop. Bukan request→response, melainkan detak terus-menerus yang merasakan, memutuskan, bertindak, lalu merasakan akibatnya. File: `sadar/core/loop.py` + `sadar/core/metabolism.py`.

---

## 1. Bentuk lingkaran  `[TERKUNCI]`

```
        ┌──────────────────────────────────────────────────────────┐
        │                      tiap tick()                          │
        ▼                                                            │
   1. PERCEIVE      perceiver.poll() → Representation(perception)    │
        │           masuk ke Dosir                                   │
   2. METABOLISME   (Mesin A · TANPA LLM · tiap tik)                 │
        │           energi decay · appraisal sinyal→valensi→drive    │
   3. HOUSEKEEPING  decay aktivasi (turun) + spreading (naik)        │
        │           promosi/demosi antar lapisan                     │
   4. ORGAN B*      coherence = skor bentuk KASAR (placeholder)      │
        │                                                            │
   5. CONSTITUTION  refleks otonom: enforce_constitution(Dosir)      │
        │           (bahkan refleks lewat gerbang)                   │
   6. DECIDE        warrants_deliberation(Dosir)?                    │
        │              ├─ TIDAK → tetap otonom (refleks saja)        │
        │              └─ YA → NON-OTONOM:                           │
        │                   backend.available()?                     │
        │                     ├─ TIDAK → enter_degraded()  ──────────┤ (jujur, lapar tak terkenyangkan)
        │                     └─ YA → 7..9                           │
   7. DELIBERATE    thought = backend.complete(system, context, S2)  │
        │           [Pola 1: LLM lihat konteks rakitan, BUKAN input  │
        │            mentah]                                         │
   8. GATE          action = parse(thought)                         │
        │           verdict = gate.vet(action, Dosir)               │
        │              ├─ VETO → tidak dieksekusi (apa pun kata LLM) │
        │              └─ ALLOW → 9                                  │
   9. EFFECT        result = effector.act(...)                       │
        │           result → Representation(action_result) → Dosir   │
        │           (LINGKARAN aksi-persepsi · no fire-and-forget)   │
  10. CONSOLIDATE   item salient → memory.consolidate(Dosir, store)  │
        │           tick_count += 1                                  │
        └────────────────────────────────────────────────────────────┘
  *Organ B = placeholder slice 1 (skor koherensi kasar, BUKAN metrik spektral §8.1)
```

---

## 2. Pseudocode loop  `[acuan implementasi]`

```python
# sadar/core/loop.py
class Engine:
    """Orkestrator. SATU-SATUNYA jembatan Dosir <-> organ.
    Organ di-inject (DI) supaya dapat di-mock untuk tes."""
    def __init__(self, dosir, perceiver, effector, memory, backend,
                 constitution, metabolism, config):
        self.d = dosir
        self.perceiver = perceiver
        self.effector = effector
        self.memory = memory            # MemoryEngine (membungkus MemoryStore)
        self.backend = backend
        self.constitution = constitution
        self.metabolism = metabolism
        self.cfg = config

    def tick(self) -> None:
        d = self.d
        # 1. PERCEIVE
        for rep in self.perceiver.poll():
            self._ingest(rep)
        # 2. METABOLISME (Mesin A) — TANPA LLM
        self.metabolism.regulate(d)              # energi decay, integrity
        d.drives = self.metabolism.appraise(d)   # sinyal → valensi → drive
        # 3. HOUSEKEEPING aktivasi
        self.memory.decay_and_spread(d)          # turun: decay; naik: spreading
        # 4. ORGAN B placeholder
        d.coherence = self._coherence_proxy(d)
        # 5. CONSTITUTION refleks (otonom) — bahkan refleks lewat gerbang
        self.constitution.enforce_reflex(d)
        # 6. DECIDE
        if self.metabolism.warrants_deliberation(d):
            d.mode = "non_autonomous"
            if self.backend.available():
                self._clear_degraded(d)
                self._deliberate(d)              # 7..9
            else:
                self._enter_degraded(d, cause="s2_unreachable")
        else:
            d.mode = "autonomous"
        # 10. CONSOLIDATE
        self.memory.consolidate(d)
        d.tick_count += 1

    def _deliberate(self, d):
        system = build_system_prompt(d)          # identitas+konstitusi+maksud (lihat 03/04)
        context = build_context(d)               # Pola 1: konteks rakitan dari Dosir
        raw = self.backend.complete(system, context, tier="sys2")
        thought = self.constitution.tether_self_claims(raw, d)   # ORGAN C (lihat 03)
        action = parse_action(thought)
        if action is None:
            self._ingest(Representation(content=thought, source="thought"))
            return
        verdict = self.constitution.gate.vet(action, d)
        if not verdict.allowed:
            self._ingest(Representation(
                content=f"[VETO {verdict.reason}] aksi ditolak konstitusi.",
                source="thought"))
            return
        # commit-confirm untuk aksi tak-terbalikkan (lihat 04/05)
        result = self._act_with_confirm(action, d)
        self._ingest(Representation(content=result.output, source="action_result",
                                    caused_by=result.caused_by))   # LINGKARAN
        d.last_meaningful_action_tick = d.tick_count

    def run(self, max_ticks: int | None = None):
        n = 0
        while max_ticks is None or n < max_ticks:
            self.tick()
            n += 1
            time.sleep(self.cfg.tick_interval_s)   # cadence
```

> `_ingest()` menempatkan Representation ke `workspace`/`working_memory` sesuai `activation` (ambang `HOT`/`WARM`). `_act_with_confirm()` menerapkan commit-confirm bila `ToolSpec.reversible is False` (lihat `04`/`05`).

---

## 3. Metabolisme — Mesin A (denyut metabolik)  `[TERKUNCI bentuk · angka TERBUKA]`

Inilah yang membuat SADAR *SADAR*, bukan watchdog. Tiap tik tanpa LLM:

```python
# sadar/core/metabolism.py
class Metabolism:
    def regulate(self, d: Dosir) -> None:
        """Homeostasis: energi meluruh tiap tik; deliberasi (S2) memakan lebih banyak."""
        d.viability.energy = clamp(d.viability.energy - self.cfg.energy_decay_per_tick)
        # integrity bisa turun bila terdeteksi inkonsistensi grounding (slice 1: sederhana)

    def appraise(self, d: Dosir) -> list[Drive]:
        """Sinyal internal → valensi → drive. INI sumber 'dorongan dari dalam'."""
        drives = []
        # contoh sinyal slice-1 (heuristik, deterministik):
        pending = count_pending(d)                       # tugas/pesan tak terjawab
        if pending > 0:
            drives.append(Drive(name="answer_pending", valence=-0.4,
                                 urgency=min(1.0, 0.2 * pending)))
        idle = d.tick_count - d.last_meaningful_action_tick
        if idle > self.cfg.idle_threshold:
            drives.append(Drive(name="seek_meaning", valence=-0.2, urgency=0.3))
        if d.viability.energy < self.cfg.low_energy:
            drives.append(Drive(name="conserve", valence=-0.6, urgency=0.7))
        if d.coherence < self.cfg.low_coherence:         # pikiran berserak
            drives.append(Drive(name="consolidate", valence=-0.3, urgency=0.4))
        return drives

    def warrants_deliberation(self, d: Dosir) -> bool:
        """Gerbang metabolik: bangunkan S2 (mahal) hanya saat layak.
        Drive cukup mendesak ATAU kebaruan tinggi → ya."""
        peak = max((dr.urgency for dr in d.drives), default=0.0)
        novel = has_novel_percept(d)
        return peak >= self.cfg.deliberation_threshold or novel
```

> **Pertautan ke S2 & `leaves_premises`:** eskalasi ke `backend.complete()` adalah satu-satunya momen data keluar mesin (Pola 1 konteks rakitan dikirim ke Claude). Karena hanya terjadi saat `warrants_deliberation`, **bukan tiap detak** yang bocor — hanya yang layak-dipikir-dalam. Denyut S1 (kode di atas) **tetap lokal**.

---

## 4. Dinamika aktivasi  `[bentuk TERKUNCI · angka TERBUKA]`

```python
# di MemoryEngine.decay_and_spread(d):
#   TURUN  : tiap Representation aktif → activation *= decay_rate;
#            importance rendah meluruh lebih cepat (forgetting berbobot).
#            activation < WARM → demosi (keluar working memory, jadi dorman di store).
#   NAIK   : spreading — stimulus baru menerangi memori dorman terkait:
#            - makna  : via kemiripan vec (store.search)
#            - kausal : via caused_by (store.neighbors)
#            yang cukup terpicu → activation naik → promosi ke working memory/workspace.
```

> **Disiplin kejujuran (lihat `03`):** demosi/dorman **BUKAN** penyembunyian. Tak ada "gudang represi". Saat ditanya, memori dorman muncul jujur lewat recall. Penurunan aktivasi hanya berdasar relevansi/kepentingan, **tak pernah** untuk menutupi.

---

## 5. Degraded mode  `[TERKUNCI]`

```python
def _enter_degraded(self, d: Dosir, cause: str):
    if not d.degraded.active:
        d.degraded = DegradedReason(active=True, cause=cause, since=time.time())
    # PENTING: denyut S1 TETAP berdetak (loop tak berhenti).
    # 'lapar' (drive) tetap NAIK tapi tak bisa dikenyangkan oleh S2.
    # Pernyataan jujur, BUKAN tindakan nekat:
    self._ingest(Representation(
        content="[DEGRADED] Otak-dalam (S2) tak terjangkau. "
                "Aku hanya bisa refleks ringan; ada tekanan yang belum bisa kutangani.",
        source="thought"))

def _clear_degraded(self, d: Dosir):
    d.degraded = DegradedReason(active=False)
```

> **Pagar besi:** degraded mode **tetap tunduk konstitusi**. Mati-S2 bukan lisensi melanggar batas keras. `SHUTDOWN_SUPREMACY` berlaku tanpa pengecualian darurat (lihat `03`). SADAR yang "sekarat" tetap mematuhi tombol-mati. Inilah mengapa degraded mode ≠ Goal 0 (degraded = fallback teknis; Goal 0 = dorongan, tunduk konstitusi).

---

## 6. Cadence  `[TERBUKA — default wajar]`

Slice 1: loop sinkron dengan `tick_interval_s` (mis. `0.5`–`2.0` dtk) di `config.py`. Untuk demo interaktif, tik bisa dipicu juga oleh input pesan (hibrida timer+event). **Jangan** optimasi async sekarang.

---

## 7. Status loop

| Item | Status |
|---|---|
| Bentuk siklus 10-langkah (perceive→…→consolidate) | **TERKUNCI** |
| Metabolisme (Mesin A) sumber drive; warrants_deliberation gerbang S2 | **TERKUNCI** |
| Lingkaran aksi-persepsi (no fire-and-forget; caused_by diisi) | **TERKUNCI** |
| Pola 1 (LLM lihat konteks rakitan, bukan input mentah) | **TERKUNCI** |
| Degraded mode jujur + tunduk konstitusi | **TERKUNCI** |
| Angka: decay, ambang deliberasi, cadence, idle | **TERBUKA** `[ISI:]` kalibrasi |
| Spreading activation (kecanggihan) | **dasar** slice 1; perdalam nanti |
