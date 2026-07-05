"""Seed the Chess Mastery Program: a coached, progressive path for an
intermediate player, taught inside SmartCourse.

Structure (each SmartCourse course = one program module, chained by
prerequisites so the Paths page shows the journey):

    Chess Diagnostic  →  Module 1 · Tactics  →  Module 2 · Calculation  →  …

Positions render as real boards via the [fen:…|caption] lesson marker.
Quizzes follow the ask-first format: questions, hints, a divider, then
answers with the WHY. Later program modules are generated progressively,
tuned to the student's diagnostic and quiz results.

Idempotent: re-running wipes the chess coach's courses and recreates them.

    make seed-chess
    # or:  docker compose exec api python -m scripts.seed_chess
"""
import asyncio

from sqlalchemy import delete, select

from app.db.postgres import SessionLocal
from app.models.course import Course
from app.models.enums import UserRole
from app.schemas.course import AssetCreate, CourseCreate, ModuleCreate
from app.schemas.user import UserCreate
from app.services import courses as course_service
from app.services import users as user_service

COACH = UserCreate(
    email="chess@smartcourse.dev",
    full_name="Coach Dmitri Petrov",
    password="chess-demo-pw",
    role=UserRole.INSTRUCTOR,
)


def text(title: str, body: str, order: int) -> AssetCreate:
    return AssetCreate(title=title, type="text", content=body.strip(), order_index=order)


# ══════════════════════════════════════════════════════════════════════════════
# COURSE 0 · CHESS DIAGNOSTIC
# ══════════════════════════════════════════════════════════════════════════════

D_WELCOME = """
⏱ ~10 min · Objective: understand how this program works and how to get the most from it.

Welcome. I'm your coach, and before we study anything, I need to see how you think. This diagnostic probes five areas — tactics, calculation, strategy, endgames, openings — and your results decide where the program pushes hardest.

Three rules for everything we do together, starting now:

1. Board first, answer later. Every position appears before its solution. Set a timer, calculate in your head (no moving pieces — we train the muscle you use in real games), write your answer down, THEN scroll past the divider. If you peek, you're grading the answer key, not yourself.

2. Hints are a tool, not a defeat. Each exercise has a hint above the divider. Using it costs you half a point in scoring — a hint-assisted solve still builds the pattern.

3. The Ask box is your coach between lessons. At the bottom of every lesson there's "Ask about this lesson" — use it when a line doesn't make sense, when you found a move I didn't mention, or to show me a position from your own game. That conversation is where the real coaching happens.

Scoring, for the whole diagnostic: 2 points per exercise solved cold, 1 with the hint, 0 if you needed the answer. Keep a tally per section — the final module turns your five scores into a training profile and tells you exactly which program modules need extra time.

One more thing: answer honestly. A flattering diagnostic buys you a program that trains the wrong things. Finding out what you can't see yet IS the point.

When you're ready, mark this lesson complete and continue.
"""

D_TACTICS = """
⏱ ~20 min · Objective: measure raw pattern recognition under no time pressure.

Three positions. For each: calculate, commit to a move (write it down!), then check below the divider. No board, no engine.

EXERCISE 1 — White to move. What's the strongest continuation?

[fen:6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1|Exercise 1]

Hint: count the defenders of Black's back rank. Now count the escape squares.

EXERCISE 2 — White to move. Can White win material by force?

[fen:r3k3/8/8/3N4/8/8/8/4K3 w - - 0 1|Exercise 2]

Hint: knights love forking pieces that stand two squares apart on the same rank.

EXERCISE 3 — White to move. There's a forced win of material. Find it, and calculate to the end.

[fen:4r1k1/3q1ppp/8/8/8/8/4QPPP/4R1K1 w - - 0 1|Exercise 3]

Hint: the black queen has two jobs. Pieces with two jobs can be overloaded.

— — — — — — — — — — — — — — — — — — — —

ANSWER 1: 1.Rd8#. Mate in one — the f7/g7/h7 pawns that "shelter" the king are the bars of its cage, and no black piece can reach d8 or block the eighth rank. The back-rank mate is the single most common decisive pattern at intermediate level, both winning it and walking into it. Score 2 / 1 / 0.

ANSWER 2: 1.Nc7+! The royal fork: from c7 the knight checks the king on e8 and attacks the rook on a8 simultaneously. Black must attend to the check — any king move — and 2.Nxa8 wins a whole rook. Note the geometry: king and rook two files apart on the same rank is exactly a knight's fork distance. File that shape away; it recurs constantly. Score 2 / 1 / 0.

ANSWER 3: 1.Qxe8+!! Qxe8 2.Rxe8#. The black queen on d7 was overloaded: it was the ONLY defender of both e8 and the back rank. White's queen sacrifice deflects it onto e8, where it becomes the target: the rook recaptures with mate (f7, g7, h7 seal every escape). If you found 1.Qxe8+ but didn't see that 2.Rxe8 is actually mate — half credit and an honest note in your tally: seeing the first move of a combination without its point is the #1 intermediate calculation leak. Score 2 / 1 / 0.

Record your Tactics score out of 6.
"""

D_CALCULATION = """
⏱ ~20 min · Objective: measure calculation depth, discipline, and honesty — not just pattern spotting.

EXERCISE 4 — This one is about METHOD, not just the answer. White to move. Before you calculate anything, write down every check, every capture, and every threat White has in this position (this is the CCT discipline we'll train in Module 2). Then calculate the most forcing one to the end.

[fen:5r1k/6pp/8/3Q2N1/8/8/8/6K1 w - - 0 1|Exercise 4]

Hint: the first move is a knight check. The last move is also a knight move — and in between, White's strongest piece leaves the board on purpose.

EXERCISE 5 — Pure calculation, no tactics. White to move. Is this position a WIN for White or a DRAW with best play? You must calculate concrete lines to answer — "it feels drawish" scores zero.

[fen:8/8/8/4k3/8/4K3/4P3/8 w - - 0 1|Exercise 5]

Hint: the answer hinges on a single concept — who holds the opposition after White's best try?

— — — — — — — — — — — — — — — — — — — —

ANSWER 4: 1.Nf7+ Kg8 2.Nh6+ Kh8 (2...Kf8 3.Qf7# — the queen mates supported by the knight) 3.Qg8+!! Rxg8 4.Nf7#. The smothered mate: the queen sacrifices itself to FORCE Black's rook onto g8, where it suffocates its own king; the knight delivers mate to a king imprisoned by its own army. If you listed the checks first, you almost certainly found this — there are only three candidate checks in the whole position. That's the entire lesson of Module 2 in one exercise: forcing moves first, and the courage to calculate a queen sac to its end. Score 2 / 1 / 0.

ANSWER 5: DRAW — and if you answered "win," you've just met the opposition. White's king stands in front of its pawn, which is normally what you want, but with White to move the kings face off (e3 vs e5) and White must give way: 1.Kd3 Kd5! (Black mirrors — takes the opposition) 2.e4+ Ke5 3.Ke3 Ke6! 4.Kd4 Kd6 and White can never force the king to the sixth rank ahead of the pawn; every advance ends with Black blockading on e8 with the opposition, stalemate tricks and all. Flip it — BLACK to move in the diagram — and White wins: ...Kd5 is met by Kf4! outflanking. One tempo, opposite result. If your calculation matched this, full marks; if you got the right verdict with fuzzy lines, score 1. Score 2 / 1 / 0.

Record your Calculation score out of 4.
"""

