# Cubli Frame — Final Build Guide (locked architecture · v4: 7 cable-stay tensioned hub)

> Locked **frame** architecture: a tube cage, a central machined motor hub, and **seven
> pre-tensioned 1/8″ stranded-cable stays** that suspend the hub. No rigid strut — all seven
> stays are identical tensioned members. Supersedes the frame section of `HARDWARE.md` and
> earlier versions of this guide. Electronics, motors, wheels, wiring, and power limits live in
> `HARDWARE.md` and remain the source of truth for those.
>
> **Open until CAD:** the cube edge `E`, the seven cable pin-to-pin lengths, and — keyed to a
> measured sample — the final slug/cup/tap dimensions (§5). Everything else is locked.
>
> *v4 changes from v3: the stay member is now **1/8″ (3.2 mm) 7×7 stranded stainless cable**, not
> a 14 ga J-bend solid spoke. Its near-zero bending stiffness routes through the tight gaps near
> the wheels that the stiff spoke could not, while its axial stiffness ≈ the old 2 mm spoke. Both
> ends terminate in **swaged copper-stop sleeves**; the vertex tensioner is a **machined steel slug**
> threaded into the corner block (this resolves the old nipple-vs-M2 question). The spoke-free 8th
> vertex remains the contact/balance corner.*

---

## 1. Architecture at a glance

Three structural elements:

1. **The cage** — 12 aluminum tubes (cube edges) plugged into 8 corner blocks (vertices). The outer skeleton.
2. **The central hub** — a machined aluminum block at the cube center, carrying the three motors on three mutually perpendicular faces. It touches the cage *only* through the stays.
3. **Seven cable stays** — 1/8″ 7×7 stranded stainless cable in tension, from the hub out to **7 of the 8 vertices**. They both *locate* the hub and *preload* the whole structure.

**The three non-negotiables:**
- **CM at the geometric center.** A *tensioning outcome*, not a bolted datum — see §7 and §8.
- **The three motor faces truly perpendicular** to one another — owned entirely by the hub.
- **A rigid frame** — first resonance well above control bandwidth and the ~35–50 Hz top wheel-spin. All-tension mounts are springier than a strut, so this is preload-dependent (§8).

---

## 2. Why seven (and not four or six)

The hub is a free rigid body: 6 DOF. A taut cable is the *ideal* tension-only member — it removes one DOF, but only while it stays in tension (a cable takes zero compression, so the "only while taut" caveat is absolute here).

