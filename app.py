import json
import random
import sqlite3
import time
import uuid
from html import escape as html_escape
from pathlib import Path
import streamlit as st
from shadowintelx_ai import AIConfigurationError, AIRequestError, configured_model, generate_feedback, is_configured
from shadowintelx_engine import NAVIGATION_PAGES, SKILLS, build_skill_profile, build_training_plan, coach_recommendation, mission_snapshot, performance_report, rank_for_xp, recommend_difficulty, skill_radar_svg
from shadowintelx_report import build_pdf_report
from shadowintelx_store import DB_PATH, award_badge, claim_mission, get_or_create_user, get_user_xp, init_db, list_attempts, list_badges, list_high_scores, list_mission_claims, record_attempt, upsert_high_score

st.set_page_config(page_title="ShadowIntelX IQ | Interview & Reasoning Studio", page_icon="🔴", layout="wide")

SCORE_FILE = Path(__file__).with_name("high_scores.json")
try:
    init_db(DB_PATH, legacy_scores_path=SCORE_FILE)
except (OSError, ValueError, sqlite3.Error) as exc:
    st.error(f"ShadowIntelX could not initialize local storage: {exc}")
    st.stop()

# Ten question choices per role and level, sampled into each practice session.
QUESTION_BANK = {
"Python Developer": {
"Beginner": [
("What makes Python useful for beginners and rapid development?", ["readable", "interpreted", "libraries"]),
("How are lists different from tuples?", ["mutable", "immutable", "change"]),
("What is a dictionary, and when would you use one?", ["key", "value", "mapping"]),
("What is the purpose of a function?", ["reuse", "parameters", "return"]),
("How would you handle an error when opening a file?", ["try", "except", "exception"]),
("What is the difference between == and is?", ["equality", "identity", "object"]),
("What is a Python module?", ["file", "functions", "import"]),
("How would you remove duplicate values from a list?", ["set", "unique", "order"]),
("What is a list comprehension?", ["expression", "loop", "list"]),
("Why split code into small functions?", ["readable", "reuse", "test"])],
"Intermediate": [
("Explain decorators and give a practical use case.", ["function", "wrapper", "modify"]),
("How do generators help with large datasets?", ["yield", "iterator", "memory"]),
("Difference between shallow and deep copy?", ["nested", "reference", "copy"]),
("How does Python's exception hierarchy work?", ["exception", "base", "catch"]),
("What are *args and **kwargs used for?", ["positional", "keyword", "arguments"]),
("What is a context manager, and why use with?", ["resource", "close", "with"]),
("What does the Global Interpreter Lock affect?", ["thread", "execution", "parallel"]),
("How would you test a function calling an external API?", ["mock", "test", "response"]),
("Difference between an iterable and an iterator?", ["iter", "next", "value"]),
("How would you profile a slow Python function?", ["profile", "bottleneck", "measure"])],
"Advanced": [
("Explain method resolution order and super().", ["mro", "inheritance", "order"]),
("When use asyncio instead of threads or processes?", ["io", "concurrent", "await"]),
("How do descriptors control attribute access?", ["descriptor", "get", "attribute"]),
("How design a backwards-compatible Python package?", ["version", "api", "tests"]),
("Explain reference counting and cyclic garbage collection.", ["reference", "cycle", "collect"]),
("How investigate memory growth in a service?", ["memory", "profile", "leak"]),
("What trade-offs arise in async decorators?", ["await", "wrapper", "metadata"]),
("How make a data pipeline restartable and idempotent?", ["idempotent", "checkpoint", "retry"]),
("When is multiprocessing a poor fit?", ["overhead", "serialization", "io"]),
("How structure observability for a production service?", ["logging", "metrics", "trace"])]},
"Data Scientist": {
"Beginner": [
("Difference between a population and a sample?", ["population", "sample", "subset"]),
("How do mean, median, and mode differ?", ["average", "middle", "frequency"]),
("Why is data cleaning important?", ["missing", "errors", "quality"]),
("What does correlation tell you—and not prove?", ["relationship", "association", "causation"]),
("What is a feature in a dataset?", ["input", "variable", "model"]),
("How explain a visualization to a non-technical audience?", ["audience", "insight", "chart"]),
("Categorical vs numerical variable?", ["category", "number", "value"]),
("Why inspect data before modeling?", ["distribution", "outlier", "quality"]),
("What is a train-test split?", ["training", "test", "unseen"]),
("How can an outlier affect an average?", ["extreme", "mean", "median"])],
"Intermediate": [
("Compare supervised and unsupervised learning.", ["labeled", "unlabeled", "target"]),
("What is data leakage and how prevent it?", ["leakage", "test", "training"]),
("Explain precision and recall with an example.", ["false", "positive", "recall"]),
("How handle class imbalance?", ["sampling", "weights", "metric"]),
("What is cross-validation?", ["fold", "validation", "training"]),
("How choose between simple and complex models?", ["baseline", "interpret", "generalize"]),
("What does a p-value represent?", ["null", "probability", "evidence"]),
("How detect multicollinearity?", ["correlation", "vif", "feature"]),
("What are linear regression assumptions?", ["linearity", "residual", "independent"]),
("How communicate uncertainty in a forecast?", ["interval", "uncertainty", "assumption"])],
"Advanced": [
("Explain and diagnose the bias-variance trade-off.", ["bias", "variance", "generalize"]),
("How design an experiment for a product change?", ["random", "control", "metric"]),
("What makes a causal claim stronger than correlation?", ["confound", "random", "causal"]),
("How monitor model drift?", ["drift", "monitor", "distribution"]),
("How evaluate a model for a high-impact decision?", ["metric", "subgroup", "validation"]),
("Calibration vs discrimination?", ["probability", "ranking", "calibration"]),
("How can missing-not-at-random data bias analysis?", ["missing", "bias", "mechanism"]),
("How select a threshold with asymmetric costs?", ["cost", "threshold", "precision"]),
("What are risks of repeated hypothesis testing?", ["multiple", "false", "significance"]),
("How make analysis reproducible?", ["version", "code", "data"])]},
"AI/ML Engineer": {
"Beginner": [
("Difference between AI, ML, and deep learning?", ["artificial", "learn", "neural"]),
("What is a training dataset?", ["data", "train", "model"]),
("Compare classification and regression.", ["class", "continuous", "prediction"]),
("What is a neural network made of?", ["neurons", "layers", "weights"]),
("What does a loss function measure?", ["error", "prediction", "actual"]),
("What is overfitting and how notice it?", ["training", "unseen", "generalize"]),
("Why scale features?", ["scale", "range", "distance"]),
("What is a model prediction?", ["input", "model", "output"]),
("Why keep a separate test dataset?", ["unseen", "evaluate", "generalize"]),
("What is a baseline model?", ["simple", "compare", "performance"])],
"Intermediate": [
("Explain gradient descent intuitively.", ["gradient", "loss", "parameters"]),
("What is backpropagation?", ["gradient", "weights", "network"]),
("How do regularization and dropout reduce overfitting?", ["regularization", "dropout", "generalize"]),
("Compare bagging and boosting.", ["ensemble", "parallel", "sequential"]),
("Choose metrics for an imbalanced classifier.", ["precision", "recall", "f1"]),
("What causes vanishing gradients?", ["gradient", "layers", "small"]),
("How serve a low-latency model?", ["latency", "batch", "cache"]),
("Why is feature engineering useful?", ["domain", "feature", "signal"]),
("How do embeddings represent language or items?", ["vector", "semantic", "similarity"]),
("What should be versioned in an ML pipeline?", ["data", "model", "code"])],
"Advanced": [
("Design a reliable online inference architecture.", ["latency", "scaling", "monitor"]),
("RAG vs fine-tuning: what are the trade-offs?", ["retrieval", "knowledge", "weights"]),
("Evaluate an LLM beyond one aggregate score.", ["human", "slice", "failure"]),
("What is distribution shift and how respond?", ["distribution", "drift", "monitor"]),
("Make training reproducible across hardware.", ["seed", "version", "deterministic"]),
("What causes leakage in an ML pipeline?", ["leakage", "split", "feature"]),
("Reduce inference cost while preserving quality.", ["quantization", "distillation", "batch"]),
("How assess fairness across subgroups?", ["subgroup", "metric", "bias"]),
("Handle rollback after a bad model release.", ["version", "rollback", "monitor"]),
("Reliability risks of an agent using tools?", ["permission", "validation", "failure"])]},
"Web Developer": {
"Beginner": [
("What roles do HTML, CSS, and JavaScript play?", ["structure", "style", "interactive"]),
("What is semantic HTML and why use it?", ["meaning", "accessibility", "elements"]),
("Difference between a class and ID in CSS?", ["selector", "unique", "reuse"]),
("How does a browser load a webpage?", ["request", "response", "render"]),
("What does responsive design mean?", ["screen", "devices", "layout"]),
("Link vs button: when use each?", ["navigate", "action", "semantic"]),
("What is the DOM?", ["document", "tree", "elements"]),
("What is a form used for?", ["input", "submit", "data"]),
("How make a page more accessible?", ["keyboard", "label", "screen"]),
("Difference between frontend and backend?", ["user", "server", "interface"])],
"Intermediate": [
("What is a REST API?", ["request", "response", "http"]),
("Compare cookies, local storage, and session storage.", ["storage", "server", "session"]),
("How do promises and async/await help?", ["promise", "async", "await"]),
("What is CORS and why does it exist?", ["origin", "browser", "policy"]),
("How improve page load performance?", ["bundle", "image", "cache"]),
("Common causes of cross-site scripting?", ["input", "escape", "script"]),
("Manage state in a growing frontend app?", ["component", "state", "data"]),
("What is the purpose of a CDN?", ["cache", "edge", "latency"]),
("How test a responsive interface?", ["viewport", "device", "test"]),
("Make a page accessible to keyboard users.", ["focus", "keyboard", "semantic"])],
"Advanced": [
("Design a secure authentication flow for a web app.", ["session", "token", "http"]),
("Prevent race conditions in client-side fetching.", ["abort", "request", "stale"]),
("Benefits and costs of server-side rendering?", ["render", "seo", "hydration"]),
("Plan a gradual migration of a large frontend.", ["incremental", "compatibility", "measure"]),
("How do CSP and output encoding reduce risk?", ["policy", "script", "escape"]),
("Diagnose a production layout shift.", ["layout", "measure", "font"]),
("Caching strategy trade-offs?", ["freshness", "invalidate", "cache"]),
("Design a resilient API client.", ["retry", "timeout", "error"]),
("Improve performance without hurting accessibility.", ["measure", "keyboard", "semantic"]),
("Protect user data in a multi-tenant app.", ["authorization", "tenant", "isolation"])]},
"Software Engineer": {
"Beginner": [
("What is an algorithm?", ["steps", "solve", "problem"]),
("What is a data structure?", ["organize", "data", "store"]),
("How do you approach debugging?", ["reproduce", "find", "fix"]),
("What is version control for?", ["changes", "history", "collaborate"]),
("Compiler vs interpreter?", ["translate", "execute", "code"]),
("What is a database table?", ["rows", "columns", "records"]),
("What is a software test?", ["expected", "actual", "behavior"]),
("Why is readable code important?", ["maintain", "understand", "team"]),
("What is an API?", ["interface", "request", "service"]),
("How break down a large problem?", ["smaller", "steps", "test"])],
"Intermediate": [
("Explain OOP and its trade-offs.", ["class", "object", "inheritance"]),
("Explain Big O; compare O(n) and O(log n).", ["input", "growth", "complexity"]),
("How do indexes speed up reads, and what do they cost?", ["search", "query", "write"]),
("Diagnose a slow database query.", ["explain", "index", "measure"]),
("Difference between a process and a thread?", ["memory", "execution", "resources"]),
("Resolve a disagreement in code review.", ["evidence", "tradeoff", "discussion"]),
("What is an integration test?", ["components", "boundary", "test"]),
("Why are database transactions important?", ["atomic", "consistency", "rollback"]),
("Design a cache invalidation strategy.", ["stale", "invalidate", "ttl"]),
("Make a service resilient to dependency failure.", ["timeout", "retry", "fallback"])],
"Advanced": [
("Explain SOLID and when it can be over-applied.", ["responsibility", "dependency", "design"]),
("Design an idempotent API for payment retries.", ["idempotent", "key", "retry"]),
("Reason about consistency in distributed systems.", ["consistency", "replica", "tradeoff"]),
("What is backpressure and how apply it?", ["queue", "consumer", "flow"]),
("Evolve a public API without breaking clients.", ["version", "compatibility", "deprecate"]),
("Investigate a production incident with limited info.", ["impact", "evidence", "rollback"]),
("What trade-offs do microservices introduce?", ["deployment", "network", "operations"]),
("Design a distributed rate limiter.", ["token", "bucket", "distributed"]),
("Balance delivery speed and maintainability.", ["risk", "feedback", "refactor"]),
("Make a critical system observable.", ["logs", "metrics", "trace"])]},
"Product Manager": {
"Beginner": [
("Explain a product manager's role.", ["customer", "team", "outcome"]),
("How decide which user problem to solve first?", ["impact", "evidence", "priority"]),
("What is a product roadmap for?", ["direction", "outcome", "sequence"]),
("How gather user feedback?", ["interview", "survey", "observe"]),
("What makes a useful product goal?", ["measurable", "outcome", "time"]),
("Communicate a feature idea to engineers.", ["problem", "context", "acceptance"]),
("What is a user persona and its limits?", ["research", "pattern", "assumption"]),
("Measure whether a feature succeeds.", ["metric", "baseline", "goal"]),
("Handle a request outside product strategy.", ["listen", "evidence", "explain"]),
("Why speak directly with customers?", ["context", "need", "feedback"])],
"Intermediate": [
("Prioritize features with competing stakeholder requests.", ["impact", "effort", "evidence"]),
("Define a north-star metric.", ["value", "behavior", "guardrail"]),
("How would you run a product experiment?", ["hypothesis", "control", "metric"]),
("Distinguish a symptom from a root user problem.", ["interview", "cause", "evidence"]),
("Launch a feature with high operational risk.", ["rollout", "monitor", "rollback"]),
("Keep a roadmap useful as priorities change.", ["outcome", "confidence", "update"]),
("Resolve design and engineering disagreement.", ["user", "tradeoff", "test"]),
("Metrics that reveal misleading engagement growth?", ["retention", "quality", "guardrail"]),
("Improve onboarding for a complex product.", ["friction", "activation", "test"]),
("Communicate a delay to stakeholders.", ["reason", "impact", "plan"])],
"Advanced": [
("Evaluate entering a new market.", ["customer", "market", "economics"]),
("Set strategy when evidence is incomplete.", ["assumption", "option", "learn"]),
("Detect a two-sided marketplace cold start.", ["liquidity", "supply", "demand"]),
("Manage cannibalization between products.", ["segment", "incremental", "tradeoff"]),
("Align teams around a multi-quarter outcome.", ["dependency", "owner", "milestone"]),
("Decide whether to sunset a widely used feature.", ["usage", "cost", "migration"]),
("How can incentives distort product metrics?", ["behavior", "gaming", "guardrail"]),
("Build product advantage from customer insight.", ["insight", "capability", "feedback"]),
("Balance growth with user trust and privacy.", ["consent", "value", "risk"]),
("Recover trust after a product decision harms users.", ["acknowledge", "remedy", "listen"])]}}

HR_INTERVIEW_BANK = [
    ("Tell me about yourself and the experiences that shaped your interests.", ["experience", "interest", "example"]),
    ("Why are you interested in this opportunity?", ["role", "company", "contribute"]),
    ("Describe a time you handled a difficult situation.", ["situation", "action", "result"]),
    ("Tell me about a time you received feedback and acted on it.", ["feedback", "change", "result"]),
    ("How do you handle disagreement in a team?", ["listen", "perspective", "resolve"]),
    ("What is a strength you would bring to this role?", ["strength", "example", "impact"]),
    ("What is one skill you are actively improving?", ["skill", "practice", "progress"]),
    ("Describe how you prioritize competing deadlines.", ["priority", "deadline", "communicate"]),
    ("Tell me about a mistake and what you learned from it.", ["mistake", "responsibility", "learn"]),
    ("What kind of team helps you do your best work?", ["team", "communication", "environment"]),
    ("What would you like to learn in your first six months?", ["learn", "goal", "contribute"]),
    ("What questions would you ask before accepting an offer?", ["expectation", "team", "growth"]),
]
TECHNICAL_ROLES = [role for role in QUESTION_BANK if role != "Product Manager"]

LOGIC = [
{"q":"What number comes next? 2, 6, 12, 20, 30, ?","c":["36","40","42","44"],"a":2,"e":"The gaps grow by 2: +4, +6, +8, +10, then +12. Answer: 42."},
{"q":"All Zorbs are Mips. Some Mips are Lums. What must be true?","c":["All Zorbs are Lums","Some Zorbs are Lums","All Zorbs are Mips","No Mips are Zorbs"],"a":2,"e":"This is stated directly. We do not know whether any Zorbs are among the Mips that are Lums."},
{"q":"At 3:15, what is the smaller angle between clock hands?","c":["0°","7.5°","15°","22.5°"],"a":1,"e":"The minute hand is at 90°. The hour hand has moved to 97.5°, so the gap is 7.5°."},
{"q":"5 machines make 5 widgets in 5 minutes. How long for 100 machines to make 100 widgets?","c":["5 minutes","20 minutes","100 minutes","500 minutes"],"a":0,"e":"Each machine makes one widget in five minutes. Working together, 100 machines make 100 widgets in five minutes."},
{"q":"Complete: 1, 1, 2, 3, 5, 8, ?","c":["11","12","13","15"],"a":2,"e":"Each number sums the previous two: 5 + 8 = 13."},
{"q":"A bat and ball cost $1.10 total. The bat costs $1 more. What does the ball cost?","c":["5¢","10¢","15¢","20¢"],"a":0,"e":"A 5¢ ball and $1.05 bat total $1.10."},
{"q":"Which is the odd one out: 8, 27, 64, 100, 125?","c":["27","64","100","125"],"a":2,"e":"8, 27, 64, and 125 are cubes. 100 is not."},
{"q":"A farmer has 17 sheep. All but 9 run away. How many remain?","c":["8","9","17","26"],"a":1,"e":"'All but 9' means 9 sheep did not run away."},
{"q":"Yesterday was two days before Thursday. What day is today?","c":["Tuesday","Wednesday","Thursday","Friday"],"a":1,"e":"Two days before Thursday is Tuesday. If yesterday was Tuesday, today is Wednesday."},
{"q":"A lily pad doubles daily and covers a pond on day 48. When was it half covered?","c":["Day 24","Day 46","Day 47","Day 48"],"a":2,"e":"One doubling earlier, on day 47, it was half covered."},
{"q":"You pass the runner in second place. What place are you in now?","c":["First","Second","Third","Cannot tell"],"a":1,"e":"You take the place of the runner you passed: second."},
{"q":"Red and blue socks are mixed in a dark drawer. Minimum picks to guarantee a matching pair?","c":["2","3","4","5"],"a":1,"e":"With two colors, the third sock must match one of the first two."},
{"q":"3 cats catch 3 mice in 3 minutes. Cats needed for 100 mice in 100 minutes?","c":["1","3","33","100"],"a":1,"e":"Each cat catches one mouse per 3 minutes. Three cats catch 100 mice in 100 minutes."},
{"q":"Complete: AZ, BY, CX, DW, ?","c":["EV","FU","EX","EW"],"a":0,"e":"First letters move forward A–E, second letters backward Z–V. Answer EV."},
{"q":"Pages numbered 1 to 100: how many times does digit 9 appear?","c":["10","19","20","21"],"a":2,"e":"Ten appearances in the ones place and ten in the tens place: 20 total."}]

# Short reasoning challenges are grouped by difficulty; each round is sampled from one level.
LOGIC_LEVELS = {
"Beginner": [
{"q":"What comes next? 5, 10, 15, 20, ?","c":["22","24","25","30"],"a":2,"e":"Add 5 each time, so the next number is 25."},
{"q":"Which word does not belong? Apple, banana, carrot, grape","c":["Apple","Banana","Carrot","Grape"],"a":2,"e":"Carrot is a vegetable; the others are fruits."},
{"q":"Mia is taller than Leo. Leo is taller than Ava. Who is shortest?","c":["Mia","Leo","Ava","Cannot tell"],"a":2,"e":"Mia > Leo > Ava, so Ava is shortest."},
{"q":"A box has 4 pairs of gloves. How many individual gloves is that?","c":["4","6","8","12"],"a":2,"e":"Each pair has two gloves: 4 × 2 = 8."},
{"q":"Complete the pattern: A, C, E, G, ?","c":["H","I","J","K"],"a":1,"e":"Skip one letter each time: A, C, E, G, I."},
{"q":"You face north, turn right, then turn around. Which way now?","c":["North","East","South","West"],"a":3,"e":"North → right to East → turn around to West."},
{"q":"Some birds can swim. All ducks are birds. Which must be true?","c":["All birds are ducks","Ducks are birds","All ducks swim","No birds swim"],"a":1,"e":"The second sentence directly tells us all ducks are birds."},
{"q":"How many corners do 3 separate squares have altogether?","c":["8","10","12","16"],"a":2,"e":"Each square has 4 corners, so 3 × 4 = 12."},
{"q":"What comes next? 1, 3, 6, 10, ?","c":["12","14","15","16"],"a":2,"e":"Add 2, then 3, then 4; next add 5 to get 15."},
{"q":"A bus leaves at 2:00 and arrives 45 minutes later. What time?","c":["2:35","2:45","3:00","3:45"],"a":1,"e":"Forty-five minutes after 2:00 is 2:45."}],
"Intermediate": [
{"q":"What comes next? 4, 9, 19, 39, ?","c":["59","69","79","89"],"a":2,"e":"Each term doubles and adds 1: 39 × 2 + 1 = 79."},
{"q":"All Nors are Vels. No Vels are Taks. Can a Nor be a Tak?","c":["Yes, always","Yes, sometimes","No","Cannot tell"],"a":2,"e":"Every Nor is a Vel, and no Vel is a Tak. Therefore no Nor can be a Tak."},
{"q":"A code shifts each letter forward by one: CAT becomes DBU. How is DOG coded?","c":["EPH","EOG","DPH","FPH"],"a":0,"e":"Move each letter forward: D→E, O→P, G→H."},
{"q":"A number is doubled, then 6 is added, giving 24. What was it?","c":["6","8","9","12"],"a":2,"e":"Work backward: (24 − 6) ÷ 2 = 9."},
{"q":"Four people each shake hands with every other person once. How many handshakes?","c":["4","5","6","8"],"a":2,"e":"There are 4×3÷2 unique pairs, which is 6 handshakes."},
{"q":"Find the missing number: 2, 5, 11, 23, ?","c":["35","45","46","47"],"a":3,"e":"Multiply by 2 then add 1: 23 × 2 + 1 = 47."},
{"q":"If yesterday was Monday, what day is three days after tomorrow?","c":["Thursday","Friday","Saturday","Sunday"],"a":2,"e":"Today is Tuesday; tomorrow Wednesday; three days after Wednesday is Saturday."},
{"q":"A clock loses 5 minutes every hour. How much does it lose in 6 hours?","c":["20 min","25 min","30 min","35 min"],"a":2,"e":"5 minutes × 6 hours = 30 minutes."},
{"q":"A recipe for 4 uses 300 g of flour. How much for 10 people?","c":["600 g","650 g","700 g","750 g"],"a":3,"e":"Each serving needs 75 g; 75 × 10 = 750 g."},
{"q":"Which is the next pair? AZ, BY, CX, ?","c":["DW","EV","DX","EW"],"a":0,"e":"First letter advances and second retreats: D and W."}],
"Advanced": [
{"q":"What comes next? 3, 4, 7, 12, 19, ?","c":["26","27","28","29"],"a":2,"e":"The differences are +1, +3, +5, +7; next add 9 to get 28."},
{"q":"Three switches control one bulb in another room. You may enter that room once. How identify the switch?","c":["Flip one and enter","Use bulb heat and light","Impossible","Flip all three"],"a":1,"e":"Turn one switch on for a while, turn it off, turn another on, then enter. Lit = second; warm = first; cold and off = third."},
{"q":"A and B together finish a job in 6 days. A alone takes 10 days. How long would B alone take?","c":["12 days","15 days","18 days","20 days"],"a":1,"e":"B's rate is 1/6 − 1/10 = 1/15 of the job per day, so 15 days."},
{"q":"A sequence follows n² + 1. What is its 8th term?","c":["57","63","65","81"],"a":2,"e":"8² + 1 = 65."},
{"q":"A fair coin is tossed twice. Given at least one head, what is the chance both are heads?","c":["1/2","1/3","1/4","2/3"],"a":1,"e":"Possible outcomes are HH, HT, TH. One of these three has two heads."},
{"q":"A 3-digit code uses distinct digits. The first is twice the last, and the middle is 1 more than the last. The digits total 13. What is the code?","c":["643","634","463","436"],"a":0,"e":"The last digit is 3, the middle 4, and the first 6: 6 + 4 + 3 = 13."},
{"q":"A 2-digit number has digits that sum to 9. Reversing its digits makes a number 27 larger. What is the original number?","c":["36","45","54","63"],"a":0,"e":"36 reversed is 63, which is 27 larger. Its digits sum to 9."},
{"q":"A square's perimeter is 48 cm. What is its area?","c":["96 cm²","120 cm²","144 cm²","196 cm²"],"a":2,"e":"Each side is 48÷4=12 cm. Area = 12² = 144 cm²."},
{"q":"Five machines make five parts in five minutes. How long do 20 machines take to make 20 parts?","c":["5 minutes","20 minutes","25 minutes","100 minutes"],"a":0,"e":"Each machine makes one part in five minutes, so 20 machines make 20 parts in five minutes."},
{"q":"A tank is 1/3 full. Adding 20 L makes it 2/3 full. What is its capacity?","c":["40 L","50 L","60 L","80 L"],"a":2,"e":"The added 20 L is 1/3 of capacity; total capacity is 60 L."}]}

# Mix in the original puzzles too, so each level has a larger rotating pool.
LOGIC_LEVELS["Beginner"].extend([LOGIC[i] for i in (0, 3, 4, 7, 8)])
LOGIC_LEVELS["Intermediate"].extend([LOGIC[i] for i in (1, 2, 9, 10, 13)])
LOGIC_LEVELS["Advanced"].extend([LOGIC[i] for i in (5, 6, 12, 14)])