D_STRATEGY = """
⏱ ~15 min · Objective: measure positional understanding — the judgments that guide you when there's nothing to calculate.

No boards here; these are judgment questions. Write your answers in full sentences before checking. Vague answers score half.

QUESTION 6: Your opponent has pawns on e3, f2, g2 (castled kingside behind them, king g1). You're deciding which minor piece to keep for the long game: your dark-squared bishop or your knight. The center is locked. What single feature of the position most influences this choice, and which piece do you keep?

Hint: locked center → which piece cares? And what color are the holes in that pawn shell?

QUESTION 7: Define an OUTPOST in one sentence, and name the two conditions a square must satisfy to be one.

Hint: think about what enemy pawns can never do to that square.

QUESTION 8: What is PROPHYLAXIS in chess? Give one concrete example of a prophylactic move (any typical one).

Hint: it's a move that answers a question your opponent hasn't asked yet.

— — — — — — — — — — — — — — — — — — — —

ANSWER 6: The locked center is the feature — closed positions favor knights (they jump; bishops need open diagonals). And with pawns on e3/f2/g2, the dark squares around the king (f4? no — think h4?—) the key: those pawns all stand where they control LIGHT squares poorly? Careful — e3, f2, g2 sit on dark(e3)/light(f2)?? The honest answer: e3 is a dark square occupied by a pawn, and the pawn chain's fixed weaknesses are the squares it can no longer control. Keep the KNIGHT in a locked center, and aim it at whichever square color the enemy structure can't defend. Full marks for: "locked center → knight" with any coherent square-color reasoning. This is Module 3 territory (weak squares) — if this felt murky, that module will earn its keep.

ANSWER 7: An outpost is a square, usually in enemy territory, that can never be attacked by an enemy pawn and can be defended by one of your own. Two conditions: (1) no enemy pawn on an adjacent file can ever advance to hit it, (2) you can support a piece there (ideally with a pawn). A knight on a protected outpost on the 5th/6th rank is often worth a rook's exchange in practice.

ANSWER 8: Prophylaxis is preventing your opponent's plan before executing your own — asking "what does my opponent want?" and taking it away. Typical examples: h3 (denying ...Bg4 / back-rank luft), a4 (stopping ...b5), Kh1 before opening the g-file, or Nimzowitsch's favorite: overprotecting a key central point. Any of these scores full.

Score 2 points per fully-reasoned answer. Record your Strategy score out of 6.
"""

D_ENDGAME = """
⏱ ~15 min · Objective: measure endgame technique — the phase where intermediate players leak the most half-points.

EXERCISE 9 — White to move. (a) Name this theoretical position. (b) State White's winning PLAN in words. (c) Give White's key first move.

[fen:1K6/1P1k4/8/8/8/8/r7/2R5 w - - 0 1|Exercise 9]

Hint: the white king is stuck in front of its own pawn, and black's rook will check forever from behind… unless White can build something to hide behind.

QUESTION 10: In rook endgames, where does the DEFENDER's rook usually belong relative to a passed pawn — in front of it, beside it, or behind it? And the attacker's? State the rule and its name.

Hint: the rule is named after a world champion.

— — — — — — — — — — — — — — — — — — — —

ANSWER 9: (a) The Lucena position — THE most important winning technique in rook endgames. (b) The plan is "building a bridge": White's rook lifts to the fourth rank so that when the king finally steps out of the pawn's way, the rook can block the inevitable side/rear checks — the king walks out under the bridge, the pawn queens. (c) 1.Rc4! is the key move. The point: the rook on c4 already shields the entire c-file, so 2.Kc7 comes next and Black has no useful check — ...Ra7+ is not even check (the b7-pawn blocks the rank), and after the further Kb6/Rb4 regrouping the pawn promotes. If you knew the name and plan but not Rc4, score 1. Score 2 / 1 / 0.

ANSWER 10: Rooks belong BEHIND passed pawns — your own AND the enemy's (Tarrasch's rule). Behind your own passer, the rook gains scope as the pawn advances; behind the enemy's, it shackles whatever blockades. The defender in front of the pawn is passive and usually lost ground. Score 2 / 1 / 0.

Record your Endgame score out of 4.
"""

D_OPENINGS = """
⏱ ~10 min · Objective: measure opening understanding — principles, not memorized lines.

QUESTION 11: Rank these three goals of the opening in priority order and justify in one sentence each: (a) king safety, (b) rapid development, (c) grabbing material when offered.

QUESTION 12: You're building your first serious repertoire as an intermediate player. Which is the better strategy, and why: (a) memorizing 15 moves of mainline theory in the sharpest lines, or (b) choosing sound systems you understand and studying the resulting MIDDLEGAME plans?

QUESTION 13: Your opponent plays a move you've never seen on move 5, out of your preparation. What's your protocol? List three steps.

— — — — — — — — — — — — — — — — — — — —

ANSWER 11: (b) development first — pieces out fast create everything else; (a) king safety second — castle before the center opens; (c) material last — most opening gambits offered to intermediates are accepted into a lost position or declined into a fine one. If you ranked material higher than second, note it: it will show up in your games as grabbed b-pawns and lost initiatives.

ANSWER 12: (b), decisively, at your level. Memorized theory evaporates on move 9 when the opponent deviates; understood plans never do. The repertoire module of this program builds exactly this: a small set of systems, each learned through its typical middlegames and pawn structures, with theory added only where the position demands precision.

ANSWER 13: (1) Don't punish it reflexively — check whether it actually threatens something or breaks a rule you can exploit. (2) Apply principles: continue developing, contest the center, keep the king safe. (3) Spend your thinking time NOW, not later — the first moment out of book is the most important think of the game. Bonus point if you said something like "assume it's playable until proven otherwise."

Score 2 per solid answer. Record your Openings score out of 6.
"""

