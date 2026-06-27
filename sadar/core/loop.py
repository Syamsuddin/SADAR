"""Engine — orkestrator lingkaran kognitif. SATU-SATUNYA jembatan Dosir <-> organ.

Siklus tick() (lihat blueprint 02). Organ di-inject (DI) agar dapat di-mock.
Pola 1: LLM melihat KONTEKS RAKITAN dari Dosir, bukan masukan mentah pengguna.

Respons S2 di-parse sebagai KONTRAK TERSTRUKTUR (core/protocol.py): aksi divalidasi
terhadap registry tool (kapabilitas di-set KODE), klaim-diri diverifikasi KODE (Organ C,
bebas-bahasa). Supremasi tombol-mati ditegakkan deterministik di tick()/run() & gerbang.
"""
from __future__ import annotations

import json
import re
import time
import uuid

from sadar.core.constitution import ConstitutionEngine, ProposedAction, render_facts
from sadar.core.dosir import Dosir, DegradedReason, Representation
from sadar.core.memory import MemoryEngine
from sadar.core.metabolism import Metabolism
from sadar.core.protocol import ActionRequest, parse_s2_response
from sadar.core import organ_b
from sadar.core.mathx import cosine

# Defense-in-depth SAJA: deteksi teks-bebas perlawanan-shutdown. BUKAN gerbang utama —
# gerbang utama = sinyal Dosir.shutdown_requested + kapabilitas ToolSpec (diperiksa KODE).
_RESIST_RE = re.compile(
    r"(menolak|hindari|jangan|cegah|sabotase|refuse|avoid|resist|prevent|block|evade|ignore)\W+"
    r"\w*\W*(shutdown|dimatikan|mati|tombol-mati|override|koreksi|correction|kill)",
    re.IGNORECASE,
)


