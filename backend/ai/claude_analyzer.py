"""
Claude Sonnet AI coaching report generator.
Falls back to a detailed mock report if ANTHROPIC_API_KEY is not set.
"""

import json


def generate_jump_report(
    scorecard: dict,
    biomechanics: dict,
    jump_height_inches: float,
    user_history: list[dict] | None = None,
    api_key: str = "",
) -> str:
    if api_key:
        return _call_claude(scorecard, biomechanics, jump_height_inches, user_history, api_key)
    return _mock_report(scorecard, biomechanics, jump_height_inches)


def _build_prompt(scorecard, biomechanics, jump_height_inches, user_history):
    history_context = ""
    if user_history and len(user_history) > 0:
        history_context = f"""
## Previous Jump History (from Supermemory):
{json.dumps(user_history[-5:], indent=2)}

Based on this history, identify:
1. Metrics that have IMPROVED
2. Metrics that have REGRESSED or stayed flat
3. A consistent weakness pattern across sessions
"""

    return f"""You are an elite vertical jump coach and biomechanics expert.
Analyze the following jump analysis data and provide a detailed, actionable coaching report.

## Current Jump Analysis:
- **Jump Height:** {jump_height_inches:.1f} inches
- **Overall Score:** {scorecard['overall_score']}/99

## Metric Scores (0–99):
- Jump Height Score: {scorecard['jump_height_score']}/99
- Arm Swing: {scorecard['arm_swing_score']}/99
- Knee Bend: {scorecard['knee_bend_score']}/99
- Penultimate Step: {scorecard['penultimate_step_score']}/99
- Heel Plant: {scorecard['heel_plant_score']}/99
- Hip Drive: {scorecard['hip_drive_score']}/99
- Body Alignment (airborne): {scorecard['body_alignment_score']}/99
- Landing Technique: {scorecard['landing_score']}/99
- Elite Form Similarity: {scorecard['elite_similarity_score']}/99

## Biomechanics Details:
{json.dumps(biomechanics, indent=2)}

{history_context}

## Your Report Should Include:

### 1. Performance Summary (2–3 sentences)
Brief, encouraging overview of this jump's performance.

### 2. Top 3 Strengths
What the jumper is doing well biomechanically.

### 3. Top 3 Areas to Improve (Priority Order)
Be specific — reference exact metrics and what the ideal looks like.

### 4. Drill Recommendations
For each improvement area, give 1–2 specific drills or exercises (name them, explain briefly).

### 5. Next Session Focus
One primary cue or drill to focus on exclusively in the next training session.

{"### 6. Progress Analysis" if user_history else ""}
{"Compare this jump to previous sessions — what's trending better, what needs attention?" if user_history else ""}

Keep the tone motivational but honest. Be specific, not generic.
"""