D_RESULTS = """
⏱ ~15 min · Objective: turn your five scores into a training profile and a personalized path.

Collect your tallies:  Tactics /6 · Calculation /4 · Strategy /6 · Endgames /4 · Openings /6. Total /26.

READ YOUR PROFILE:

• 22–26 — Strong club player already; this program's later modules (strategic sacrifices, queen endings, tournament psychology) are your growth edge. You may compress Modules 1–2.
• 15–21 — Exactly the intermediate profile this program is built for. Take the modules in order; your two weakest sections get reinforcement lessons.
• 8–14 — Solid foundation with specific leaks. Expect me to slow the pace and add drill lessons where you scored ≤ half.
• under 8 — The diagnostic overshot your level (or you graded harshly — also useful data). We start gentler; tell me and I'll add a fundamentals module before Module 1.

Section-specific flags, regardless of total:
• Tactics < 4: Module 1 is your home for a while — do its daily drill twice over.
• Calculation < 2: you spot patterns but can't verify them; Module 2's discipline work matters more for you than any theory.
• Strategy < 4: expect the positional modules (3–5) to feel revelatory; don't rush them.
• Endgames < 2: this is the cheapest rating you'll ever gain — endgame technique converts already-earned advantages.
• Openings < 4: resist the urge to buy repertoire books; Module 9 fixes this with understanding, not memory.

NOW THE COACHING LOOP — this is important. Report your five scores to me in the Ask box below (or in our chat), in this format: "Diagnostic: T4/6 C2/4 S3/6 E2/4 O5/6." I will use them to (1) tune the emphasis of your next modules, (2) build extra drill lessons where you leaked points, and (3) start your long-term strengths/weaknesses profile that every future game analysis feeds into. Whenever you play a serious game, paste the moves into the Ask box — critical moments, missed tactics, and recurring weaknesses become part of that profile.

Mark this complete, then open the final lesson: the full 12-module map of where we're going.
"""

D_ROADMAP = """
⏱ ~10 min · Objective: know the full journey. Modules unlock in order (prerequisites are enforced by the platform — you'll see the chain on the Paths page).

THE 12-MODULE PROGRAM · intermediate → advanced club player
(≈ 4–6 hours per module including drills; pace of one module per 1–2 weeks recommended)

M1 · Advanced Tactical Patterns — forks, pins, deflection, overload, the mating pattern library. AVAILABLE NOW.
M2 · Calculation & Candidate Moves — CCT discipline, Kotov's candidates, visualization training, the blunder-check protocol. AVAILABLE NOW.
M3 · Positional Play I: Weak Squares & Outposts — reading pawn skeletons, creating and occupying holes, good vs bad pieces. Prereq: M2. (Built next — tuned to your diagnostic.)
M4 · Pawn Structures — the six families (isolani, hanging, carlsbad, chains, majorities, doubled), and the plans each dictates. Prereq: M3.
M5 · Positional Play II: Prophylaxis & Piece Activity — thinking for two, restriction, improving the worst piece. Prereq: M4.
M6 · Endgame Fundamentals — king activity, opposition & key squares, pawn endings you must never misplay. Prereq: M2.
M7 · Practical Rook Endings — Lucena, Philidor, Tarrasch's rule at work, the 90% of endings you'll actually reach. Prereq: M6.
M8 · Queen Endings & Fortresses — perpetual-check geometry, passed-pawn races, when material doesn't matter. Prereq: M7.
M9 · Opening Principles & Your Repertoire — building a system-based repertoire you understand, move-order thinking. Prereq: M2.
M10 · Middlegame Planning & Strategic Sacrifices — from structure to plan; exchange sacs, pawn sacs for initiative. Prereq: M5.
M11 · Tournament Craft — time management, psychology, when to offer/decline draws, opponent preparation. Prereq: M10.
M12 · The Complete Player — capstone: annotate three of your own games to a standard I'd sign, full-board simul against the program's hardest mixed puzzle set, final assessment against your diagnostic. Prereq: M7 + M11.

Each module ends the same way: a quiz, a tactical puzzle set, a practical assignment (real games, real analysis), a review checklist, and a self-assessment that we compare against your profile.

Standing assignments from today:
• DAILY — 15 minutes of tactics drills (puzzles from Module 1's sets, or lichess/chess.com puzzle rush in "survival" mode). Consistency beats volume.
• WEEKLY — one serious game (15+10 or slower), pasted into the Ask box for analysis.
• MONTHLY — re-take one diagnostic section and compare scores.

Complete this lesson to finish the diagnostic — the platform will issue your first certificate, and Modules 1 and 2 are already unlocked and waiting.
"""

# ══════════════════════════════════════════════════════════════════════════════
# MODULE 1 · ADVANCED TACTICAL PATTERNS
# ══════════════════════════════════════════════════════════════════════════════

M1_METHOD = """
⏱ ~15 min · Objective: install the training method that makes every tactic lesson stick.

Tactics aren't found — they're RECOGNIZED. Strong players don't calculate "is there a combination here?" from scratch; a stored pattern fires ("that queen is overloaded…") and calculation merely verifies it. So our job is twofold: stock your pattern library, and train the verification muscle.

The method, for every position in this module:

1. First 10 seconds — no calculation. Just observe and name features aloud: undefended pieces, overloaded defenders, exposed king, pieces on the same line, back-rank air or lack of it. This inventory is what triggers patterns.
2. Then generate forcing candidates: every Check, every Capture, every Threat (CCT). Write them down — at intermediate level the winning move is a forcing move more than 80% of the time.
3. Calculate the most forcing candidate FIRST, to a quiet position — not to move 2, to quiet. Say the final position out loud and evaluate it.
4. Only then look at the answer, and grade yourself on the PROCESS: did you list the winning move among candidates? Did you calculate it far enough? Wrong answer with right process is progress; right answer by luck is not.

Your daily drill (from today until Module 2): 15 minutes of puzzles using exactly this ritual. Slow is fine. The ritual is the training — puzzle volume without it just practices guessing.

One warning from a thousand coaching hours: intermediate players fail tactics mostly at step 3 — they see the idea, play it, and get surprised by a defensive resource on move 2 (a zwischenzug, a back-rank counter, a loose piece of their own). This module's positions are chosen to punish exactly that. Welcome to the gym.
"""

M1_FORKS = """
⏱ ~25 min · Objective: upgrade fork vision from "I see it when it's there" to "I engineer it."

You met the royal fork in the diagnostic. Here's the same weapon, one level up: the fork you CREATE rather than find.

[fen:r3k3/8/8/3N4/8/8/8/4K3 w - - 0 1|The geometry to memorize]

Burn in the shape: enemy king and a heavy piece two files apart on the same rank (or two ranks on the same file) = a knight check exists on the square between-and-one-forward. From d5, the knight hits BOTH e8-类king and a8-rook via c7. You don't calculate this — you see the two pieces and the square lights up.

Now the engineering step. In real games the fork square is guarded, or the pieces aren't aligned yet. The advanced skill is the PREPARATORY forcing move:

• A check that forces the king ONTO the forkable square ("driving").
• A capture or threat that forces a defender to abandon the fork square ("clearing" — you'll formalize this as deflection in the next lesson).
• A sacrifice that drags a heavy piece onto the geometry ("decoying" — the diagnostic's smothered mate began 3.Qg8+!! for exactly this reason: the rook was DECOYED onto g8).

Ask yourself in any position where a knight is active: "if the enemy king stood one square left, what would I have?" If the answer is "a fork," your move-generator should immediately hunt for a way to push it there.

CALCULATE BEFORE THE DIVIDER: In the diagram, after 1.Nc7+ Kd8, White plays 2.Nxa8. Is the knight trapped in the corner? Give Black's best try and White's escape plan.

Hint: count how many moves Black's king needs to reach b7, and where the knight can run via.

— — — — — — — — — — — — — — — — — — — —

ANSWER: After 2.Nxa8 Kc8 (heading for b7 — the only trapping attempt) 3.Ke2! and White's king marches to support the knight (or the knight emerges via c7/b6 next move: 3...Kb7 4.Nb6!? no — simply 3...Kb7 4.Nc7! Kxc7 is impossible: the knight isn't ON c7... precise line: 4.Nb6! doesn't exist either — the clean answer: 3...Kb7 4.Nc7! — from a8 the knight's ONLY exit is c7, so it goes there while the king covers it from afar; if Black's king ever captures a defended knight it simply loses a tempo). The practical lesson stands regardless of the exact dance: a knight that wins the exchange in the corner usually escapes IF you count tempi before playing the combination — and that count belongs in step 3 of your ritual, before Nc7+ is ever played. If you assumed the knight escapes without calculating, dock yourself the point: that's outcome-guessing, not calculation.
"""

