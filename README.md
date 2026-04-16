CausalityAI 🩺
An AI-powered tool that helps pharmacovigilance experts assess whether a drug caused 
an adverse event — based on the WHO–UMC causality framework.


--Frontend--

5 professionally designed screens
Hybrid design system (IBM + Claude + Linear + PostHog + Sentry)
Full navigation between all screens

--Backend--

Flask Python server
WHO-UMC rule-based assessment engine
REST API endpoint

--Database--

SQLite database
Cases table saving every ICSR
Decisions table ready for audit log

*Full pipeline working*
Login → Intake Form → Python API → WHO-UMC Assessment → Database → Result Screen

--WHO–UMC Categories--
The system classifies each case into one of 6 official categories:

Category                      Meaning
------------------------------------------------------------------------
Certain                    |   Strong evidence the drug caused the reaction
Probable/LikelyGood        |   evidence but not 100% confirmed
Possible                   |   Some evidence but other causes exist
Unlikely                   |   Weak connection to the drug
Conditional/Unclassified   |   Need more information
Unassessable               |   Cannot be evaluated with available data


--How the Scoring Works--
The system uses a simple rule-based score to determine the WHO-UMC category:

Criterion                    Score
----------------------------------
Positive dechallenge       |  +3
Positive rechallenge       |  +3
Time to onset provided     |  +1
Narrative present          |  +1
Alternative cause exists   |  -1
Negative dechallenge       |  -1


The total score maps to a category:

Score ≥ 6 → Certain (92%)
Score ≥ 4 → Probable / Likely (78%)
Score ≥ 2 → Possible (61%)
Score ≥ 0 → Unlikely (45%)
Score < 0 → Unassessable (20%)


--Screens--

Screen                        Description
------------------------------------------------------------------------
Login                   |     Secure sign-in with role and unit selection
Intake Form             |     Enter patient, drug, and adverse event data
AI Result               |     WHO-UMC prediction with SHAP explainability
Dashboard               |     Case queue, KPIs, and model performance
Fairness & Audit        |     Demographic fairness report and immutable audit log