MEMORY_GAMES={
"Sequence Memory":{"description":"Watch the digits, then enter them in order.","base":{"Beginner":4,"Intermediate":6,"Advanced":8},"seconds":{"Beginner":5,"Intermediate":4,"Advanced":3}},
"Card Match":{"description":"Flip two cards at a time and remember each symbol's position.","pairs":{"Beginner":3,"Intermediate":6,"Advanced":8}},
"Number Recall":{"description":"Memorize the number before it disappears, then type it back.","base":{"Beginner":4,"Intermediate":6,"Advanced":8},"seconds":{"Beginner":5,"Intermediate":4,"Advanced":3}},
"Object Memory":{"description":"Remember the objects, then select them from a mixed set.","base":{"Beginner":3,"Intermediate":5,"Advanced":7},"seconds":{"Beginner":6,"Intermediate":5,"Advanced":4}},
}
MEMORY_OBJECTS=[("Apple",chr(0x1F34E)),("Balloon",chr(0x1F388)),("Cat",chr(0x1F431)),("Diamond",chr(0x1F48E)),("Flower",chr(0x1F338)),("Guitar",chr(0x1F3B8)),("Heart",chr(0x1F49C)),("Key",chr(0x1F511)),("Leaf",chr(0x1F343)),("Moon",chr(0x1F319)),("Rocket",chr(0x1F680)),("Sun",chr(0x1F31E)),("Trophy",chr(0x1F3C6)),("Umbrella",chr(0x2602)),("Watch",chr(0x231A))]

VERBAL_BANK = {
"Vocabulary": {
"Beginner": [
("Choose the closest meaning of 'curious'.", ["Eager to learn", "Very tired", "Angry", "Careless"], 0, "Curious means eager to know or learn."),
("What does 'brief' mean?", ["Short", "Loud", "Difficult", "Polite"], 0, "Brief means short in time or length."),
("Choose the opposite of 'generous'.", ["Selfish", "Helpful", "Kind", "Friendly"], 0, "Generous means willing to give; selfish is the opposite."),
("What does 'repair' mean?", ["Fix", "Break", "Hide", "Borrow"], 0, "To repair something is to fix it."),
("Choose the closest meaning of 'quiet'.", ["Silent", "Busy", "Bright", "Quick"], 0, "Quiet means making little or no sound.")],
"Intermediate": [
("What does 'reluctant' mean?", ["Unwilling or hesitant", "Very excited", "Completely certain", "Easy to please"], 0, "Reluctant describes hesitation or unwillingness."),
("Choose a synonym for 'accurate'.", ["Precise", "Ordinary", "Careless", "Unclear"], 0, "Accurate means correct and precise."),
("In 'The evidence was scarce', what does 'scarce' mean?", ["Limited", "Reliable", "Recent", "Unusual"], 0, "Scarce means present in small amounts."),
("Choose the opposite of 'expand'.", ["Contract", "Explain", "Increase", "Create"], 0, "Contract means to become smaller; expand means to grow."),
("What does 'consequence' mean?", ["A result", "A suggestion", "A question", "A promise"], 0, "A consequence is an outcome or result.")],
"Advanced": [
("What does 'ambiguous' mean?", ["Open to more than one interpretation", "Clearly proven", "Impossible to change", "Unusually brief"], 0, "Ambiguous language can be understood in more than one way."),
("Choose the closest meaning of 'mitigate'.", ["Make less severe", "Make more visible", "Predict exactly", "Remove completely"], 0, "Mitigate means to reduce the severity or impact."),
("In 'a pragmatic solution', what does 'pragmatic' mean?", ["Practical and realistic", "Theoretical only", "Emotionally intense", "Unnecessarily complex"], 0, "Pragmatic describes a practical approach focused on what works."),
("Choose the opposite of 'transient'.", ["Permanent", "Temporary", "Uncertain", "Frequent"], 0, "Transient means temporary; permanent is its opposite."),
("What does 'corroborate' mean?", ["Support with additional evidence", "Disagree without reason", "Summarize briefly", "Delay a decision"], 0, "To corroborate is to confirm a claim with supporting evidence.")]},
"Analogies": {
"Beginner": [
("Bird is to nest as bee is to ___.", ["Hive", "Web", "Den", "Stable"], 0, "A nest is a bird's home; a hive is a bee's home."),
("Puppy is to dog as kitten is to ___.", ["Cat", "Horse", "Bird", "Fish"], 0, "A puppy is a young dog; a kitten is a young cat."),
("Hot is to cold as day is to ___.", ["Night", "Sun", "Light", "Warm"], 0, "These are opposite pairs: hot/cold and day/night."),
("Pen is to write as knife is to ___.", ["Cut", "Read", "Paint", "Fold"], 0, "A pen is used to write; a knife is used to cut."),
("Hand is to glove as foot is to ___.", ["Sock", "Hat", "Sleeve", "Belt"], 0, "A glove covers a hand; a sock covers a foot.")],
"Intermediate": [
("Author is to book as composer is to ___.", ["Music", "Canvas", "Recipe", "Building"], 0, "An author creates a book; a composer creates music."),
("Seed is to tree as egg is to ___.", ["Bird", "Nest", "Feather", "Shell"], 0, "A seed can grow into a tree; an egg can develop into a bird."),
("Thermometer is to temperature as barometer is to ___.", ["Air pressure", "Speed", "Distance", "Weight"], 0, "A thermometer measures temperature; a barometer measures air pressure."),
("Generous is to giving as curious is to ___.", ["Learning", "Sleeping", "Hiding", "Arguing"], 0, "Generosity is a tendency to give; curiosity is a desire to learn."),
("Chapter is to book as scene is to ___.", ["Play", "Actor", "Audience", "Ticket"], 0, "A chapter is a section of a book; a scene is a section of a play.")],
"Advanced": [
("Blueprint is to building as outline is to ___.", ["Essay", "Editor", "Library", "Sentence"], 0, "A blueprint plans a building; an outline plans an essay."),
("Oasis is to desert as island is to ___.", ["Ocean", "Mountain", "Forest", "Valley"], 0, "An oasis is an area within a desert; an island is land within an ocean."),
("Diagnosis is to treatment as analysis is to ___.", ["Decision", "Question", "Observation", "Measurement"], 0, "Diagnosis informs treatment; analysis helps inform a decision."),
("Skeptic is to doubt as advocate is to ___.", ["Support", "Ignore", "Measure", "Delay"], 0, "A skeptic questions a claim; an advocate supports a position."),
("Eulogy is to praise as critique is to ___.", ["Evaluate", "Celebrate", "Imitate", "Translate"], 0, "A eulogy praises; a critique evaluates, often by discussing strengths and weaknesses.")]},
"Reading comprehension": {
"Beginner": [
("Mina takes the bus at 8:00 every morning. Today it arrived ten minutes late, so she reached school at 8:40. Why was Mina late?", ["The bus arrived late", "She missed school", "She walked slowly", "The school opened early"], 0, "The passage directly says the bus was ten minutes late."),
("A garden has six red flowers and four yellow flowers. How many flowers are there altogether?", ["10", "2", "6", "12"], 0, "Six plus four is ten."),
("Omar reads for twenty minutes before bed because he wants to learn new words. What is his reason for reading?", ["To learn new words", "To catch a bus", "To water plants", "To cook dinner"], 0, "Omar reads because he wants to learn new words."),
("The library is closed on Sunday but opens at 9 a.m. on Monday. When can you first visit after Sunday?", ["Monday at 9 a.m.", "Sunday evening", "Monday at 8 a.m.", "Saturday at 9 a.m."], 0, "It opens Monday at 9 a.m."),
("Leah packed an umbrella after she saw dark clouds. What did she expect might happen?", ["Rain", "Snow", "Strong heat", "A power cut"], 0, "Dark clouds and an umbrella suggest she expected rain.")],
"Intermediate": [
("A community center extended its evening hours after workers said they could not attend daytime classes. Attendance rose most among adults with full-time jobs. Which conclusion is best supported?", ["Evening hours made classes easier for some workers to attend", "All adults prefer night classes", "Daytime classes are no longer useful", "Every worker attended a class"], 0, "The passage links the extended hours with increased attendance among working adults."),
("Nadia checked two weather reports before planning a picnic. Both predicted light rain, so she moved it indoors. Why did she change the plan?", ["Both reports suggested rain", "The venue was closed", "Her guests cancelled", "She dislikes picnics"], 0, "She relied on the two forecasts predicting rain."),
("A shop reduced food waste by marking down items near their sell-by date. More customers bought those items, and fewer were discarded. What is the main result?", ["Discounts helped sell food that might otherwise be wasted", "All food became cheaper", "Customers stopped buying fresh items", "The shop closed early"], 0, "The passage says more near-date food sold and less was discarded."),
("Ravi practices a presentation aloud and records himself. He notices that he speaks too quickly, so he adds pauses. What skill is he trying to improve?", ["Clear spoken delivery", "Handwriting", "Listening to music", "Typing speed"], 0, "He adjusts his pace and pauses to make his spoken presentation clearer."),
("The team first blamed a slow website on the images. After compressing them, the page remained slow; a review then found an inefficient database query. What does this show?", ["The first explanation was incomplete", "Images always slow websites", "The database was working perfectly", "The page was not slow"], 0, "The image change did not fix the issue, and a different cause was found.")],
"Advanced": [
("A city added protected bike lanes. Counts showed more weekday cycling, but surveys found little change in weekend rides. The report notes that the lanes connect office districts better than parks. Which interpretation best fits the evidence?", ["The network may be more useful for commuting than for leisure trips", "Every resident now cycles to work", "Protected lanes reduce all weekend travel", "The surveys prove the lanes failed"], 0, "The weekday increase and route locations suggest a stronger commuting benefit."),
("A study found that students who took handwritten notes scored slightly higher on a recall quiz than students who typed. The authors warn that the groups also differed in prior knowledge. What is the key limitation?", ["The score difference cannot confidently be attributed to note-taking method alone", "The quiz contained no questions", "Typing is impossible for students", "Handwriting always improves memory"], 0, "Prior knowledge is a possible confounding factor, so the method alone may not explain the result."),
("A company introduced a four-day workweek in one department. Output stayed stable for three months, while employee satisfaction rose. The trial had no comparison group. What is the most careful conclusion?", ["The trial is promising, but it cannot establish that the schedule caused the changes", "The schedule will work for every company", "Output increased dramatically", "Employee satisfaction was unchanged"], 0, "Without a comparison group, other factors could explain the observed changes."),
("A writer removes technical terms from a public notice. Readers understand the main action more often, but specialists say an important distinction is now unclear. What trade-off did the writer make?", ["Accessibility improved while some precision was lost", "The notice became longer and harder", "Specialists understood it better", "The main action disappeared"], 0, "Simplifying language improved general understanding but blurred a distinction."),
("A survey reports that people who sleep longer tend to report better concentration. Participants self-reported both sleep and concentration. Which statement is justified?", ["The measures are associated, but the survey does not prove sleep caused concentration to improve", "More sleep always improves concentration", "Concentration causes people to sleep longer", "The survey objectively measured brain activity"], 0, "An association in self-reported survey data does not establish causation.")]},
"Word reasoning": {
"Beginner": [
("Rearrange the letters in LISTEN to make a word meaning quiet.", ["SILENT", "ENLIST", "TINSEL", "INLETS"], 0, "LISTEN rearranges to SILENT, which means quiet."),
("Which word completes both phrases: ___ cake and ___ day?", ["Birth", "Rain", "Book", "Blue"], 0, "Birthday cake and birthday are both common phrases."),
("Choose the word that rhymes with 'light'.", ["Bright", "Late", "Let", "Lot"], 0, "Light and bright rhyme."),
("Which pair are anagrams (the same letters in a different order)?", ["listen / silent", "quiet / quick", "learn / linear", "speak / space"], 0, "LISTEN and SILENT use the same six letters in a different order."),
("Put these words in alphabetical order: pear, apple, mango.", ["apple, mango, pear", "mango, apple, pear", "pear, mango, apple", "apple, pear, mango"], 0, "Alphabetically, apple comes before mango, then pear.")],
"Intermediate": [
("Which word completes the relationship: author, book; architect, ___.", ["Building", "Blueprint", "Brick", "Client"], 0, "An author creates a book; an architect designs a building."),
("If every letter moves one step forward, what does MIND become?", ["NJOE", "NJOD", "LJMC", "NINE"], 0, "M to N, I to J, N to O, and D to E gives NJOE."),
("Which word has the most letters in common with 'stone' in the same positions?", ["Shone", "Stove", "Store", "Atone"], 0, "Shone shares S, O, N, and E in the same positions."),
("A word means both 'to look quickly' and 'a brief view'. Which word fits?", ["Glance", "Stare", "Watch", "Study"], 0, "Glance can mean to look quickly or a brief look."),
("Choose a word that connects 'page' and 'web'.", ["Browser", "Pencil", "Shelf", "Envelope"], 0, "A web page is viewed using a browser.")],
"Advanced": [
("In the analogy 'ephemeral : lasting :: obscure : ___', choose the best completion.", ["Clear", "Hidden", "Brief", "Complex"], 0, "Ephemeral contrasts with lasting; obscure contrasts with clear."),
("A word ladder changes one letter each step: COLD, CORD, CARD, ___. Which word completes it to name a hospital section?", ["CARE", "WARD", "BARD", "CART"], 1, "CARD changes to WARD by replacing C with W; a ward is a section of a hospital."),
("Which word is the odd one out by meaning?", ["Candid", "Frank", "Sincere", "Secretive"], 3, "Candid, frank, and sincere suggest openness; secretive suggests concealment."),
("If 'some' means at least one, and some editors are writers while all writers are readers, what must follow?", ["Some editors are readers", "All editors are readers", "No editors are readers", "Some readers are not writers"], 0, "The editors who are writers must also be readers."),
("Choose the most precise word: 'The evidence ___ the claim, but does not prove it.'", ["Supports", "Guarantees", "Erases", "Avoids"], 0, "Evidence can support a claim without conclusively proving it.")]},
"Grammar & communication": {
"Beginner": [
("Choose the correct sentence.", ["She goes to school every day.", "She go to school every day.", "She going to school every day.", "She gone to school every day."], 0, "With she/he/it in the simple present, the verb usually takes -s."),
("Choose the correct article: 'I ate ___ apple.'", ["an", "a", "the", "no article"], 0, "Use 'an' before a vowel sound: an apple."),
("Choose the polite request.", ["Could you please help me?", "Give help now.", "You help me.", "Help, you."], 0, "'Could you please...' is a courteous way to make a request."),
("Choose the correct past tense: 'Yesterday, we ___ a movie.'", ["watched", "watch", "watching", "watches"], 0, "The past tense of watch is watched."),
("Which reply is a clear, friendly introduction?", ["Hello, I'm Asha. It's nice to meet you.", "Asha me.", "You know who I am.", "Meeting."], 0, "This reply is complete, polite, and easy to understand.")],
"Intermediate": [
("Choose the correct sentence.", ["Neither of the answers is correct.", "Neither of the answers are correct.", "Neither answers is correct.", "Neither answer were correct."], 0, "Neither is grammatically singular in this construction, so use 'is'."),
("Choose the clearest professional reply to a meeting request.", ["Tuesday at 2 p.m. works for me. Thank you.", "Maybe. You decide.", "I can maybe probably do it.", "Meeting yes."], 0, "It gives a definite time and uses a courteous tone."),
("Complete the sentence: 'I have lived here ___ 2022.'", ["since", "for", "during", "from"], 0, "Use 'since' with a starting point in time."),
("Choose the best connector: 'The train was delayed; ___, we arrived late.'", ["as a result", "for example", "meanwhile", "instead of"], 0, "'As a result' clearly signals the consequence of the delay."),
("Which sentence is concise and clear?", ["Please send the report by Friday.", "I am writing to ask if it might be possible for you to send the report sometime by Friday.", "The report, if you can, Friday, send.", "It is the report that is needed by me Friday."], 0, "The first sentence communicates the request directly and politely.")],
"Advanced": [
("Choose the sentence with correct parallel structure.", ["The role involves planning, writing, and presenting.", "The role involves planning, writing, and to present.", "The role involves to plan, writing, and presenting.", "The role involves plan, writing, and presentation."], 0, "The three activities use matching -ing forms."),
("Choose the most tactful way to disagree in a discussion.", ["I see your point. Could we also consider another option?", "That idea is obviously wrong.", "No, stop talking.", "You never understand this."], 0, "It acknowledges the other person and introduces an alternative respectfully."),
("Choose the correctly punctuated sentence.", ["After the meeting, we sent the notes.", "After the meeting we, sent the notes.", "After, the meeting we sent the notes.", "After the meeting; we sent, the notes."], 0, "A comma follows the introductory phrase 'After the meeting'."),
("Which edit removes ambiguity? 'When Maya called Sara, she was driving.'", ["Maya called Sara while Maya was driving.", "When Maya called Sara, she was driving.", "She was driving when she called her.", "While driving, she called her."], 0, "Repeating Maya's name makes clear who was driving."),
("Choose the strongest concise update to a teammate.", ["The draft is ready. I have flagged two figures for your review.", "I just wanted to mention that there is sort of a draft and maybe two figures.", "Draft, figures, review perhaps.", "Everything is finished, though two figures still need checking."], 0, "It is direct and accurately states both what is ready and what needs review.")]}}