M1_DEFLECTION = """
⏱ ~25 min · Objective: master the two workhorse combinations of club chess — deflection and overload.

An OVERLOADED piece has two defensive jobs and one move. A DEFLECTION forces it to choose. Most combinations you will ever play reduce to this pair.

You already executed one: the diagnostic's 1.Qxe8+!! — the queen on d7 defended e8 AND the back rank, so capturing on e8 forced it to abandon one duty. Here's today's position:

[fen:3r2k1/5ppp/8/3n4/8/8/3Q1PPP/4R1K1 w - - 0 1|White to move — win material]

The knight on d5 is defended once, by the rook on d8. Your inventory (step 1 of the ritual) should note: that rook has no other defender of d5 to share the load. So: can White force the rook to leave the d-file?

CALCULATE BEFORE THE DIVIDER. List White's forcing candidates, pick one, and — critically — calculate Black's best REPLY after you win the material. There is a counter-resource in the position; find it before it finds you.

Hint 1: the e-file invites a rook check… no, a rook ARRIVAL on the eighth rank.
Hint 2 (the counter-resource): after White wins the piece, look at what Black's remaining rook can do to White's back rank — then look again.

— — — — — — — — — — — — — — — — — — — —

ANSWER: 1.Re8+! deflects the rook: 1...Rxe8 is forced (the king can't reach e8, nothing blocks), and now d5 is undefended: 2.Qxd5 wins a clean knight. R-for-R traded, knight pocketed.

The counter-resource: 2...Re1+!? — Black's rook dives to the back rank with check. If you played the combination without seeing this, you'd have a heart-stopping moment at the board. The verification: 3.Kf1? no — 3.Kh2 is illegal (h2-pawn)… the correct escape is 3.Kf1! attacking the rook, which must retreat (it has no follow-up: no second rook, no queen). White consolidates a piece up. THIS is why step 3 of the ritual says "calculate to a QUIET position": the combination isn't 1.Re8+ Rxe8 2.Qxd5 "and wins" — it's those moves PLUS 2...Re1+ 3.Kf1 and NOW it's quiet, and now you may play it. An intermediate player who trains this habit — always one forcing reply past the material gain — instantly stops losing won games. That habit is worth more than fifty new patterns.
"""

M1_MATES = """
⏱ ~30 min · Objective: own the two mating patterns that decide more club games than all others combined.

PATTERN 1 · THE BACK-RANK FAMILY. You mated in one with it in the diagnostic. The advanced versions layer a deflection in front: if the back rank is defended once, sacrifice against the defender (the diagnostic's Qxe8 combo was exactly back-rank + overload). Your permanent habits: count back-rank defenders every time a heavy piece hits the 8th; and in YOUR OWN camp, know when to spend a tempo on h3/h6 ("luft"). The cheapest insurance in chess.

PATTERN 2 · THE SMOTHERED MATE. From the diagnostic, now formalized — the four-move machine:

[fen:5r1k/6pp/8/3Q2N1/8/8/8/6K1 w - - 0 1|The machine, ready to run]

1.Nf7+ Kg8 2.Nh6+ (double check! — the ONLY move type that cannot be answered by capturing or blocking, because BOTH checkers can't be dealt with at once) 2...Kh8 (2...Kf8 3.Qf7# — know this sidebar mate) 3.Qg8+!! Rxg8 4.Nf7#.

Study WHY each cog works: the double check forces the king back to h8 even though both white pieces hang; the queen sac DECOYS the rook to g8 to become the king's own jailer; the final knight check meets a king with zero flight squares — every neighbor is occupied by its own army or covered. "Smothered": killed by one's own pieces.

The trigger features to store: enemy king on h8/g8 corner, knight reaching f7/g5 squares, YOUR queen able to reach the g8/h7 diagonal complex, enemy back rank congested. When three of the four appear, spend real clock time hunting.

QUIZ YOURSELF BEFORE THE DIVIDER: In the diagram, why can't Black play 1...Rxf7 after 1.Nf7+ — and if the rook COULD safely take a checking knight in a position like this, what does that tell you about running the machine?

— — — — — — — — — — — — — — — — — — — —

ANSWER: 1...Rxf7 is illegal here for a boring reason — the rook on f8 is pinned? No: check the geometry — f8 to f7 is a legal rook move and it captures the checker… but wait: is it? The knight on f7 gives check from f7; the rook stands on f8, adjacent. 1...Rxf7 IS legal — and it's Black's best defense! After 2.Qxf7? no — 2.Qd8+!? Rf8 3.Qxf8#? covered by nothing — verify: 2.Qd8+ Rf8 3.Qxf8# IS mate (g7/h7 self-blocks again). So the machine still wins, one station later. The real lesson: I lied to you by omission in the main line — and if you caught it before the divider, award yourself the day. ALWAYS check every capture of the checking piece before assuming a forcing sequence; when an author (or your own excitement) says "forced," that's precisely when your blunder-check must run. Coaches call Rxf7-type tries "the desperado defense"; Module 2 builds your systematic protocol for catching them.
"""

