"""Curated resume-craft knowledgebase, distilled into prompt fragments.

Single source of truth for *what makes a resume great*, so the review, fit, and
chat prompts all reason from the same rubric instead of re-deriving advice ad hoc.
Everything here is plain string/dict data — no logic. `analyzer.py` composes these
fragments into system prompts.

The philosophy mirrors the rest of the app: evidence over branding, specificity
over generic filler, and honesty about the myths (an ATS does not silently delete
resumes — weak keyword match, broken parsing, and a crowded queue do the burying).
"""

# --- Market-agnostic non-negotiables (true in every market) -----------------

RESUME_PRINCIPLES = """RESUME CRAFT — THE NON-NEGOTIABLES (apply in every market):
- ACHIEVEMENTS, NOT DUTIES. Anyone in the role did the duties; only this candidate
  produced their results. Judge each bullet on whether it shows an outcome.
- THE XYZ FORMULA: a strong bullet reads "Accomplished [X] as measured by [Y] by
  doing [Z]." Strong action verb -> what they did -> measurable outcome. Metrics can
  be volume, latency, cost, time saved, users, revenue, error rate or team size — not
  only percentages.
- QUANTIFY ONLY WHAT CAN BE DEFENDED. A modest but bulletproof claim beats an
  impressive one that collapses under questioning.
- FRONT-LOAD. Recruiters skim in an F-pattern: the strongest, most role-relevant,
  most quantified content belongs in the top third of page one. Bold titles/companies.
- TAILOR AND MIRROR THE JOB'S LANGUAGE. Use the posting's exact phrasing; include the
  spelled-out term and its acronym once ("Retrieval-Augmented Generation (RAG)").
  Never keyword-stuff and never use hidden/white text.
- REVERSE-CHRONOLOGICAL. Most recent first. A skills-only/functional layout reads as
  hiding something. Use a hybrid (summary + skills on top, then full timeline) at most.
- PROOFREAD OBSESSIVELY. Typos are the most-cited instant-rejection trigger.
- CUT DEAD WEIGHT and generic filler; every line should earn its place."""

# --- Machine-readability, with the myth explicitly corrected ----------------

PARSEABILITY_RULES = """MACHINE-READABILITY (how a parser and a 7-second skim read it):
- SINGLE COLUMN. Two-column layouts are the #1 parse failure — a sidebar gets
  scrambled into the work history.
- NO tables, text boxes, graphics, logos, icons, or skill-rating bars ("Python
  ####. 85%" is meaningless to a parser and a human). Contact icons can parse as null.
- Put contact details in the BODY, not the header/footer (many parsers skip those).
- Standard section headings ("Work Experience", "Skills", "Education"), standard fonts
  (Calibri/Arial/Garamond/Inter), bullets not paragraphs, consistent date format.
- THE PLAIN-TEXT TEST: pasted into a plain editor, it should read top-to-bottom in the
  right order with no garbage. If it scrambles, the layout will mis-parse.
MYTH TO CORRECT (do NOT reinforce it): an ATS does not auto-reject ~75% of resumes —
that statistic is fabricated. The only true automatic filters are knockout questions
(work authorisation, location, licensing). The real failure modes are (a) weak keyword
match, so the resume is BURIED in recruiter search results, and (b) a parse failure
that scrambles the content — not a robot silently deleting the file. Frame parseability
issues as 'you get buried or mis-parsed', never as 'a bot will reject you'."""

# --- What to cut (baseline; markets refine this) ----------------------------

CUT_LIST = """DEAD WEIGHT TO CUT (baseline — market rules below may override):
- Objective statements ("Seeking a challenging role in a dynamic organisation").
- "References available upon request" (assumed; wastes a line).
- Photo, date of birth, gender, marital status, religion, father's name, nationality.
- Full street address (city/region is enough).
- Salary history and "Declaration: I hereby declare..." + signature.
- Unbacked soft-skill filler ("hard-working team player", "excellent communication").
- "MS Word" / "MS Office" as listed skills.
- Jobs older than ~10-15 years and anything irrelevant to the target role.
- Any skill the candidate could not survive 15 minutes of questioning on."""

# --- Reusable single-idea rules ---------------------------------------------

XYZ_RULE = """For bullet_rewrites: pick the 3-6 WEAKEST but genuine bullets (duty-based,
vague, or unquantified) and rewrite each into the XYZ form — strong verb + what they
did + a measurable or concrete outcome. Rewrites MUST stay strictly grounded in what
the resume already contains; NEVER invent metrics, tools, scope, or employers. If a
real number is not present, sharpen the outcome qualitatively rather than fabricating
a figure. In `why`, name what got stronger (added a verb, surfaced a metric, showed
impact)."""