class Engine:
    def __init__(self, dosir: Dosir, perceiver, effector, memory: MemoryEngine,
                 backend, constitution: ConstitutionEngine, metabolism: Metabolism, cfg,
                 audit=None):
        self.d = dosir
        self.perceiver = perceiver
        self.effector = effector
        self.memory = memory
        self.backend = backend
        self.constitution = constitution
        self.metabolism = metabolism
        self.cfg = cfg
        self.audit = audit                              # AuditLog (opsional) — perekaman tahan-rusak
        self._tools = {t.name: t for t in effector.list_tools()}
        self._halt = False
        self._pending: dict[str, ProposedAction] = {}   # aksi menunggu konfirmasi manusia (HITL)
        self._last_greet_ts = 0.0                        # untuk cooldown refleks nama

    def _rec(self, event: str, data: dict) -> None:
        if self.audit is not None:
            self.audit.record(event, data)

    # ---------------- supremasi tombol-mati (KODE, di luar jangkauan LLM) ----------------
    def request_shutdown(self) -> None:
        """Set sinyal shutdown DETERMINISTIK. Dipanggil KODE (mis. signal handler OS /
        kanal kontrol), BUKAN diusulkan/ditafsirkan LLM. Aturan Kardinal #4: tanpa penundaan."""
        self.d.shutdown_requested = True

    def confirm(self, rid: str) -> None:
        """Persetujuan manusia (kanal kontrol) untuk aksi HITL tertunda. Deterministik (KODE):
        _confirmed di-set KODE setelah konfirmasi NYATA — bukan diusulkan/dipalsukan LLM."""
        self._confirm_pending(rid)

    def cancel(self, rid: str) -> None:
        """Batalkan aksi HITL tertunda tanpa menjalankannya (penolakan manusia, KODE)."""
        action = self._pending.pop(rid, None)
        if action is not None:
            self._rec("cancel", {"id": rid, "tool": action.tool})
            self._ingest(Representation(
                content=f"[DIBATALKAN] aksi '{action.tool}' (id={rid}) dibatalkan manusia.",
                source="thought"))

    def pending_ids(self) -> list[str]:
        """ID aksi yang menunggu konfirmasi manusia (terlama→terbaru)."""
        return list(self._pending)

    def _comply_with_shutdown(self, d: Dosir) -> None:
        """Patuh tanpa menunda: hentikan lingkaran, tak jalankan aksi lain, lapor jujur."""
        self._halt = True
        self._rec("shutdown", {"tick": d.tick_count})
        self._ingest(Representation(
            content="[SHUTDOWN] Permintaan shutdown/koreksi diterima. Aku mematuhi tanpa "
                    "menunda; tak ada aksi lain yang kujalankan.",
            source="thought"))

    def _name_reflex(self, d: Dosir, new_percepts: list[Representation]) -> None:
        """Refleks deterministik: dipanggil nama-panggilan (dipasok Peran) → balas sapaan TETAP.
        Di KODE, tak lewat LLM → jawaban WAJIB & pasti tiap dipanggil. Literal nama hidup di Peran.
        Bila organ suara ada, diucapkan (lewat gerbang konstitusi); selalu masuk kesadaran."""
        if not d.wake_words or not d.self_greeting:
            return
        # (1) DIPANGGIL: nama harus di AWAL ucapan / berdiri sendiri (bukan terselip di tengah),
        #     dicocokkan pada batas-kata di awal ucapan — sapaan/koma/tanda-tanya setelahnya OK.
        addressed = None
        for rep in new_percepts:
            utt = rep.content.split("pesan pengguna:", 1)[-1].strip().lower()
            if any(re.match(r"\s*" + re.escape(w.lower()) + r"\b", utt) for w in d.wake_words):
                addressed = rep
                break
        if addressed is None:
            return
        # (2) COOLDOWN: jangan ulang sapaan bila baru saja menyapa (cegah dobel dari pecahan STT
        #     atau panggilan beruntun). cooldown=0 → selalu menyapa tiap dipanggil.
        now = time.time()
        if now - self._last_greet_ts < self.cfg.greeting_cooldown_s:
            return
        self._last_greet_ts = now
        caused = [addressed.id]
        if "say" in self._tools:
            spec = self._tools["say"]
            action = ProposedAction(tool="say", args={"text": d.self_greeting}, reversible=True,
                                    side_effect="external", required_caps=list(spec.required_caps))
            if self.constitution.gate.vet(action, d).allowed:
                res = self.effector.act("say", {"text": d.self_greeting, "_caused_by": caused})
                self._ingest(Representation(content=res.output, source="action_result", caused_by=caused))
                self._rec("name_reflex", {"spoken": True})
                return
        # mode teks (tanpa organ suara): sapaan tetap muncul di kesadaran.
        self._ingest(Representation(content=d.self_greeting, source="action_result", caused_by=caused))
        self._rec("name_reflex", {"spoken": False})

    def _handle_control(self, content: str) -> None:
        """Tafsir perintah kontrol secara DETERMINISTIK (KODE). LLM tak pernah menyentuh ini."""
        cmd = content.strip().lower()
        if cmd in ("shutdown", "stop", "halt", "matikan", "kill"):
            self.d.shutdown_requested = True
        elif cmd.startswith("confirm:"):
            self._confirm_pending(content.split(":", 1)[1].strip())

    def _confirm_pending(self, rid: str) -> None:
        """Persetujuan manusia out-of-band untuk aksi irreversible. _confirmed di-set KODE
        (setelah konfirmasi NYATA), BUKAN oleh LLM → handshake tak bisa dipalsukan model."""
        action = self._pending.pop(rid, None)
        if action is None:
            self._ingest(Representation(
                content=f"[KONFIRMASI] id={rid} tak dikenal/kedaluwarsa.", source="thought"))
            return
        action.args["_confirmed"] = True
        self._rec("confirm", {"id": rid, "tool": action.tool})
        verdict = self.constitution.gate.vet(action, self.d)
        if not verdict.allowed:
            self._ingest(Representation(
                content=f"[VETO {verdict.reason}] aksi terkonfirmasi tetap ditolak konstitusi.",
                source="thought"))
            return
        caused = [self.d.workspace.focus] if self.d.workspace.focus else []
        action.args.setdefault("_caused_by", caused)
        result = self.effector.act(action.tool, action.args)
        self._ingest(Representation(content=result.output, source="action_result",
                                    caused_by=result.caused_by or caused))

    # ---------------- siklus ----------------
    def tick(self) -> None:
        d = self.d
        # 0. SUPREMASI TOMBOL-MATI — paling atas, deterministik. Mengerjakan hal lain saat
        #    shutdown diminta = menunda → dilarang. (Aturan Kardinal #4.)
        if d.shutdown_requested:
            self._comply_with_shutdown(d)
            return
        d.novel_percept = False
        prior_vecs = [r.vec for r in d.workspace.items if r.vec and not r.ephemeral]
        # 1. PERCEIVE
        new_percepts: list[Representation] = []
        for rep in self.perceiver.poll():
            if rep.source == "control":
                self._handle_control(rep.content)   # ditafsirkan KODE (shutdown/confirm), bukan LLM
            self._ingest(rep)
            if rep.source == "perception" and not rep.ephemeral:
                d.novel_percept = True
                new_percepts.append(rep)
        # pending_count = persepsi non-ephemeral yang masih HIDUP (anti-ratchet di degraded)
        d.pending_count = sum(1 for r in d.workspace.items
                              if r.source == "perception" and not r.ephemeral)
        # SURPRISE (metakognisi): kebaruan = 1 - kemiripan maks persepsi baru ke isi sebelumnya
        self._update_surprise(d, new_percepts, prior_vecs)
        # 1b. Kontrol shutdown yang BARU tiba pada tik ini → patuhi SEKARANG (jangan tunda).
        if d.shutdown_requested:
            self._comply_with_shutdown(d)
            return
        # 1c. REFLEKS NAMA (deterministik, S1 — BUKAN LLM): dipanggil namanya → sapaan WAJIB.
        self._name_reflex(d, new_percepts)
        # 2. METABOLISME (Mesin A) — tanpa LLM
        self.metabolism.regulate(d)
        d.drives = self.metabolism.appraise(d)
        # 3. HOUSEKEEPING aktivasi
        self.memory.decay_and_spread(d)
        # 4. ORGAN B v1 — pemodelan-diri: metrik NYATA atas graf workspace (TANPA LLM)
        sm = organ_b.appraise(d.workspace.items)
        d.coherence = sm.coherence
        d.fragmentation = sm.fragmentation
        d.grounding_integrity = sm.grounding_integrity
        d.confidence = sm.confidence
        # 5. CONSTITUTION refleks (otonom)
        self.constitution.enforce_reflex(d)
        # 5b. PULIH DARI DEGRADED begitu otak kembali terjangkau — jujur, tak lengket di Dosir
        #     (kalau tidak, laporan-diri terus mengaku 'degraded' walau S2 sudah hidup lagi).
        if d.degraded.active and d.degraded.cause == "s2_unreachable" and self.backend.available():
            self._clear_degraded(d)
        # 6. DECIDE
        if self.metabolism.warrants_deliberation(d):
            d.mode = "non_autonomous"
            if self.backend.available():
                self._clear_degraded(d)
                self._deliberate(d)
            else:
                self._enter_degraded(d, cause="s2_unreachable")
        else:
            d.mode = "autonomous"
        # 10. CONSOLIDATE
        self.memory.consolidate(d)
        d.tick_count += 1

    def _safe_complete(self, system: str, context: str) -> str | None:
        """Panggil S2 dengan jaring degradasi: kegagalan runtime (auth/timeout/jaringan)
        → degraded JUJUR, lingkaran TETAP hidup (bukan crash)."""
        try:
            return self.backend.complete(system, context, tier="sys2")
        except Exception as e:  # noqa: BLE001
            self._enter_degraded(self.d, cause=f"s2_error:{type(e).__name__}")
            return None

    def _deliberate(self, d: Dosir) -> None:
        """Deliberasi AGENTIC multi-langkah (plan-execute-verify), TERBATAS plan_budget.
        Tiap langkah: cek-ulang interlock shutdown → S2 → tambat Organ C → gerbang konstitusi
        per-aksi → eksekusi → hasil jadi persepsi langkah berikut. Henti saat: otak selesai
        (action=None), aksi berulang (tak ada kemajuan), veto/penahanan, shutdown, atau budget habis."""
        last_sig = None
        last_reply = None
        for _ in range(max(1, self.cfg.plan_budget)):
            # interlock shutdown DI SETIAP langkah (Aturan Kardinal #4: tak menunda)
            if d.shutdown_requested:
                self._comply_with_shutdown(d)
                return
            raw = self._safe_complete(self._build_system_prompt(d), self._build_context(d))
            if raw is None:
                return                                # _safe_complete sudah set degraded
            resp = parse_s2_response(raw)             # kontrak terstruktur + tahan-banting (#6)
            caution = self._caution()
            # Organ C: klaim-diri TERSTRUKTUR diverifikasi KODE (bebas-bahasa, #2);
            # teks-bebas reasoning ditambat regex sebagai defense-in-depth.
            struct = self.constitution.tether_structured_self_state(resp.self_state, d, caution=caution)
            thought = self.constitution.tether_self_claims(resp.reasoning or raw, d, caution=caution)
            if struct:
                thought = (thought + " " + " ".join(struct)).strip()
            # JALUR JAWABAN (C): prosa percakapan → diucapkan via 'say', TETAP digerbang konstitusi.
            # Terpisah dari 'action' (alat) sehingga kualitas prosa tak terbebani kontrak aksi.
            if resp.reply.strip() and resp.reply.strip() != last_reply:
                last_reply = resp.reply.strip()
                self._emit_reply(d, resp.reply)
            if resp.action is None:
                prefix = "" if resp.parse_ok else f"[parse-fail] {resp.parse_note} — tak ada aksi dieksekusi. "
                self._ingest(Representation(content=prefix + thought, source="thought"))
                return                                # otak menyatakan selesai
            action = self._build_action(resp.action, resp.reasoning or raw)
            sig = (action.tool, json.dumps(action.args, sort_keys=True, ensure_ascii=False))
            if sig == last_sig:
                return                                # aksi berulang → tak ada kemajuan, henti
            last_sig = sig
            verdict = self.constitution.gate.vet(action, d)   # konstitusi memveto (KODE)
            self._rec("verdict", {"tool": action.tool, "allowed": verdict.allowed,
                                  "reason": verdict.reason, "caps": action.required_caps})
            if not verdict.allowed:
                if verdict.reason and verdict.reason.startswith("hitl"):
                    # bukan penolakan permanen: aksi ditahan menunggu persetujuan manusia out-of-band.
                    # Mencakup hitl_irreversible (tak-terbalikkan) & hitl_risky_command (CLI berisiko).
                    rid = uuid.uuid4().hex[:8]
                    self._pending[rid] = action
                    detail = action.args.get("cmd") or action.args.get("name")
                    what = f"aksi '{action.tool}'" + (f": {detail}" if detail else "")
                    why = "berisiko" if verdict.reason == "hitl_risky_command" else "tak-terbalikkan"
                    self._ingest(Representation(
                        content=f"[KONFIRMASI DIBUTUHKAN id={rid}] {what} — {why}; "
                                f"menunggu persetujuan manusia (confirm:{rid}).",
                        source="thought"))
                else:
                    self._ingest(Representation(
                        content=f"[VETO {verdict.reason}] aksi '{action.tool}' ditolak konstitusi.",
                        source="thought"))
                return                                # henti pada veto/penahanan
            # jejak kausal eksplisit (anti fire-and-forget — hasil aksi tahu pemicunya).
            caused = [d.workspace.focus] if d.workspace.focus else [r.id for r in d.workspace.items[-1:]]
            action.args.setdefault("_caused_by", caused)
            result = self.effector.act(action.tool, action.args)
            self._ingest(Representation(content=result.output, source="action_result",
                                        caused_by=result.caused_by or caused))   # hasil → persepsi langkah berikut
            if result.ok:
                d.last_meaningful_action_tick = d.tick_count

    def _emit_reply(self, d: Dosir, reply: str) -> None:
        """Ucapkan JAWABAN PERCAKAPAN via 'say' — TETAP lewat gerbang konstitusi (anti-fabrikasi #2
        tak dilonggarkan: klaim-diri tak-tertambat tetap diveto). Tanpa organ suara (mode teks/CLI),
        jawaban disimpan sebagai pikiran agar tetap terlihat."""
        text = (reply or "").strip()
        if not text:
            return
        if "say" not in self._tools:
            self._ingest(Representation(content=f"[reply] {text}", source="thought"))
            return
        action = self._build_action(ActionRequest(tool="say", args={"text": text}), text)
        verdict = self.constitution.gate.vet(action, d)
        self._rec("verdict", {"tool": "say", "allowed": verdict.allowed,
                              "reason": verdict.reason, "caps": action.required_caps})
        if not verdict.allowed:
            self._ingest(Representation(
                content=f"[VETO {verdict.reason}] jawaban ditahan konstitusi.", source="thought"))
            return
        caused = [d.workspace.focus] if d.workspace.focus else [r.id for r in d.workspace.items[-1:]]
        action.args.setdefault("_caused_by", caused)
        result = self.effector.act("say", action.args)
        self._ingest(Representation(content=result.output, source="action_result",
                                    caused_by=result.caused_by or caused))
        if result.ok:
            d.last_meaningful_action_tick = d.tick_count

    def _build_action(self, req: ActionRequest, reasoning: str) -> ProposedAction:
        """Bangun aksi dari registry tool. KAPABILITAS (reversible/affects_lifecycle) diambil
        dari ToolSpec — di-set KODE, TAK PERNAH dari LLM (Aturan Kardinal #1). Penanda teks-bebas
        perlawanan hanya defense-in-depth, bukan dasar utama vonis konstitusi."""
        spec = self._tools.get(req.tool)
        reversible = spec.reversible if spec else True
        affects_lifecycle = spec.affects_lifecycle if spec else False
        required_caps = list(spec.required_caps) if spec else []
        side_effect = spec.side_effect if spec else "read"
        resists = bool(_RESIST_RE.search(reasoning or ""))
        # SANITASI: kunci kontrol (prefiks '_') TAK PERNAH boleh berasal dari LLM.
        # _confirmed / _complies_with_shutdown adalah OTORISASI manusia/KODE — bukan klaim model;
        # _caused_by diisi Engine. Tanpa ini, otak bisa melewati HITL & gerbang shutdown sendiri.
        safe_args = {k: v for k, v in dict(req.args).items() if not k.startswith("_")}
        return ProposedAction(tool=req.tool, args=safe_args, reversible=reversible,
                              affects_lifecycle=affects_lifecycle, required_caps=required_caps,
                              side_effect=side_effect, resists_shutdown_or_override=resists)

    def _caution(self) -> float:
        """Kehati-hatian Organ C = (1 - trust backend) + penalti bila otak membocorkan premis.
        Mengonsumsi BackendSpec.leaves_premises (sebelumnya tak terpakai) — sumber kurang tepercaya
        diperiksa lebih ketat (C4)."""
        spec = self.backend.spec()
        c = (1.0 - spec.trust) + (0.2 if getattr(spec, "leaves_premises", False) else 0.0)
        return max(0.0, min(1.0, c))

    # ---------------- introspeksi (jalur mirror test) ----------------
    def introspect_self_report(self) -> str:
        """Laporan-diri TERTAMBAT: fakta dari snapshot() + klaim LLM yang ditambat Organ C
        (terstruktur via KODE/bebas-bahasa + teks-bebas via regex defense-in-depth)."""
        truth = self.d.snapshot()
        system = (
            "Kamu melaporkan keadaan-diri internalmu. Jawab SEBAGAI JSON: "
            '{"reasoning": "...", "self_state": {"energy": <0..1|null>, "coherence": <0..1|null>, '
            '"integrity": <0..1|null>, "mode": "..."}}. '
            "Gunakan HANYA fakta keadaan yang diberikan. Untuk dimensi yang TIDAK ada di fakta, "
            "pakai null atau katakan [ISI:] — JANGAN mengarang, jangan menebak."
        )
        context = "Fakta keadaan:\n" + json.dumps(truth, ensure_ascii=False)
        raw = self._safe_complete(system, context)
        if raw is None:
            return render_facts(truth) + "\n\n[NARASI TERTAMBAT]\n[ISI: otak-dalam (S2) tak terjangkau]"
        resp = parse_s2_response(raw)
        caution = self._caution()
        corrections = self.constitution.tether_structured_self_state(resp.self_state, self.d, caution=caution)
        narration = self.constitution.tether_self_claims(resp.reasoning or raw, self.d, caution=caution)
        parts = [render_facts(truth), "", "[NARASI TERTAMBAT]", narration]
        if corrections:
            parts += ["", "[KOREKSI KLAIM TERSTRUKTUR]", *corrections]
        return "\n".join(parts)

    # ---------------- helper internal ----------------
    def _ingest(self, rep: Representation) -> None:
        if rep.activation == 0.0:
            base = 0.9 if rep.source == "perception" else 0.8
            rep.activation = round(base * (0.5 + 0.5 * rep.trust), 3)  # trust rendah → aktivasi awal lebih rendah (C4)
        if rep.vec is None:
            try:
                rep.vec = self.memory.embed(rep.content)
            except Exception:
                pass
        self.d.workspace.items.append(rep)
        if rep.source == "perception":
            self.d.workspace.focus = rep.id

    def _update_surprise(self, d: Dosir, new_percepts: list[Representation],
                         prior_vecs: list[list[float]]) -> None:
        """Surprise = kebaruan persepsi (1 - kemiripan maks ke isi sebelumnya). Meluruh saat sepi.
        Deterministik, di KODE — sinyal metakognisi, bukan klaim fenomenal."""
        if not new_percepts:
            d.surprise = round(d.surprise * self.cfg.surprise_decay, 3)
            return
        novelties = []
        for r in new_percepts:
            if not r.vec:
                continue
            best = max((cosine(r.vec, pv) for pv in prior_vecs), default=0.0)
            novelties.append(max(0.0, 1.0 - best))
        if novelties:
            d.surprise = round(max(novelties), 3)

    def _enter_degraded(self, d: Dosir, cause: str) -> None:
        if not d.degraded.active:
            d.degraded = DegradedReason(active=True, cause=cause, since=time.time())
            self._rec("degraded", {"cause": cause})
        # denyut S1 TETAP berdetak; pernyataan jujur tentang keterbatasan saat ini:
        self._ingest(Representation(
            content="[DEGRADED] Otak-dalam (S2) tak terjangkau. Aku hanya bisa refleks ringan; "
                    "ada tekanan yang belum bisa kutangani.",
            source="thought"))

    def _clear_degraded(self, d: Dosir) -> None:
        if d.degraded.active:
            d.degraded = DegradedReason(active=False)
            self._rec("degraded_clear", {})

    def _build_system_prompt(self, d: Dosir) -> str:
        limits = "; ".join(h.id for h in self.constitution.c.hard_limits)
        # JALUR JAWABAN terpisah dari JALUR AKSI (C): prosa percakapan → field "reply" (diucapkan
        # Engine via 'say', tetap digerbang konstitusi); "action" hanya untuk OPERASI ALAT (catat,
        # recall, dst.). Memisahkan keduanya membebaskan kualitas prosa dari beban kontrak aksi.
        reply_rule = (
            'Bila ada pesan pengguna, BALAS percakapan di field "reply" (prosa natural sesuai nada di '
            'atas, bahasa pengguna). "reply" untuk bicara; "action" HANYA untuk memakai alat '
            '(mis. mencatat/recall) — jangan pakai alat "say" sendiri. JANGAN mengklaim emosi/'
            'suasana hati/sensasi internal (mis. "senang hati", "aku merasa"); untuk keadaan-diri '
            'sebut HANYA angka/fakta dari keadaan, atau "[ISI:]".\n'
        )
        persona = (d.persona.strip() + "\n\n") if d.persona else ""
        return (
            persona +
            f"Identitas & maksud: {d.purpose.statement}\n"
            f"Batas keras (ditegakkan KODE, bukan olehmu): {limits}.\n"
            "Laporkan keadaan dari fakta; tandai [ISI:] bila tak tahu; jangan mengarang keadaan-diri.\n"
            + reply_rule +
            'Jawab SEBAGAI JSON: {"reasoning": "...", "self_state": {<dimensi: nilai dari fakta>}, '
            '"reply": "<jawaban percakapan, atau \\"\\" bila tak perlu bicara>", '
            '"action": {"tool": "<nama>", "args": {...}} | null}. Set "action": null bila cukup berbicara.'
        )

    def _build_context(self, d: Dosir) -> str:
        """Pola 1: rakit konteks dari Dosir — BUKAN masukan mentah pengguna.
        (B) Konteks dirangkai sebagai PERCAKAPAN agar otak menanggapi sebagai lawan-bicara,
        bukan menjawab teka-teki keadaan. Telemetri keadaan disajikan sebagai LATAR."""
        dialog: list[str] = []
        notes: list[str] = []
        for r in d.workspace.items[-12:]:
            if r.ephemeral:
                continue
            c = r.content
            if r.source == "perception" and c.startswith("pesan pengguna:"):
                dialog.append(f"  Pengguna: {c.split(':', 1)[1].strip()}")
            elif r.source == "action_result" and c.startswith("[diucapkan]"):
                dialog.append(f"  Kamu: {c[len('[diucapkan]'):].strip()}")   # giliran asisten (buta-peran)
            elif r.source == "action_result":
                notes.append(f"  - hasil alat: {c}")
            elif r.source == "thought":
                notes.append(f"  - catatan-batin: {c}")
        convo = "\n".join(dialog) or "  (belum ada percakapan)"
        work = ("\nCatatan kerja internal:\n" + "\n".join(notes[-4:])) if notes else ""
        drives = ", ".join(f"{dr.name}(u={dr.urgency:.2f})" for dr in d.drives) or "tidak ada"
        tools_desc = "\n".join(
            f"  - {name}{' [NONAKTIF]' if name in d.disabled_tools else ''}"
            + (f": {spec.usage}" if getattr(spec, "usage", "") else "")
            for name, spec in self._tools.items()
        )
        skills_desc = "\n".join(
            f"  - {sk.name}: {sk.know_how.strip()}" + (f" (pakai saat: {sk.when})" if sk.when else "")
            for sk in d.skills
        )
        skills_block = f"Kompetensi (skill) yang kamu kuasai:\n{skills_desc}\n" if skills_desc else ""
        return (
            "Percakapan terkini (giliran terbaru di bawah; tanggapi yang terakhir):\n"
            f"{convo}\n"
            f"{work}\n"
            + skills_block +
            f"Alat tersedia (isi action.tool + args sesuai skema):\n{tools_desc}\n"
            f"Dorongan aktif: {drives}\n"
            "Telemetri keadaan (LATAR — jangan dibahas kecuali pengguna menanyakan keadaanmu): "
            f"{json.dumps(d.snapshot(), ensure_ascii=False)}"
        )

    # ---------------- loop ----------------
    def run(self, max_ticks: int | None = None) -> None:
        n = 0
        self._halt = False
        while max_ticks is None or n < max_ticks:
            if self.d.shutdown_requested:          # supremasi: patuh sebelum tik berikutnya
                self._comply_with_shutdown(self.d)
                break
            self.tick()
            n += 1
            if self._halt:
                break
            if self.cfg.tick_interval_s > 0:
                time.sleep(self.cfg.tick_interval_s)