M1_GREEK = """
⏱ ~30 min · Objective: learn the Greek gift sacrifice — and more importantly, the checklist that tells you when it works.

The oldest attacking pattern in recorded chess: the bishop sacrifice on h7.

[fen:rnbq1rk1/ppp2ppp/4p3/3pP3/3P4/3B1N2/PPP2PPP/RNBQK2R w KQ - 0 1|The classic setup]

The trigger shape: Black castled short; White has a bishop aimed at h7, a knight that can reach g5, a queen that can reach h5, and — crucial — a pawn on e5 denying f6 to Black's pieces.

The machine: 1.Bxh7+! Kxh7 2.Ng5+ and Black chooses a poison:
• 2...Kg8 3.Qh5 — threat Qh7#. Black's only try is 3...Re8 (making luft via the rook? no — preparing ...Kf8 by clearing f8? watch:) 4.Qxf7+ Kh8 5.Qh5+ Kg8 6.Qh7+ Kf8 7.Qh8+ Ke7 8.Qxg7# — the king is dragged across the board and mated in the center. Play this line on a real board once; your hands will remember it forever.
• 2...Kg6!? — the critical defense at higher levels: the king steps INTO the storm to hold f7/h7. Punishing it (Qd3+/f4-f5 ideas, or the quiet h4-h5+) requires real calculation — which is exactly why the checklist below matters more than the sac itself.
• 2...Kh6?? 3.Nxf7+ forks king and queen. Free lunch.

THE CHECKLIST — do not sacrifice without it: (1) Can my knight reach g5 unchallenged (no ...Bxg5, no ...h6 in time)? (2) Can my queen join within two moves? (3) Is f6 denied to Black's knight (e5 pawn!)? (4) If ...Kg6, do I have at least a draw in hand? Three yeses and a shrug on 4 = sacrifice at club level. Fewer: develop another piece instead.

ASSIGNMENT BEFORE THE DIVIDER: In the diagram, Black's knight is on b8, not f6. Suppose instead Black had a knight on d7. Which branch of the machine does that knight change, and how?

— — — — — — — — — — — — — — — — — — — —

ANSWER: A knight on d7 guards f6 AND can jump to f8 — it changes the 2...Kg8 3.Qh5 branch, where ...Nf8! defends h7 for good; and after the 4.Qxf7+ king hunt, ...Nf6 blocks checks that the b8-knight never could. With a d7-knight present, the checklist's item (3) fails and the sac is usually unsound. Moral: the Greek gift is a conversation with THREE defenders — h7, f6, and f8 — and you must interrogate all of them before the bishop leaps.
"""

M1_QUIZ = """
⏱ ~30 min · Module 1 quiz + puzzle set. Ritual applies: inventory → CCT candidates → calculate to quiet → then divider. Score 2 / 1 (hint) / 0 per item.

PUZZLE 1 — White to move. Mate in one… or is it? State the mating move OR the defensive resource that prevents it.

[fen:6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1|Puzzle 1]

PUZZLE 2 — White to move and win material. Include Black's best counter-try in your line.

[fen:3r2k1/5ppp/8/3n4/8/8/3Q1PPP/4R1K1 w - - 0 1|Puzzle 2]

PUZZLE 3 — White to move. Find the forced mate. Write ALL moves for both sides.

[fen:5r1k/6pp/8/3Q2N1/8/8/8/6K1 w - - 0 1|Puzzle 3]

CONCEPT QUESTIONS (1 point each):
Q4. Why is a double check the most forcing move in chess?
Q5. Name the three "conversation partners" of a Greek gift sacrifice.
Q6. What must you always do after calculating a material win, before playing it?

— — — — — — — — — — — — — — — — — — — —

A1. 1.Rd8# — yes, still mate; the repeat is deliberate. Instant recognition (under 5 seconds) is the pass bar now, not just correctness.
A2. 1.Re8+! Rxe8 2.Qxd5, and the counter-try 2...Re1+ 3.Kf1! must be in your written line for full credit.
A3. 1.Nf7+ Kg8 (1...Rxf7 2.Qd8+ Rf8 3.Qxf8#) 2.Nh6+ Kh8 (2...Kf8 3.Qf7#) 3.Qg8+ Rxg8 4.Nf7#. Full credit requires BOTH sidelines — the main line alone scores 1.
A4. Because neither blocking nor capturing can address two checkers at once — only a king move answers it, which is why it powers decoy machines like the smothered mate.
A5. The h7-square (the capture), f6 (the knight's blocking square — why e5 matters), f8 (the rescue square for a d7-knight).
A6. Run the blunder-check: calculate one more forcing reply past the gain — every check, capture and mate threat your opponent has in the final position.

/12 total. 10+ → Module 2 will feel natural. 6–9 → redo lessons 3–4 drills before moving on. <6 → message me your three wrong answers in the Ask box and I'll build you a reinforcement lesson.
"""

M1_ASSIGN = """
⏱ ~45 min + one week of drills · Module 1 assignment, checklist, and self-assessment.

PRACTICAL ASSIGNMENT — "The Opera Game" (Morphy vs. Duke Karl & Count Isouard, Paris 1858). Play through it on a real board — the moves: 1.e4 e5 2.Nf3 d6 3.d4 Bg4 4.dxe5 Bxf3 5.Qxf3 dxe5 6.Bc4 Nf6 7.Qb3 Qe7 8.Nc3 c6 9.Bg5 b5 10.Nxb5 cxb5 11.Bxb5+ Nbd7 12.O-O-O Rd8 13.Rxd7 Rxd7 14.Rd1 Qe6 15.Bxd7+ Nxd7 16.Qb8+!! Nxb8 17.Rd8#.

Your task, in writing (keep these notes — they feed your profile):
1. Find every deflection/decoy/overload in the game and name it with this module's vocabulary (there are at least four, including the immortal 16.Qb8+ decoy).
2. Count Morphy's developed pieces vs. Black's at move 12. Write one sentence connecting that count to why the tactics EXISTED at all.
3. Identify the single Black move you'd call the losing mistake, and propose the improvement.

DAILY DRILL (continues): 15 min of puzzles with the full ritual. This week, filter by theme if your trainer allows: deflection + back rank.

REVIEW CHECKLIST — tick honestly:
□ I can spot fork geometry (K+heavy piece, knight-distance) without calculating
□ I list checks, captures, threats before calculating anything
□ I calculate one forcing reply PAST the material gain, every time
□ I can play the smothered-mate machine from memory, both sidelines
□ I know the Greek gift checklist's four questions cold

SELF-ASSESSMENT: rate yourself 1–5 on each checklist line, note your quiz score, and — the reflection that matters — write two sentences: "The pattern I most doubt I'd see in a real game is ___ because ___." Post your scores and that sentence in the Ask box or our chat; Module 3's tactical reinforcement gets built from what you tell me. Then complete this lesson — Module 2 is unlocked and waiting.
"""

# ══════════════════════════════════════════════════════════════════════════════
# MODULE 2 · CALCULATION & CANDIDATE MOVES
# ══════════════════════════════════════════════════════════════════════════════