QUOTES = [("Great things are done by a series of small things brought together.","Vincent van Gogh"),("It always seems impossible until it's done.","Nelson Mandela"),("Success is the sum of small efforts, repeated day in and day out.","Robert Collier"),("The secret of getting ahead is getting started.","Mark Twain"),("Believe you can and you're halfway there.","Theodore Roosevelt"),("You don't have to be great to start, but you have to start to be great.","Zig Ziglar"),("I have not failed. I've just found 10,000 ways that won't work.","Thomas Edison"),("Confidence comes from discipline and training.","Robert Kiyosaki"),("Small progress is still progress.","Keep going")]

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');
:root{--ink:#fff5f5;--muted:#b7a9ae;--line:rgba(255,96,112,.17);--cyan:#ff4355;--violet:#ff7a68}
.stApp{background:radial-gradient(ellipse at 8% 2%,rgba(190,20,43,.27),transparent 31%),radial-gradient(ellipse at 91% 4%,rgba(112,17,34,.24),transparent 29%),radial-gradient(ellipse at 50% 48%,rgba(55,17,24,.16),transparent 58%),#080808;color:var(--ink);font-family:'DM Sans',sans-serif}
header[data-testid="stHeader"]{background:transparent}.block-container{max-width:1200px;padding-top:2rem;padding-bottom:3rem}
[data-testid="stSidebar"]{background:radial-gradient(ellipse at 0 0,rgba(173,26,44,.15),transparent 55%),linear-gradient(180deg,#100b0d,#0b090a);border-right:1px solid var(--line);box-shadow:inset -12px 0 35px #ff30420a}[data-testid="stSidebar"] *{color:#f1e6e8}
h1,h2,h3{font-family:'Manrope',sans-serif;letter-spacing:-.04em;color:#f6f8ff}
.hero{padding:2rem 2.15rem;border-radius:26px;border:1px solid rgba(255,91,106,.32);background:radial-gradient(ellipse at 18% 0%,rgba(182,35,52,.24),transparent 48%),linear-gradient(115deg,rgba(44,12,17,.98),rgba(20,14,17,.96) 56%,rgba(47,13,21,.95));box-shadow:0 24px 70px #000b,0 0 38px #e523391c,inset 0 1px 0 #ffffff0c;position:relative;overflow:hidden;margin-bottom:1.25rem}
.hero:after{content:'';position:absolute;width:330px;height:330px;border:1px solid #ff536255;border-radius:50%;right:-125px;top:-168px;box-shadow:0 0 18px #ff43551c,0 0 0 30px #ff43550d,0 0 0 65px #ff435509}
.eyebrow{color:var(--cyan);text-transform:uppercase;letter-spacing:.18em;font-size:.73rem;font-weight:700;text-shadow:0 0 14px #ff435566}.hero h1{font-size:clamp(2.3rem,5vw,3.8rem);line-height:1.02;margin:.75rem 0 .65rem;text-shadow:0 2px 24px #ff435522}.hero p{color:#b8c6d7;max-width:640px;font-size:1.03rem;line-height:1.65;margin:0}
.pill{display:inline-block;padding:.38rem .75rem;border-radius:999px;background:linear-gradient(110deg,#ff43551f,#ff43550c);border:1px solid #ff435566;color:#ffb0b8;font-size:.75rem;margin:.3rem .35rem 0 0;box-shadow:0 0 14px #ff435512,inset 0 1px 0 #ffffff0c}
.section-label{color:var(--cyan);font-weight:700;font-size:.78rem;letter-spacing:.14em;text-transform:uppercase;margin:.7rem 0 .45rem}
.quote-card{border:1px solid #ff43554a;border-left:3px solid var(--violet);background:radial-gradient(ellipse at 0 0,rgba(181,30,47,.2),transparent 62%),linear-gradient(120deg,#321218e8,#171012f5);padding:1.25rem 1.45rem;border-radius:16px;margin:1.15rem 0;color:#fff0f1;font-size:1.02rem;line-height:1.6;box-shadow:0 12px 34px #0005,0 0 24px #ff43550b,inset 0 1px 0 #ffffff09}.quote-card small{display:block;color:#c3aeb2;margin-top:.45rem;letter-spacing:.04em}
.panel{background:radial-gradient(ellipse at 0 0,rgba(162,28,44,.12),transparent 58%),linear-gradient(145deg,#191012f5,#100c0df5);border:1px solid var(--line);border-radius:20px;padding:1.3rem 1.4rem;margin:.55rem 0 1rem;box-shadow:0 10px 30px #0003,inset 0 1px 0 #ffffff08}.tip{color:#c1b2b5;font-size:.9rem;line-height:1.55}
.panel{transition:transform .2s ease,border-color .2s ease,box-shadow .2s ease}.panel:hover{transform:translateY(-2px);border-color:#ff536277;box-shadow:0 16px 42px #0008,0 0 28px #ff30421c,inset 0 1px 0 #ffffff12}
.hero .eyebrow{animation:ember 3.2s ease-in-out infinite alternate}@keyframes ember{from{text-shadow:0 0 4px #ff435522}to{text-shadow:0 0 15px #ff4355a6}}
div[data-testid="stTextArea"] textarea,div[data-testid="stTextInput"] input{background:#fff8f8!important;color:#201316!important;border:2px solid #ff4355!important;border-radius:12px!important;font-size:1rem!important;box-shadow:0 0 0 3px #ff43551c!important}
div[data-testid="stTextArea"] textarea::placeholder,div[data-testid="stTextInput"] input::placeholder{color:#64748b!important;opacity:1!important}label,div[data-testid="stWidgetLabel"] p{color:#e4ebf4!important;font-weight:600!important}
div.stButton>button{background:linear-gradient(110deg,#d91f36,#f03b4f 55%,#ff5867);color:white;border:1px solid #ff7180;border-radius:11px;padding:.58rem 1.1rem;font-weight:700;transition:.2s;box-shadow:0 5px 20px #ed203633,0 0 0 1px #ff53621a,inset 0 1px 0 #ffffff35}div.stButton>button:hover{background:linear-gradient(110deg,#f02c43,#ff5363 55%,#ff7a68);border:1px solid #ff9ca5;transform:translateY(-1px);box-shadow:0 8px 28px #ed20365c,0 0 22px #ff435545,inset 0 1px 0 #ffffff55}
div[data-testid="stProgress"] div[role="progressbar"]>div{background:linear-gradient(90deg,#e52339,#ff7a68);box-shadow:0 0 12px #ff435566}[data-testid="stMetric"]{background:radial-gradient(ellipse at 0 0,#6c1b2733,transparent 70%),linear-gradient(145deg,#1c1114,#120e10);padding:1rem;border:1px solid var(--line);border-radius:15px;box-shadow:0 10px 30px #0004,inset 0 1px 0 #ffffff08}[data-testid="stMetricLabel"]{color:#c3adb2!important}[data-testid="stMetricValue"]{color:#ff6471!important;text-shadow:0 0 18px #ff43553b}
[data-testid="stExpander"]{background:linear-gradient(135deg,#211216e8,#171012e8);border:1px solid var(--line);border-radius:14px;box-shadow:0 8px 24px #0003}[data-testid="stExpander"]:hover{border-color:#ff435555;box-shadow:0 10px 30px #0005,0 0 18px #ff435511}hr{border-color:var(--line);box-shadow:0 0 8px #ff435522}footer{visibility:hidden}
.signature{margin-top:.45rem;text-align:center;color:#8d7b7f;font-size:.7rem;letter-spacing:.2em;text-transform:uppercase}.signature b{color:#ff5362;font-weight:800}
@media(max-width:700px){.block-container{padding:1rem}.hero{padding:1.45rem}.hero h1{font-size:2.45rem}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation-duration:.01ms!important;transition-duration:.01ms!important}}
:root{--ink:#fff5f5;--muted:#b7a9ae;--line:rgba(255,96,112,.17);--cyan:#ff4355;--violet:#ff7a68}
*{box-sizing:border-box}
.stApp{background:radial-gradient(ellipse at 8% 0%,rgba(190,20,43,.2),transparent 30%),radial-gradient(ellipse at 96% 12%,rgba(112,17,34,.18),transparent 27%),linear-gradient(180deg,#0b0809 0%,#090708 48%,#0c0809 100%);color:var(--ink);font-family:'DM Sans',sans-serif}
.block-container{max-width:1320px;padding:2rem 2.4rem 3.25rem}
[data-testid="stSidebar"]{background:radial-gradient(ellipse at 0 0,rgba(173,26,44,.13),transparent 52%),linear-gradient(180deg,#100b0d,#0b090a);border-right:1px solid var(--line);box-shadow:inset -12px 0 35px #ff30420a}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p{line-height:1.55}
[data-testid="stSidebar"] [data-testid="stRadio"] label{border:1px solid transparent;border-radius:11px;padding:.32rem .55rem;transition:background .18s ease,border-color .18s ease}
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover{background:#ff435510;border-color:#ff43552b}
h1,h2,h3{font-family:'Manrope',sans-serif;letter-spacing:-.035em;color:#f6f8ff}
h2{margin-top:1.3rem}
.hero{padding:2.45rem 2.6rem;border-radius:28px;border:1px solid rgba(255,91,106,.27);background:radial-gradient(ellipse at 18% 0%,rgba(182,35,52,.2),transparent 48%),linear-gradient(115deg,rgba(44,12,17,.98),rgba(20,14,17,.97) 56%,rgba(47,13,21,.96));box-shadow:0 24px 70px #0009,inset 0 1px 0 #ffffff0c;position:relative;overflow:hidden;margin:0 0 1.65rem}
.hero:before{content:'';position:absolute;inset:0;background:linear-gradient(115deg,transparent 0%,#ffffff04 48%,transparent 70%);pointer-events:none}
.hero:after{content:'';position:absolute;width:340px;height:340px;border:1px solid #ff536244;border-radius:50%;right:-145px;top:-190px;box-shadow:0 0 0 34px #ff43550a,0 0 0 72px #ff435507;pointer-events:none}
.hero .eyebrow{animation:none;text-shadow:none}
.hero h1{font-size:clamp(2.45rem,5vw,4rem);line-height:1.04;margin:.85rem 0 .8rem;text-shadow:0 2px 24px #ff43551c}
.hero p{color:#c1b4b8;max-width:650px;font-size:1.02rem;line-height:1.7;margin:0 0 .55rem}
.pill{padding:.4rem .78rem;background:linear-gradient(110deg,#ff43551b,#ff43550a);border-color:#ff43554c;color:#ffb0b8;font-size:.74rem;margin:.45rem .35rem 0 0;letter-spacing:.02em;box-shadow:none}
.section-label{font-size:.72rem;letter-spacing:.15em;margin:.8rem 0 .48rem}
.quote-card{background:radial-gradient(ellipse at 0 0,rgba(181,30,47,.17),transparent 62%),linear-gradient(120deg,#281116e8,#151012f5);padding:1.35rem 1.55rem;border-radius:18px;margin:1.3rem 0;line-height:1.7;box-shadow:0 14px 36px #0004,inset 0 1px 0 #ffffff08}
.quote-card small{margin-top:.5rem;font-size:.78rem}
.panel{background:radial-gradient(ellipse at 0 0,rgba(162,28,44,.1),transparent 58%),linear-gradient(145deg,#191012f5,#100c0df5);border:1px solid var(--line);border-radius:20px;padding:1.4rem 1.5rem;margin:.65rem 0 1.05rem;box-shadow:0 12px 32px #0003,inset 0 1px 0 #ffffff08;transition:transform .2s ease,border-color .2s ease,box-shadow .2s ease}
.panel:hover{transform:translateY(-2px);border-color:#ff53625c;box-shadow:0 18px 42px #0006,0 0 24px #ff304215,inset 0 1px 0 #ffffff0d}
.tip{font-size:.89rem;line-height:1.65}
div[data-testid="stTextArea"] textarea,div[data-testid="stTextInput"] input{border:1px solid #ff6471!important;border-radius:12px!important;box-shadow:0 0 0 3px #ff435510!important;transition:box-shadow .18s ease,border-color .18s ease}
div[data-testid="stTextArea"] textarea:focus,div[data-testid="stTextInput"] input:focus{border-color:#ff4355!important;box-shadow:0 0 0 4px #ff435526!important}
div[data-testid="stTextArea"] textarea::placeholder,div[data-testid="stTextInput"] input::placeholder{color:#75686b!important;opacity:1!important}
label,div[data-testid="stWidgetLabel"] p{color:#e4dadd!important;font-weight:600!important}
div[data-baseweb="select"]>div{background:#171012;border-color:#553038;border-radius:11px;color:#fff5f5}
div[data-baseweb="select"]>div:hover{border-color:#ff536277}
div.stButton>button{border-radius:12px;padding:.62rem 1.12rem;letter-spacing:.01em;transition:transform .18s ease,box-shadow .18s ease,border-color .18s ease;box-shadow:0 6px 18px #ed203626,inset 0 1px 0 #ffffff35}
div.stButton>button:hover{transform:translateY(-1px);box-shadow:0 9px 24px #ed203644,inset 0 1px 0 #ffffff55}
div.stButton>button:focus{box-shadow:0 0 0 3px #ff43553b,0 6px 18px #ed203626}
[data-testid="stProgress"]{margin:.45rem 0 1rem}
[data-testid="stProgress"] div[role="progressbar"]{background:#2a171b;border-radius:99px;overflow:hidden}
[data-testid="stProgress"] div[role="progressbar"]>div{box-shadow:0 0 10px #ff43553d}
[data-testid="stMetric"]{padding:1.1rem 1.15rem;border-radius:17px;box-shadow:0 12px 30px #0003,inset 0 1px 0 #ffffff08}
[data-testid="stMetricLabel"]{font-size:.75rem!important;letter-spacing:.08em;text-transform:uppercase}
[data-testid="stMetricValue"]{text-shadow:0 0 16px #ff435526;font-family:'Manrope',sans-serif}
[data-testid="stExpander"]{border-radius:15px;box-shadow:0 8px 24px #0003;transition:border-color .18s ease}
[data-testid="stExpander"]:hover{border-color:#ff435555}
[data-testid="stTable"]{border:1px solid var(--line);border-radius:14px;overflow:hidden}
hr{margin:1.5rem 0}
.signature{margin-top:.55rem;font-size:.68rem}
@media(max-width:900px){.block-container{padding:1.5rem 1.35rem 2.5rem}.hero{padding:2rem}.hero h1{font-size:clamp(2.2rem,7vw,3.2rem)}}
@media(max-width:600px){.block-container{padding:1rem .9rem 2rem}.hero{padding:1.55rem 1.35rem;border-radius:22px}.panel{padding:1.1rem 1.15rem;border-radius:17px}.quote-card{padding:1.1rem 1.2rem}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation-duration:.01ms!important;transition-duration:.01ms!important;scroll-behavior:auto!important}}
.skill-row{margin:1rem 0 1.25rem}
.skill-row-head{display:flex;align-items:center;justify-content:space-between;gap:1rem;margin-bottom:.5rem;color:#e8dfe1;font-size:.9rem}
.skill-row-head strong{color:#ff6471;font-family:'Manrope',sans-serif;font-size:.92rem}
.skill-track{height:9px;background:#2a171b;border:1px solid #ff43551c;border-radius:99px;overflow:hidden;box-shadow:inset 0 1px 3px #0008}
.skill-track span{display:block;height:100%;border-radius:inherit;background:linear-gradient(90deg,#d91f36,#ff7a68);box-shadow:0 0 12px #ff435540;transition:width .5s ease}
.coach-card{height:100%;min-height:210px;position:relative;overflow:hidden;padding:1.35rem 1.45rem;border:1px solid var(--line);border-radius:19px;background:radial-gradient(ellipse at 100% 0%,rgba(190,20,43,.16),transparent 58%),linear-gradient(145deg,#1c1013f5,#110c0df5);box-shadow:0 14px 34px #0004,inset 0 1px 0 #ffffff09}
.coach-card:after{content:'';position:absolute;width:130px;height:130px;right:-78px;bottom:-82px;border:1px solid #ff536233;border-radius:50%;box-shadow:0 0 0 18px #ff435508;pointer-events:none}
.coach-card h3{font-size:1.25rem;margin:.7rem 0 .55rem}
.coach-foot{position:relative;margin-top:1.15rem;padding-top:.8rem;border-top:1px solid var(--line);color:#b7a9ae;font-size:.78rem;z-index:1}
.coach-foot b{color:#ff9ca5;font-weight:700}

/* ShadowIntelX command-center interface */
:root{--hud-red:#ff334c;--hud-red-soft:#ff6976;--hud-blue:#60a5fa;--hud-panel:rgba(9,13,20,.84);--hud-stroke:rgba(255,61,82,.4);--hud-muted:#9ba8bb}
.stApp{background-color:#05070b;background-image:radial-gradient(ellipse at 47% -8%,rgba(50,77,111,.3),transparent 37%),radial-gradient(ellipse at 95% 12%,rgba(151,18,38,.19),transparent 30%),linear-gradient(rgba(79,114,155,.045) 1px,transparent 1px),linear-gradient(90deg,rgba(79,114,155,.045) 1px,transparent 1px),linear-gradient(180deg,#080b11 0%,#06080d 55%,#090a0f 100%);background-size:auto,auto,48px 48px,48px 48px,auto}
.block-container{max-width:1540px;padding:1.3rem clamp(1rem,2.5vw,2.6rem) 3.1rem;position:relative}
[data-testid="stSidebar"]{min-width:254px!important;max-width:254px!important;background:linear-gradient(180deg,rgba(8,12,19,.98),rgba(5,8,13,.99));border-right:1px solid rgba(104,134,174,.2);box-shadow:12px 0 42px #0008,inset -1px 0 #ffffff09}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p{color:#aab6c8}
[data-testid="stSidebar"] [data-testid="stRadio"]{margin-top:.55rem}
[data-testid="stSidebar"] [data-testid="stRadio"] label{min-height:42px;margin:.13rem 0;padding:.48rem .65rem;border:1px solid transparent;border-radius:10px;color:#c9d2e1;transition:background .18s ease,border-color .18s ease,transform .18s ease}
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover{background:linear-gradient(90deg,#ff334c18,#5a92d00b);border-color:#ff43552c;transform:translateX(2px)}
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked){background:linear-gradient(100deg,rgba(194,24,48,.3),rgba(50,18,29,.55));border-color:#ff52647a;box-shadow:inset 3px 0 #ff3e55,0 0 18px #ff27341b;color:#fff}
.command-header{display:grid;grid-template-columns:minmax(250px,1fr) minmax(250px,1.05fr) auto;align-items:center;gap:1.2rem;margin:0 0 1.15rem;padding:.85rem 1.05rem;border:1px solid rgba(119,147,185,.2);border-radius:18px;background:linear-gradient(110deg,rgba(11,16,24,.94),rgba(10,13,20,.84) 55%,rgba(22,10,15,.9));box-shadow:0 12px 38px #0007,inset 0 1px #ffffff0b;backdrop-filter:blur(14px)}
.brand-lockup{display:flex;align-items:center;gap:.8rem;min-width:0}.brand-sigil{width:48px;height:48px;display:grid;place-items:center;flex:none;border:1px solid #ff4a5d80;border-radius:14px;background:radial-gradient(circle,#ff334c25,#090b10 70%);color:#ff5264;box-shadow:0 0 22px #ff334c2a,inset 0 0 16px #ff334c12}.brand-sigil svg{width:32px;height:32px;filter:drop-shadow(0 0 7px #ff233f88)}
.brand-title{font-family:'Manrope',sans-serif;font-weight:800;font-size:clamp(1rem,1.8vw,1.43rem);letter-spacing:.045em;color:#f3f6fb;white-space:nowrap}.brand-title span{color:#ff5367;text-shadow:0 0 15px #ff334c55}.brand-subtitle{margin-top:.15rem;color:#8290a4;font-size:.7rem;letter-spacing:.12em;text-transform:uppercase}
.header-quote{padding-left:1rem;border-left:1px solid #ff435533;color:#e0e7f1;font:500 .93rem/1.45 'DM Sans',sans-serif}.header-quote span{display:block;color:#ff7783;font-size:.59rem;font-weight:700;letter-spacing:.18em;margin-bottom:.22rem}.header-quote small{display:block;color:#8290a4;font-size:.67rem;margin-top:.25rem}
.profile-chip{display:flex;align-items:center;gap:.65rem;min-width:180px;padding:.45rem .6rem;border:1px solid #7587a528;border-radius:13px;background:#080c13a8}.avatar-orb{width:36px;height:36px;display:grid;place-items:center;flex:none;border-radius:50%;border:1px solid #ff536477;background:radial-gradient(circle at 50% 35%,#ff596c44,#17101a 68%);color:#ff7480;font-size:.75rem;font-weight:800}.profile-copy{min-width:0;flex:1}.profile-copy strong,.profile-copy small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.profile-copy strong{font-size:.77rem;color:#f4f6fa}.profile-copy small{margin-top:.12rem;color:#8995a7;font-size:.65rem}.profile-meter{width:55px;height:4px;flex:none;border-radius:8px;background:#28303e;overflow:hidden}.profile-meter span{display:block;height:100%;border-radius:inherit;background:linear-gradient(90deg,#e61e3c,#ff6c77);box-shadow:0 0 10px #ff394f}
.sidebar-brand{display:flex;align-items:center;gap:.68rem;margin:.4rem 0 1rem;padding:.7rem .45rem .95rem;border-bottom:1px solid #7587a526}.sidebar-brand .brand-sigil{width:42px;height:42px;border-radius:12px}.sidebar-brand strong{display:block;font-family:'Manrope',sans-serif;letter-spacing:.06em;font-size:.85rem;color:#eef3fb}.sidebar-brand small{color:#8491a4;font-size:.64rem;letter-spacing:.09em;text-transform:uppercase}
.hud-card{position:relative;overflow:hidden;border:1px solid rgba(135,154,185,.24);border-radius:17px;background:linear-gradient(145deg,rgba(12,18,28,.94),rgba(7,10,16,.94));box-shadow:0 15px 40px #0005,inset 0 1px #ffffff0b}.hud-card:before{content:'';position:absolute;inset:0;pointer-events:none;border-radius:inherit;background:linear-gradient(115deg,#ffffff08,transparent 27%,transparent 72%,#ff40520b)}.hud-kicker{color:#ff7582;font-size:.63rem;font-weight:800;letter-spacing:.16em;text-transform:uppercase}.hud-card h2,.hud-card h3{margin:.28rem 0 .45rem;color:#f5f7fb}.hud-muted{color:#9ba8bb;font-size:.8rem;line-height:1.55}.dashboard-welcome{min-height:240px;padding:1.25rem 1.4rem;border-color:#ff4a5d55;background:radial-gradient(ellipse at 100% 0%,rgba(169,26,46,.2),transparent 50%),linear-gradient(135deg,rgba(17,20,30,.97),rgba(7,10,15,.97));box-shadow:0 18px 45px #0007,0 0 26px #ff27340d,inset 0 1px #ffffff0d}.welcome-title{margin:.45rem 0 .38rem;font:800 clamp(1.45rem,2.3vw,2.15rem)/1.12 'Manrope',sans-serif;letter-spacing:-.045em;color:#f8f8fb}.welcome-name{color:#ff6374}.welcome-xp{display:flex;align-items:center;justify-content:space-between;gap:1rem;margin:.95rem 0 .3rem;color:#c5ceda;font-size:.71rem}.xp-track{height:7px;border:1px solid #ff435533;border-radius:99px;background:#131a25;overflow:hidden}.xp-track span{display:block;height:100%;border-radius:inherit;background:linear-gradient(90deg,#c71432,#ff364e 62%,#ff8790);box-shadow:0 0 15px #ff334c77}.welcome-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:.55rem;margin-top:1rem}.welcome-stat{padding:.58rem .65rem;border:1px solid #96a9c31b;border-radius:11px;background:#05080d66}.welcome-stat small{display:block;color:#8794a8;font-size:.6rem;letter-spacing:.08em;text-transform:uppercase}.welcome-stat b{display:block;margin-top:.2rem;color:#f2f4f8;font-size:.94rem}
.brain-card{height:100%;min-height:240px;position:relative;overflow:hidden;display:flex;flex-direction:column;justify-content:center;padding:.65rem .8rem;border:1px solid #ff3f5549;border-radius:18px;background:radial-gradient(ellipse at 52% 48%,rgba(183,21,49,.23),transparent 48%),linear-gradient(145deg,#0d121c,#080a10 74%);box-shadow:0 16px 44px #0008,inset 0 0 42px #ff27340a}.brain-card:after{content:'';position:absolute;inset:0;pointer-events:none;background:linear-gradient(0deg,#080a10d9 0%,transparent 36%,transparent 82%,#080a106b)}.brain-caption{position:absolute;left:1rem;bottom:.7rem;z-index:2;color:#a9b4c5;font-size:.63rem;letter-spacing:.12em;text-transform:uppercase}.brain-caption b{color:#ff6b7a}.brain-card svg{width:100%;max-height:235px;z-index:1}.neural-glow{filter:drop-shadow(0 0 7px #ff304f99)}.neural-node{animation:nodePulse 2.8s ease-in-out infinite alternate;transform-box:fill-box;transform-origin:center}.neural-node:nth-of-type(2n){animation-delay:.9s}.orbit-line{transform-origin:center;animation:orbitBreath 7s ease-in-out infinite alternate}.neural-scan{animation:scan 4s linear infinite}.quick-stack{display:flex;flex-direction:column;gap:.55rem}.quick-tile{display:flex;align-items:center;gap:.72rem;min-height:65px;padding:.67rem .75rem;border:1px solid #8798b429;border-radius:13px;background:linear-gradient(120deg,#0c121ddf,#0a0e15e8);box-shadow:0 7px 18px #0004;transition:transform .18s ease,border-color .18s ease,box-shadow .18s ease}.quick-tile:hover{transform:translateX(3px);border-color:#ff526377;box-shadow:0 8px 22px #0006,0 0 16px #ff334c1c}.quick-icon{width:34px;height:34px;display:grid;place-items:center;flex:none;border:1px solid #ff46563a;border-radius:10px;background:#ff344c12;color:#ff6b79;font-size:1.05rem}.quick-tile strong{display:block;color:#eaf0f8;font-size:.76rem}.quick-tile small{display:block;color:#8491a4;font-size:.62rem;margin-top:.15rem}
.section-heading{display:flex;align-items:end;justify-content:space-between;gap:1rem;margin:1.25rem 0 .5rem}.section-heading h2{margin:0;color:#edf2f9;font:750 1.13rem 'Manrope',sans-serif;letter-spacing:-.025em}.section-heading p{margin:.18rem 0 0;color:#8693a6;font-size:.72rem}.arena-tile{height:100%;min-height:180px;position:relative;overflow:hidden;padding:.78rem;border:1px solid #8393ac31;border-radius:15px;background:linear-gradient(155deg,#111824,#090d14);box-shadow:0 10px 26px #0005;transition:transform .2s ease,border-color .2s ease,box-shadow .2s ease}.arena-tile:hover{transform:translateY(-3px);border-color:#ff4c6177;box-shadow:0 15px 32px #0008,0 0 22px #ff334c14}.arena-art{height:74px;display:grid;place-items:center;position:relative;overflow:hidden;margin:-.78rem -.78rem .6rem;border-bottom:1px solid #8b9cb11a;background:radial-gradient(circle at 50% 80%,var(--arena-glow,rgba(255,51,76,.23)),transparent 58%),linear-gradient(130deg,#111a29,#090d15)}.arena-art:before,.arena-art:after{content:'';position:absolute;width:110px;height:110px;border:1px solid var(--arena-stroke,#ff3d5552);border-radius:50%;box-shadow:0 0 20px var(--arena-glow,rgba(255,51,76,.15)),0 0 0 14px #ffffff03}.arena-art:after{width:72px;height:72px;border-style:dashed;animation:orbitBreath 9s linear infinite}.arena-art span{position:relative;z-index:1;font-size:1.65rem;color:var(--arena-ink,#ff6676);filter:drop-shadow(0 0 10px var(--arena-glow,rgba(255,51,76,.6)))}.arena-tile h3{margin:.05rem 0 .2rem;font-size:.88rem;color:#f0f3f8}.arena-tile p{min-height:2.4em;margin:0;color:#909db0;font-size:.65rem;line-height:1.45}.arena-tile .arena-meta{margin-top:.5rem;color:#ff7784;font-size:.58rem;letter-spacing:.08em;text-transform:uppercase}
.dashboard-lower{padding:1rem 1.05rem}.dashboard-dna{padding:.95rem 1rem .35rem;margin:.2rem 0 .65rem}.dashboard-dna svg{display:block;max-height:345px;margin:.15rem auto 0}.mini-mission-title{font-size:.9rem;font-weight:700;color:#edf1f7}.mini-leader-row{display:grid;grid-template-columns:22px 1fr auto;gap:.5rem;align-items:center;padding:.43rem 0;border-bottom:1px solid #8798b41b;color:#cbd4e0;font-size:.68rem}.mini-leader-row:last-child{border-bottom:0}.mini-leader-rank{color:#ff7784;font-weight:800}.mini-leader-score{color:#9ca9ba;font-variant-numeric:tabular-nums}.mini-empty{padding:.6rem .2rem;color:#93a0b1;font-size:.75rem;line-height:1.5}
div[data-testid="stTextArea"] textarea,div[data-testid="stTextInput"] input{background:#0b1019!important;color:#f4f6fa!important;border:1px solid #71829b!important;border-radius:10px!important;box-shadow:inset 0 1px 5px #0008!important}div[data-testid="stTextArea"] textarea:focus,div[data-testid="stTextInput"] input:focus{border-color:#ff576b!important;box-shadow:0 0 0 3px #ff425324,0 0 15px #ff334c18!important}div[data-testid="stTextArea"] textarea::placeholder,div[data-testid="stTextInput"] input::placeholder{color:#8390a2!important}
div[data-baseweb="select"]>div{background:#0c111a;border-color:#65758b;color:#f1f4f8}div[data-baseweb="select"] svg{fill:#b4c0d0}
[data-testid="stMetric"]{background:linear-gradient(140deg,#121925,#090d14);border-color:#8495ae35}[data-testid="stMetricLabel"]{color:#aab7c8!important}[data-testid="stMetricValue"]{color:#ff6777!important;text-shadow:0 0 16px #ff43552e}
[data-testid="stDataFrame"],[data-testid="stTable"]{border:1px solid #71829b39;border-radius:12px;overflow:hidden} [data-testid="stExpander"]{background:#0b1018cf;border-color:#7587a536}
@keyframes nodePulse{0%{opacity:.52;transform:scale(.84)}100%{opacity:1;transform:scale(1.2)}}@keyframes orbitBreath{0%{transform:scale(.96) rotate(-6deg);opacity:.55}100%{transform:scale(1.04) rotate(6deg);opacity:1}}@keyframes scan{0%{transform:translateY(-95px);opacity:0}15%{opacity:.45}85%{opacity:.22}100%{transform:translateY(95px);opacity:0}}
@media(max-width:1100px){.command-header{grid-template-columns:1fr auto}.header-quote{display:none}.arena-tile{min-height:170px}}
@media(max-width:780px){.block-container{padding:1rem .85rem 2rem}.command-header{grid-template-columns:1fr auto;gap:.55rem;padding:.7rem}.brand-sigil{width:40px;height:40px}.profile-chip{min-width:auto}.profile-meter{display:none}.welcome-stats{gap:.35rem}.welcome-stat{padding:.5rem}.brain-card{min-height:195px}.brain-card svg{max-height:185px}}
@media(max-width:520px){.command-header{grid-template-columns:1fr}.profile-chip{display:none}.brand-title{font-size:1rem}.sidebar-brand{margin-top:.15rem}.welcome-stats{grid-template-columns:repeat(3,minmax(0,1fr))}.welcome-stat b{font-size:.78rem}.arena-tile{min-height:155px;padding:.6rem}.arena-art{margin:-.6rem -.6rem .5rem;height:62px}}
@media(prefers-reduced-motion:reduce){.neural-node,.orbit-line,.neural-scan,.arena-art:after{animation:none!important}}
.dashboard-welcome{min-height:275px}.brain-card{min-height:275px;background:radial-gradient(ellipse at 50% 62%,rgba(184,22,48,.32),transparent 40%),linear-gradient(180deg,transparent 58%,rgba(6,9,14,.88)),repeating-linear-gradient(90deg,transparent 0 8.1%,rgba(117,153,193,.13) 8.2%,transparent 8.35% 16.5%),linear-gradient(145deg,#111a28,#080b11 76%)}.brain-card:before{content:'';position:absolute;inset:42% 0 0;background:linear-gradient(0deg,rgba(87,115,151,.11),transparent 75%),repeating-linear-gradient(0deg,transparent 0 13px,rgba(122,155,192,.08) 14px,transparent 15px);pointer-events:none}.brain-card svg{max-height:265px}
.hud-card,.arena-tile{backdrop-filter:blur(10px)}
.arena-tile{min-height:150px;padding:.62rem;border-radius:13px}.arena-art{height:76px;margin:-.62rem -.62rem .52rem}.arena-tile h3{font-size:.77rem}.arena-tile p{min-height:2em;font-size:.59rem}.arena-tile .arena-meta{font-size:.53rem}
.dashboard-dna{min-height:280px}.dashboard-dna svg{max-height:245px}.dna-observed{display:flex;align-items:center;justify-content:space-between;margin:.45rem 0 .25rem;color:#adb8c7;font-size:.64rem}.dna-observed strong{color:#ff6979;font-size:.78rem}.dna-track{height:5px;border-radius:9px;background:#17202d;overflow:hidden}.dna-track span{display:block;height:100%;background:linear-gradient(90deg,#ce1c38,#ff6573);box-shadow:0 0 12px #ff334c66}
.story-card{height:100%;min-height:206px;position:relative;overflow:hidden;border:1px solid #71829b3d;border-radius:16px;background:#080c13;box-shadow:0 14px 38px #0007}.story-card svg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}.story-shade{position:absolute;inset:0;background:linear-gradient(90deg,#080b12ed 0%,#080b1288 48%,#080b1222 100%),linear-gradient(0deg,#080b12bb,transparent 55%)}.story-copy{position:absolute;left:1rem;right:1rem;bottom:.9rem;color:#f2f4f8}.story-copy span{color:#ff7481;font-size:.58rem;font-weight:800;letter-spacing:.16em}.story-copy blockquote{margin:.45rem 0 .25rem;font:700 .92rem/1.35 'Manrope',sans-serif}.story-copy small{color:#b6c0ce;font-size:.65rem}
div[data-testid="stVerticalBlockBorderWrapper"]{border-color:#71829b45!important;border-radius:15px!important;background:linear-gradient(145deg,#0b111bdf,#070a10eb)!important;box-shadow:0 12px 28px #0005,inset 0 1px #ffffff08!important}
div[data-testid="column"]:has(.arena-tile) div.stButton>button{padding:.42rem .45rem;font-size:.67rem}
@media(max-width:1080px){div[data-testid="stHorizontalBlock"]:has(.arena-tile):has(>div[data-testid="column"]:nth-child(6)){display:grid!important;grid-template-columns:repeat(3,minmax(0,1fr));gap:.65rem}div[data-testid="stHorizontalBlock"]:has(.arena-tile):has(>div[data-testid="column"]:nth-child(6))>div[data-testid="column"]{width:auto!important;flex:unset!important;min-width:0!important}}
@media(max-width:650px){div[data-testid="stHorizontalBlock"]:has(.arena-tile):has(>div[data-testid="column"]:nth-child(6)){grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:1050px){.arena-tile{min-height:158px}.dashboard-dna{min-height:240px}}
@media(max-width:760px){.dashboard-welcome,.brain-card{min-height:225px}.brain-card svg{max-height:220px}}
/* Blood-red professional command console across every feature screen. */
:root{--hud-red:#ef1236;--hud-red-soft:#ff405a;--hud-blue:#bd354b;--hud-panel:rgba(13,8,12,.94);--hud-stroke:rgba(210,15,47,.48);--hud-muted:#a79ba2}
.stApp{background:#070508;background-image:radial-gradient(ellipse at 67% 0%,rgba(105,0,27,.25),transparent 40%),radial-gradient(ellipse at 100% 22%,rgba(174,0,36,.12),transparent 32%),linear-gradient(rgba(148,14,42,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(148,14,42,.035) 1px,transparent 1px),linear-gradient(180deg,#090609,#070609 55%,#090609);background-size:auto,auto,42px 42px,42px 42px,auto}
.block-container{max-width:1600px;padding:1rem clamp(1rem,2.2vw,2.25rem) 3rem}
[data-testid="stSidebar"]{min-width:250px!important;max-width:250px!important;background:linear-gradient(180deg,#10080d 0%,#09070a 50%,#080609 100%);border-right:1px solid #54101f;box-shadow:12px 0 46px #0009,inset -1px 0 #ef12360d}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p{color:#aaa0a7}
[data-testid="stSidebar"] [data-testid="stRadio"] label{border-radius:9px;color:#c8bec4;min-height:40px}
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover{background:linear-gradient(90deg,#5e0a1e66,#200b12);border-color:#76152b;transform:translateX(2px)}
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked){background:linear-gradient(95deg,#681022,#260a12);border-color:#a61533;box-shadow:inset 3px 0 #ff183e,0 0 24px #a800251c;color:#fff}
.command-header{border-color:#54101f;background:linear-gradient(105deg,#10090eeb,#0b080ce8 52%,#1b080eef);box-shadow:0 14px 42px #0009,inset 0 1px #ffffff0c}
.brand-sigil{border-color:#aa142f;background:radial-gradient(circle,#e710352c,#10070c 72%);color:#ff263f;box-shadow:0 0 25px #d600302d,inset 0 0 18px #ef123616}
.brand-title span,.welcome-name{color:#ff2848;text-shadow:0 0 17px #ed123b52}
.header-quote{border-color:#85132c;color:#e5dce1}.header-quote span{color:#ff526a}
.hud-card{border-color:#4d1422;background:linear-gradient(145deg,rgba(18,10,15,.97),rgba(9,7,11,.98));box-shadow:0 16px 44px #0008,inset 0 1px #ffffff09}
.hud-card:before{background:linear-gradient(115deg,#ffffff06,transparent 28%,transparent 72%,#ef12360c)}
.hud-kicker{color:#ff536b}.hud-muted{color:#a99ea5}
.dashboard-welcome{border-color:#78162b;background:radial-gradient(ellipse at 100% 0%,rgba(181,8,42,.22),transparent 52%),linear-gradient(135deg,#170b12,#09070b 78%)}
.welcome-stat,.profile-chip{border-color:#55202d;background:#0b080dba}
.welcome-stat b{color:#f7eef1}.xp-track{border-color:#5b1726;background:#180910}.xp-track span{background:linear-gradient(90deg,#99051e,#df092f 60%,#ff4058);box-shadow:0 0 17px #f10e3877}
.brain-card{border-color:#96142e;background:radial-gradient(ellipse at 50% 62%,rgba(200,6,43,.38),transparent 42%),linear-gradient(180deg,transparent 55%,rgba(8,5,9,.86)),repeating-linear-gradient(90deg,transparent 0 8.1%,rgba(180,45,67,.14) 8.2%,transparent 8.35%),linear-gradient(145deg,#160c12,#09070b 76%);box-shadow:0 18px 50px #000a,0 0 28px #ce092b22,inset 0 0 42px #ef123611}
.brain-card:after{background:linear-gradient(0deg,#08060bd9,transparent 30%,transparent 88%,#08060b50)}
.brain-card svg{position:relative;z-index:1;width:100%;height:100%;min-height:285px;max-height:340px;display:block;overflow:visible}
.brain-caption{color:#c5b5bc}.brain-caption b{color:#ff4c64}
.arena-tile{border-color:#45131f;background:linear-gradient(155deg,#180e14,#0b080c);box-shadow:0 10px 28px #0007}
.arena-tile:hover{border-color:#a51b36;box-shadow:0 16px 34px #0009,0 0 23px #df09251e}
.arena-art{--arena-glow:rgba(205,8,43,.33)!important;--arena-stroke:#a81432!important;--arena-ink:#ff405a!important;border-bottom-color:#6a172a;background:radial-gradient(circle at 50% 80%,var(--arena-glow),transparent 60%),linear-gradient(130deg,#1b0d14,#0b080c)}
.arena-art:before,.arena-art:after{border-color:var(--arena-stroke,#a51b36)}
.arena-art span{color:var(--arena-ink,#ff405b);font-size:1.4rem;font-weight:800;letter-spacing:.04em;text-shadow:0 0 13px currentColor}
.section-heading h2,.hud-card h2,.hud-card h3{color:#f5edf0}
.section-heading p,.mini-empty{color:#a1969d}
.dashboard-dna{border-color:#65162a;background:linear-gradient(150deg,#160b11,#09070b)}
.dna-observed strong,.mini-leader-rank,.mini-leader-score{color:#ff4963}.dna-track{background:#1c0a11}.dna-track span{background:linear-gradient(90deg,#a60725,#ff2949);box-shadow:0 0 13px #f30c3d67}
.mini-leader-row{border-color:#461421;color:#d6cbd0}
.story-card{border-color:#601428;background:#10070d;box-shadow:0 16px 40px #0009,0 0 20px #ce09251b}.story-copy span{color:#ff526c}
.screen-intro{position:relative;display:flex;align-items:center;justify-content:space-between;gap:1rem;margin:.15rem 0 1.35rem;padding:1rem 1.2rem;border:1px solid #5d1226;border-radius:15px;background:linear-gradient(105deg,#160a11f5,#0b080cf5 66%,#19080ef5);box-shadow:0 13px 34px #0007,inset 0 1px #ffffff09;overflow:hidden}
.screen-intro:after{content:'';position:absolute;top:0;right:0;width:34%;height:100%;pointer-events:none;background:linear-gradient(90deg,transparent,rgba(174,6,39,.1)),repeating-linear-gradient(135deg,transparent 0 14px,rgba(255,33,65,.07) 15px,transparent 16px)}
.screen-intro-copy,.screen-intro-status{position:relative;z-index:1}.screen-intro-label{color:#ff526c;font-size:.61rem;font-weight:800;letter-spacing:.18em;text-transform:uppercase}.screen-intro h1{margin:.18rem 0 .12rem;color:#f8f0f3;font:800 clamp(1.25rem,2vw,1.8rem)/1.1 'Manrope',sans-serif;letter-spacing:-.035em}.screen-intro p{margin:0;color:#aa9ca4;font-size:.76rem;line-height:1.5}.screen-intro-status{display:flex;align-items:center;gap:.55rem;padding:.5rem .7rem;border:1px solid #4d1825;border-radius:999px;background:#0a070bd9;color:#c6b6be;font-size:.62rem;letter-spacing:.09em;text-transform:uppercase;white-space:nowrap}.system-pulse{width:7px;height:7px;border-radius:50%;background:#ff2548;box-shadow:0 0 12px #ff2548;animation:systemPulse 1.8s ease-in-out infinite}
div.stButton>button{background:linear-gradient(145deg,#160d13,#0c090d)!important;color:#eee4e8!important;border:1px solid #541526!important;border-radius:9px!important;box-shadow:inset 0 1px #ffffff09!important;transition:transform .16s ease,border-color .16s ease,box-shadow .16s ease!important}
div.stButton>button:hover{background:linear-gradient(110deg,#2b0b16,#16090f)!important;color:#fff!important;border-color:#c31a3a!important;transform:translateY(-1px);box-shadow:0 7px 20px #bc092633!important}
div.stButton>button[data-testid="stBaseButton-primary"],div.stButton>button[kind="primary"]{background:linear-gradient(110deg,#8c061f,#ce092d 58%,#f21d3e)!important;color:white!important;border-color:#ee3651!important;box-shadow:0 6px 20px #a9002d44,inset 0 1px #ffffff28!important}
div.stButton>button[data-testid="stBaseButton-primary"]:hover,div.stButton>button[kind="primary"]:hover{background:linear-gradient(110deg,#ae0827,#e31338 58%,#ff4056)!important;border-color:#ff5269!important;box-shadow:0 9px 24px #d5003d62!important}
div[data-testid="stTextArea"] textarea,div[data-testid="stTextInput"] input{background:#0b080c!important;color:#f5edf0!important;border-color:#5b1b2c!important}
div[data-testid="stTextArea"] textarea:focus,div[data-testid="stTextInput"] input:focus{border-color:#f02849!important;box-shadow:0 0 0 3px #ef123626,0 0 16px #ef123626!important}
div[data-baseweb="select"]>div{background:#0b080c;border-color:#57202e;color:#f2e9ed}div[data-baseweb="select"] svg{fill:#c7aeb7}
[data-testid="stMetric"]{background:linear-gradient(145deg,#190b12,#0a080c);border:1px solid #551426;border-radius:12px}[data-testid="stMetricLabel"]{color:#baabb2!important}[data-testid="stMetricValue"]{color:#ff405b!important;text-shadow:0 0 15px #e6123b40}
[data-testid="stExpander"],div[data-testid="stVerticalBlockBorderWrapper"]{background:linear-gradient(145deg,#150b11,#0a080c)!important;border-color:#4c1826!important;border-radius:13px!important}
[data-testid="stTabs"] button[role="tab"]{color:#bcaeb5}[data-testid="stTabs"] button[role="tab"][aria-selected="true"]{color:#ff526c;border-bottom-color:#ed1539}
[data-testid="stDataFrame"],[data-testid="stTable"]{border-color:#4c1826;border-radius:12px;overflow:hidden}
::selection{background:#98112d;color:white}
@keyframes systemPulse{0%,100%{opacity:.55;box-shadow:0 0 5px #ff2548}50%{opacity:1;box-shadow:0 0 14px #ff2548}}
@keyframes brainTurn{0%{transform:rotateY(-18deg) rotateX(5deg) scale(.94)}50%{transform:rotateY(162deg) rotateX(5deg) scale(.94)}100%{transform:rotateY(342deg) rotateX(5deg) scale(.94)}}
.brain3d-stage{transform-style:preserve-3d;isolation:isolate}.brain3d-stage:after{content:'';position:absolute;inset:12% 18% 24%;z-index:0;pointer-events:none;border-radius:50%;background:#cb082c;opacity:.12;filter:blur(44px)}
.brain3d-rotor{z-index:1;backface-visibility:visible;transform-origin:center center;filter:drop-shadow(0 0 18px #e10b352b)}.brain3d-rotor svg{position:absolute!important;inset:0!important;width:100%!important;height:100%!important;min-height:0!important;max-height:none!important;display:block!important;overflow:visible!important}.brain3d-platform{position:absolute!important;inset:0!important;width:100%!important;height:100%!important;min-height:0!important;max-height:none!important;z-index:0!important}.brain3d-slice{backface-visibility:visible}.brain3d-depth{filter:drop-shadow(0 0 4px #d40c342e)}
@media(max-width:760px){.screen-intro{align-items:flex-start;flex-direction:column;padding:.9rem}.screen-intro-status{font-size:.57rem}.brain-card svg{min-height:230px}.brain3d-stage{height:285px!important;min-height:285px!important}.brain3d-rotor{inset:4% 4% 12%!important}}
@media(prefers-reduced-motion:reduce){.system-pulse{animation:none!important}.brain3d-rotor{animation-duration:36s!important}}
.brain3d-stage{height:330px!important;min-height:0!important;perspective:760px;background:radial-gradient(ellipse at 50% 47%,#250711 0%,#10070c 54%,#090609 100%);box-shadow:0 16px 46px #000a,0 0 26px #ce092b20,inset 0 0 46px #e10b3514}
.brain3d-stage:after{inset:13% 29% 30%;opacity:.14;filter:blur(42px)}
.brain3d-rotor{inset:0 0 5%;transform-style:preserve-3d;transform-origin:50% 45%;animation:brainSpin 9.5s linear infinite;filter:none!important}
.neural-mesh-canvas{backface-visibility:hidden;will-change:transform}.neural-mesh-canvas[data-face="front"]{transform:translateZ(9px);filter:drop-shadow(0 0 15px #f0123b44)}.neural-mesh-canvas[data-face="back"]{transform:translateZ(-9px) rotateY(180deg);opacity:.88;filter:brightness(.74) saturate(.9)}
.brain3d-orbit{animation-duration:6.8s}.brain3d-readout{font-size:8px;letter-spacing:1.15px}.brain3d-caption{font-size:8px;color:#c39ba5}
@keyframes brainSpin{from{transform:rotateY(0deg) rotateX(-2deg)}to{transform:rotateY(360deg) rotateX(2deg)}}
.arena-tile{min-height:188px;padding:.95rem;border-radius:17px;background:radial-gradient(ellipse at 78% 0%,#45101d88,transparent 52%),linear-gradient(150deg,#1b0d14 0%,#10090e 57%,#09070b 100%);box-shadow:0 14px 32px #0009,inset 0 1px #ffffff0a;transition:transform .22s ease,border-color .22s ease,box-shadow .22s ease}
.arena-tile:hover{transform:translateY(-5px);border-color:#e33452;box-shadow:0 22px 40px #000b,0 0 30px #df092536,inset 0 1px #ffffff12}
.arena-art{height:58px;margin:-.95rem -.95rem .82rem;border-bottom-color:#73172a;background:linear-gradient(100deg,#250d15,#170a10 55%,#0d080d);overflow:hidden}
.arena-art:before{width:126px;height:126px;left:auto;right:14%;top:-94%;border-color:#bd203c77;box-shadow:0 0 28px #cf163052,0 0 0 18px #ffeff107}
.arena-art:after{width:96px;height:96px;left:auto;right:17%;top:-72%;border-color:#ff526b55;animation:arenaOrbit 15s linear infinite}
.arena-art-kicker{position:absolute;top:11px;left:15px;z-index:2;color:#ffc0c9;font:750 .58rem monospace;letter-spacing:.15em}
.arena-art-index{position:absolute;top:7px;right:15px;z-index:2;color:#ff829533;font:800 2.45rem/1 'Manrope',sans-serif;letter-spacing:-.08em}
.arena-symbol{position:absolute;left:57%;top:50%;z-index:3;width:30px;height:30px;display:grid;place-items:center;transform:translate(-50%,-50%);color:#ff7489;filter:drop-shadow(0 0 7px #ff3153aa);animation:symbolGlow 3.6s ease-in-out infinite}
.arena-symbol svg{display:block;width:100%;height:100%;fill:none;stroke:currentColor;stroke-width:1.65;stroke-linecap:round;stroke-linejoin:round}
@keyframes symbolGlow{0%,100%{opacity:.7}50%{opacity:1}}
.arena-card-kicker{margin:0 0 .3rem;color:#ff7488;font:750 .57rem monospace;letter-spacing:.14em}
.arena-tile h3{margin:.08rem 0 .28rem;color:#fff5f7;font-size:1.22rem;letter-spacing:-.03em;text-shadow:0 0 19px #ed123b24}.arena-tile p{min-height:2.4em;margin:0;color:#c4b4bb;font-size:.76rem;line-height:1.5}
@keyframes arenaOrbit{to{transform:rotate(360deg)}}
div[data-testid="column"]:has(.arena-tile) div.stButton>button{margin-top:.24rem;padding:.58rem .65rem;font-size:.72rem;letter-spacing:.04em}
@media(max-width:760px){.brain3d-stage{height:285px!important}.arena-tile{min-height:180px}.arena-art{height:55px}}
@media(prefers-reduced-motion:reduce){.brain3d-rotor{animation-duration:36s!important}.brain3d-orbit{animation-duration:28s!important}}
</style>""", unsafe_allow_html=True)

if "quote" not in st.session_state: st.session_state.quote = random.choice(QUOTES)
if "xp_bank" not in st.session_state: st.session_state.xp_bank = 0

def _begin_attempt(prefix):
    st.session_state[f"{prefix}_attempt_key"] = uuid.uuid4().hex
    st.session_state[f"{prefix}_attempt_started"] = time.monotonic()
    st.session_state[f"{prefix}_attempt_user_id"] = st.session_state.get("active_user_id")


def _attempt_duration(prefix):
    started = st.session_state.get(f"{prefix}_attempt_started")
    return max(0.0, time.monotonic() - float(started)) if started else 0.0


def _save_attempt(prefix, arena, skill, level, score, max_score, xp_earned=0, details=None):
    user_id = st.session_state.get(f"{prefix}_attempt_user_id") or st.session_state.get("active_user_id")
    attempt_key = st.session_state.get(f"{prefix}_attempt_key")
    if not user_id:
        return False
    if not attempt_key:
        _begin_attempt(prefix)
        attempt_key = st.session_state[f"{prefix}_attempt_key"]
    created = record_attempt(
        user_id=int(user_id), attempt_key=attempt_key, arena=arena, skill=skill, level=level,
        score=score, max_score=max_score, duration_seconds=_attempt_duration(prefix),
        xp_earned=xp_earned, details=details or {}, db_path=DB_PATH,
    )
    if int(user_id) == int(st.session_state.get("active_user_id", -1)):
        st.session_state.xp_bank = get_user_xp(int(user_id), DB_PATH)
    return created


def _active_attempts():
    user_id = st.session_state.get("active_user_id")
    return list_attempts(int(user_id), DB_PATH) if user_id else []


def _adaptive_recommendation(skill, default="Beginner"):
    return recommend_difficulty(_active_attempts(), skill, default)


def load_high_scores():
    if "high_scores_cache" not in st.session_state:
        st.session_state.high_scores_cache = list_high_scores(DB_PATH)
    return st.session_state.high_scores_cache

def record_high_score(player, arena, level, score, unit="points"):
    row = upsert_high_score(player, arena, level, score, unit, DB_PATH)
    st.session_state.high_scores_cache = list_high_scores(DB_PATH)
    return row

def finish_focus(score, unit="points"):
    if st.session_state.get("focus_done"): return
    st.session_state.focus_active=False; st.session_state.focus_done=True
    st.session_state.focus_score=round(float(score),2); st.session_state.focus_unit=unit
    record_high_score(st.session_state.focus_player, "Focus | "+st.session_state.focus_game, st.session_state.focus_level, score, unit)
    game = st.session_state.focus_game
    if game == "Reaction Rush":
        quality = len(st.session_state.get("focus_latencies", []))
        maximum = max(1, int(st.session_state.get("focus_attempts", 0)))
    elif game == "Typing Speed":
        quality, maximum = st.session_state.get("focus_typing_accuracy", 0), 100
    else:
        quality, maximum = st.session_state.focus_score, st.session_state.focus_goal
    focus_details = {"game": game, "display_score": st.session_state.focus_score, "unit": unit, "metric_name": "accuracy"}
    if game == "Reaction Rush":
        latencies = st.session_state.get("focus_latencies", [])
        focus_details.update({"successful_reactions": len(latencies), "false_starts": st.session_state.get("focus_false_starts", 0), "average_reaction_ms": round(sum(latencies) / len(latencies), 1) if latencies else None})
    _save_attempt("focus", f"Focus | {game}", "focus", st.session_state.focus_level, quality, max(1, maximum), 0,
                  focus_details)

@st.fragment(run_every="1s")
def focus_round():
    if not st.session_state.get("focus_active"): return
    game=st.session_state.focus_game; level=st.session_state.focus_level
    remaining=max(0.0,st.session_state.focus_deadline-time.time())
    if remaining<=0:
        if game=="Reaction Rush":
            vals=st.session_state.focus_latencies; finish_focus(max(0,round(1000-(sum(vals)/len(vals) if vals else 1000))),"reaction points")
        elif game=="Typing Speed": finish_focus(st.session_state.get("focus_typing_score",0),"WPM")
        else: finish_focus(st.session_state.focus_score)
        st.rerun(); return
    st.progress(min(1.0,1-remaining/st.session_state.focus_duration),text=f"{game} | {level}")
    st.metric("TIME LEFT",f"{remaining:.1f}s")
    if game=="Reaction Rush":
        attempts=st.session_state.focus_attempts
        if attempts>=st.session_state.focus_goal:
            vals=st.session_state.focus_latencies; finish_focus(max(0,round(1000-(sum(vals)/len(vals) if vals else 1000))),"reaction points"); st.rerun(); return
        if st.session_state.focus_phase=="wait" and time.time()>=st.session_state.focus_signal_at:
            st.session_state.focus_phase="signal"; st.session_state.focus_signal_shown=time.perf_counter(); st.rerun(); return
        if st.session_state.focus_phase=="wait":
            st.markdown("<div class='panel'><h3>Wait for the signal...</h3><p class='tip'>Stay ready. Tapping early counts as a false start.</p></div>",unsafe_allow_html=True)
            if st.button("Tap early",key=f"early_{attempts}"):
                st.session_state.focus_false_starts+=1; st.session_state.focus_attempts+=1
                st.session_state.focus_signal_at=time.time()+random.uniform(1.0,2.5); st.rerun()
        else:
            st.markdown("<div class='panel' style='text-align:center;background:linear-gradient(120deg,#8f1026,#f02d49)'><h1>NOW!</h1></div>",unsafe_allow_html=True)
            if st.button("TAP NOW",type="primary",key=f"signal_{attempts}",use_container_width=True):
                st.session_state.focus_latencies.append((time.perf_counter()-st.session_state.focus_signal_shown)*1000)
                st.session_state.focus_attempts+=1; st.session_state.focus_phase="wait"
                st.session_state.focus_signal_at=time.time()+random.uniform(1.0,2.5); st.rerun()
        st.caption(f"Hits {len(st.session_state.focus_latencies)} / {st.session_state.focus_goal} | False starts {st.session_state.focus_false_starts}"); return
    if game=="Colour Trap":
        if st.session_state.focus_round>=st.session_state.focus_goal: finish_focus(st.session_state.focus_score); st.rerun(); return
        palette=[("RED","#ff4055"),("BLUE","#4f8cff"),("GREEN","#38c77a"),("YELLOW","#ffd447")]
        word,ink=st.session_state.focus_color_word,st.session_state.focus_color_ink
        st.markdown(f"<div class='panel' style='text-align:center'><div class='section-label'>TAP THE INK COLOUR</div><h1 style='color:{ink[1]};font-size:3.4rem'>{word}</h1><p class='tip'>Ignore the word. Choose its ink colour.</p></div>",unsafe_allow_html=True)
        cols=st.columns(4)
        for i,(name,color) in enumerate(palette):
            if cols[i].button(name.title(),key=f"colour_{st.session_state.focus_round}_{name}",use_container_width=True):
                st.session_state.focus_score += int(name==ink[0]); st.session_state.focus_round+=1
                st.session_state.focus_color_word=random.choice(palette)[0]; st.session_state.focus_color_ink=random.choice(palette); st.rerun()
        st.caption(f"Correct {st.session_state.focus_score} | Round {st.session_state.focus_round+1} / {st.session_state.focus_goal}"); return
    if game=="Target Hunt":
        if st.session_state.focus_round>=st.session_state.focus_goal: finish_focus(st.session_state.focus_score); st.rerun(); return
        size=st.session_state.focus_grid; target=st.session_state.focus_target
        st.markdown(f"<div class='panel'><div class='section-label'>FIND THE TARGET</div><h3>Tap number {target}</h3><p class='tip'>Scan quickly and accurately.</p></div>",unsafe_allow_html=True)
        values=list(range(1,size*size+1)); random.Random(st.session_state.focus_round*31+int(st.session_state.focus_seed)).shuffle(values)
        for row in range(size):
            cols=st.columns(size)
            for col in range(size):
                value=values[row*size+col]
                if cols[col].button(str(value),key=f"target_{st.session_state.focus_round}_{value}",use_container_width=True):
                    st.session_state.focus_score += int(value==target); st.session_state.focus_round+=1
                    st.session_state.focus_target=random.randint(1,size*size); st.rerun()
        st.caption(f"Found {st.session_state.focus_score} | Round {st.session_state.focus_round+1} / {st.session_state.focus_goal}"); return
    st.markdown("<div class='panel'><div class='section-label'>TYPE THE TEXT ACCURATELY</div><p class='tip'>Keep typing until the timer ends, then submit to calculate speed.</p></div>",unsafe_allow_html=True)
    st.markdown(f"### {st.session_state.focus_typing_prompt}")
    typed=st.text_area("Your typing",key="focus_typed_text",height=120,placeholder="Start typing the passage here...")
    elapsed=max(1.0,min(st.session_state.focus_duration,time.time()-st.session_state.focus_started))
    words=typed.split(); prompt=st.session_state.focus_typing_prompt.split()
    matches=sum(1 for i,w in enumerate(words) if i<len(prompt) and w==prompt[i]); accuracy=100*matches/max(1,len(words))
    st.session_state.focus_typing_accuracy = round(accuracy, 2)
    wpm=len(words)/(elapsed/60); st.session_state.focus_typing_score=round(wpm*accuracy/100)
    st.caption(f"Live pace: {round(wpm)} WPM | Accuracy: {round(accuracy)}%")
    if st.button("Finish typing round"):
        finish_focus(st.session_state.focus_typing_score,"WPM"); st.rerun()

def navigate(target):
    st.session_state.nav_page = target


BRAND_MARK = """<svg viewBox='0 0 48 48' fill='none' aria-hidden='true'><path d='M24 5.5 37.5 13v15.5L24 42 10.5 28.5V13L24 5.5Z' stroke='currentColor' stroke-width='1.5'/><path d='M15 27c2-7 4-12 9-12s7 5 9 12M18 27c2 2 3.5 3 6 3s4-1 6-3M24 15v18M18 21h12M19 33l-4 4m14-4 4 4' stroke='currentColor' stroke-width='1.6' stroke-linecap='round'/><circle cx='24' cy='11' r='2' fill='currentColor'/></svg>"""
NAV_ICONS = {
    "Home": "⌂", "Interview practice": "◉", "IQ teller & logic": "⌘", "Math speed arena": "∑",
    "Memory games": "◈", "Verbal arena": "文", "Focus arena": "◎", "High scores": "♜",
    "Progress & results": "▥", "Skill DNA & Shadow Coach": "⌬", "Shadow Missions": "✦",
    "Mind Boss Battles": "⚔", "Performance Intelligence": "▤",
}

if "profile_name" not in st.session_state:
    st.session_state.profile_name = "Guest"

with st.sidebar:
    st.markdown(f"<div class='sidebar-brand'><div class='brand-sigil'>{BRAND_MARK}</div><div><strong>SHADOWINTELX <span style='color:#ff5268'>IQ</span></strong><small>Neural training system</small></div></div>", unsafe_allow_html=True)
    profile_locked = any(st.session_state.get(key, False) for key in ("interview_active", "logic_active", "math_active", "memory_active", "verbal_active", "focus_active", "boss_active"))
    profile_name = st.text_input("Local practice profile", key="profile_name", max_chars=32, disabled=profile_locked)
    profile = get_or_create_user(profile_name, DB_PATH)
    if st.session_state.get("active_user_id") != profile["id"]:
        st.session_state.active_user_id = profile["id"]
        st.session_state.active_profile_name = profile["display_name"]
        st.session_state.xp_bank = profile["xp"]
    st.caption("Saved locally on this device · no account required")
    st.markdown("## Navigate")
    page = st.radio("Choose a space", list(NAVIGATION_PAGES), format_func=lambda name: f"{NAV_ICONS.get(name, '◈')}   {name}", label_visibility="collapsed", key="nav_page")
    st.markdown("---")
    st.markdown("**A little progress each day adds up.**")
    current_level = 1 + st.session_state.xp_bank // 100
    rank = rank_for_xp(st.session_state.xp_bank)
    st.caption(f"Persistent rank: {rank['name']} · {rank['xp']} XP")
    st.progress(rank["progress"], text=f"{rank['next_xp']} XP to {rank['next_rank']}")
    st.markdown(f"<div class='panel'><div class='section-label'>YOUR PRACTICE LEVEL</div><h3>Level {current_level}</h3><p class='tip'>{st.session_state.xp_bank} XP · {100 - st.session_state.xp_bank % 100} XP to the next level</p></div>", unsafe_allow_html=True)
    st.caption("Practice with purpose. Learn from every attempt.")

header_quote, header_author = st.session_state.quote
safe_profile_name = html_escape(str(st.session_state.active_profile_name))
st.markdown(f"""<div class="command-header"><div class="brand-lockup"><div class="brand-sigil">{BRAND_MARK}</div><div><div class="brand-title">SHADOWINTELX <span>IQ</span></div><div class="brand-subtitle">Train your mind · Unlock your potential</div></div></div><div class="header-quote"><span>DAILY FIELD NOTE</span>“{html_escape(header_quote)}”<small>— {html_escape(header_author)}</small></div><div class="profile-chip"><div class="avatar-orb">{safe_profile_name[:1].upper()}</div><div class="profile-copy"><strong>{safe_profile_name}</strong><small>{rank['name']} · {st.session_state.xp_bank:,} XP</small></div><div class="profile-meter"><span style="width:{rank['progress'] * 100:.1f}%"></span></div></div></div>""", unsafe_allow_html=True)

if page != "Home":
    screen_descriptions = {
        "Interview practice": "Practice HR, technical, and role-based interviews with feedback tied to your answers.",
        "IQ teller & logic": "Work through reasoning puzzles and review the logic behind each answer.",
        "Math speed arena": "Train mental arithmetic with timed rounds and adjustable difficulty.",
        "Memory games": "Exercise recall, sequence memory, and visual attention.",
        "Verbal arena": "Build vocabulary and communication through focused question sets.",
        "Focus arena": "Practice reaction, attention, and sustained focus in short activities.",
        "High scores": "Review saved personal bests from this device.",
        "Progress & results": "See practice history, scores, and round summaries.",
        "Skill DNA & Shadow Coach": "Explore measured skills and get next-step suggestions from saved results.",
        "Shadow Missions": "Track daily and weekly objectives, streaks, and earned rewards.",
        "Mind Boss Battles": "Combine skill arenas in multi-stage challenge rounds.",
        "Performance Intelligence": "Review accuracy, time, strengths, and suggested next practice.",
        "Logic & IQ-style quiz": "Take a mixed reasoning set and inspect your answer explanations.",
    }
    screen_index = NAVIGATION_PAGES.index(page) + 1
    screen_subtitle = screen_descriptions.get(page, "Train with focused rounds and review your saved progress.")
    st.markdown(f"<div class='screen-intro'><div class='screen-intro-copy'><div class='screen-intro-label'>ShadowIntelX / module {screen_index:02d}</div><h1>{html_escape(page)}</h1><p>{html_escape(screen_subtitle)}</p></div><div class='screen-intro-status'><span class='system-pulse'></span> Local system &middot; ready</div></div>", unsafe_allow_html=True)

def quote_card():
    quote, author = st.session_state.quote
    st.markdown(f"<div class='quote-card'>“{quote}”<small>— {author}</small></div>", unsafe_allow_html=True)


def neural_hero_svg():
    """Render an offline, rotating red neural wireframe brain."""
    css = """<style>
      html,body{margin:0;width:100%;height:100%;overflow:hidden;background:#090609}
      .brain3d-stage{position:relative;width:100%;height:330px;overflow:hidden;perspective:760px;isolation:isolate;border:1px solid #8d1730;border-radius:18px;background:radial-gradient(ellipse at 50% 47%,#250711 0%,#10070c 54%,#090609 100%);box-shadow:0 16px 46px #000a,0 0 26px #ce092b20,inset 0 0 46px #e10b3514}
      .brain3d-stage:after{content:'';position:absolute;inset:13% 29% 30%;z-index:0;pointer-events:none;border-radius:50%;background:#d20a32;opacity:.14;filter:blur(42px)}
      .brain3d-platform{position:absolute;inset:0;width:100%;height:100%;z-index:0;pointer-events:none}
      .brain3d-rotor{position:absolute;inset:0 0 5%;z-index:1;transform-style:preserve-3d;transform-origin:50% 45%;animation:brainSpin 9.5s linear infinite}
      .neural-mesh-canvas{position:absolute;inset:0;width:100%;height:100%;display:block;pointer-events:none;backface-visibility:hidden;will-change:transform}
      .neural-mesh-canvas[data-face="front"]{transform:translateZ(9px);filter:drop-shadow(0 0 15px #f0123b44)}.neural-mesh-canvas[data-face="back"]{transform:translateZ(-9px) rotateY(180deg);opacity:.88;filter:brightness(.74) saturate(.9)}
      .brain3d-orbit{position:absolute;inset:0;z-index:2;pointer-events:none;transform-origin:50% 43%;animation:orbitTurn 6.8s linear infinite}
      .brain3d-orbit svg{display:block;width:100%;height:100%;overflow:visible}
      .brain3d-anatomy{position:absolute;inset:0;z-index:3;pointer-events:none}.brain3d-anatomy svg{display:block;width:100%;height:100%}.brain3d-anatomy path{fill:none;stroke:#ff546d66;stroke-width:1;stroke-dasharray:2 3}.brain3d-anatomy circle{fill:#ff8799;filter:drop-shadow(0 0 4px #ff3153)}.brain3d-anatomy text{fill:#d5abb4;font:700 7px monospace;letter-spacing:1px}
      .neural-scan{position:absolute;left:14%;right:14%;top:30%;z-index:2;height:1px;pointer-events:none;background:linear-gradient(90deg,transparent,#ff8193aa,transparent);box-shadow:0 0 9px #ff2349a6;animation:scanLine 3.6s ease-in-out infinite}
      .brain3d-readout{position:absolute;top:10px;z-index:4;color:#ff657b;font:700 8px monospace;letter-spacing:1.15px}.brain3d-readout.left{left:12px}.brain3d-readout.right{right:12px;color:#c9a2ad;font-size:8px}
      .brain3d-caption{position:absolute;left:14px;bottom:11px;z-index:4;color:#c39ba5;font:600 8px monospace;letter-spacing:1.2px;text-transform:uppercase}
      @keyframes orbitTurn{to{transform:rotate(360deg)}}
      @keyframes brainSpin{from{transform:rotateY(0deg) rotateX(-2deg)}to{transform:rotateY(360deg) rotateX(2deg)}}
      @keyframes scanLine{0%{transform:translateY(-62px);opacity:0}20%{opacity:.7}80%{opacity:.36}100%{transform:translateY(100px);opacity:0}}
      @media(max-width:700px){.brain3d-stage{height:285px}.brain3d-readout{font-size:7px}.brain3d-anatomy text{font-size:6px}.neural-scan{left:8%;right:8%}}
      @media(prefers-reduced-motion:reduce){.brain3d-rotor{animation-duration:34s!important}.brain3d-orbit{animation-duration:28s!important}.neural-scan{animation-duration:8s!important}}
    </style>"""
    return css + """
      <div class='brain3d-stage' role='img' aria-label='Rotating shaded red neural brain mesh display'>
        <svg class='brain3d-platform' viewBox='0 0 720 420' aria-hidden='true'>
          <defs><linearGradient id='platformBeam' x1='0' y1='0' x2='0' y2='1'><stop stop-color='#ff234a' stop-opacity='.34'/><stop offset='1' stop-color='#ff234a' stop-opacity='0'/></linearGradient></defs>
          <path d='M360 236v96' stroke='url(#platformBeam)' stroke-width='112'/>
          <g fill='none' stroke='#ef173b'><ellipse cx='360' cy='332' rx='214' ry='29' stroke-width='2'/><ellipse cx='360' cy='332' rx='174' ry='21' stroke-opacity='.7'/><ellipse cx='360' cy='332' rx='125' ry='13' stroke-opacity='.52'/></g>
          <path d='M0 350h720M90 367h540M180 384h360' stroke='#7b1229' stroke-opacity='.5'/>
          <g fill='#ff4c65'><circle cx='147' cy='332' r='3'/><circle cx='573' cy='332' r='3'/><circle cx='220' cy='344' r='2'/><circle cx='500' cy='344' r='2'/></g>
        </svg>
        <div class='brain3d-rotor'><canvas class='neural-mesh-canvas' data-face='front' aria-hidden='true'></canvas><canvas class='neural-mesh-canvas' data-face='back' aria-hidden='true'></canvas></div>
        <div class='brain3d-orbit' aria-hidden='true'><svg viewBox='0 0 720 420'><ellipse cx='360' cy='181' rx='252' ry='153' fill='none' stroke='#ff3357' stroke-opacity='.26' stroke-width='1.2' stroke-dasharray='2 9'/><circle cx='612' cy='181' r='8' fill='#240914' stroke='#ff778b' stroke-width='1.5'/><circle cx='612' cy='181' r='3.8' fill='#fff0f3' style='filter:drop-shadow(0 0 8px #ff254d)'/><circle cx='108' cy='181' r='2.7' fill='#ff536d'/></svg></div>
        <div class='brain3d-anatomy' aria-hidden='true'><svg viewBox='0 0 720 420'><g><path d='M74 151h82l82 24'/><circle cx='238' cy='175' r='2.5'/><text x='74' y='143'>FRONTAL LOBE</text><path d='M646 128h-76l-64 27'/><circle cx='506' cy='155' r='2.5'/><text x='548' y='119'>CORTEX</text><path d='M649 257h-88l-91-34'/><circle cx='470' cy='223' r='2.5'/><text x='561' y='249'>CEREBELLUM</text></g></svg></div>
        <div class='neural-scan'></div>
        <div class='brain3d-readout left'>NEURAL CORE &middot; ACTIVE VISUAL</div>
        <div class='brain3d-readout right'>360&deg; ORBIT</div>
        <div class='brain3d-caption'>Red neural mesh &middot; local visual display</div>
      </div>
      <script>
      (() => {
        const stage = document.currentScript.previousElementSibling;
        const canvas = stage && stage.querySelector('.neural-mesh-canvas[data-face="front"]');
        const backCanvas = stage && stage.querySelector('.neural-mesh-canvas[data-face="back"]');
        const ctx = canvas && canvas.getContext('2d');
        const backCtx = backCanvas && backCanvas.getContext('2d');
        if (!stage || !canvas || !ctx) return;

        const cerebrum = new Path2D();
        cerebrum.moveTo(98, 183);
        cerebrum.bezierCurveTo(95, 165, 103, 149, 120, 139);
        cerebrum.bezierCurveTo(112, 122, 125, 105, 146, 102);
        cerebrum.bezierCurveTo(152, 82, 174, 73, 194, 81);
        cerebrum.bezierCurveTo(210, 62, 234, 61, 251, 76);
        cerebrum.bezierCurveTo(269, 59, 293, 62, 308, 79);
        cerebrum.bezierCurveTo(327, 65, 352, 71, 365, 89);
        cerebrum.bezierCurveTo(386, 77, 409, 89, 414, 109);
        cerebrum.bezierCurveTo(435, 110, 449, 126, 443, 145);
        cerebrum.bezierCurveTo(460, 157, 460, 178, 446, 192);
        cerebrum.bezierCurveTo(455, 211, 441, 228, 420, 233);
        cerebrum.bezierCurveTo(406, 250, 383, 255, 363, 247);
        cerebrum.bezierCurveTo(347, 258, 326, 252, 312, 240);
        cerebrum.bezierCurveTo(315, 257, 324, 273, 330, 287);
        cerebrum.bezierCurveTo(333, 296, 340, 301, 346, 296);
        cerebrum.bezierCurveTo(353, 291, 348, 280, 345, 269);
        cerebrum.bezierCurveTo(342, 259, 343, 251, 348, 245);
        cerebrum.bezierCurveTo(329, 261, 304, 260, 286, 247);
        cerebrum.bezierCurveTo(267, 261, 240, 258, 225, 239);
        cerebrum.bezierCurveTo(203, 250, 179, 241, 171, 221);
        cerebrum.bezierCurveTo(149, 228, 129, 215, 128, 196);
        cerebrum.bezierCurveTo(114, 199, 102, 193, 98, 183);
        cerebrum.closePath();
        const brainPath = cerebrum;
        const folds = new Path2D();
        folds.moveTo(138, 145); folds.bezierCurveTo(154, 125, 180, 126, 191, 142); folds.bezierCurveTo(202, 157, 186, 169, 170, 166);
        folds.moveTo(180, 101); folds.bezierCurveTo(168, 115, 176, 130, 192, 135); folds.bezierCurveTo(210, 141, 218, 155, 211, 171);
        folds.moveTo(224, 84); folds.bezierCurveTo(211, 98, 217, 113, 234, 119); folds.bezierCurveTo(249, 125, 255, 139, 247, 152);
        folds.moveTo(274, 82); folds.bezierCurveTo(259, 98, 266, 113, 284, 120); folds.bezierCurveTo(300, 127, 304, 142, 294, 156);
        folds.moveTo(326, 92); folds.bezierCurveTo(313, 108, 321, 120, 338, 126); folds.bezierCurveTo(356, 132, 361, 147, 350, 162);
        folds.moveTo(385, 110); folds.bezierCurveTo(372, 124, 379, 139, 396, 144); folds.bezierCurveTo(412, 149, 416, 163, 408, 177);
        folds.moveTo(166, 193); folds.bezierCurveTo(182, 179, 201, 184, 211, 198); folds.bezierCurveTo(220, 211, 236, 215, 249, 204);
        folds.moveTo(257, 187); folds.bezierCurveTo(269, 171, 291, 171, 303, 185); folds.bezierCurveTo(314, 198, 330, 202, 343, 190);
        folds.moveTo(356, 207); folds.bezierCurveTo(373, 192, 394, 193, 405, 207); folds.bezierCurveTo(414, 218, 425, 219, 435, 212);
        const cerebellum = new Path2D();
        cerebellum.moveTo(365, 212);
        cerebellum.bezierCurveTo(381, 198, 407, 202, 421, 218);
        cerebellum.bezierCurveTo(434, 232, 426, 245, 411, 248);
        cerebellum.bezierCurveTo(393, 251, 376, 236, 365, 212);
        cerebellum.closePath();
        const cerebellumFolia = new Path2D();
        cerebellumFolia.moveTo(371, 216); cerebellumFolia.bezierCurveTo(386, 208, 405, 211, 422, 224);
        cerebellumFolia.moveTo(374, 223); cerebellumFolia.bezierCurveTo(390, 215, 408, 219, 426, 231);
        cerebellumFolia.moveTo(379, 231); cerebellumFolia.bezierCurveTo(395, 223, 410, 229, 421, 238);
        const sulci = new Path2D();
        sulci.moveTo(139, 178); sulci.bezierCurveTo(171, 158, 207, 159, 237, 172); sulci.bezierCurveTo(257, 180, 272, 180, 285, 172);
        sulci.moveTo(296, 96); sulci.bezierCurveTo(282, 121, 289, 145, 300, 163); sulci.bezierCurveTo(309, 177, 308, 192, 297, 204);
        const random = (() => {
          let seed = 0x51ad0;
          return () => {
            seed = (seed * 1664525 + 1013904223) >>> 0;
            return seed / 4294967296;
          };
        })();
        const nodes = [];
        let attempts = 0;
        while (nodes.length < 245 && attempts < 14000) {
          attempts++;
          const x = 98 + random() * 365;
          const y = 76 + random() * 220;
          if (ctx.isPointInPath(brainPath, x, y)) nodes.push({ x, y, phase: random() * Math.PI * 2, size: 0.7 + random() * 0.8 });
        }
        const edges = [];
        const edgeKeys = new Set();
        nodes.forEach((node, index) => {
          const nearest = [];
          for (let other = 0; other < nodes.length; other++) {
            if (other === index) continue;
            const dx = node.x - nodes[other].x, dy = node.y - nodes[other].y;
            const distance = dx * dx + dy * dy;
            if (distance < 74 * 74) nearest.push({ other, distance });
          }
          nearest.sort((a, b) => a.distance - b.distance);
          nearest.slice(0, 5).forEach(({ other }) => {
            const key = index < other ? `${index}:${other}` : `${other}:${index}`;
            if (!edgeKeys.has(key)) { edgeKeys.add(key); edges.push([index, other]); }
          });
        });



        let width = 1, height = 1, scaleX = 1, scaleY = 1, offsetX = 0, offsetY = 0;
        const resize = () => {
          const bounds = stage.getBoundingClientRect();
          width = Math.max(1, bounds.width);
          height = Math.max(1, bounds.height);
          const dpr = Math.min(window.devicePixelRatio || 1, 2);
          canvas.width = Math.round(width * dpr);
          canvas.height = Math.round(height * dpr);
          ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
          if (backCanvas && backCtx) {
            backCanvas.width = canvas.width;
            backCanvas.height = canvas.height;
          }
          const fitScale = Math.min(width * 0.96 / 500, height * 0.98 / 320);
          scaleX = fitScale * 0.65;
          scaleY = fitScale * 0.79;
          offsetX = (width - 500 * scaleX) / 2 - 18 * scaleX;
          offsetY = (height - 320 * scaleY) / 2 - 17 * scaleY;
        };
        if (window.ResizeObserver) new ResizeObserver(resize).observe(stage);
        else window.addEventListener('resize', resize);
        resize();

        const draw = timestamp => {
          const time = timestamp / 1000;
          ctx.clearRect(0, 0, width, height);
          ctx.save();
          ctx.translate(offsetX, offsetY);
          ctx.scale(scaleX, scaleY);
          ctx.save();
          ctx.clip(brainPath);
          const tissue = ctx.createLinearGradient(120, 68, 410, 298);
          tissue.addColorStop(0, 'rgba(151, 24, 55, 0.88)');
          tissue.addColorStop(0.42, 'rgba(78, 12, 32, 0.94)');
          tissue.addColorStop(0.72, 'rgba(41, 8, 23, 0.94)');
          tissue.addColorStop(1, 'rgba(125, 15, 43, 0.85)');
          ctx.fillStyle = tissue;
          ctx.fillRect(75, 60, 410, 270);

          const tissueLight = ctx.createRadialGradient(236, 126, 10, 244, 150, 202);
          tissueLight.addColorStop(0, 'rgba(255, 108, 139, 0.38)');
          tissueLight.addColorStop(0.55, 'rgba(205, 34, 70, 0.14)');
          tissueLight.addColorStop(1, 'rgba(76, 8, 28, 0.04)');
          ctx.fillStyle = tissueLight;
          ctx.fillRect(75, 60, 410, 270);

          const cerebellumShade = ctx.createRadialGradient(390, 218, 5, 394, 225, 44);
          cerebellumShade.addColorStop(0, 'rgba(223, 48, 83, 0.40)');
          cerebellumShade.addColorStop(1, 'rgba(43, 6, 21, 0.64)');
          ctx.fillStyle = cerebellumShade;
          ctx.fill(cerebellum);
          ctx.strokeStyle = 'rgba(255, 130, 153, 0.28)';
          ctx.lineWidth = 1.35;
          ctx.stroke(cerebellumFolia);

          ctx.lineCap = 'round';
          ctx.lineJoin = 'round';
          ctx.strokeStyle = 'rgba(255, 111, 143, 0.26)';
          ctx.lineWidth = 2.2;
          ctx.shadowColor = 'rgba(255, 44, 82, 0.34)';
          ctx.shadowBlur = 4;
          ctx.stroke(folds);
          ctx.strokeStyle = 'rgba(48, 5, 21, 0.42)';
          ctx.lineWidth = 1.05;
          ctx.shadowBlur = 0;
          ctx.stroke(folds);
          ctx.strokeStyle = 'rgba(44, 5, 20, 0.56)';
          ctx.lineWidth = 2.25;
          ctx.stroke(sulci);

          const scanY = 70 + ((time * 55) % 260);
          const scan = ctx.createLinearGradient(80, scanY, 470, scanY);
          scan.addColorStop(0, 'rgba(255, 52, 83, 0)');
          scan.addColorStop(0.5, 'rgba(255, 110, 137, 0.36)');
          scan.addColorStop(1, 'rgba(255, 52, 83, 0)');
          ctx.fillStyle = scan;
          ctx.fillRect(80, scanY - 1.1, 390, 2.2);

          for (let index = 0; index < edges.length; index++) {
            const [a, b] = edges[index];
            const first = nodes[a], second = nodes[b];
            const pulse = 0.76 + 0.24 * Math.sin(time * 1.8 + first.phase + second.phase);
            const alpha = (0.46 + (index % 4 === 0 ? 0.28 : 0.08)) * pulse;
            ctx.strokeStyle = `rgba(255, ${Math.round(31 + pulse * 34)}, ${Math.round(50 + pulse * 52)}, ${alpha})`;
            ctx.lineWidth = index % 5 === 0 ? 1.55 : 1.12;
            ctx.shadowColor = 'rgba(255, 28, 65, 0.66)';
            ctx.shadowBlur = index % 8 === 0 ? 4.5 : 0;
            ctx.beginPath();
            ctx.moveTo(first.x, first.y);
            ctx.lineTo(second.x, second.y);
            ctx.stroke();
          }
          ctx.shadowBlur = 0;
          ctx.shadowColor = 'rgba(255, 33, 68, 0.95)';
          ctx.shadowBlur = 12;
          for (const node of nodes) {
            const pulse = 0.72 + 0.28 * Math.sin(time * 2.7 + node.phase);
            ctx.fillStyle = `rgba(255, ${Math.round(136 + pulse * 90)}, ${Math.round(148 + pulse * 96)}, ${0.64 + pulse * 0.34})`;
            ctx.beginPath();
            ctx.arc(node.x, node.y, node.size * (0.82 + pulse * 0.44), 0, Math.PI * 2);
            ctx.fill();
          }
          ctx.restore();

          ctx.shadowColor = 'rgba(255, 26, 63, 0.9)';
          ctx.shadowBlur = 18;
          ctx.strokeStyle = 'rgba(255, 73, 104, 0.86)';
          ctx.lineWidth = 2.8;
          ctx.stroke(brainPath);
          ctx.strokeStyle = 'rgba(255, 166, 181, 0.56)';
          ctx.lineWidth = 0.85;
          ctx.shadowBlur = 2;
          ctx.stroke(brainPath);
          ctx.restore();
          if (backCtx && backCanvas) {
            backCtx.setTransform(1, 0, 0, 1, 0, 0);
            backCtx.clearRect(0, 0, backCanvas.width, backCanvas.height);
            backCtx.drawImage(canvas, 0, 0);
          }
          window.requestAnimationFrame(draw);
        };
        window.requestAnimationFrame(draw);
      })();
      </script>
    """

def make_math_question(level):
    if level == "Beginner":
        kind = random.choice(["add", "subtract", "multiply"])
        if kind == "add":
            a, b = random.randint(10, 99), random.randint(10, 99)
            return f"{a} + {b} = ?", a + b
        if kind == "subtract":
            a, b = sorted([random.randint(10, 99), random.randint(10, 99)], reverse=True)
            return f"{a} − {b} = ?", a - b
        a, b = random.randint(2, 12), random.randint(2, 12)
        return f"{a} × {b} = ?", a * b
    if level == "Intermediate":
        kind = random.choice(["add", "multiply", "divide", "percent"])
        if kind == "add":
            a, b = random.randint(100, 999), random.randint(100, 999)
            return f"{a} + {b} = ?", a + b
        if kind == "multiply":
            a, b = random.randint(12, 35), random.randint(3, 18)
            return f"{a} × {b} = ?", a * b
        if kind == "divide":
            b, answer = random.randint(3, 15), random.randint(12, 60)
            return f"{b * answer} ÷ {b} = ?", answer
        percent, value = random.choice([10, 15, 20, 25, 30]), random.choice([80, 120, 160, 200, 240, 400])
        return f"{percent}% of {value} = ?", percent * value // 100
    kind = random.choice(["multiply", "divide", "percent", "square"])
    if kind == "multiply":
        a, b = random.randint(24, 89), random.randint(12, 39)
        return f"{a} × {b} = ?", a * b
    if kind == "divide":
        b, answer = random.randint(12, 36), random.randint(18, 85)
        return f"{b * answer} ÷ {b} = ?", answer
    if kind == "percent":
        percent, value = random.choice([12, 15, 18, 22, 35, 40]), random.choice([150, 200, 250, 300, 400, 500])
        return f"{percent}% of {value} = ?", percent * value // 100
    a = random.randint(12, 35)
    return f"{a}² = ?", a * a

def show_math_summary():
    score = sum(x["correct"] for x in st.session_state.math_answers)
    math_duration = st.session_state.get("math_duration", 60)
    _save_attempt("math", "Math Speed", "maths", st.session_state.math_level, score, max(1, len(st.session_state.math_answers)), score * 10, {"duration_setting": math_duration, "question_count": len(st.session_state.math_answers)})
    record_high_score(st.session_state.get("math_player", "Player"), "Math Speed", f"{st.session_state.math_level} | {math_duration}s", round(100*score/max(1,len(st.session_state.math_answers))), "accuracy %")
    st.session_state.math_best_score = max(st.session_state.get("math_best_score", 0), score)
    xp = score * 10
    st.markdown("### Sprint complete · your mind is warming up")
    a, b, c = st.columns(3)
    a.metric("Correct", f"{score} / {len(st.session_state.math_answers)}")
    b.metric("XP earned", f"+{xp}")
    c.metric("Personal best", f"{st.session_state.math_best_score} correct")
    st.markdown("<p class='tip'>Build a personal best by repeating the same level. Short, focused rounds help you practice speed while keeping accuracy in view.</p>", unsafe_allow_html=True)
    with st.expander("Review this round"):
        for item in st.session_state.math_answers:
            st.markdown(f"**{item['question']}** Your answer: {item['response']} · {'✓' if item['correct'] else 'Answer: ' + str(item['answer'])}")
    if st.button("Run it back →"):
        st.session_state.math_done = False
        st.rerun()

@st.fragment(run_every="1s")
def math_round():
    if not st.session_state.get("math_active", False):
        if st.session_state.get("math_done", False):
            show_math_summary()
        return
    items = st.session_state.math_items
    index = st.session_state.math_index
    remaining = max(0, int(st.session_state.math_deadline - time.time() + 0.999))
    if remaining == 0 or index >= len(items):
        st.session_state.math_active = False
        st.session_state.math_done = True
        st.rerun()
        return
    st.progress(min(1.0, index / len(items)), text=f"Problem {min(index + 1, len(items))} of {len(items)} · {st.session_state.math_level}")
    st.metric("TIME REMAINING", f"{remaining}s", "Keep a steady rhythm")
    if st.session_state.get("math_last_result"):
        prior = st.session_state.math_last_result
        st.success(f"Nice! +10 XP · {prior['question']} = {prior['answer']}" if prior["correct"] else f"Answer: {prior['answer']} · reset, refocus, keep going")
    if st.session_state.get("math_active"):
        question, expected = items[index]
        st.markdown(f"<div class='panel'><div class='section-label'>QUICK THINK · NO CALCULATOR</div><h3>{question}</h3><p class='tip'>Trust your working memory. Accuracy first, speed follows.</p></div>", unsafe_allow_html=True)
        response = st.text_input("YOUR ANSWER", placeholder="Type the number here…", key=f"math_answer_{index}")
        submitted = st.button("Lock in · next problem →", type="primary", key=f"math_submit_{index}")
        if submitted:
            if time.time() >= st.session_state.math_deadline:
                st.session_state.math_active, st.session_state.math_done = False, True
            elif not response.strip() or not response.strip().lstrip("-+").isdigit():
                st.warning("Enter a whole-number answer to keep your round moving.")
                return
            else:
                is_correct = int(response.strip()) == expected
                st.session_state.math_answers.append({"question": question, "answer": expected, "response": response.strip(), "correct": is_correct})
                if is_correct: st.session_state.xp_bank += 10
                st.session_state.math_last_result = {"question": question, "answer": expected, "correct": is_correct}
                st.session_state.math_index += 1
                if st.session_state.math_index >= len(items):
                    st.session_state.math_active, st.session_state.math_done = False, True
            st.rerun()
    if st.session_state.get("math_done", False):
        show_math_summary()

def prepare_memory_round():
    mode, level = st.session_state.memory_mode, st.session_state.memory_level
    offset = st.session_state.memory_round - 1
    config = MEMORY_GAMES[mode]
    st.session_state.memory_stage = "show"
    st.session_state.memory_deadline = time.time() + config["seconds"][level]
    if mode == "Sequence Memory":
        length = config["base"][level] + offset
        st.session_state.memory_sequence = [str(random.randint(0,9)) for _ in range(length)]
    elif mode == "Number Recall":
        length = config["base"][level] + offset
        st.session_state.memory_number = str(random.randint(10**(length-1),10**length-1))
    elif mode == "Object Memory":
        targets = random.sample(MEMORY_OBJECTS, config["base"][level])
        extras = random.sample([x for x in MEMORY_OBJECTS if x not in targets], 4)
        st.session_state.memory_targets = targets
        st.session_state.memory_options = random.sample(targets + extras, len(targets)+4)


def finish_memory_game():
    st.session_state.memory_active = False
    st.session_state.memory_done = True
    if not st.session_state.get("memory_counted",False):
        st.session_state.memory_sessions = st.session_state.get("memory_sessions",0)+1
        st.session_state.memory_counted = True
        if st.session_state.memory_mode == "Card Match":
            total = MEMORY_GAMES[st.session_state.memory_mode]["pairs"][st.session_state.memory_level]
        elif st.session_state.memory_mode == "Object Memory":
            total = len(st.session_state.memory_targets)
        else:
            total = 5
        st.session_state.memory_summary = {"game":st.session_state.memory_mode,"level":st.session_state.memory_level,"score":st.session_state.memory_score,"total":total}


def show_memory_summary():
    mode, level, score = st.session_state.memory_mode, st.session_state.memory_level, st.session_state.memory_score
    memory_total = max(1, int(st.session_state.get("memory_summary", {}).get("total", 5)))
    memory_xp = score * 5 if mode == "Object Memory" else score * 10
    _save_attempt("memory", f"Memory | {mode}", "memory", level, score, memory_total, memory_xp, {"game": mode, "moves": st.session_state.get("memory_moves")})
    st.markdown(f"### {mode} complete")
    a,b,c=st.columns(3)
    if mode=="Card Match":
        a.metric("Pairs found",f"{score} / {MEMORY_GAMES[mode]['pairs'][level]}"); b.metric("Moves",st.session_state.memory_moves); c.metric("XP earned",f"+{score*10}")
    elif mode=="Object Memory":
        a.metric("Objects remembered",f"{score} / {len(st.session_state.memory_targets)}"); b.metric("Level",level); c.metric("XP earned",f"+{score*5}")
    else:
        a.metric("Rounds cleared",f"{st.session_state.memory_cleared_rounds} / 5"); b.metric("Level",level); c.metric("XP earned",f"+{score*10}")
    st.markdown("<p class='tip'>Memory grows through focused practice. Take a breath, then try another game or level.</p>",unsafe_allow_html=True)
    if st.button("Play again",key="memory_play_again"):
        st.session_state.memory_done=False
        st.rerun()


@st.fragment(run_every="1s")
def memory_game():
    if not st.session_state.get("memory_active",False):
        if st.session_state.get("memory_done",False): show_memory_summary()
        return
    mode,level=st.session_state.memory_mode,st.session_state.memory_level
    if mode=="Card Match":
        cards=st.session_state.memory_cards; selected=st.session_state.memory_selected; matched=st.session_state.memory_matched
        st.progress(len(matched)/len(cards),text=f"Pairs found: {len(matched)//2} / {len(cards)//2} | Moves: {st.session_state.memory_moves}")
        if st.session_state.get("memory_feedback"): st.info(st.session_state.memory_feedback)
        if len(selected)==2 and selected[0] not in matched:
            st.warning("No match. Notice both positions, then flip them back.")
            if st.button("Flip cards back",key="memory_flip_back"):
                st.session_state.memory_selected=[]; st.session_state.memory_feedback=None; st.rerun()
        cols=st.columns(4)
        for i,symbol in enumerate(cards):
            label=symbol if i in matched or i in selected else chr(0x1F0A0)
            with cols[i%4]:
                if st.button(label,key=f"memory_card_{i}",use_container_width=True,disabled=i in matched or len(selected)==2):
                    st.session_state.memory_feedback=None
                    current=list(st.session_state.memory_selected)
                    if i not in current:
                        if not current: st.session_state.memory_selected=[i]
                        else:
                            first=current[0]; st.session_state.memory_moves+=1
                            if cards[first]==cards[i]:
                                st.session_state.memory_matched=sorted(set(matched+[first,i]))
                                st.session_state.memory_score+=1; st.session_state.xp_bank+=10
                                st.session_state.memory_selected=[]; st.session_state.memory_feedback="Pair found! +10 XP"
                                if len(st.session_state.memory_matched)==len(cards): finish_memory_game()
                            else: st.session_state.memory_selected=[first,i]
                    st.rerun()
        return
    if st.session_state.memory_stage=="show":
        remaining=max(0,int(st.session_state.memory_deadline-time.time()+.999))
        if remaining==0:
            st.session_state.memory_stage="recall"; st.rerun()
        st.progress((st.session_state.memory_round-1)/5,text=f"Round {st.session_state.memory_round} of 5 | {level}")
        st.metric("MEMORIZE",f"{remaining}s","Look carefully")
        if mode=="Sequence Memory": shown="  |  ".join(st.session_state.memory_sequence)
        elif mode=="Number Recall": shown=st.session_state.memory_number
        else: shown="   ".join(f"{emoji} {name}" for name,emoji in st.session_state.memory_targets)
        st.markdown(f"<div class='panel' style='text-align:center'><div class='section-label'>{mode}</div><h1 style='letter-spacing:.16em'>{shown}</h1><p class='tip'>{MEMORY_GAMES[mode]['description']}</p></div>",unsafe_allow_html=True)
        st.caption("The display hides automatically when the timer ends.")
        return
    if mode in ("Sequence Memory","Number Recall"):
        st.progress((st.session_state.memory_round-1)/5,text=f"Round {st.session_state.memory_round} of 5 | {level}")
        prompt="Type the digits in the same order." if mode=="Sequence Memory" else "Type the complete number."
        st.markdown(f"<div class='panel'><div class='section-label'>RECALL ROUND {st.session_state.memory_round}</div><h3>{prompt}</h3></div>",unsafe_allow_html=True)
        response=st.text_input("YOUR RECALL",placeholder="Type your answer here...",key=f"memory_recall_{st.session_state.memory_round}")
        if st.button("Check memory",type="primary",key=f"memory_check_{st.session_state.memory_round}"):
            expected="".join(st.session_state.memory_sequence) if mode=="Sequence Memory" else st.session_state.memory_number
            clean=response.replace(" ","").replace(",","").replace("-","")
            if clean==expected:
                st.session_state.memory_score+=1; st.session_state.memory_cleared_rounds=st.session_state.memory_round; st.session_state.xp_bank+=10
                st.session_state.memory_feedback="Perfect recall! +10 XP"
                if st.session_state.memory_round>=5: finish_memory_game()
                else: st.session_state.memory_round+=1; prepare_memory_round()
            else:
                st.session_state.memory_feedback=f"The answer was {expected}. You cleared {st.session_state.memory_cleared_rounds} rounds."; finish_memory_game()
            st.rerun()
        if st.session_state.get("memory_feedback"): st.caption(st.session_state.memory_feedback)
        return
    if mode=="Object Memory":
        st.markdown(f"<div class='panel'><div class='section-label'>OBJECT RECALL | {level.upper()}</div><h3>Which objects were in your snapshot?</h3></div>",unsafe_allow_html=True)
        labels=[f"{emoji} {name}" for name,emoji in st.session_state.memory_options]
        chosen=st.multiselect("Select every object you remember",labels,key="memory_object_choices")
        if st.button("Check objects",type="primary",key="memory_object_check"):
            targets={f"{emoji} {name}" for name,emoji in st.session_state.memory_targets}
            score=len(set(chosen)&targets); st.session_state.memory_score=score; st.session_state.xp_bank+=score*5
            finish_memory_game(); st.rerun()


def _make_boss_stages(level, role):
    logic = random.choice(LOGIC_LEVELS[level])
    verbal_category = random.choice(list(VERBAL_BANK))
    verbal = random.choice(VERBAL_BANK[verbal_category][level])
    interview = random.choice(QUESTION_BANK[role][level])
    math_question, math_answer = make_math_question(level)
    return [
        {"name": "Logic Trial", "skill": "logic", "type": "choice", "question": logic["q"], "choices": logic["c"], "answer": logic["a"], "explanation": logic["e"]},
        {"name": "Math Sprint", "skill": "maths", "type": "number", "question": math_question, "answer": math_answer, "explanation": f"The exact answer is {math_answer}."},
        {"name": "Verbal Signal", "skill": "verbal", "type": "choice", "question": verbal[0], "choices": verbal[1], "answer": verbal[2], "explanation": verbal[3]},
        {"name": "Interview Finale", "skill": "interview", "type": "text", "question": interview[0], "keywords": interview[1], "explanation": "A strong response names the key idea and supports it with a specific example."},
    ]


if page == "Home":
    home_attempts = _active_attempts()
    home_profile = build_skill_profile(home_attempts)
    home_missions = mission_snapshot(home_attempts)
    home_rank = rank_for_xp(st.session_state.xp_bank)
    home_daily = home_missions["missions"][0]
    safe_name = html_escape(str(st.session_state.active_profile_name))
    xp_percent = home_rank["progress"] * 100
    measured_skills = sum(item["accuracy"] is not None for item in home_profile.values())
    observed_accuracies = [item["accuracy"] for item in home_profile.values() if item["accuracy"] is not None]
    observed_accuracy = round(sum(observed_accuracies) / len(observed_accuracies)) if observed_accuracies else None

    st.markdown("<div class='hud-kicker'>NEURAL COMMAND CENTER &middot; STUDENT PROFILE</div>", unsafe_allow_html=True)
    top_left, top_middle, top_right = st.columns([1.02, 1.35, .92], gap="medium")
    with top_left:
        st.markdown(f"<div class='hud-card dashboard-welcome'><div class='hud-kicker'>WELCOME BACK, {safe_name.upper()}</div><div class='welcome-title'>Ready to level up<br>your <span class='welcome-name'>mind?</span></div><div class='hud-muted'>Your next skill milestone starts with one focused round.</div><div class='welcome-xp'><b>{home_rank['name']} &middot; {home_rank['xp']:,} XP</b><span>{home_rank['next_xp']:,} XP to {home_rank['next_rank']}</span></div><div class='xp-track'><span style='width:{xp_percent:.1f}%'></span></div><div class='welcome-stats'><div class='welcome-stat'><small>Daily streak</small><b>&#10022; {home_missions['current_streak']} days</b></div><div class='welcome-stat'><small>Saved rounds</small><b>{len(home_attempts):,}</b></div><div class='welcome-stat'><small>Skill DNA</small><b>{measured_skills} / 6 areas</b></div></div></div>", unsafe_allow_html=True)
    with top_middle:
        neural_frame = getattr(st, "iframe", None)
        if neural_frame is not None:
            neural_frame(neural_hero_svg(), height=350, alt="Rotating 3D neural brain display")
        else:
            st.components.v1.html(neural_hero_svg(), height=350, scrolling=False)
    with top_right:
        with st.container(border=True):
            st.markdown("<div class='section-heading' style='margin:.1rem 0 .75rem'><div><h2>Quick access</h2><p>Choose your next move</p></div></div>", unsafe_allow_html=True)
            quick_links = [
                ("START PRACTICE", "Choose an arena", "IQ teller & logic"),
                ("SHADOW COACH", "Open your skill plan", "Skill DNA & Shadow Coach"),
                ("VIEW REPORTS", "Track saved progress", "Performance Intelligence"),
            ]
            for index, (label, description, target) in enumerate(quick_links):
                st.button(f"{label}   >", key=f"quick_access_{index}", use_container_width=True, on_click=navigate, args=(target,))
                st.caption(description)

    arena_items = [
        ("Interview", "Ace your interviews", "Interview practice", "rgba(255,55,77,.27)", "#ff6979", "CAREER READINESS"),
        ("Logic & IQ", "Think. Solve. Win.", "IQ teller & logic", "rgba(69,148,255,.3)", "#69adff", "PATTERN RECOGNITION"),
        ("Maths", "Speed & accuracy", "Math speed arena", "rgba(255,55,77,.27)", "#ff6979", "NUMERICAL REASONING"),
        ("Memory", "Remember more", "Memory games", "rgba(166,95,255,.3)", "#bd91ff", "RECALL TRAINING"),
        ("Focus", "Stay sharp", "Focus arena", "rgba(255,174,76,.3)", "#ffc071", "ATTENTION CONTROL"),
        ("Verbal", "Communicate better", "Verbal arena", "rgba(55,203,188,.27)", "#6ce0d2", "LANGUAGE SKILLS"),
    ]
    arena_symbols = {
        "Interview": "<svg viewBox='0 0 40 40' aria-hidden='true'><rect x='15' y='5' width='10' height='20' rx='5'/><path d='M10 19a10 10 0 0 0 20 0M20 29v6m-6 0h12'/></svg>",
        "Logic & IQ": "<svg viewBox='0 0 40 40' aria-hidden='true'><path d='M20 6c-4-4-11-1-11 5-5 2-6 8-2 11-2 5 2 10 7 9 2 4 7 4 10 1 5 1 9-4 7-8 4-4 2-9-2-11 0-5-5-9-9-7Z'/><path d='M20 8v23m-7-17c4 1 5 3 5 6m9-5c-4 1-5 3-5 6m-10 4c3-1 5 0 6 2m9-2c-3-1-5 0-6 2'/></svg>",
        "Maths": "<svg viewBox='0 0 40 40' aria-hidden='true'><path d='M11 9h19L15 31h18M14 5h13M13 35h14'/><circle cx='29' cy='10' r='1.5'/></svg>",
        "Memory": "<svg viewBox='0 0 40 40' aria-hidden='true'><path d='m20 5 14 8v15l-14 8-14-8V13Z'/><path d='m6 13 14 8 14-8M20 21v15m-7-27 14 8'/><circle cx='20' cy='21' r='2.2'/></svg>",
        "Focus": "<svg viewBox='0 0 40 40' aria-hidden='true'><circle cx='20' cy='20' r='14'/><circle cx='20' cy='20' r='7'/><circle cx='20' cy='20' r='1.5'/><path d='M20 3v4m0 26v4M3 20h4m26 0h4'/></svg>",
        "Verbal": "<svg viewBox='0 0 40 40' aria-hidden='true'><path d='M7 8h21a6 6 0 0 1 6 6v8a6 6 0 0 1-6 6h-8l-8 6v-6H7a6 6 0 0 1-6-6v-8a6 6 0 0 1 6-6Z'/><path d='M11 18h2m5 0h2m5 0h2'/></svg>",
    }
    st.markdown("<div class='section-heading'><div><h2>Practice arenas</h2><p>Sharpen different skills. Build your future.</p></div><span class='hud-kicker'>06 MODULES</span></div>", unsafe_allow_html=True)
    for row_start in range(0, len(arena_items), 3):
        arena_columns = st.columns(3, gap="medium")
        for arena_index, (col, item) in enumerate(zip(arena_columns, arena_items[row_start:row_start + 3]), start=row_start + 1):
            title, subtitle, target, glow, ink, category = item
            with col:
                st.markdown(f"<div class='arena-tile' data-arena='{arena_index:02d}'><div class='arena-art' style='--arena-glow:{glow};--arena-stroke:{ink}66;--arena-ink:{ink}'><div class='arena-art-kicker'>ARENA {arena_index:02d}</div><div class='arena-symbol'>{arena_symbols[title]}</div><div class='arena-art-index'>{arena_index:02d}</div></div><div class='arena-card-kicker'>{category}</div><h3>{html_escape(title)}</h3><p>{html_escape(subtitle)}</p></div>", unsafe_allow_html=True)
                st.button("Launch arena >", key=f"launch_arena_{target}", use_container_width=True, on_click=navigate, args=(target,))

    st.markdown("<div class='section-heading'><div><h2>Skill profile &amp; live progress</h2><p>Personal signals drawn from this profile&#39;s saved practice.</p></div></div>", unsafe_allow_html=True)
    dna_col, mission_col, leader_col, story_col = st.columns([1.0, 1.0, 1.05, 1.18], gap="medium")
    with dna_col:
        dna_accuracy = (f"<div class='dna-observed'><span>Observed accuracy</span><strong>{observed_accuracy}%</strong></div><div class='dna-track'><span style='width:{observed_accuracy}%'></span></div>" if observed_accuracy is not None else "<div class='mini-empty'>Complete a saved round to reveal measured skill progress.</div>")
        st.html(f"<div class='hud-card dashboard-dna'><div class='hud-kicker'>SIX-AREA PROFILE &middot; {measured_skills}/6 MEASURED</div><div class='mini-mission-title'>Your Skill DNA</div>{skill_radar_svg(home_profile)}{dna_accuracy}</div>")
        st.button("Explore Skill DNA >", key="home_open_dna", use_container_width=True, on_click=navigate, args=("Skill DNA & Shadow Coach",))
    with mission_col:
        claim_key = (home_daily["key"], home_daily["period"])
        is_claimed = claim_key in list_mission_claims(int(st.session_state.active_user_id), DB_PATH)
        pct = min(100, round(home_daily["progress"] * 100 / home_daily["goal"]))
        st.markdown(f"<div class='hud-card dashboard-lower'><div class='hud-kicker'>&#10022; TODAY'S MISSION</div><div class='mini-mission-title'>{home_daily['title']}</div><div class='hud-muted'>{home_daily['description']}</div><div class='welcome-xp'><span>Progress &middot; {home_daily['progress']} / {home_daily['goal']}</span><b>+{home_daily['xp']} XP</b></div><div class='xp-track'><span style='width:{pct}%'></span></div><p class='hud-muted'>{'Reward claimed for today.' if is_claimed else 'Complete real practice rounds to unlock the reward.'}</p></div>", unsafe_allow_html=True)
        if home_daily["ready"] and not is_claimed:
            if st.button(f"Claim daily reward - +{home_daily['xp']} XP", key="home_claim_daily", use_container_width=True):
                if claim_mission(int(st.session_state.active_user_id), home_daily["key"], home_daily["period"], home_daily["xp"], DB_PATH):
                    st.session_state.xp_bank = get_user_xp(int(st.session_state.active_user_id), DB_PATH)
                st.rerun()
        st.button("Open all missions >", key="home_open_missions", use_container_width=True, on_click=navigate, args=("Shadow Missions",))
    with leader_col:
        board = load_high_scores()[:4]
        if board:
            board_rows = []
            for index, row in enumerate(board, 1):
                player_text = html_escape(str(row["player"]))
                arena_text = html_escape(str(row["arena"]))
                board_rows.append(f"<div class='mini-leader-row'><span class='mini-leader-rank'>#{index:02d}</span><span>{player_text}<small style='display:block;color:#7f8da1'>{arena_text}</small></span><span class='mini-leader-score'>{row['score']:g} {html_escape(str(row['unit']))}</span></div>")
            board_content = "".join(board_rows)
        else:
            board_content = "<div class='mini-empty'>No saved scores yet. Complete a Math, Verbal, or Focus round to create a real personal best.</div>"
        st.markdown(f"<div class='hud-card dashboard-lower'><div class='hud-kicker'>LOCAL LEADERBOARD</div><div class='mini-mission-title'>Personal bests</div><div class='hud-muted'>Saved arena scores from this device</div>{board_content}</div>", unsafe_allow_html=True)
        st.button("Open leaderboard >", key="home_open_leaderboard", use_container_width=True, on_click=navigate, args=("High scores",))
    with story_col:
        home_quote, home_author = st.session_state.quote
        quote_svg = """<svg viewBox='0 0 560 240' preserveAspectRatio='xMidYMid slice' aria-hidden='true'><defs><linearGradient id='sky' x1='0' y1='0' x2='0' y2='1'><stop stop-color='#293554'/><stop offset='.52' stop-color='#b25266'/><stop offset='1' stop-color='#111827'/></linearGradient><linearGradient id='cityGlow' x1='0' y1='0' x2='1' y2='1'><stop stop-color='#ffc1a0'/><stop offset='1' stop-color='#6077a0'/></linearGradient></defs><rect width='560' height='240' fill='url(#sky)'/><circle cx='396' cy='72' r='43' fill='#ffb58f' opacity='.32'/><path d='M0 153 74 114l51 28 72-56 62 59 54-38 66 44 76-71 105 64v96H0Z' fill='#171c2b' opacity='.76'/><g fill='#101723'><path d='M17 117h34v87H17zM59 93h48v111H59zM119 129h34v75h-34zM164 82h53v122h-53zM232 110h37v94h-37zM278 73h51v131h-51zM342 105h36v99h-36zM388 68h54v136h-54zM454 113h41v91h-41zM505 88h42v116h-42z'/></g><g fill='url(#cityGlow)' opacity='.52'><path d='M68 105h5v6h-5zm12 0h5v6h-5zm0 15h5v6h-5zm96-24h6v8h-6zm14 0h6v8h-6zm0 17h6v8h-6zm97-31h6v8h-6zm14 0h6v8h-6zm0 17h6v8h-6zm96-13h6v9h-6zm14 0h6v9h-6zm0 18h6v9h-6z'/></g><path d='M0 208c96-11 164-7 253 0 109 9 195-3 307-10v42H0Z' fill='#0a0e17'/><path d='M282 202c-11-10-13-27-8-39 4-10 2-17-1-24 15 4 22 17 19 30 8-5 11-13 10-21 13 12 12 32 4 43l15 12h-48z' fill='#070a10'/><path d='M0 221h560M83 208l-42 32m117-31 4 31m173-30 35 31m74-39 62 39' stroke='#7385a5' stroke-opacity='.25' fill='none'/><path d='M350 226h170' stroke='#ff6478' stroke-opacity='.6'/></svg>"""
        st.html(f"<div class='story-card'>{quote_svg}<div class='story-shade'></div><div class='story-copy'><span>FIELD NOTE</span><blockquote>&#8220;{html_escape(str(home_quote))}&#8221;</blockquote><small>&mdash; {html_escape(str(home_author))}</small></div></div>")
    st.markdown("<p class='hud-muted' style='margin-top:1.2rem'>Practice snapshots describe saved results in these activities; they are not standardized IQ, hiring, or diagnostic scores.</p>", unsafe_allow_html=True)

elif page == "Interview practice":
    st.markdown("<div class='section-label'>CAREER READY · INTERVIEW STUDIO</div>", unsafe_allow_html=True)
    if not st.session_state.get("interview_active", False):
        st.markdown("### Build your practice session")
        st.markdown("<p class='tip'>Choose your role and level. Each session includes 10 carefully selected questions.</p>", unsafe_allow_html=True)
        with st.container(border=True):
            a, b = st.columns(2)
            with a:
                name = st.text_input("Your name", placeholder="e.g. Alex Morgan", key="candidate_name")
                round_type = st.selectbox("Interview round", ["Role-based", "HR", "Technical"], key="interview_round_choice")
                role_options = TECHNICAL_ROLES if round_type == "Technical" else list(QUESTION_BANK)
                role = st.selectbox("Target role", role_options, key="candidate_role")
            with b:
                level_options = ["Beginner", "Intermediate", "Advanced"]
                adaptive = _adaptive_recommendation("interview", "Intermediate")
                level = st.selectbox("Difficulty", level_options, index=level_options.index(adaptive["level"]), key="candidate_level")
                st.caption(f"Adaptive suggestion: {adaptive['reason']}")
                st.markdown("<div class='tip'>💡 <b>Answer tip:</b> Use STAR for experience questions: Situation, Task, Action, Result. For technical questions, explain your reasoning and trade-offs.</div>", unsafe_allow_html=True)
            if st.button("Begin my session →", type="primary"):
                if not name.strip(): st.warning("Add your name to personalize your practice session.")
                else:
                    st.session_state.interview_name = name.strip()
                    st.session_state.interview_role, st.session_state.interview_level = role, level
                    st.session_state.interview_round_type = round_type
                    pool = HR_INTERVIEW_BANK if round_type == "HR" else QUESTION_BANK[role][level]
                    st.session_state.interview_items = random.sample(pool, min(10, len(pool)))
                    st.session_state.interview_index, st.session_state.interview_results = 0, []
                    st.session_state.interview_active, st.session_state.interview_done = True, False
                    for state_key in list(st.session_state.keys()):
                        if str(state_key).startswith(("submitted_", "answer_", "ai_interview_feedback_")):
                            del st.session_state[state_key]
                    _begin_attempt("interview")
                    st.rerun()
    else:
        items, index = st.session_state.interview_items, st.session_state.interview_index
        question, keywords = items[index]
        st.markdown(f"### {st.session_state.interview_role} <span class='pill'>{st.session_state.interview_level}</span>", unsafe_allow_html=True)
        st.progress(index / len(items), text=f"Question {index + 1} of {len(items)}")
        st.markdown(f"<div class='panel'><div class='section-label'>QUESTION {index + 1:02d} · TAKE A BREATH, THEN BEGIN</div><h3>{question}</h3><p class='tip'>A clear structure and specific example can make a strong answer memorable.</p></div>", unsafe_allow_html=True)
        answer = st.text_area("YOUR ANSWER", key=f"answer_{index}", height=220, placeholder="Start typing here… Your answer is saved in this session. Explain the idea, why it matters, and a concrete example.")
        count = len(answer.strip().split())
        st.caption(f"{count} words · Aim for a clear, well-supported answer")
        if not st.session_state.get(f"submitted_{index}", False) and st.button("Submit answer →", type="primary"):
            if count < 5: st.warning("Write a little more so you have room to explain your thinking.")
            else:
                words = set(answer.lower().replace("/", " ").replace("-", " ").replace(",", " ").replace(".", " ").replace("?", " ").split())
                score = round(10 * sum(word.lower() in words for word in keywords) / len(keywords), 1)
                feedback = "Strong topic coverage. Add a concrete example to make it even more compelling." if score >= 7 else "A good start. Name key concepts and connect them with a brief example." if score >= 4 else "Keep going. Explain the main idea, then add a relevant detail or example."
                st.session_state.interview_results.append({"question": question, "answer": answer, "score": score, "feedback": feedback})
                st.session_state.xp_bank += 5
                st.session_state[f"submitted_{index}"] = True
                st.rerun()
        if st.session_state.get(f"submitted_{index}", False):
            result = st.session_state.interview_results[index]
            st.metric("Practice coverage", f"{result['score']}/10")
            st.write(result["feedback"])
            st.caption("This instant score checks selected topic words only. It is a reflection aid, not a judgment of correctness or hiring readiness.")
            if is_configured():
                st.caption(f"Model feedback is available through {configured_model()}. Your answer is sent only if you request it below.")
                if st.button("Request model feedback", key=f"ai_interview_{index}"):
                    prompt = f"Interview type: {st.session_state.get('interview_round_type', 'Role-based')}\nRole: {st.session_state.interview_role}\nLevel: {st.session_state.interview_level}\nQuestion: {result['question']}\nStudent answer: {result['answer'][:4000]}"
                    instructions = "Give concise interview practice feedback. Identify two specific strengths, one improvement, and one reflective follow-up question. Evaluate only the content provided; do not predict hiring outcomes, infer personal traits, or assign a readiness score."
                    try:
                        with st.spinner("Reviewing with the configured model…"):
                            st.session_state[f"ai_interview_feedback_{index}"] = generate_feedback(instructions, prompt)
                    except (AIConfigurationError, AIRequestError) as exc:
                        st.warning(str(exc))
                    st.rerun()
                if st.session_state.get(f"ai_interview_feedback_{index}"):
                    st.info(st.session_state[f"ai_interview_feedback_{index}"])
            else:
                st.caption("Model feedback is unavailable until OPENAI_API_KEY and OPENAI_MODEL are configured. Current feedback uses the offline keyword rubric.")
            if index + 1 < len(items):
                if st.button("Save & continue →"):
                    st.session_state.interview_index += 1; st.rerun()
            elif st.button("See my session summary →"):
                st.session_state.interview_active, st.session_state.interview_done = False, True; st.rerun()
        if st.button("End this session"):
            st.session_state.interview_active, st.session_state.interview_done = False, True; st.rerun()

    if st.session_state.get("interview_done", False) and st.session_state.get("interview_results"):
        results = st.session_state.interview_results
        average = sum(item["score"] for item in results) / len(results)
        _save_attempt("interview", f"Interview {st.session_state.get('interview_round_type', 'Role-based')} | {st.session_state.interview_role}", "interview", st.session_state.interview_level, average, 10, 5 * len(results), {"metric_name": "topic_coverage", "round_type": st.session_state.get("interview_round_type", "Role-based"), "role": st.session_state.interview_role, "question_count": len(results)})
        st.markdown("---")
        st.markdown("### Session complete — nice work, " + st.session_state.get("interview_name", "there") + "!")
        st.metric("Average topic coverage", f"{average:.1f}/10", f"{len(results)} answers practiced")
        st.markdown("<p class='tip'>Use this as a reflection prompt. Revisit an answer, add an example, and practice saying it aloud.</p>", unsafe_allow_html=True)
        for i, result in enumerate(results, 1):
            with st.expander(f"{i}. {result['question']} · {result['score']}/10"):
                st.markdown("**Your answer**"); st.write(result["answer"]); st.write(result["feedback"])
        if st.button("Practice another session"):
            st.session_state.interview_done = False; st.session_state.interview_results = []; st.rerun()

elif page == "IQ teller & logic":
    st.markdown("<div class='section-label'>THE IQ TELLER · LOGIC LAB</div>", unsafe_allow_html=True)
    st.markdown("### Find your reasoning rhythm")
    st.markdown("<p class='tip'>Pick a level, solve 10 short puzzles, and get a personalized practice snapshot. Think of the teller as a playful guide—not an actual IQ test.</p>", unsafe_allow_html=True)
    if not st.session_state.get("logic_active", False) and not st.session_state.get("logic_done", False):
        with st.container(border=True):
            logic_levels = list(LOGIC_LEVELS)
            adaptive = _adaptive_recommendation("logic", "Beginner")
            level = st.selectbox("Choose your challenge level", logic_levels, index=logic_levels.index(adaptive["level"]), key="logic_difficulty")
            st.caption(f"Adaptive suggestion: {adaptive['reason']}")
            descriptions = {"Beginner":"Build confidence with patterns, simple deductions, and everyday number sense.","Intermediate":"Stretch your pattern spotting, multi-step reasoning, and careful reading.","Advanced":"Take on probability, algebraic reasoning, and layered logic."}
            st.markdown(f"<p class='tip'>{descriptions[level]}</p>", unsafe_allow_html=True)
            if st.button("Start my reasoning round →", type="primary"):
                st.session_state.logic_items = random.sample(LOGIC_LEVELS[level], 10)
                st.session_state.logic_level = level
                st.session_state.logic_index, st.session_state.logic_answers = 0, []
                st.session_state.logic_active, st.session_state.logic_done = True, False
                _begin_attempt("logic")
                for key in list(st.session_state.keys()):
                    if str(key).startswith("logic_submitted_"): del st.session_state[key]
                st.rerun()
    elif st.session_state.get("logic_active", False):
        i = st.session_state.logic_index
        item = st.session_state.logic_items[i]
        st.markdown(f"### {st.session_state.logic_level} <span class='pill'>Challenge {i + 1} / 10</span>", unsafe_allow_html=True)
        st.progress(i / len(st.session_state.logic_items), text=f"Reasoning round · {i + 1} of 10")
        st.markdown(f"<div class='panel'><div class='section-label'>PAUSE · LOOK FOR THE CLUE</div><h3>{item['q']}</h3></div>", unsafe_allow_html=True)
        choice = st.radio("Choose your answer", item["c"], key=f"logic_choice_{i}")
        if not st.session_state.get(f"logic_submitted_{i}", False) and st.button("Lock in answer →", type="primary"):
            correct = item["c"].index(choice) == item["a"]
            st.session_state.logic_answers.append({"question": item["q"], "choice": choice, "correct": correct, "explanation": item["e"], "correct_answer": item["c"][item["a"]]})
            if correct: st.session_state.xp_bank += 5
            st.session_state[f"logic_submitted_{i}"] = True
            st.rerun()
        if st.session_state.get(f"logic_submitted_{i}", False):
            result = st.session_state.logic_answers[i]
            st.success("Excellent spot! +5 XP" if result["correct"] else f"Good thinking. The answer is {result['correct_answer']}.")
            st.info(result["explanation"])
            if i + 1 < len(st.session_state.logic_items):
                if st.button("Next puzzle →"):
                    st.session_state.logic_index += 1
                    st.rerun()
            elif st.button("Reveal my reasoning snapshot →"):
                st.session_state.logic_active, st.session_state.logic_done = False, True
                st.rerun()
    else:
        answers = st.session_state.get("logic_answers", [])
        score = sum(x["correct"] for x in answers)
        pct = score / max(len(answers), 1)
        if pct >= .8: band, next_step = "Pattern spotter", "Try the next difficulty up to keep your reasoning flexible."
        elif pct >= .5: band, next_step = "Curious thinker", "Review the explanations, then repeat this level to build a stronger rhythm."
        else: band, next_step = "Skill builder", "You showed up and practiced. Try another round and look for one clue at a time."
        st.markdown("### Your IQ teller snapshot")
        _save_attempt("logic", "Logic", "logic", st.session_state.get("logic_level", "Beginner"), score, max(1, len(answers)), 5 * score, {"question_count": len(answers)})
        a, b = st.columns(2)
        a.metric("Puzzles solved", f"{score} / {len(answers)}", f"{st.session_state.get('logic_level', 'Practice')} level")
        b.metric("Today’s badge", band, "+" + str(score * 5) + " XP")
        st.progress(pct, text="Accuracy in this 10-puzzle round")
        st.markdown(f"<div class='quote-card'>{next_step}<small>A practice snapshot for this round · not an IQ score</small></div>", unsafe_allow_html=True)
        st.markdown("<p class='tip'>This short, unstandardized puzzle set cannot estimate IQ, diagnose ability, or predict success. It only summarizes your answers to these questions at this difficulty today.</p>", unsafe_allow_html=True)
        with st.expander("Review each answer and explanation"):
            for n, result in enumerate(answers, 1):
                st.markdown(f"**{n}. {result['question']}**")
                st.caption(f"Your answer: {result['choice']} · {'Correct' if result['correct'] else 'Answer: ' + result['correct_answer']}")
                st.write(result["explanation"])
        if st.button("Play another level →"):
            st.session_state.logic_active, st.session_state.logic_done = False, False
            st.session_state.logic_answers = []
            st.rerun()

elif page == "Math speed arena":
    st.markdown("<div class='section-label'>SPEED & ACCURACY · MATH ARENA</div>", unsafe_allow_html=True)
    st.markdown("### Train the quick-calculation muscle")
    st.markdown("<p class='tip'>A focused sprint for mental math. No calculator needed—accuracy builds confidence, and confidence builds speed.</p>", unsafe_allow_html=True)
    if not st.session_state.get("math_active", False) and not st.session_state.get("math_done", False):
        with st.container(border=True):
            a, b = st.columns(2)
            with a:
                math_player = st.text_input("Player name", key="math_player_entry", placeholder="Enter your name for the leaderboard")
                math_levels = ["Beginner", "Intermediate", "Advanced"]
                adaptive = _adaptive_recommendation("maths", "Beginner")
                math_level = st.selectbox("Calculation level", math_levels, index=math_levels.index(adaptive["level"]), key="math_level_choice")
                st.caption(f"Adaptive suggestion: {adaptive['reason']}")
            with b:
                duration = st.selectbox("Sprint timer", [30, 60, 90], index=1, format_func=lambda seconds: f"{seconds} seconds", key="math_duration_choice")
            descriptions = {"Beginner":"Two-digit addition, subtraction, and times tables.","Intermediate":"Bigger products, exact division, and friendly percentages.","Advanced":"Two-digit multiplication, squares, percentages, and larger division."}
            st.markdown(f"<p class='tip'>{descriptions[math_level]} Your round ends when the timer runs out.</p>", unsafe_allow_html=True)
            if st.button("Start the sprint", type="primary", disabled=not math_player.strip()):
                st.session_state.math_player = " ".join(math_player.split())[:24]
                st.session_state.math_duration = duration
                st.session_state.math_items = [make_math_question(math_level) for _ in range(100)]
                st.session_state.math_level = math_level
                st.session_state.math_index, st.session_state.math_answers = 0, []
                st.session_state.math_last_result = None
                st.session_state.math_deadline = time.time() + duration
                st.session_state.math_active, st.session_state.math_done = True, False
                _begin_attempt("math")
                st.rerun()
    if st.session_state.get("math_active", False) or st.session_state.get("math_done", False):
        math_round()

elif page == "Memory games":
    st.markdown("<div class='section-label'>MEMORY & FOCUS | SHADOWINTELX TRAINING ROOM</div>", unsafe_allow_html=True)
    st.markdown("### Build your memory muscle")
    st.markdown("<p class='tip'>Four quick games. Three levels. Focus, remember, and improve at your own pace.</p>", unsafe_allow_html=True)
    if not st.session_state.get("memory_active", False) and not st.session_state.get("memory_done", False):
        with st.container(border=True):
            a,b=st.columns(2)
            with a:
                mode=st.selectbox("Choose a memory game",list(MEMORY_GAMES),key="memory_mode_choice")
                memory_levels=["Beginner","Intermediate","Advanced"]
                adaptive=_adaptive_recommendation("memory","Beginner")
                level=st.selectbox("Choose difficulty",memory_levels,index=memory_levels.index(adaptive["level"]),key="memory_level_choice")
                st.caption(f"Adaptive suggestion: {adaptive['reason']}")
            with b:
                st.markdown(f"<div class='panel'><div class='section-label'>{mode.upper()}</div><p class='tip'>{MEMORY_GAMES[mode]['description']}</p><p class='tip'>Selected level: <b>{level}</b></p></div>",unsafe_allow_html=True)
            if st.button("Start memory challenge",type="primary"):
                st.session_state.memory_mode,st.session_state.memory_level=mode,level
                st.session_state.memory_active,st.session_state.memory_done=True,False
                st.session_state.memory_counted=False
                st.session_state.memory_score,st.session_state.memory_round=0,1
                st.session_state.memory_cleared_rounds,st.session_state.memory_feedback=0,None
                _begin_attempt("memory")
                for round_key in range(1, 16):
                    key = f"memory_recall_{round_key}"
                    if key in st.session_state: del st.session_state[key]
                if "memory_object_choices" in st.session_state: del st.session_state["memory_object_choices"]
                if mode=="Card Match":
                    symbols=[chr(0x1F34E),chr(0x1F680),chr(0x1F338),chr(0x1F48E),chr(0x1F431),chr(0x1F3B8),chr(0x1F319),chr(0x1F3C6)]
                    pair_count=MEMORY_GAMES[mode]["pairs"][level]
                    cards=symbols[:pair_count]*2; random.shuffle(cards)
                    st.session_state.memory_cards=cards
                    st.session_state.memory_selected,st.session_state.memory_matched=[],[]
                    st.session_state.memory_moves,st.session_state.memory_stage=0,"cards"
                else:
                    prepare_memory_round()
                st.rerun()
    elif st.session_state.get("memory_active",False) or st.session_state.get("memory_done",False):
        memory_game()

elif page == "Verbal arena":
    st.markdown("<div class='section-label'>LANGUAGE & COMMUNICATION | VERBAL ARENA</div>", unsafe_allow_html=True)
    st.markdown("### Find the right words. Say them with confidence.")
    st.markdown("<p class='tip'>Practice vocabulary, analogies, reading comprehension, word reasoning, grammar, and everyday communication. Each round gives you a short explanation so you can learn as you go.</p>", unsafe_allow_html=True)
    category_names = list(VERBAL_BANK)
    levels = ["Beginner", "Intermediate", "Advanced"]
    if not st.session_state.get("verbal_active", False) and not st.session_state.get("verbal_done", False):
        with st.container(border=True):
            left, right = st.columns(2)
            with left:
                verbal_player = st.text_input("Player name", key="verbal_player_entry", placeholder="Enter your name for the leaderboard")
                category = st.selectbox("Choose a verbal skill", category_names, key="verbal_category_choice")
                adaptive = _adaptive_recommendation("verbal", "Beginner")
                level = st.selectbox("Choose your level", levels, index=levels.index(adaptive["level"]), key="verbal_level_choice")
                st.caption(f"Adaptive suggestion: {adaptive['reason']}")
            with right:
                st.markdown(f"<div class='panel'><div class='section-label'>{category.upper()}</div><p class='tip'>Five focused questions with friendly explanations.</p><p class='tip'>Level: <b>{level}</b></p></div>", unsafe_allow_html=True)
            if st.button("Start verbal practice", type="primary", disabled=not verbal_player.strip()):
                st.session_state.verbal_player = " ".join(verbal_player.split())[:24]
                st.session_state.verbal_category = category
                st.session_state.verbal_level = level
                st.session_state.verbal_items = random.sample(VERBAL_BANK[category][level], min(5, len(VERBAL_BANK[category][level])))
                st.session_state.verbal_index = 0
                st.session_state.verbal_answers = []
                st.session_state.verbal_active = True
                st.session_state.verbal_done = False
                _begin_attempt("verbal")
                for key in list(st.session_state.keys()):
                    if str(key).startswith("verbal_submitted_") or str(key).startswith("verbal_choice_"):
                        del st.session_state[key]
                st.rerun()
    elif st.session_state.get("verbal_active", False):
        idx = st.session_state.verbal_index
        items = st.session_state.verbal_items
        item = items[idx]
        st.progress(idx / len(items), text=f"Question {idx + 1} of {len(items)} | {st.session_state.verbal_category} ? {st.session_state.verbal_level}")
        st.markdown(f"<div class='panel'><div class='section-label'>QUESTION {idx + 1:02d}</div><h3>{item[0]}</h3></div>", unsafe_allow_html=True)
        choice = st.radio("Choose your answer", item[1], key=f"verbal_choice_{idx}")
        if not st.session_state.get(f"verbal_submitted_{idx}", False) and st.button("Check my answer", type="primary", key=f"verbal_check_{idx}"):
            correct = item[1].index(choice) == item[2]
            st.session_state.verbal_answers.append({"question": item[0], "choice": choice, "correct": correct, "answer": item[1][item[2]], "explanation": item[3]})
            if correct:
                st.session_state.xp_bank += 5
            st.session_state[f"verbal_submitted_{idx}"] = True
            st.rerun()
        if st.session_state.get(f"verbal_submitted_{idx}", False):
            result = st.session_state.verbal_answers[idx]
            if result["correct"]:
                st.success("Correct. Keep building that language instinct! +5 XP")
            else:
                st.info(f"Good practice. The answer is: {result['answer']}")
            st.caption(item[3])
            if idx + 1 < len(items):
                if st.button("Next question", key=f"verbal_next_{idx}"):
                    st.session_state.verbal_index += 1
                    st.rerun()
            elif st.button("See my verbal snapshot", key="verbal_finish"):
                st.session_state.verbal_active = False
                st.session_state.verbal_done = True
                if not st.session_state.get("verbal_counted", False):
                    st.session_state.verbal_sessions = st.session_state.get("verbal_sessions", 0) + 1
                    st.session_state.verbal_counted = True
                st.session_state.verbal_summary = {
                    "player": st.session_state.verbal_player,
                    "category": st.session_state.verbal_category,
                    "level": st.session_state.verbal_level,
                    "score": sum(x["correct"] for x in st.session_state.verbal_answers),
                    "total": len(st.session_state.verbal_answers),
                }
                pct = round(100*st.session_state.verbal_summary["score"]/max(1,st.session_state.verbal_summary["total"]))
                record_high_score(st.session_state.verbal_player, f"Verbal | {st.session_state.verbal_category}", st.session_state.verbal_level, pct, "accuracy %")
                _save_attempt("verbal", f"Verbal | {st.session_state.verbal_category}", "verbal", st.session_state.verbal_level, st.session_state.verbal_summary["score"], max(1, st.session_state.verbal_summary["total"]), 5 * st.session_state.verbal_summary["score"], {"category": st.session_state.verbal_category, "question_count": st.session_state.verbal_summary["total"]})
                st.rerun()
    else:
        summary = st.session_state.get("verbal_summary", {})
        answers = st.session_state.get("verbal_answers", [])
        score, total = summary.get("score", 0), summary.get("total", len(answers))
        verbal_player_name = summary.get("player", "Player")
        st.markdown(f"### Verbal snapshot | {verbal_player_name}")
        col1, col2 = st.columns(2)
        col1.metric("Correct", f"{score} / {total}")
        col2.metric("Practice area", summary.get("category", "Verbal skills"))
        st.progress(score / max(total, 1), text="Correct answers in this round")
        st.markdown("<div class='quote-card'>Speak to be understood, and listen to understand.<small>Clear communication grows with practice</small></div>", unsafe_allow_html=True)
        if summary.get("category") == "Grammar & communication":
            st.markdown("#### Say it clearly")
            st.caption("Read this prompt aloud, then answer in two or three clear sentences:")
            st.markdown("<div class='panel'><h3>Describe one skill you are learning and how you practice it.</h3><p class='tip'>Try this pattern: main idea ? one detail ? a confident closing sentence.</p></div>", unsafe_allow_html=True)
            st.text_area("Optional reflection: write your response", key="verbal_speaking_reflection", height=110, placeholder="I am learning... I practice by...")
        with st.expander("Review your answers"):
            for n, answer in enumerate(answers, 1):
                st.markdown(f"**{n}. {answer['question']}**")
                st.write(f"Your answer: {answer['choice']} ? {'Correct' if answer['correct'] else 'Answer: ' + answer['answer']}")
                st.caption(answer["explanation"])
        if st.button("Practice another verbal round"):
            st.session_state.verbal_done = False
            st.session_state.verbal_active = False
            st.session_state.verbal_counted = False
            st.session_state.verbal_answers = []
            st.session_state.verbal_summary = None
            for key in list(st.session_state.keys()):
                if str(key).startswith("verbal_submitted_") or str(key).startswith("verbal_choice_"):
                    del st.session_state[key]
            st.rerun()

elif page == "Focus arena":
    st.markdown("<div class='section-label'>ATTENTION & SPEED | FOCUS ARENA</div>", unsafe_allow_html=True)
    st.markdown("### Lock in. React. Beat your best.")
    st.markdown("<p class='tip'>Four timed games for attention, visual scanning, reaction time, and typing speed. Every challenge has three levels.</p>", unsafe_allow_html=True)
    games=["Reaction Rush","Colour Trap","Target Hunt","Typing Speed"]
    levels=["Beginner","Intermediate","Advanced"]
    if not st.session_state.get("focus_active",False) and not st.session_state.get("focus_done",False):
        with st.container(border=True):
            left,right=st.columns(2)
            with left:
                player=st.text_input("Player name",key="focus_player_entry",placeholder="Enter your name for the leaderboard")
                game=st.selectbox("Choose a focus game",games,key="focus_game_choice")
                adaptive=_adaptive_recommendation("focus","Beginner")
                level=st.selectbox("Choose level",levels,index=levels.index(adaptive["level"]),key="focus_level_choice")
                st.caption(f"Adaptive suggestion: {adaptive['reason']}")
            duration={"Beginner":30,"Intermediate":45,"Advanced":60}[level]
            st.markdown(f"<div class='panel'><div class='section-label'>{game.upper()}</div><p class='tip'>Level: <b>{level}</b> | Timer: <b>{duration} seconds</b></p></div>",unsafe_allow_html=True)
            if st.button("Start focus challenge",type="primary",disabled=not player.strip()):
                st.session_state.focus_player=" ".join(player.split())[:24]
                st.session_state.focus_game,st.session_state.focus_level=game,level
                st.session_state.focus_duration=duration
                st.session_state.focus_started=time.time(); st.session_state.focus_deadline=time.time()+duration
                _begin_attempt("focus")
                st.session_state.focus_score=0; st.session_state.focus_round=0
                st.session_state.focus_goal={"Beginner":10,"Intermediate":18,"Advanced":25}[level]
                st.session_state.focus_seed=random.random()
                st.session_state.focus_active,st.session_state.focus_done=True,False
                if game=="Reaction Rush":
                    st.session_state.focus_attempts=0; st.session_state.focus_latencies=[]; st.session_state.focus_false_starts=0
                    st.session_state.focus_phase="wait"; st.session_state.focus_signal_at=time.time()+random.uniform(1.5,3.5)
                elif game=="Colour Trap":
                    palette=[("RED","#ff4055"),("BLUE","#4f8cff"),("GREEN","#38c77a"),("YELLOW","#ffd447")]
                    st.session_state.focus_goal={"Beginner":15,"Intermediate":25,"Advanced":35}[level]
                    st.session_state.focus_color_word=random.choice(palette)[0]; st.session_state.focus_color_ink=random.choice(palette)
                elif game=="Target Hunt":
                    st.session_state.focus_grid={"Beginner":3,"Intermediate":4,"Advanced":5}[level]
                    st.session_state.focus_target=random.randint(1,st.session_state.focus_grid**2)
                else:
                    prompts=["Clear communication helps every team work toward shared goals.","Small daily practice can build confidence and improve focus.","Careful readers notice details and explain their ideas clearly."]
                    st.session_state.focus_typing_prompt=random.choice(prompts); st.session_state.focus_typed_text=""; st.session_state.focus_typing_score=0
                    st.session_state.focus_typing_accuracy=0
                st.rerun()
    elif st.session_state.get("focus_active",False):
        focus_round()
    else:
        st.markdown(f"### Challenge complete ? {st.session_state.get('focus_player','Player')}")
        st.metric("Your score",f"{st.session_state.get('focus_score',0)} {st.session_state.get('focus_unit','points')}")
        if st.session_state.focus_game=="Reaction Rush" and st.session_state.get("focus_latencies"):
            st.caption(f"Average reaction: {sum(st.session_state.focus_latencies)/len(st.session_state.focus_latencies):.0f} ms | False starts: {st.session_state.focus_false_starts}")
        st.success("Your best score for this player and level is kept on the High Scores board.")
        if st.button("Play another focus game"):
            st.session_state.focus_done=False; st.session_state.focus_active=False; st.rerun()

elif page == "High scores":
    st.markdown("<div class='section-label'>LEADERBOARD | PERSONAL BESTS</div>", unsafe_allow_html=True)
    st.markdown("### High scores dashboard")
    st.markdown("<p class='tip'>Best score for each player, game, and level. A higher score moves the player up the board automatically.</p>", unsafe_allow_html=True)
    rows=load_high_scores()
    if rows:
        groups={}
        for row in rows:
            groups.setdefault((row["arena"],row["level"]),[]).append(row)
        st.markdown("#### Current champions")
        for (arena,level),group in sorted(groups.items()):
            winner=max(group,key=lambda row:float(row["score"]))
            safe_arena = html_escape(str(arena).upper())
            safe_player = html_escape(str(winner["player"]))
            safe_level = html_escape(str(level))
            safe_unit = html_escape(str(winner["unit"]))
            safe_updated = html_escape(str(winner["updated"]))
            st.markdown(f"<div class='panel'><div class='section-label'>#1 ? {safe_arena}</div><h3>{safe_player}</h3><p class='tip'>{safe_level} | <b>{winner['score']:g} {safe_unit}</b> | Personal best: {safe_updated}</p></div>",unsafe_allow_html=True)
        st.markdown("#### Full leaderboard")
        ordered=sorted(rows,key=lambda row:(row["arena"].casefold(),row["level"].casefold(),-float(row["score"]),row["player"].casefold()))
        st.table([{"Rank":rank,"Player":row["player"],"Game":row["arena"],"Level":row["level"],"Best":f"{row['score']:g} {row['unit']}","Date":row["updated"]} for rank,row in enumerate(ordered,1)])
    else:
        st.markdown("<div class='panel'><h3>The first record is waiting</h3><p class='tip'>Add your name before a Math, Verbal, or Focus challenge. Your best score appears here and moves to #1 when it beats the current champion.</p></div>",unsafe_allow_html=True)

elif page == "Skill DNA & Shadow Coach":
    attempts = _active_attempts()
    profile = build_skill_profile(attempts)
    st.markdown("<div class='section-label'>SAVED PERFORMANCE · SIX SKILL AREAS</div>", unsafe_allow_html=True)
    st.markdown("### Skill DNA & Shadow Coach")
    st.caption("Scores come from this local profile's completed saved rounds and are normalized to each arena's rubric. Interview scores measure keyword topic coverage, not answer correctness. Missing skills stay unmeasured.")
    radar_col, scores_col = st.columns([1, 1])
    with radar_col:
        st.html(skill_radar_svg(profile))
        st.caption("The radar outline appears after all six areas have saved results; measured areas are plotted before then.")
    with scores_col:
        for key, item in profile.items():
            if item["accuracy"] is None:
                st.markdown(f"**{item['label']}** · No saved attempts yet")
            else:
                trend = "new baseline" if item["trend"] is None else f"{item['trend']:+.1f} points vs previous rounds"
                st.markdown(f"**{item['label']}** · {item['accuracy']:.1f}% average saved score · {item['attempts']} rounds · {trend}")
    st.markdown("#### Historical progress")
    if attempts:
        history = attempts[-30:]
        chart_data = {"Round": list(range(1, len(history) + 1)), "Saved score": [float(item["accuracy"]) for item in history]}
        st.line_chart(chart_data, x="Round", y="Saved score", y_label="Saved score (%)", height=260)
    else:
        st.info("Your skill history will appear after your first completed practice round.")
    st.markdown("#### Shadow AI Coach")
    st.caption("The offline recommendation is generated by deterministic rules from your saved results. Model-written feedback is separate, optional, and appears only when a model is configured and you request it.")
    recommendation = coach_recommendation(attempts)
    if recommendation:
        st.markdown(f"<div class='coach-card'><div class='section-label'>OFFLINE COACH · EXPLAINABLE</div><h3>Next focus: {recommendation['label']}</h3><p class='tip'>{recommendation['explanation']}</p><div class='coach-foot'>Suggested exercise: <b>{recommendation['exercise']}</b></div></div>", unsafe_allow_html=True)
        if is_configured():
            st.caption(f"Optional model review is available ({configured_model()}). Only aggregate scores are sent, and only after you request it.")
            feedback_key = f"shadow_ai_coach_feedback_{st.session_state.active_user_id}"
            if st.button("Ask configured model for a training insight", key=f"shadow_ai_coach_request_{st.session_state.active_user_id}"):
                measured = {key: {"average_normalized_score": value["accuracy"], "recent_normalized_score": value["recent_accuracy"], "completed_rounds": value["attempts"]} for key, value in profile.items() if value["accuracy"] is not None}
                instructions = "Act as a careful study coach. Use only the supplied saved metrics. Explain one strength, one area to practice, and a realistic next exercise. Never invent measurements, predict hiring outcomes, or diagnose ability. If data is limited, say so."
                try:
                    with st.spinner("Reviewing saved aggregate results with the configured model…"):
                        st.session_state[feedback_key] = generate_feedback(instructions, json.dumps(measured, ensure_ascii=False))
                except (AIConfigurationError, AIRequestError) as exc:
                    st.warning(str(exc))
                st.rerun()
            if st.session_state.get(feedback_key):
                st.info(st.session_state[feedback_key])
        else:
            st.caption("Offline coaching is active. Model feedback requires OPENAI_API_KEY and OPENAI_MODEL; no model calls are made without both.")
    else:
        st.info("Complete and save a practice round to create a data-based coaching recommendation.")
    with st.expander("Shadow Mirror · suggested 7-day plan"):
        for item in build_training_plan(attempts, 7):
            st.markdown(f"**{item['day']} · {item['skill']}** — {item['objective']}")
            st.button("Open this practice", key=f"mirror_{st.session_state.active_user_id}_{item['day']}", on_click=navigate, args=(item["page"],))

elif page == "Shadow Missions":
    user_id = int(st.session_state.active_user_id)
    attempts = _active_attempts()
    mission_state = mission_snapshot(attempts)
    rank = rank_for_xp(st.session_state.xp_bank)
    if mission_state["current_streak"] >= 7:
        award_badge(user_id, "seven_day_streak", "Seven-Day Streak", DB_PATH)
    st.markdown("<div class='section-label'>CONSISTENCY · XP · UNLOCKS</div>", unsafe_allow_html=True)
    st.markdown("### Shadow Missions")
    streak_a, streak_b, streak_c = st.columns(3)
    streak_a.metric("Current streak", f"{mission_state['current_streak']} days")
    streak_b.metric("Longest streak", f"{mission_state['longest_streak']} days")
    streak_c.metric("Current rank", rank["name"], f"{rank['xp']} XP")
    st.caption("Streaks count days with saved completed rounds. Rewards are claimed once per mission period.")
    claims = list_mission_claims(user_id, DB_PATH)
    mission_columns = st.columns(3)
    for column, mission in zip(mission_columns, mission_state["missions"]):
        with column:
            claimed = (mission["key"], mission["period"]) in claims
            st.markdown(f"<div class='panel'><div class='section-label'>{'DAILY' if mission['key'].startswith('daily') else 'WEEKLY'}</div><h3>{mission['title']}</h3><p class='tip'>{mission['description']}</p></div>", unsafe_allow_html=True)
            st.progress(mission["progress"] / mission["goal"], text=f"{mission['progress']} / {mission['goal']} · +{mission['xp']} XP")
            if claimed:
                st.success("Reward claimed for this period")
            elif mission["ready"]:
                if st.button(f"Claim +{mission['xp']} XP", key=f"claim_{user_id}_{mission['key']}_{mission['period']}", type="primary"):
                    if claim_mission(user_id, mission["key"], mission["period"], mission["xp"], DB_PATH):
                        st.session_state.xp_bank = get_user_xp(user_id, DB_PATH)
                    st.rerun()
            else:
                st.caption("Complete the mission to unlock its reward.")
    st.markdown("#### Earned badges")
    badges = list_badges(user_id, DB_PATH)
    if badges:
        badge_cols = st.columns(min(4, len(badges)))
        for index, badge in enumerate(badges):
            with badge_cols[index % len(badge_cols)]:
                st.markdown(f"<div class='panel'><div class='section-label'>BADGE</div><h3>{badge['label']}</h3><p class='tip'>{badge['earned_at'][:10]}</p></div>", unsafe_allow_html=True)
    else:
        st.info("Badges unlock from real saved milestones: completing a first round, exploring skills, and building a practice habit.")

elif page == "Mind Boss Battles":
    st.markdown("<div class='section-label'>MULTI-ARENA · FOUR STAGES</div>", unsafe_allow_html=True)
    st.markdown("### Mind Boss Battles")
    st.caption("Clear logic, maths, verbal, and interview stages in one run. Scores and rewards are saved only when the battle is complete.")
    if not st.session_state.get("boss_active", False) and not st.session_state.get("boss_done", False):
        roles = list(QUESTION_BANK)
        levels = ["Beginner", "Intermediate", "Advanced"]
        left, right = st.columns(2)
        with left:
            role = st.selectbox("Interview role for the final stage", roles, key="boss_role_choice")
        with right:
            adaptive = _adaptive_recommendation("logic", "Beginner")
            level = st.selectbox("Battle difficulty", levels, index=levels.index(adaptive["level"]), key="boss_level_choice")
        st.caption(f"Adaptive suggestion: {adaptive['reason']}")
        if st.button("Enter the battle", type="primary"):
            st.session_state.boss_role = role
            st.session_state.boss_level = level
            st.session_state.boss_stages = _make_boss_stages(level, role)
            st.session_state.boss_results = []
            st.session_state.boss_index = 0
            st.session_state.boss_active = True
            st.session_state.boss_done = False
            _begin_attempt("boss")
            st.rerun()
    elif st.session_state.get("boss_active", False):
        stages = st.session_state.boss_stages
        index = st.session_state.boss_index
        stage = stages[index]
        st.progress(index / len(stages), text=f"Stage {index + 1} of {len(stages)} · {stage['name']}")
        st.markdown(f"<div class='panel'><div class='section-label'>{stage['name'].upper()}</div><h3>{stage['question']}</h3><p class='tip'>Level: {st.session_state.boss_level}</p></div>", unsafe_allow_html=True)
        response = None
        if stage["type"] == "choice":
            response = st.radio("Choose your answer", stage["choices"], key=f"boss_choice_{st.session_state.boss_attempt_key}_{index}")
        elif stage["type"] == "number":
            response = st.text_input("Your answer", key=f"boss_number_{st.session_state.boss_attempt_key}_{index}", placeholder="Enter a whole number")
        else:
            response = st.text_area("Your interview response", key=f"boss_answer_{st.session_state.boss_attempt_key}_{index}", height=150, placeholder="Explain your thinking and give a concrete example.")
        if st.button("Lock in this stage", type="primary", key=f"boss_submit_{st.session_state.boss_attempt_key}_{index}"):
            if stage["type"] == "choice":
                stage_score = int(stage["choices"].index(response) == stage["answer"])
                maximum = 1
                correct = bool(stage_score)
            elif stage["type"] == "number":
                clean = str(response or "").strip()
                if not clean or not clean.lstrip("-+").isdigit():
                    st.warning("Enter a whole-number answer before continuing.")
                    st.stop()
                correct = int(clean) == int(stage["answer"])
                stage_score, maximum = int(correct), 1
            else:
                words = set(str(response or "").lower().replace("/", " ").replace("-", " ").replace(",", " ").replace(".", " ").split())
                if len(str(response or "").strip().split()) < 5:
                    st.warning("Write at least five words so the practice rubric has enough context.")
                    st.stop()
                stage_score = round(10 * sum(keyword.casefold() in words for keyword in stage["keywords"]) / max(1, len(stage["keywords"])), 1)
                maximum = 10
                correct = stage_score >= 5
            result = {"name": stage["name"], "skill": stage["skill"], "level": st.session_state.boss_level, "score": stage_score, "max_score": maximum, "accuracy": round(100 * stage_score / maximum, 1), "correct": correct, "explanation": stage["explanation"]}
            st.session_state.boss_results.append(result)
            st.session_state.boss_index += 1
            if st.session_state.boss_index >= len(stages):
                st.session_state.boss_active = False
                st.session_state.boss_done = True
            st.rerun()
        st.caption("This battle combines existing arenas; each stage keeps its own underlying answer rules.")
    else:
        results = st.session_state.get("boss_results", [])
        total_score = sum(float(item["score"]) for item in results)
        total_max = max(1, sum(float(item["max_score"]) for item in results))
        battle_accuracy = round(100 * total_score / total_max)
        battle_xp = 25 + round(25 * battle_accuracy / 100)
        stage_details = [{"skill": item["skill"], "accuracy": item["accuracy"], "level": item["level"]} for item in results]
        _save_attempt("boss", "Mind Boss Battle", "boss", st.session_state.boss_level, battle_accuracy, 100, battle_xp, {"metric_name": "composite_score", "role": st.session_state.boss_role, "stages": stage_details, "completed_stages": len(results)})
        record_high_score(st.session_state.active_profile_name, "Mind Boss Battle", st.session_state.boss_level, battle_accuracy, "accuracy %")
        left, middle, right = st.columns(3)
        left.metric("Battle score", f"{battle_accuracy}%")
        middle.metric("Stages cleared", f"{sum(bool(item['correct']) for item in results)} / 4")
        right.metric("XP reward", f"+{battle_xp}")
        st.markdown("#### Stage review")
        for result in results:
            st.markdown(f"**{result['name']}** · {result['score']:g} / {result['max_score']:g} · {result['accuracy']:g}%")
            st.caption(result["explanation"])
        if st.button("Run another battle", type="primary"):
            st.session_state.boss_done = False
            st.session_state.boss_results = []
            st.rerun()

elif page == "Performance Intelligence":
    attempts = _active_attempts()
    report = performance_report(attempts)
    st.markdown("<div class='section-label'>SAVED HISTORY · ACTIONABLE REVIEW</div>", unsafe_allow_html=True)
    st.markdown("### Performance Intelligence Report")
    if not attempts:
        st.info("No saved attempts yet. Complete an activity to create your first report. No example statistics are shown as personal results.")
    else:
        a, b, c, d = st.columns(4)
        a.metric("Saved rounds", report["attempt_count"])
        b.metric("Question-round accuracy", f"{report['accuracy']:.1f}%" if report["accuracy"] is not None else "Not measured", f"Mean from {report['accuracy_attempt_count']} rounds")
        c.metric("Average completion time", f"{report['average_duration']:.1f}s")
        d.metric("XP from saved rounds", report["xp_earned"])
        high, low = st.columns(2)
        if report["strongest"]:
            high.markdown(f"<div class='panel'><div class='section-label'>CURRENT STRENGTH</div><h3>{report['strongest']['label']}</h3><p class='tip'>{report['strongest']['recent_accuracy']:.1f}% average normalized score across recent rounds</p></div>", unsafe_allow_html=True)
        if report["weakest"]:
            low.markdown(f"<div class='panel'><div class='section-label'>NEXT PRACTICE AREA</div><h3>{report['weakest']['label']}</h3><p class='tip'>{report['weakest']['recent_accuracy']:.1f}% average normalized score across recent rounds</p></div>", unsafe_allow_html=True)
        if report["accuracy"] is None:
            st.caption("No accuracy-based question rounds are saved yet. Interview topic coverage and other arena scores remain available in the normalized performance history.")
        else:
            st.caption("Accuracy includes only rounds with right-or-wrong outcomes. Topic-coverage and mixed challenge scores are shown separately as normalized results.")
        st.markdown("#### Saved performance history")
        history = report["recent"]
        chart_data = {"Round": list(range(1, len(history) + 1)), "Saved score": [float(item["accuracy"]) for item in history]}
        st.line_chart(chart_data, x="Round", y="Saved score", y_label="Saved score (%)", height=260)
        if report["recommendation"]:
            st.markdown(f"**Recommended next step:** {report['recommendation']['exercise']} {report['recommendation']['explanation']}")
    pdf_bytes = build_pdf_report(st.session_state.active_profile_name, report)
    st.download_button("Download performance report (PDF)", data=pdf_bytes, file_name="shadowintelx-performance-report.pdf", mime="application/pdf", type="primary")
    st.caption("The report includes only saved local attempts. It is a practice summary, not a hiring, IQ, or diagnostic assessment.")

elif page == "Logic & IQ-style quiz":
    st.markdown("<div class='section-label'>THINK CLEARLY · LOGIC LAB</div>", unsafe_allow_html=True)
    st.markdown("### A workout for your reasoning")
    st.markdown("<p class='tip'>15 short puzzles, with an explanation after each. This is a casual reasoning quiz—not an IQ test, diagnosis, or measure of your potential.</p>", unsafe_allow_html=True)
    if not st.session_state.get("logic_active", False) and not st.session_state.get("logic_done", False):
        st.markdown("<div class='panel'><h3>Ready to stretch your brain?</h3><p class='tip'>Take your time, read carefully, and learn from each explanation.</p></div>", unsafe_allow_html=True)
        if st.button("Start 15-question quiz →", type="primary"):
            st.session_state.logic_items = random.sample(LOGIC, len(LOGIC))
            st.session_state.logic_index, st.session_state.logic_answers = 0, []
            st.session_state.logic_active = True; st.rerun()
    elif st.session_state.get("logic_active", False):
        i = st.session_state.logic_index; item = st.session_state.logic_items[i]
        st.progress(i / len(st.session_state.logic_items), text=f"Challenge {i + 1} of {len(st.session_state.logic_items)}")
        st.markdown(f"<div class='panel'><div class='section-label'>CHALLENGE {i + 1:02d}</div><h3>{item['q']}</h3></div>", unsafe_allow_html=True)
        choice = st.radio("Choose your answer", item["c"], key=f"logic_choice_{i}")
        if st.button("Lock in answer →", type="primary"):
            correct = item["c"].index(choice) == item["a"]
            st.session_state.logic_answers.append({"question": item["q"], "choice": choice, "correct": correct, "explanation": item["e"], "correct_answer": item["c"][item["a"]]})
            st.session_state[f"logic_submitted_{i}"] = True; st.rerun()
        if st.session_state.get(f"logic_submitted_{i}", False):
            result = st.session_state.logic_answers[i]
            st.success("That's right! ✦" if result["correct"] else f"Good try. The answer is {result['correct_answer']}.")
            st.info(result["explanation"])
            if i + 1 < len(st.session_state.logic_items):
                if st.button("Next challenge →"):
                    st.session_state.logic_index += 1; st.rerun()
            elif st.button("View my reasoning snapshot →"):
                st.session_state.logic_active, st.session_state.logic_done = False, True; st.rerun()
    else:
        answers = st.session_state.get("logic_answers", [])
        score = sum(answer["correct"] for answer in answers); pct = score / max(len(answers), 1)
        if pct >= .8: band, encouraging = "Strong puzzle run", "You spotted many patterns and worked through tricky wording with care."
        elif pct >= .55: band, encouraging = "Steady problem solving", "You found several good routes. Reviewing explanations can sharpen your approach."
        else: band, encouraging = "Curious learner", "Every puzzle is a chance to practice. Try another round and notice which strategies help."
        st.markdown("### Your reasoning snapshot")
        a, b = st.columns(2); a.metric("Puzzles solved", f"{score} / {len(answers)}"); b.metric("Practice snapshot", band)
        st.markdown(f"<div class='quote-card'>{encouraging}<small>Practice reflection · not an IQ score</small></div>", unsafe_allow_html=True)
        st.progress(pct, text="Correct answers in this quiz")
        st.markdown("<p class='tip'>This playful quiz is not standardized, normed, or designed to estimate IQ. A score cannot tell you your IQ level or predict your ability. It reflects only how you did on these particular puzzles today.</p>", unsafe_allow_html=True)
        with st.expander("Review all puzzle explanations"):
            for n, answer in enumerate(answers, 1):
                st.markdown(f"**{n}. {answer['question']}**"); st.write(f"Your answer: {answer['choice']} · {'Correct' if answer['correct'] else 'Keep practicing'}"); st.caption(answer["explanation"])
        if st.button("Play a fresh round →"):
            st.session_state.logic_done = False; st.session_state.logic_answers = []
            for key in list(st.session_state.keys()):
                if str(key).startswith("logic_submitted_"): del st.session_state[key]
            st.rerun()

else:
    st.markdown("<div class='section-label'>YOUR JOURNEY · PROGRESS & RESULTS</div>", unsafe_allow_html=True)
    st.markdown("### Your practice, in one place")
    interview = st.session_state.get("interview_results", []); logic = st.session_state.get("logic_answers", []); math_answers = st.session_state.get("math_answers", [])
    a, b, c, d, e, f = st.columns(6)
    a.metric("Interview answers", len(interview)); b.metric("Logic solved", sum(x["correct"] for x in logic)); c.metric("Math best", st.session_state.get("math_best_score", 0)); d.metric("Memory games", st.session_state.get("memory_sessions", 0)); e.metric("Verbal rounds", st.session_state.get("verbal_sessions", 0)); f.metric("XP bank", st.session_state.xp_bank)
    practice_signals = []
    if interview:
        coverage = round(10 * sum(item["score"] for item in interview) / len(interview))
        practice_signals.append(("Interview coverage", max(0, min(100, coverage)), "Interview practice", "Practice one answer with a specific example and a clear result."))
    if logic:
        logic_pct = round(100 * sum(item["correct"] for item in logic) / len(logic))
        practice_signals.append(("Reasoning", logic_pct, "IQ teller & logic", "Review one missed explanation, then try a fresh reasoning round."))
    if math_answers:
        math_pct = round(100 * sum(item["correct"] for item in math_answers) / len(math_answers))
        practice_signals.append(("Mental math", math_pct, "Math speed arena", "Aim for accurate calculations first, then repeat a short sprint."))
    memory_snapshot = st.session_state.get("memory_summary")
    if memory_snapshot and memory_snapshot.get("total"):
        memory_pct = round(100 * memory_snapshot["score"] / memory_snapshot["total"])
        practice_signals.append(("Memory", memory_pct, "Memory games", "Try the same memory game again and focus on one additional round or pair."))
    verbal_snapshot = st.session_state.get("verbal_summary")
    if verbal_snapshot and verbal_snapshot.get("total"):
        verbal_pct = round(100 * verbal_snapshot["score"] / verbal_snapshot["total"])
        practice_signals.append(("Verbal communication", verbal_pct, "Verbal arena", "Review the explanations and retry the skill area you just practiced."))
    if practice_signals:
        st.markdown("#### Practice skill snapshot")
        st.caption("A view of your latest completed rounds in this session—not a hiring or employability score.")
        skill_col, coach_col = st.columns([1.15, 0.85])
        with skill_col:
            for label, score, _, _ in practice_signals:
                st.markdown(f"<div class='skill-row'><div class='skill-row-head'><span>{label}</span><strong>{score}%</strong></div><div class='skill-track'><span style='width:{score}%'></span></div></div>", unsafe_allow_html=True)
        weakest = min(practice_signals, key=lambda item: item[1])
        strongest = max(practice_signals, key=lambda item: item[1])
        with coach_col:
            st.markdown(f"<div class='coach-card'><div class='section-label'>YOUR NEXT STEP</div><h3>Build on {weakest[0].lower()}</h3><p class='tip'>{weakest[3]}</p><div class='coach-foot'>Strongest latest result: <b>{strongest[0]}</b> · {strongest[1]}%</div></div>", unsafe_allow_html=True)
            if st.button(f"Practice {weakest[0].lower()} next", type="primary", key="practice_recommendation"):
                navigate(weakest[2])
                st.rerun()
    if not interview and not logic and not math_answers and not st.session_state.get("memory_summary") and not st.session_state.get("verbal_summary"):
        st.markdown("<div class='panel'><h3>Your first practice session is waiting</h3><p class='tip'>Complete an interview round, logic quiz, or math sprint and your results will appear here. Saved attempts and XP remain with this local profile on this device.</p></div>", unsafe_allow_html=True)
    if interview:
        st.markdown("#### Latest interview answers")
        for i, result in enumerate(interview, 1):
            with st.expander(f"{i}. {result['question']} · {result['score']}/10"):
                st.write(result["answer"]); st.caption(result["feedback"])
    if logic:
        st.markdown(f"#### Latest logic round · {sum(x['correct'] for x in logic)} of {len(logic)} solved")
        with st.expander("Review explanations"):
            for result in logic:
                st.markdown(f"**{result['question']}**"); st.caption(result["explanation"])
    if st.session_state.get("memory_summary"):
        memory_result=st.session_state.memory_summary
        st.markdown(f"#### Latest memory challenge | {memory_result['game']} / {memory_result['level']}")
        score_label = "objects recalled" if memory_result["game"] == "Object Memory" else "pairs found" if memory_result["game"] == "Card Match" else "rounds cleared"
        st.caption(f"{score_label.title()}: {memory_result['score']}")
    if st.session_state.get("verbal_summary"):
        verbal_result = st.session_state.verbal_summary
        st.markdown(f"#### Latest verbal round | {verbal_result['category']} / {verbal_result['level']}")
        st.caption(f"Correct: {verbal_result['score']} of {verbal_result['total']}")
    if math_answers:
        st.markdown(f"#### Latest math sprint · {sum(x['correct'] for x in math_answers)} of {len(math_answers)} correct")
        with st.expander("Review calculations"):
            for result in math_answers:
                st.markdown(f"**{result['question']}** Your answer: {result['response']} · {'Correct' if result['correct'] else 'Answer: ' + str(result['answer'])}")
    quote_card()

st.markdown("---")
st.markdown("<p class='tip' style='text-align:center'>✦ Made for consistent practice, clear thinking, and confident next steps.</p>", unsafe_allow_html=True)
st.markdown("<div class='signature'>Designed by <b>SK</b></div>", unsafe_allow_html=True)