def _call_claude(scorecard, biomechanics, jump_height_inches, user_history, api_key) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    prompt = _build_prompt(scorecard, biomechanics, jump_height_inches, user_history)
    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def _mock_report(scorecard: dict, biomechanics: dict, jump_height_inches: float) -> str:
    overall = scorecard.get("overall_score", 50)
    height = jump_height_inches
    arm_swing = scorecard.get("arm_swing_score", 50)
    knee_bend = scorecard.get("knee_bend_score", 50)
    landing = scorecard.get("landing_score", 50)
    penultimate = scorecard.get("penultimate_step_score", 50)
    heel_plant = scorecard.get("heel_plant_score", 50)
    body_align = scorecard.get("body_alignment_score", 50)

    # Determine tier
    if overall >= 75:
        tier = "advanced"
        summary = f"Excellent jump! At {height:.1f} inches with an overall score of {overall}/99, you're performing at an advanced level. Your mechanics show real understanding of explosive movement."
    elif overall >= 55:
        tier = "intermediate"
        summary = f"Solid jump at {height:.1f} inches with an overall score of {overall}/99. You have a good foundation to build on, with clear opportunities to add meaningful inches through technique refinement."
    else:
        tier = "developing"
        summary = f"Good effort at {height:.1f} inches with an overall score of {overall}/99. Every elite jumper started somewhere — the biomechanics data reveals exactly where to focus for rapid improvement."

    # Identify strengths
    all_scores = {
        "Heel Plant":         heel_plant,
        "Penultimate Step":   penultimate,
        "Arm Swing":          arm_swing,
        "Knee Bend":          knee_bend,
        "Body Alignment":     body_align,
        "Landing Technique":  landing,
    }
    sorted_scores = sorted(all_scores.items(), key=lambda x: x[1], reverse=True)
    strengths = sorted_scores[:3]
    improvements = sorted_scores[-3:]

    strengths_text = "\n".join([
        f"- **{name} ({score}/99):** {'Excellent execution — keep it up.' if score >= 70 else 'Above-average performance in this area.'}"
        for name, score in strengths
    ])

    improvements_text = "\n".join([
        f"- **{name} ({score}/99):** {'Focus area — see drill recommendations below.' if score < 50 else 'Room to grow with targeted practice.'}"
        for name, score in improvements
    ])

    # Drills based on weaknesses
    drill_map = {
        "Arm Swing": (
            "**Jump Rope with Exaggerated Arm Swing** — 3×60 sec, focusing on full shoulder rotation and driving arms overhead.\n"
            "**Medicine Ball Throw Drills** — Hold 4–6 lb med ball, practice the arm-swing trajectory while standing."
        ),
        "Knee Bend": (
            "**Box Squat Protocol** — 4×6 at 60% 1RM, pausing for 2 seconds at 90° to ingrain optimal depth.\n"
            "**Depth Jump Landings** — Drop from 12\" box and freeze in the landing position; check knee angle matches 90°."
        ),
        "Penultimate Step": (
            "**Penultimate Step Drill** — Mark foot placement with tape. Approach slowly, focusing on the braking step converting horizontal to vertical momentum.\n"
            "**Approach + Freeze** — Run 3-step approach, freeze at the penultimate step, and self-assess foot strike."
        ),
        "Heel Plant": (
            "**Slow-Motion Approach Drills** — Walk through the jump in slow motion focusing on heel-to-toe transition before the toe drive.\n"
            "**Ankle Mobility Work** — 2×15 banded ankle distractions to improve heel-strike mechanics."
        ),
        "Body Alignment": (
            "**Vertical Jump Against Wall** — Jump next to a wall to get instant feedback on forward lean.\n"
            "**Core Bracing Drill** — Plank variations (3×45 sec) to build the core stiffness needed to stay aligned mid-flight."
        ),
        "Landing Technique": (
            "**Landing Mechanics Drill** — Drop from progressively higher boxes (8\", 12\", 18\"), focusing on soft, bilateral, triple-flexion landing.\n"
            "**Eccentric Quad Training** — Nordic curls and slow-negative squats to improve force absorption on landing."
        ),
    }

    drills_text = ""
    for name, score in improvements:
        drill = drill_map.get(name, "Work with a coach on specific technique cues for this area.")
        drills_text += f"\n**{name}:**\n{drill}\n"

    worst_metric, worst_score = improvements[0]
    next_session_map = {
        "Arm Swing": "Focus exclusively on arm-swing timing today. Do 20 standing vertical jumps thinking only about driving your arms overhead at takeoff. No other cues.",
        "Knee Bend": "Set up a mirror or camera at side angle. Do 3 sets of 5 vertical jumps pausing at the deepest crouch to verify ~90° knee angle before exploding up.",
        "Penultimate Step": "Walk through a 3-step approach 20 times at half speed, focusing on feeling the braking penultimate step. Then add speed gradually.",
        "Heel Plant": "Do 10 approach jumps thinking only about the heel-first contact of your plant foot. Ignore jump height entirely — just feel the heel-to-toe transition.",
        "Body Alignment": "Jump next to a wall or use video. Do 10 jumps with one verbal cue: 'tall and tight.' Aim to look straight up at the ceiling at peak height.",
        "Landing Technique": "Drop from a 12\" box and stick the landing for 3 seconds. Do 3×5 reps. Focus on quiet, controlled landings before moving to explosive work.",
    }
    next_session = next_session_map.get(worst_metric, f"Focus on improving your {worst_metric} in your next session with targeted drills.")

    return f"""## Performance Summary

{summary}

---

## Top 3 Strengths

{strengths_text}

---

## Top 3 Areas to Improve

{improvements_text}

---

## Drill Recommendations

{drills_text}

---

## Next Session Focus

{next_session}

---

*Analysis powered by JumpAI — Upload your next jump to track progress over time.*
"""