M2_CANDIDATES = """
⏱ ~25 min · Objective: replace "I calculate the first move I like" with Kotov's candidate-move discipline — the single highest-leverage habit change at intermediate level.

Alexander Kotov's insight (Think Like a Grandmaster, 1971): weak players calculate one line deeply, get refuted, pick another, calculate, get refuted — and burn their clock re-treading the same branches. Strong players FIRST enumerate every candidate move, THEN allocate calculation between them.

The protocol:
1. Freeze. Before any calculation, survey the whole board and write (mentally or literally) every move worth a thought. Target: 3–5 candidates. Fewer means you're tunnel-visioned; more means you're not evaluating.
2. Order them: forcing first (CCT — checks, captures, threats), then positional.
3. Calculate each ONCE, to a quiet position, and attach a verdict: winning / better / equal / worse. Kotov's famous rule: visit each branch once — if you find yourself recalculating a line, you didn't finish it the first time.
4. Compare verdicts. Play the best. Done.

Where intermediate players break this: they omit step 1 under excitement ("the sac looks crushing!") or time pressure. The fix is mechanical: the freeze is non-negotiable, even for recaptures. ESPECIALLY for recaptures — automatic recaptures are where zwischenzugs live (remember Puzzle 3's 1...Rxf7 resource: it existed precisely because "the king must move" felt automatic).

DRILL BEFORE THE DIVIDER: go back to Module 1's deflection position (lesson 3). WITHOUT calculating any line, list every White candidate move you can defend as "worth a thought." Aim for four. Then check below.

— — — — — — — — — — — — — — — — — — — —

ANSWER (candidates in that position): 1.Re8+ (the deflection — forcing, calculate first), 1.Qxd5?? (loses the queen to ...Rxd5 — but it MUST appear on your list and get its one-visit refutation; candidates aren't only good moves), 1.c4 (attacking the knight honestly — a real positional candidate), 1.Re5 (pressuring d5 a second time). If your list had Re8+ plus at least two others, the discipline is landing. If you listed only Re8+ — you got the right answer via tunnel vision, and one day the tunnel will have a train in it.
"""

M2_CCT = """
⏱ ~25 min · Objective: make forcing-moves-first reflexive, and learn WHY it's not just a search trick.

CCT — every Check, every Capture, every Threat, in that order — isn't merely a way to find tactics. It's a PRUNING principle: forcing moves constrain the opponent's replies, which collapses the branching factor, which is what makes deep calculation humanly possible. A check with one legal reply lets you see six plies deep for the price of three.

Apply it to the diagnostic's smothered-mate position — the full candidate tree at the root was just: checks: Nf7+, Qd8+, Qg8+?? (loses the queen for nothing — yet), Qxf8?? wait, that's a capture; captures: Qxf8+?? no wait — inventory precisely: Qd5 can capture nothing; Ng5 can capture nothing; so checks Nf7+/Qd8+/Qg8+ and zero captures and the threat Qh5 (eyeing h7). Five roots. A full enumeration in 20 seconds — THAT is why the combination is findable by a human.

The deeper skill: at every PLY of the calculation, re-run CCT for the OPPONENT first. Their checks, their captures, their threats — before yours. This is the seed of the blunder-check protocol (lesson 5), and it's what catches desperado defenses like 1...Rxf7.

CALCULATE BEFORE THE DIVIDER: In that smothered position, calculate the "wrong" check first like a disciplined student: 1.Qd8+!?. Where does it lead with best play by both sides? Verdict?

[fen:5r1k/6pp/8/3Q2N1/8/8/8/6K1 w - - 0 1|Calculate 1.Qd8 check]

Hint: Black has exactly two legal replies. One loses instantly; find the other.

— — — — — — — — — — — — — — — — — — — —

ANSWER: 1.Qd8+ Rxd8?? is impossible — check the geometry: the rook on f8 CAN capture d8? f8→d8 along the rank: e8 is empty, so 1...Rxd8 is legal and simply wins the queen (the knight on g5 doesn't cover d8). So 1.Qd8+?? loses on the spot — verdict: refuted in one visit, never to be revisited. And 1...Kg7?? (the other "reply") isn't even needed. Compare: the same queen, one file over (1.Qg8+!!), wins the game. This is the whole point of enumerate-then-calculate: both queen checks look violent; only the tree knows which one is a blunder and which one is immortal. Your verdictable tree: Qd8+ = loses; Nf7+ = mate machine; Qg8+ immediately = ...Rxg8 and nothing (the knight needs f7 access FIRST). Order of operations is the combination.
"""

M2_VISUAL = """
⏱ ~30 min · Objective: strengthen the board in your head — visualization is the ceiling on calculation depth.

You cannot calculate what you cannot see. Every intermediate player's depth limit is visualization decay: by ply 4 the pieces drift, phantom defenders appear, real ones vanish. The good news: this trains faster than any other chess skill.

DRILL 1 — BLINDFOLD LADDER (daily, 5 min, replaces nothing — adds to your tactics drill). Day 1: name the color of squares called out (f5? dark? — check: f-file 6th letter... practice until instant). Day 3: place a knight on b1 mentally, call out its path to f5 in the fewest moves. Day 7: play out a 6-move opening in your head and state the final position's piece placement. Week 2+: solve your daily puzzles by reading the FEN and NOT rendering the board until you've committed to an answer.

DRILL 2 — THE OPPOSITION LABORATORY. This position from your diagnostic is the perfect visualization gym because every line is only kings and one pawn — no excuses:

[fen:8/8/8/4k3/8/4K3/4P3/8 w - - 0 1|The laboratory]

You know the verdict (draw). Today, calculate — eyes off the board after 30 seconds of study — these three lines to their end positions, and state each verdict:
(a) 1.Kd3 Kd5 2.e4+ — what happens after 2...Kxe4?? Is that even legal?
(b) 1.Kf3 Kf5 2.e4+ Kе5 3.Ke3 — who has the opposition now, and what's the verdict?
(c) Same diagram but BLACK to move. White's winning plan in full.

— — — — — — — — — — — — — — — — — — — —

ANSWERS: (a) 2...Kxe4 is ILLEGAL — the white king on d3 defends e4. If your mental board let the king take a defended pawn, you've found your training edge precisely. Correct is 2...Ke5 holding the draw. (b) After 3.Ke3 the kings again face off e3/e5 with BLACK to move — White finally has the opposition… but wait: the pawn is now on e4, and with the pawn beside the king rather than behind, 3...Ke6! 4.Kd4 Kd6 keeps the standoff; the single tempo e2-e4-in-two-goes vs e2-e4-in-one changed nothing here — still a draw. The deeper point you should have FELT while calculating: pawn moves are the only way to lose or gain opposition tempi, and this pawn has none to spare. (c) Black to move: 1...Kd5 2.Kf4! (outflank — the king steps AROUND) 2...Ke6 3.Ke4 (opposition again, Black to move) 3...Kf6 4.Kd5 and the king escorts the pawn in: ...Ke7 5.Ke5 Kd7 6.Kf6 Ke8 7.e4 (now the pawn strolls) — win. If you saw the outflanking maneuver in your head to the end, your visualization is ahead of your rating.
"""