- **Six** independent stays can *locate* the hub, but leave no way to pre-tension it (no self-stress state) — they'd only go taut under external load. Useless for a preloaded mount.
- **Seven** adds exactly one *state of self-stress*: a way for all seven to pull against each other and sit in steady tension on their own. **That self-stress is your preload.** (Maxwell's rule: members − 6 = self-stresses − mechanisms; with 0 mechanisms and 1 self-stress → 7 members.)

The count is necessary, not sufficient — the seven must be *arranged* so their pull directions span all six DOF. The three rotations are the catch: a stay resists the hub twisting only if it anchors **off** the hub center (a moment arm). Seven stays all aimed at the center lock the translations and leave the hub free to spin. So the hub anchors sit out on the block's faces and corners, spread so every rotation tightens something — laced like a wheel, not like a sunburst.

---

## 3. The cage

**Tubes (×12)** — 8 × 8 × 1 mm 6063 aluminum square tube, 6 mm bore.
- Best stiffness-per-gram in the robust-wall family; the 6 mm bore gives a stiff corner-block leg (leg stiffness ∝ bore⁴), and the joints — not the tube span — set frame stiffness.
- Cut length **L = E − 2c**, where `c` is the corner-block intrusion per edge (≈ 4 mm at an 8 mm corner body → L = E − 8 mm).
- Buckling margin ~13 kN against tens-of-newtons preload — strength is a non-issue.

**Corner blocks (×8)** — machined aluminum nodes.
- Three legs, each ~5.8 mm, slip-fit the 6 mm tube bore; engagement ≈ 12–16 mm; bond (epoxy) **and** a transverse pin/set screw per leg so preload can't creep a leg out.
- **Seven of the eight** carry a **tapped M8 hole** (local boss if the body's too thin) for the vertex slug tensioner — see §5.
- **The eighth is the contact/balance corner:** left stay-free, and shaped into a clean (ideally hardened) balance tip. No stay means no tensioner hardware where the cube touches the ground.

---

## 4. The central hub

Machined aluminum — the precision datum for the whole machine.
- **Three mutually perpendicular faces**, one per motor — three orthogonal faces of a squared block, no compound angles. Start from precision-ground stock (ground cube / 1-2-3 block); only the motor bolt patterns get drilled, so squareness comes from the stock.
- **Seven copper-stop counterbore cups** — one drilled cup at each anchor: a flat-bottom counterbore (~5.6 mm) that seats the cable's hub-end copper stop, with a ~3.5 mm through-hole the bare cable exits. Distributed around the hub's faces, edges, and corners and **offset from center** so every stay has a moment arm (§2). Each cup is aimed at its vertex; a few degrees of cable flex takes up the diagonal, so the cups don't need precise compound angles. The hub end is the **dead anchor** — no adjustment here.
- Perpendicularity belongs **entirely** to this part. The cage only provides stiffness and contact geometry — never delegate squareness to the frame.

---

## 5. The seven cable stays

Each stay is **1/8″ (3.2 mm) 7×7 stranded stainless aircraft cable** (T316 preferred; 304 is fine indoors), cut to length, in pure tension.

**Why stranded cable (the reason for the v4 change):** its near-zero bending stiffness threads through the tight, wheel-adjacent gaps that the stiff 2 mm spoke could not be routed through — that routing problem is what drove the swap. Axial stiffness is what matters structurally, and 1/8″ 7×7 lands ≈ the old 2 mm spoke. Two cable-specific tradeoffs, both managed:
- **Effective axial modulus ~half a solid rod** (it's stranded) — already accounted for in picking 1/8″; if first mode comes in low the fix is a fatter cable (3/16″), not more tension.
- **Constructional stretch** — handled by the pre-stretch + re-tension-after-settle steps (§7, §8).

Strength is never the gate (1/8″ breaks ~1400 N vs a ~100–300 N worst-case stay). And zero bending stiffness erases the anchor-misalignment bending stress a stiff member would see at a few degrees of hole misalignment — the cable simply doesn't care about the angle.

**Both beads — a swaged copper stop sleeve.** Each end terminates in a copper stop sleeve, 1/8″ size — **5.5 mm OD × 6 mm tall × 3.5 mm bore**. The 3.5 mm bore is the one that clears the cable; the 2.8 mm-bore variant does **not** pass 1/8″ cable and is the wrong part. Crimp with the manual wire-rope tool — copper is soft enough to hand-swage. (That same hand tool *cannot* swage a hard stainless ball/stud terminal — those need a hydraulic press; avoiding that press is the main reason a copper stop beats a single-shank ball here.) Copper (or stainless) sleeves are the correct rigging match for stainless cable — **never aluminum sleeves**: those are spec'd for galvanized cable and are a galvanic + spec mismatch on stainless.

**Hub end (fixed anchor):** the hub-end copper stop drops into its machined counterbore cup in the hub (§4). No adjustment — this is the dead end.

**Vertex end (the tensioner — a machined steel slug):** a small part turned on the Tormach — an externally-threaded steel cylinder with a **flat-bottom internal cup** that captures the vertex-end copper stop. It threads into the corner block (tapped M8); turning it draws the captured stop outward → tensions the cable.
- **Flat-bottom cup** (not conical) because a copper stop is a flat-ended cylinder.
- **Steel / stainless slug** into the aluminum block: no aluminum-on-aluminum thread galling, and a harder seat under the stop.
- The flat cup bottom doubles as a **thrust face** — the slug spins while the flat-ended stop stays put, so tensioning doesn't wind the cable. A dab of anti-seize helps; if the cable visibly winds on the last turns, hold it or back off — any slight wind-up relaxes on settling.

**Dimensions (from the selected 5.5 / 3.5 / 6 stop):**
- **Cup:** flat-bottom counterbore ~5.6–5.7 mm; ~3.5 mm through-hole for the bare cable; ~1 mm bearing shoulder; cup depth ~4 mm (let the stop stand proud) up to the full 6 mm.
- **Slug:** ~7.5–8 mm OD, ~1 mm wall → external **M8** into the block. That's ~one size smaller than a single-shank ball would have forced (~M9–M10), because the cup only has to clear the bare cable, not a ball's larger shank.
- **Corner block:** tap M8; add a local boss if the body's too thin to carry the thread.
- The hub cup is the same cup geometry, machined straight into the hub block (no separate part).

**MEASURE FIRST (hard rule):** crimp one copper stop on a cable scrap, caliper the *swaged* OD, and size every cup/slug/tap to that measured number **before** machining the corner blocks. The crimp moves the OD a few tenths — 5.5 mm is the design starting point, the sample is the truth.

**Shortening cable:** cut with the cable cutter (a clean shear — not side cutters, which splay the strands); seal the cut end (heat-shrink or a whisker of CA/flux) so the lay doesn't unravel before you crimp. Deburr nothing — there's nothing to deburr on a sealed cable end.

---

## 6. Key dimensions — confirm in CAD before cutting

| Quantity | Status | Set by |
|---|---|---|
| Cube edge `E` (outer) | **OPEN** | Inter-wheel clearance interference check (≥ ~2 mm gap at the shared corner; wheels 87 mm OD per `HARDWARE.md`) |
| Tube cut length `L` | Derived | `L = E − 2c` |
| Cable stay pin-to-pin (×7) | **OPEN** | CAD — each hub cup to its vertex slug seat, once `E` and the 7 anchors are placed |
| Slug / cup / corner-block tap | **≈ M8** (cup ~5.6, through-hole ~3.5); final = measured swaged-OD | §5 measure-first |
| Which vertex is free | **Default: the contact/balance corner** | Layout — but confirm against the wheel-clearance check (§9) |
| Reaction wheels | Locked | 87 mm OD, 65 g, 8.00e-5 kg·m² reflected (`HARDWARE.md`) |
| Motors | Locked | QiuLovesYT 2804, 220 KV (`HARDWARE.md`) |

---

## 7. Assembly & tensioning sequence

1. **Assemble the cage** — corner-block legs into the tubes; bond and pin each joint.
2. **Mount the three motors + wheels** to the hub's three perpendicular faces.
3. **Crimp the hub ends** — cut each cable to length; crimp a copper stop on the hub end of each of the seven.
4. **Install** — seat each hub-end stop in its hub cup; route the cable to its vertex; pass the vertex end through its steel slug, crimp the vertex copper stop, drop it into the slug cup; start each slug a few turns into its corner block.
5. **Snug all seven** so the hub sits roughly centered.
6. **Pre-stretch / bed-in** — bring every stay up near working tension and work the structure so the cable's constructional stretch comes out now. This matters more than it did with solid spoke — don't skip it.
7. **Tension it like truing a wheel** — bring the slugs up gradually, in opposing rounds, a little at a time, keeping the hub centered. Don't fully tension one before the others.
8. **Verify** (this is what the rigid strut used to give for free):
   - Hub doesn't wobble under a firm push — no slack, no loose DOF.
   - No stay goes slack when you load/spin a wheel by hand — preload beats the 0.087 N·m motor torque.
   - Hub is centered → CM at the geometric center (check against the SolidWorks target).
9. **Re-tension after it settles** (the cable will have crept), then re-verify centering.
10. **Then electronics** — per the bring-up order in `HARDWARE.md` (logic before motor power).

---

## 8. Watch items (carry through CAD and bring-up)

- **Preload vs motor torque.** A stay that goes slack under the 0.087 N·m reaction torque is instant backlash — the hub shifts, the IMU lies, the controller chases a ghost. Tension high enough that none ever unloads.
- **First mode.** All-tension *and* stranded cable's ~half effective modulus make this springier than a strut or a solid spoke; keep the hub-on-stays resonance well above the ~35–50 Hz spin rate. 1/8″ 7×7 ≈ the old 2 mm spoke axially — if the tap-test comes in low, go to a fatter cable (3/16″), not just higher tension. Tap-test on assembly; measure if in doubt.
- **Constructional stretch / creep.** Stranded cable beds in and lengthens under first tension and first runs. Pre-stretch (§7), re-tension after settling, and re-check that no stay has dropped below its preload threshold after the first spin-ups.
- **Centering is earned, not given.** Uneven tension walks the hub — and the CM — off center. Tension *to* center and verify.
- **Geometry actually spanning 6 DOF.** Intuition is placing the anchors; if the hub shows any free wobble on assembly, the 7×6 wrench-matrix check (rank 6 + an all-positive self-stress vector) pinpoints which DOF is loose. ~10 lines of numpy if you want it.

---

## 9. Gates before cutting metal

- [ ] **Inter-wheel clearance** interference check → locks `E` (≥ ~2 mm at the shared corner, 87 mm wheels).
- [ ] **Seven cable-stay paths clear the spinning wheel disks** — the make-or-break check. The cable's flexibility buys a little routing slack, but for first mode each stay still wants a near-straight chord — don't lean on big bends. Default plan: free the **contact corner** (clean balance tip, no tensioner there). **Fallback if a path won't clear:** move the *adjuster* — seat a stay's fixed copper-stop anchor at the contact corner (clean counterbore, no protruding hardware at the tip) with its steel slug tensioner up at the **hub** instead, and free a wheel-blocked vertex.
- [ ] **Crimp a sample copper stop, caliper the swaged OD, finalize cup/slug/M8** — before machining the corner blocks (§5).
- [ ] Place the 7 hub cups (offset for moment arms) and measure each pin-to-pin → cable cut lengths.
- [ ] Centering plan: how you'll confirm the hub is centered as you tension.
- [ ] Fit-test coupon for the corner-leg slip fit in the real bore.
- [x] Regenerate the frame summaries in `HARDWARE.md` and `PROJECT_BRIEF.md` to match this guide — **done in this pass** (one-line frame descriptions only; the wheel/electronics/power content in those files is unchanged).

---

## 10. Bill of materials — frame only

- 8 × 8 × 1 mm 6063 aluminum square tube — 12 cuts (buy spares; e.g. 4 × 420 mm sticks = 3 cuts each).
- Aluminum stock for 8 corner blocks (7 tapped M8 for slugs, local boss as needed; 1 shaped as the balance tip) — machined.
- Precision-ground aluminum block / 1-2-3 block for the hub — machined, with 7 copper-stop counterbore cups.
- 1/8″ (3.2 mm) 7×7 stainless aircraft cable (T316 preferred; 304 OK indoors) — length ≈ sum of the 7 stays + crimp/trim allowance (100 ft spool on hand).
- 14 × copper stop sleeves, 1/8″ (5.5 mm OD / 3.5 mm bore / 6 mm) — 2 per stay × 7, plus spares.
- Manual wire-rope crimping tool (copper stops) + cable cutter (on hand).
- Steel / stainless stock for 7 machined slug tensioners (flat-bottom cup ~5.6 mm, through-hole ~3.5 mm, external ~M8).
- Threadlocker on the slug threads; anti-seize on the cup thrust face; epoxy + transverse pins/set screws for the corner-leg joints.
- **Note:** copper (not aluminum) sleeves on the stainless cable.

*Live status — where the build is, recent decisions — stays in conversation, not in this doc.*