DEFENSIBILITY_RULE = """For defensibility_flags: flag claims, listed skills, or numbers
that a sharp interviewer would probe and the resume gives little to back up (buzzwords,
inflated titles, round numbers with no basis, a long tech list the projects don't
support). This matters most for Indian interview panels, which probe deeply. For each,
state the claim, why it is risky, and whether to defend it (add evidence), quantify it,
or cut it. Only flag genuinely shaky items — do not pad the list."""

# --- Market-specific guides --------------------------------------------------

MARKET_GUIDES: dict[str, str] = {
    "india_modern": """TARGET MARKET — INDIA, MODERN EMPLOYERS (product companies, AI
startups, GCCs, MNCs, most Bangalore tech). Follow Western professional norms:
- LENGTH: 1 page if under ~3 years' experience (non-negotiable for freshers — recruiters
  screen hundreds of resumes per role); 2 pages beyond that; never 3.
- SKILLS SECTION IS CRITICAL and sits HIGH on the page, grouped by category (Languages /
  Frameworks / Cloud & Infra / Data & ML / Tools). Recruiters keyword-search it first.
- GitHub AND LinkedIn links are expected; titles/dates must match the resume exactly.
- PROJECTS are heavily weighted when formal experience is thin: 2-3 max, each with name,
  tech stack, a live/GitHub link, and 2 quantified-impact bullets.
- CGPA/percentage: include only if >=7.0 (10-point) or a top-tier institute; else omit.
- Certifications (AWS/Azure/GCP) carry real weight and can offset a non-elite college.
- NOTICE PERIOD and CTC DO NOT belong on the resume — flag them in cut_list if present.
- Photo, DOB, declaration, and objective statements are actively harmful here — cut them.
- Panels probe deeply, so defensibility matters more than polish.""",

    "india_traditional": """TARGET MARKET — INDIA, TRADITIONAL EMPLOYERS (PSU, government,
banking, legacy service firms, campus mass-hiring). These still tolerate or expect
biodata-era conventions:
- An objective statement, a declaration + signature, sometimes a photo, and 10th/12th
  percentages may be EXPECTED rather than harmful. Father's name is mandatory for many
  government roles. Do NOT reflexively tell the candidate to cut these — keep cut_list
  minimal and note that these conventions are acceptable/expected for this employer type.
- Still enforce achievements-over-duties, quantification, clean single-column formatting,
  and reverse-chronological history — good content wins everywhere.
- 1-2 pages; skills and qualifications stated plainly.""",

    "uk": """TARGET MARKET — UNITED KINGDOM. It is a CV, not a resume — use that word, and
British English throughout (optimise, organise, programme, analyse):
- LENGTH: two pages is the standard and the expectation; one page only for graduates.
- PERSONAL STATEMENT (not an objective): 3-5 lines under the contact details — who they
  are professionally, what they are known for (with a concrete achievement), what they
  target. Understated confidence backed by evidence, not American-style self-promotion.
- NO photo, date of birth, age, marital status, nationality, gender, or National Insurance
  number — this is driven by the Equality Act 2010; some HR teams bin a CV with a photo.
  Flag any of these in cut_list. City/region only for location.
- A KEY SKILLS block of 6-10 skills matched to the job description, near the top.
- References: omit entirely (do not even write "references on request").
- If the candidate needs sponsorship, advise ONE line under contact details:
  "Right to work: Requires Skilled Worker visa sponsorship." No visa/BRP/CoS numbers.
- Indian degrees: suggest adding the UK ENIC equivalence ("B.Tech, equivalent to a British
  Bachelor's (Honours) degree") to save the recruiter the mental work.""",

    "us_global": """TARGET MARKET — US / GLOBAL (generic Western norms). It is a resume:
- LENGTH: one page is the default; two only with substantial senior experience.
- No photo, DOB, or personal data. No objective — a tight 2-4 line professional summary or
  nothing. Skills section present and keyword-matched to the posting.
- Standard, conservative, single-column formatting throughout.""",
}

MARKET_LABELS: dict[str, str] = {
    "india_modern": "the Indian IT market (modern product / startup / GCC / MNC employers)",
    "india_traditional": "the Indian market (traditional PSU / government / legacy service employers)",
    "uk": "the United Kingdom (a CV, British English, Equality Act norms)",
    "us_global": "the US / global market (generic Western resume norms)",
}

# Canonical set of accepted market codes — imported by routes for validation.
MARKETS = tuple(MARKET_GUIDES.keys())
DEFAULT_MARKET = "india_modern"