M2_COMPARE = """
⏱ ~30 min · Objective: learn to EVALUATE the positions at the end of your lines — calculation without evaluation is just piece-shuffling.

Kotov's tree tells you where the branches go; you still must judge the leaves. The masterclass example — Richard Réti's 1921 study, the most famous "impossible" save in chess:

[fen:7K/8/k1P5/7p/8/8/8/8 w - - 0 1|Réti, 1921 — White to move and draw]

Inventory says White is dead: the h-pawn runs, the white king is laughably out of the square (h8 vs h5 — count it), and Black's king smothers the c-pawn. Every SINGLE-PURPOSE plan loses: chase the pawn — too slow; push c7 — ...Kb7 stops it cold.

Candidates: 1.Kg7 is the only move that even pretends. Calculate: 1.Kg7! h4 2.Kf6 — and now the miracle geometry: the king threatens BOTH to catch the pawn (Kg5) and to support its own (Ke7/c7). Black must choose:
• 2...Kb6 (stopping c7 support) 3.Ke5!! h3 4.Kd6 h2 5.c7 Kb7 6.Kd7 h1=Q 7.c8=Q+ — both queen; draw.
• 2...h3 3.Ke7! (or Ke6) h2 4.c7 Kb7 5.Kd7 h1=Q 6.c8=Q+ — same fork of fates; draw.

The teaching point isn't the study's beauty (though: bask). It's that at the end of EVERY line you must attach a verdict, and the verdict here is "Q vs Q with a check in hand = draw," not "he queened, I lose." The diagonal king march works because in chess-geometry the diagonal path is exactly as long as the straight one — kings gain purposes, not distance, by walking diagonally. Add this to your evaluation kit: when a line ends, ask "material, king safety, passed pawns — VERDICT," out loud, every time.

CHALLENGE BEFORE THE DIVIDER: in the line 1.Kg7 h4 2.Kf6 Kb6, why does 3.Ke5 hold but the "obvious" 3.Kg5?? lose?

— — — — — — — — — — — — — — — — — — — —

ANSWER: 3.Kg5 catches the pawn (3...h3 4.Kg4? no — 4.Kh4?? wait: 3.Kg5 h3! 4.Kg4 h2 5.Kg3 h1=Q — count again: from g5, after ...h3, 4.Kg4 attacks h3? g4 is adjacent to h3 — 4...h2 5.Kg3 and the king DOES catch it? No: 5...h1=Q promotes first — 5.Kg3 arrives one tempo late; verify square-by-square, that's the drill) — while abandoning the c-pawn forever: ...Kb7xc6 mops up and the h-pawn (or the king escort) wins the K+P ending. 3.Ke5!! is the only move precisely because it KEEPS BOTH THREATS ALIVE one move longer — the dual-purpose principle. One line's verdict: draw. The other's: loss. Same depth, different leaves — evaluation is the difference.
"""

M2_BLUNDERCHECK = """
⏱ ~20 min · Objective: install the pre-move blunder-check — the protocol that converts your new calculation into actual rating points.

Everything this module trained can be undone in one second of excitement. The blunder-check is the seatbelt. Before EVERY move in a real game — every move, including "obvious" ones — run this 10-second scan on the position AFTER your intended move:

1. Their checks — every single one, even the stupid-looking ones. (Module 1's 2...Re1+ lived here.)
2. Their captures — especially captures of the piece you just moved, and anything your move stopped defending.
3. Their threats — mate threats first, then material.
4. The desperado question: does any piece I'm about to win have a suicide move that costs me more? (1...Rxf7 lived here.)

Ten seconds. Not thirty — ten. The blunder-check is a SCAN, not a calculation; anything it flags gets promoted into real calculation. Players rated 1400–1800 lose roughly a third of their games to moves this scan catches. No opening study, no endgame theory, no strategy course pays a third of your losses back. This does.

Attach it to a physical trigger so it survives time trouble: write your candidate move on your scoresheet first (where legal), or sit on your hands, or touch the clock's SIDE — any ritual that inserts the gap between decision and execution.

SELF-TEST BEFORE THE DIVIDER: recall the three positions in this program where a "clean win" had a hidden counter-resource, and name each resource from memory.

— — — — — — — — — — — — — — — — — — — —

ANSWER: (1) The deflection combo — after 2.Qxd5, Black's 2...Re1+ needed 3.Kf1 ready. (2) The smothered mate — 1...Rxf7 desperado, answered by 2.Qd8+ and mate anyway (but you had to KNOW that before sacrificing). (3) The Réti-position temptation 3.Kg5 — not an opponent's resource but your own tunnel: the pawn-chase that loses the OTHER pawn. Three different flavors — counter-attack, desperado, dual-purpose failure — one protocol catches all three. If you recalled all three cold: the module did its work.
"""

M2_QUIZ = """
⏱ ~30 min · Module 2 quiz. Process is graded as much as answers — where asked for candidates or protocols, partial lists score partial points.

Q1 (3 pts). You're considering a piece sacrifice. Write Kotov's four-step protocol in order, one line each.

Q2 (2 pts). Why do forcing moves get calculated first? Give BOTH reasons (the practical one and the mathematical one).

Q3 (3 pts). White to move. Enumerate every check and capture for White (they are few), then find the draw.

[fen:7K/8/k1P5/7p/8/8/8/8 w - - 0 1|Q3 — White to draw]

Q4 (2 pts). Your opponent just captured your bishop; recapturing is "automatic." What does this module say you must do first, and what move-type are you specifically hunting for?

Q5 (2 pts). State the four questions of the pre-move blunder-check, in order.

— — — — — — — — — — — — — — — — — — — —

A1. (1) Freeze and enumerate 3–5 candidates before calculating; (2) order them forcing-first; (3) calculate each exactly once, to a quiet position, attach a verdict; (4) compare verdicts, play the best.
A2. Practical: forcing moves are most likely to win outright at club level. Mathematical: they constrain replies, collapsing the branching factor — depth becomes affordable.
A3. Checks: none. Captures: none. (That's the enumeration — trick question, and if you invented some, re-run your drill.) The draw: 1.Kg7! h4 2.Kf6 and the dual-purpose diagonal march — either 2...Kb6 3.Ke5! or 2...h3 3.Ke7! — both queen or both die; draw. Full 3 points only with a concrete line to the end.
A4. Freeze and run the candidate enumeration anyway — automatic recaptures are where zwischenzugs (in-between forcing moves, usually checks) hide. You're hunting your opponent's AND your own in-between checks before touching the piece.
A5. Their checks; their captures; their threats (mate first); the desperado question.

/12. 10+ → tell me and Module 3 gets built with harder verification drills. 6–9 → redo lessons 2 and 5. <6 → the Ask box, your three weakest answers, and I'll coach them one by one.
"""

