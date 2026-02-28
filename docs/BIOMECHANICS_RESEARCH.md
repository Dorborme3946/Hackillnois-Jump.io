# Biomechanics Research — JumpAI

References and methodology behind each metric in the scoring system.

---

## Jump Height (30% weight)

**Method:** Flight-time derivation using physics formula:

```
h = g × (t_flight / 2)² / 2
```

Where `g = 9.81 m/s²`. Flight time is detected from ankle trajectory elevation above ground baseline using YOLO pose keypoints (indices 15, 16).

**Elite benchmark:** 40" (NBA combine top performers, e.g., Zion Williamson 45" measured).

**Reference:** Linthorne, N.P. (2001). *Analysis of standing vertical jumps using a force platform.* American Journal of Physics.

---

## Arm Swing (10% weight)

**Metric:** Wrist vertical displacement (pixels) through the last 15 frames before takeoff, normalized to 200px range = score of 99.

**Rationale:** Arm swing accounts for ~10–13% of jump height by transferring angular momentum and timing the elastic energy release. A full overhead arm drive is critical.

**Reference:** Lees, A., Vanrenterghem, J., & De Clercq, D. (2004). *Understanding how an arm swing enhances performance in the vertical jump.* Journal of Biomechanics, 37(12), 1929–1940.

---

## Knee Bend Angle (10% weight)

**Metric:** Minimum knee angle (degrees) in the last 10 frames before takeoff. Optimal = ~90°. Penalty applied for >120° (too shallow) or <60° (too deep).

**Rationale:** Optimal squat depth pre-jump maximizes muscle force production via the force-velocity and length-tension relationships of the quadriceps and gluteus maximus.

**Reference:** Vanrenterghem, J., et al. (2008). *Effect of jump height on the kinematics of jumping.* Journal of Strength and Conditioning Research.

---

## Penultimate Step (10% weight)

**Metric:** Detected via hip X-velocity spike (>2.5× mean velocity) 2–3 steps before takeoff, indicating a braking stride.

**Rationale:** The penultimate step allows horizontal-to-vertical momentum conversion — a hallmark of elite jump technique. Absence significantly reduces jump height in approach jumps.

**Reference:** Brughelli, M., et al. (2011). *Effects of running velocity on running kinetics and kinematics.* Journal of Strength and Conditioning Research.

---

## Heel Plant (5% weight)

**Metric:** Binary detection of heel strike (ankle Y coordinate pattern: heel → toe within 0.1s) before explosive toe drive.

**Rationale:** Heel plant allows the Achilles tendon to load eccentrically and store elastic energy for the concentric phase (stretch-shortening cycle). Absent in poor technique (toe-only jumpers).

**Reference:** Isaiah Rivera coaching methodology; supported by SSC (stretch-shortening cycle) research by Komi, P.V. (2000).

---

## Hip Drive (10% weight)

**Metric:** Peak hip height during flight, normalized relative to standing height (derived from pre-jump frames). Score = normalized ratio × 99.

**Rationale:** Hip drive contributes to overall center-of-mass elevation. Elite jumpers achieve hip height well above their standing height due to full hip extension at takeoff.

**Reference:** Bobbert, M.F., & van Ingen Schenau, G.J. (1988). *Coordination in vertical jumping.* Journal of Biomechanics, 21(3), 249–262.

---

## Body Alignment Airborne (5% weight)

**Metric:** Horizontal offset ratio between nose and hip during flight frames. Lower lean = higher score.

**Rationale:** Forward lean during flight wastes energy and reduces peak height. Elite jumpers maintain vertical alignment at peak to maximize height.

**Reference:** Standard biomechanics: projectile motion — center of mass trajectory is fixed at takeoff. Body posture does not affect height but indicates technique quality.

---

## Landing Technique (5% weight)

**Metric:** Knee bend increase detected within 10 frames of landing (initial angle → reduced angle = soft landing = score 1.0). Stiff landing = score 0.3.

**Rationale:** Soft landings (triple flexion: ankle, knee, hip) distribute ground reaction force over more time, reducing peak forces on ACL and patellar tendon by up to 50%.

**Reference:** Hewett, T.E., et al. (2005). *Biomechanical measures of neuromuscular control and valgus loading of the knee predict anterior cruciate ligament injury risk.* American Journal of Sports Medicine.

---

## Elite Similarity (15% weight)

**Metric:** Cosine similarity between user pose sequence embedding and pre-computed elite gallery embeddings. Scaled to 0–99.

**Model:** `EliteJumpModel` — SpatialJointEncoder (MLP per frame) + TemporalEncoder (Bidirectional GRU) → 512-d normalized embedding. Trained with triplet margin loss.

**Elite Training Sources:**
- Isaiah Rivera (YouTube — documented elite one-foot technique)
- OneFootGod series
- Olympic high jump footage
- NBA combine vertical jump clips
- Volleyball spike approach analysis
- NTU-RGB+D and Human3.6M academic datasets (supplemental)

---

## Scoring Formula

```python
overall = sum(metric_score × weight for all metrics)
```

Each metric is scaled to [0–99]. The overall score is a weighted sum:

| Metric | Weight |
|---|---|
| Jump Height | 30% |
| Arm Swing | 10% |
| Knee Bend | 10% |
| Penultimate Step | 10% |
| Heel Plant | 5% |
| Hip Drive | 10% |
| Body Alignment | 5% |
| Landing | 5% |
| Elite Similarity | 15% |

---

## Known Limitations

- **Pixel-space measurements** depend on consistent camera distance. Close-up videos skew scores.
- **Frontal-view limitation**: Depth metrics (penultimate step, arm swing in sagittal plane) are unreliable from front-facing cameras.
- **Confidence thresholds**: Keypoints below 0.5 confidence are interpolated, which may introduce errors.
- **Elite gallery size**: With fewer than 100 elite embeddings, cosine similarity scores have high variance.