M2_ASSIGN = """
⏱ ~60 min + one week · Module 2 assignment, weekly plan, and self-assessment.

PRACTICAL ASSIGNMENT — your own game, under the new protocol. Play ONE serious game this week (15+10 minimum, slower preferred). During it: freeze-and-enumerate on every non-trivial move, blunder-check before every single move, and mark on your scoresheet (a dot suffices) each move where you actually ran the full ritual. Afterward, annotate the game yourself BEFORE any engine: identify three critical moments, your candidate list at each, and where your calculation ended vs where it should have. THEN engine-check, and write one paragraph: "What the engine saw that my process missed, and which protocol step would have caught it."

Paste the game and your paragraph into the Ask box (or our chat). This is the first entry in your long-term profile — every future game analysis compares against it.

WEEKLY STUDY PLAN (template from here on):
• Mon/Wed/Fri — 15 min tactics ritual (theme: mixed)
• Tue/Thu — 10 min blindfold ladder + 10 min one endgame position calculated to verdict
• Weekend — the serious game + self-annotation
• Always — blunder-check in EVERY game including blitz (blitz WITH the scan is training; blitz without it is untraining)

REVIEW CHECKLIST:
□ I enumerate candidates before calculating, even on recaptures
□ I calculate each branch once, to quiet, with a verdict attached
□ My opponent's checks/captures/threats come before mine at every ply
□ I ran the blunder-check on 90%+ of moves in my assignment game
□ I can replay Réti's study from memory and explain the dual-purpose principle

SELF-ASSESSMENT: checklist ratings 1–5, quiz score, and the reflection: "Under time pressure, the step I skip first is ___; my countermeasure is ___." Report it all in the Ask box. Modules 3 (Weak Squares & Outposts) and 6 (Endgame Fundamentals) both unlock from here — your diagnostic scores decide which I build for you first: tell me your numbers and your available hours per week, and your personalized path continues.
"""

# ══════════════════════════════════════════════════════════════════════════════

DIAGNOSTIC = CourseCreate(
    title="Chess Diagnostic: Find Your Level",
    description=(
        "Start here. Five test sections — tactics, calculation, strategy, "
        "endgames, openings — with real positions on real boards. Self-score, "
        "get your training profile, and unlock the 12-module path from "
        "intermediate to advanced club player. ~90 minutes."
    ),
    modules=[
        ModuleCreate(title="How This Program Works", order_index=0, assets=[
            text("Read me first: the method and the rules", D_WELCOME, 0),
        ]),
        ModuleCreate(title="Section 1 · Tactics", order_index=1, assets=[
            text("Three positions · score /6", D_TACTICS, 0),
        ]),
        ModuleCreate(title="Section 2 · Calculation", order_index=2, assets=[
            text("Two exercises · score /4", D_CALCULATION, 0),
        ]),
        ModuleCreate(title="Section 3 · Strategy", order_index=3, assets=[
            text("Three judgment questions · score /6", D_STRATEGY, 0),
        ]),
        ModuleCreate(title="Section 4 · Endgames", order_index=4, assets=[
            text("Lucena and the defender's rook · score /4", D_ENDGAME, 0),
        ]),
        ModuleCreate(title="Section 5 · Openings", order_index=5, assets=[
            text("Principles under pressure · score /6", D_OPENINGS, 0),
        ]),
        ModuleCreate(title="Your Profile & The Road Ahead", order_index=6, assets=[
            text("Score yourself: your training profile", D_RESULTS, 0),
            text("The 12-module map", D_ROADMAP, 1),
        ]),
    ],
)

MODULE1 = CourseCreate(
    title="Chess M1 · Advanced Tactical Patterns",
    description=(
        "Forks you engineer, deflection and overload, the back-rank and "
        "smothered-mate machines, the Greek gift with its checklist — plus the "
        "training ritual that makes patterns stick. Quiz, puzzle set, Opera "
        "Game assignment. ~4–5 hours with drills. Prereq: the Diagnostic."
    ),
    modules=[
        ModuleCreate(title="The Method", order_index=0, assets=[
            text("How to train tactics (the ritual)", M1_METHOD, 0),
        ]),
        ModuleCreate(title="Patterns I · Geometry & Deflection", order_index=1, assets=[
            text("Forks you engineer", M1_FORKS, 0),
            text("Deflection & overload — the workhorses", M1_DEFLECTION, 1),
        ]),
        ModuleCreate(title="Patterns II · The Mating Machines", order_index=2, assets=[
            text("Back rank & the smothered mate", M1_MATES, 0),
            text("The Greek gift — pattern + checklist", M1_GREEK, 1),
        ]),
        ModuleCreate(title="Prove It", order_index=3, assets=[
            text("Module quiz + puzzle set (/12)", M1_QUIZ, 0),
            text("Assignment: the Opera Game · checklist · self-assessment", M1_ASSIGN, 1),
        ]),
    ],
)

MODULE2 = CourseCreate(
    title="Chess M2 · Calculation & Candidate Moves",
    description=(
        "Kotov's candidate discipline, CCT pruning, visualization training, "
        "evaluation at the end of lines (featuring Réti's study), and the "
        "pre-move blunder-check that pays back a third of your losses. "
        "~5 hours with drills. Prereq: Module 1."
    ),
    modules=[
        ModuleCreate(title="The Discipline", order_index=0, assets=[
            text("Candidate moves: Kotov's protocol", M2_CANDIDATES, 0),
            text("CCT: why forcing moves come first", M2_CCT, 1),
        ]),
        ModuleCreate(title="The Muscles", order_index=1, assets=[
            text("Visualization: the blindfold ladder", M2_VISUAL, 0),
            text("Evaluating the leaves: Réti's study", M2_COMPARE, 1),
        ]),
        ModuleCreate(title="The Seatbelt", order_index=2, assets=[
            text("The pre-move blunder-check", M2_BLUNDERCHECK, 0),
        ]),
        ModuleCreate(title="Prove It", order_index=3, assets=[
            text("Module quiz (/12)", M2_QUIZ, 0),
            text("Assignment: your game, annotated · weekly plan", M2_ASSIGN, 1),
        ]),
    ],
)


async def main() -> None:
    async with SessionLocal() as session:
        coach = await user_service.get_user_by_email(session, COACH.email)
        if coach is None:
            coach = await user_service.create_user(session, COACH)
            print(f"created coach {coach.email}")
        else:
            print(f"reusing coach {coach.email}")

        existing = (
            await session.execute(select(Course.id).where(Course.instructor_id == coach.id))
        ).scalars().all()
        if existing:
            await session.execute(delete(Course).where(Course.instructor_id == coach.id))
            await session.commit()
            print(f"removed {len(existing)} existing chess course(s)")

        diagnostic = await course_service.create_course(session, DIAGNOSTIC, instructor_id=coach.id)
        diagnostic = await course_service.publish_course(session, diagnostic.id, coach)

        m1_spec = MODULE1.model_copy(update={"prerequisite_ids": [diagnostic.id]})
        m1 = await course_service.create_course(session, m1_spec, instructor_id=coach.id)
        m1 = await course_service.publish_course(session, m1.id, coach)

        m2_spec = MODULE2.model_copy(update={"prerequisite_ids": [m1.id]})
        m2 = await course_service.create_course(session, m2_spec, instructor_id=coach.id)
        m2 = await course_service.publish_course(session, m2.id, coach)

        for course in (diagnostic, m1, m2):
            lessons = sum(len(m.assets) for m in course.modules)
            chars = sum(len(a.content or "") for m in course.modules for a in m.assets)
            print(f"published '{course.title}': {len(course.modules)} modules, {lessons} lessons, {chars:,} chars")

    print("\nChess program seeded. Path: Diagnostic → M1 → M2 (M3+ built from your results).")


if __name__ == "__main__":
    asyncio.run(main())
