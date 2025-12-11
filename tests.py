import streamlit as st
import sys
import re

# Mock Streamlit Session State
if "awaiting_dept_scope" not in st.session_state:
    st.session_state.awaiting_dept_scope = False
if "awaiting_college_scope" not in st.session_state:
    st.session_state.awaiting_college_scope = False
if "pending_intent" not in st.session_state:
    st.session_state.pending_intent = None
if "user_name" not in st.session_state:
    st.session_state.user_name = "TestUser"
if "chat" not in st.session_state:
    st.session_state.chat = []

try:
    from app import route, data, OFFICIAL_SOURCE
except ImportError:
    print("❌ Error: Could not import 'app.py'.")
    sys.exit(1)


def run_tests():
    print("==========================================================")
    print("CASmate Comprehensive Unit Tests (Fixed & Adjusted)")
    print("==========================================================\n")

    test_cases = [
        # ==============================================================================
        # SECTION 1: CRITICAL BUGS & BASELINE
        # ==============================================================================
        {
            "cat": "BugFix",
            "input": "prereq of microbiology?",
            "should_contain": ["Microbiology", "no listed prerequisites"],
            "should_not_contain": ["I found a few courses", "Medical Microbiology"],
            "expect_source": True,
            "desc": "Exact Match Priority (Microbiology)"
        },
        {
            "cat": "BugFix",
            "input": "medical microbiology prerequisite?",
            "should_contain": ["Prerequisite of Medical Microbiology", "MED 102"],
            "should_not_contain": ["I found a few courses"],
            "expect_source": True,
            "desc": "Exact Match Priority (Medical Microbiology)"
        },
        {
            "cat": "BugFix",
            "input": "is there a prereq for microbiology?",
            "should_contain": ["Microbiology", "no listed prerequisites"],
            "should_not_contain": ["I found a few courses", "Medical Microbiology"],
            "expect_source": True,
            "desc": "Exact Match Priority (Is there a prereq...)"
        },
        {
            "cat": "BugFix",
            "input": "political science 4th year subjects",
            "should_contain": ["3-year trimester", "Registrar"],
            "should_not_contain": ["I found a few courses", "PS 101"],
            "expect_source": False,
            "desc": "4th Year Missing Data Handling"
        },
        {
            "cat": "BugFix",
            "input": "2nd year 1st sem polsci subjects",
            "should_contain": ["Courses for Second year Bachelor of Arts in Political Science", "Introduction to International Relations"],
            "should_not_contain": ["First year", "Fundamentals of Political Science"],
            "expect_source": True,
            "desc": "Correct Year Parsing (2nd year != 1st year)"
        },
        {
            "cat": "BugFix",
            "input": "purposive communication units",
            "should_contain": ["Purposive Communication", "3 units"],
            "should_not_contain": ["Total units for"],
            "expect_source": True,
            "desc": "PCOM Units vs Program Units"
        },
        {
            "cat": "BugFix",
            "input": "Mathematics in the Modern World units?",
            "should_contain": ["Mathematics in the Modern World", "3 units"],
            "should_not_contain": ["What would you like to know"],
            "expect_source": True,
            "desc": "MMW Units check"
        },
        {
            "cat": "BugFix",
            "input": "How many units do I take as first year cs student?",
            "should_contain": ["Total units for First year Bachelor of Science in Computer Science"],
            "should_not_contain": ["Second year", "Third year", "Overall for Year 2"],
            "expect_source": True,
            "desc": "Year Specific Unit Load (First Year CS)"
        },

        # ==============================================================================
        # SECTION 2: BASIC CURRICULUM CHECKS
        # ==============================================================================
        # CS
        {"cat": "Curriculum", "input": "1st year cs subjects", "should_contain": ["CC 111"], "expect_source": True, "desc": "CS Year 1"},
        {"cat": "Curriculum", "input": "2nd year cs subjects", "should_contain": ["CS 211"], "expect_source": True, "desc": "CS Year 2"},
        {"cat": "Curriculum", "input": "3rd year cs subjects", "should_contain": ["Software Engineering"], "expect_source": True, "desc": "CS Year 3"},
        # BIO
        {"cat": "Curriculum", "input": "1st year bio subjects", "should_contain": ["General Zoology"], "expect_source": True, "desc": "BIO Year 1"},
        {"cat": "Curriculum", "input": "2nd year bio subjects", "should_contain": ["Microbiology"], "expect_source": True, "desc": "BIO Year 2"},
        {"cat": "Curriculum", "input": "3rd year bio subjects", "should_contain": ["Medical Microbiology"], "expect_source": True, "desc": "BIO Year 3"},

        # PSYCH
        {"cat": "Curriculum", "input": "1st year psych subjects", "should_contain": ["Introduction to Psychology"], "expect_source": True, "desc": "PSYCH Year 1"},
        {"cat": "Curriculum", "input": "2nd year psych subjects", "should_contain": ["Experimental Psychology"], "expect_source": True, "desc": "PSYCH Year 2"},
        {"cat": "Curriculum", "input": "3rd year psych subjects", "should_contain": ["Research in Psychology"], "expect_source": True, "desc": "PSYCH Year 3"},

        # POLSCI
        {"cat": "Curriculum", "input": "1st year polsci subjects", "should_contain": ["Fundamentals of Political Science"], "expect_source": True, "desc": "POLS Year 1"},
        {"cat": "Curriculum", "input": "2nd year polsci subjects", "should_contain": ["Introduction to Comparative Politics"], "expect_source": True, "desc": "POLS Year 2"},
        {"cat": "Curriculum", "input": "3rd year polsci subjects", "should_contain": ["Qualitative and Quantitative"], "expect_source": True, "desc": "POLS Year 3"},

        # COMM
        {"cat": "Curriculum", "input": "1st year comm subjects", "should_contain": ["Communication Theory"], "expect_source": True, "desc": "COMM Year 1"},
        {"cat": "Curriculum", "input": "2nd year comm subjects", "should_contain": ["Advertising Principles"], "expect_source": True, "desc": "COMM Year 2"},
        {"cat": "Curriculum", "input": "3rd year comm subjects", "should_contain": ["Communication Management"], "expect_source": True, "desc": "COMM Year 3"},

        # ==============================================================================
        # SECTION 3: PREREQUISITE LOGIC
        # ==============================================================================
        {
            "cat": "Prereq",
            "input": "Prereq of Data Structures",
            "should_contain": ["Prerequisite", "Intermediate Programming"],
            "expect_source": True,
            "desc": "Alias Prereq (Data Structures)"
        },
        {
            "cat": "Prereq",
            "input": "Prerequisite of Math in the Modern World?",
            "should_contain": ["Prerequisite", "Math Review"],
            "expect_source": True,
            "desc": "Prerequisite of MMW (General Ed)"
        },
        {
            "cat": "Prereq",
            "input": "prereq of thesis 2?",
            "should_contain": ["Thesis/Special Project 1", "Thesis 1"], 
            "expect_source": True,
            "desc": "Thesis Sequence Prereq"
        },
        {
            "cat": "Prereq",
            "input": "pathfit 4 prereq",
            "should_contain": ["PATHFIT 2"],
            "expect_source": True,
            "desc": "PATHFIT Sequence"
        },

        # ==============================================================================
        # SECTION 4: UNITS
        # ==============================================================================
        {
            "cat": "Units",
            "input": "How many units for MMW?",
            "should_contain": ["MMW", "3 units"],
            "expect_source": True,
            "desc": "Course Units (Code)"
        },
        {
            "cat": "Units",
            "input": "cs 111 units?",
            "should_contain": ["CC 111", "units"],
            "expect_source": False,
            "desc": "Course Units (Fuzzy Code Clarification)"
        },
        {
            "cat": "Units",
            "input": "total units 1st year cs",
            "should_contain": ["Total units for", "First year", "Bachelor of Science in Computer Science"],
            "expect_source": True,
            "desc": "Program Year Total Units"
        },

        # ==============================================================================
        # SECTION 5: DEPT HEADS
        # ==============================================================================
        {
            "cat": "DeptHead",
            "input": "who is the head of computer science?",
            "should_contain": ["PROF. RC"],
            "expect_source": False, 
            "desc": "Specific Dept Head"
        },
        {
            "cat": "DeptHead",
            "input": "list department heads",
            "should_contain": ["Do you mean CAS department heads"],
            "expect_source": False,
            "desc": "List All Heads (Interactive check)"
        },
        {
            "cat": "DeptHead",
            "input": "who is the dean?",
            "should_contain": ["The current CAS Dean is DR. YSL", "check with their respective offices"],
            "should_not_contain": ["Which college dean"],
            "expect_source": False,
            "desc": "Dean Query (Direct Answer + Disclaimer)"
        },

        # ==============================================================================
        # SECTION 6: EDGE CASES
        # ==============================================================================
        {
            "cat": "Edge",
            "input": "Psychology",
            "should_contain": ["I'm a bit lost", "tell me exactly what you need"],
            "should_not_contain": ["I found a few courses", "I found **"],
            "expect_source": False,
            "desc": "Ambiguous Search (Psychology)"
        },
        {
            "cat": "Edge",
            "input": "Communication?",
            "should_contain": ["I'm a bit lost", "tell me exactly what you need"],
            "should_not_contain": ["I found a few courses", "I found **"],
            "expect_source": False,
            "desc": "Ambiguous Search (Communication)"
        },
        {
            "cat": "Edge",
            "input": "Community",
            "should_contain": ["I'm a bit lost", "tell me exactly what you need"],
            "should_not_contain": ["Communication"],
            "expect_source": False,
            "desc": "False Positive Program Match"
        },

        # ==============================================================================
        # SECTION 7: UNSUPPORTED PROGRAMS
        # ==============================================================================
        {
            "cat": "Unsupported",
            "input": "BA English Language units?",
            "should_contain": ["BA in English Language", "ask the department head"],
            "should_not_contain": ["Bachelor of Arts in Communication", "Political Science"],
            "expect_source": False,
            "desc": "Unsupported Program (BAEL Units) - Strict"
        },
        {
            "cat": "Unsupported",
            "input": "units for AB English Language",
            "should_contain": ["BA in English Language", "best bet is to ask the department head"],
            "should_not_contain": ["Bachelor of Arts in Political Science", "Approved Curriculum"], 
            "expect_source": False,
            "desc": "Unsupported Program (ABEL Units) - Strict"
        },
        {
            "cat": "Unsupported",
            "input": "curriculum for English Language",
            "should_contain": ["BA in English Language", "ask the department head"],
            "should_not_contain": ["Approved Curriculum"],
            "expect_source": False,
            "desc": "Unsupported Program (BAEL Curriculum) - Variation 1"
        },
        {
            "cat": "Unsupported",
            "input": "units for ABEL",
            "should_contain": ["BA in English Language", "ask the department head"],
            "expect_source": False,
            "desc": "Unsupported Program (ABEL Abbreviation) - Units"
        },
        {
            "cat": "Unsupported",
            "input": "BAEL curriculum",
            "should_contain": ["BA in English Language", "ask the department head"],
            "expect_source": False,
            "desc": "Unsupported Program (BAEL Abbreviation) - Curriculum"
        },
        {
            "cat": "Vague",
            "input": "english units",
            "should_contain": ["I'm a bit lost", "tell me exactly what you need"],
            "should_not_contain": ["BA in English Language", "Communication", "Political Science"],
            "expect_source": False,
            "desc": "Vague Query (Generic 'english units') - Expect Clarification"
        },

        # ==============================================================================
        # SECTION 8: NEW COMPREHENSIVE COVERAGE
        # ==============================================================================

        # --- 8.1 EXPANDED PROGRAM COVERAGE: CS ---
        {
            "cat": "CS-Expanded",
            "input": "total units for 2nd year computer science",
            "should_contain": ["Total units for Second year Bachelor of Science in Computer Science"],
            "expect_source": True,
            "desc": "CS Year 2 Total Units (Math Check)"
        },
        {
            "cat": "CS-Expanded",
            "input": "prerequisite of Automata Theory",
            "should_contain": ["Prerequisite of Automata Theory", "Numerical Analysis"],
            "expect_source": True,
            "desc": "CS Specialized Course Prereq"
        },

        # --- 8.2 EXPANDED PROGRAM COVERAGE: PSYCH ---
        {
            "cat": "PSYCH-Expanded",
            "input": "units for 1st year bs psychology",
            "should_contain": ["Total units for First year Bachelor of Science in Psychology"],
            "expect_source": True,
            "desc": "PSYCH Year 1 Units"
        },
        {
            "cat": "PSYCH-Expanded",
            "input": "what are the subjects for 2nd year psych 2nd sem?",
            "should_contain": ["Courses for Second year Bachelor of Science in Psychology, Second Trimester", "Abnormal Psychology"],
            "expect_source": True,
            "desc": "PSYCH Year 2 Sem 2 Curriculum"
        },

        # --- 8.3 EXPANDED PROGRAM COVERAGE: POLSCI ---
        {
            "cat": "POLS-Expanded",
            "input": "units for 3rd year political science",
            "should_contain": ["Total units for Third year Bachelor of Arts in Political Science"],
            "expect_source": True,
            "desc": "POLS Year 3 Units"
        },
        {
            "cat": "POLS-Expanded",
            "input": "prereq of Philippine Public Administration",
            "should_contain": ["of Philippine Public Administration", "Fundamentals of Political Science"],
            "expect_source": True,
            "desc": "POLS Specialized Course Prereq"
        },

        # --- 8.4 EXPANDED PROGRAM COVERAGE: BIO ---
        {
            "cat": "BIO-Expanded",
            "input": "2nd year biology 1st trimester subjects",
            "should_contain": ["Courses for Second year Bachelor of Science in Biology", "Microbiology", "Evolutionary Biology"],
            "expect_source": True,
            "desc": "BIO Year 2 Sem 1 Curriculum"
        },
        {
            "cat": "BIO-Expanded",
            "input": "total units 3rd year bs bio",
            "should_contain": ["Total units for Third year Bachelor of Science in Biology"],
            "expect_source": True,
            "desc": "BIO Year 3 Units"
        },

        # --- 8.5 EXPANDED PROGRAM COVERAGE: COMM ---
        {
            "cat": "COMM-Expanded",
            "input": "units for 2nd year communication",
            "should_contain": ["Total units for Second year Bachelor of Arts in Communication"],
            "expect_source": True,
            "desc": "COMM Year 2 Units"
        },
        {
            "cat": "COMM-Expanded",
            "input": "prereq of Advertising Principles",
            "should_contain": ["Advertising Principles and Practice", "no listed prerequisites"],
            "expect_source": True,
            "desc": "COMM Course Prereq Check (Direct Match)"
        },

        # --- 8.6 SPECIAL LOGIC: DIAGNOSTIC/THESIS/PATHFIT ---
        {
            "cat": "SpecialLogic",
            "input": "prereq of IENG",
            "should_contain": ["English Review", "diagnostic", "Guidance Office"],
            "expect_source": None,
            "desc": "Diagnostic Course Logic (IENG)"
        },
        {
            "cat": "SpecialLogic",
            "input": "prereq of IMAT",
            "should_contain": ["Math Review", "diagnostic", "Guidance Office"],
            "expect_source": None,
            "desc": "Diagnostic Course Logic (IMAT)"
        },
        {
            "cat": "SpecialLogic",
            "input": "overview of pathfit",
            "should_contain": ["The PATHFIT (Physical Fitness) subjects are taken in sequence", "PATHFIT 1", "PATHFIT 2"],
            "expect_source": True,
            "desc": "Generic PATHFIT Overview"
        },
        {
            "cat": "SpecialLogic",
            "input": "thesis prerequisites",
            "should_contain": ["Here are the thesis and research courses across CAS", "Thesis/Special Project"],
            "expect_source": True,
            "desc": "Generic Thesis Overview"
        },
        {
            "cat": "SpecialLogic",
            "input": "nstp prerequisites",
            "should_contain": ["National Service Training Program", "NSTP 1", "NSTP 2"],
            "expect_source": True,
            "desc": "Generic NSTP Overview"
        },

        # --- 8.7 EDGE CASES & FALLBACKS ---
        {
            "cat": "Edge-Expanded",
            "input": "5th year cs subjects",
            "should_contain": ["3-year trimester", "Registrar"],
            "expect_source": False,
            "desc": "Year Level Out of Bounds (Year 5)"
        },
        {
            "cat": "Edge-Expanded",
            "input": "who is head of mathematics department",
            "should_contain": ["The department head is DR. NL"],
            "expect_source": False,
            "desc": "Dept Head Query (Full phrasing)"
        },
        {
            "cat": "Edge-Expanded",
            "input": "units for unknownprogram",
            "should_contain": ["not quite sure which program you mean", "Computer Science"],
            "expect_source": None,
            "desc": "Unknown Program Graceful Fallback"
        },
        # ==============================================================================
        # SECTION 9: MAXIMUM UNITS / OVERLOAD LOGIC
        # ==============================================================================
        {
            "cat": "Units-Max",
            "input": "What is the maximum number of units I can take as a first year CS student?",
            "should_contain": [
                "don't have the official maximum number of units",
                "Bachelor of Science in Computer Science",
                "What I can show you instead is the usual total units",
                "check with the department head",
                "PROF. RC"
            ],
            "should_not_contain": ["maximum number of units is 25", "you can take up to"],
            "expect_source": False,
            "desc": "Max Units - Computer Science"
        },
        {
            "cat": "Units-Max",
            "input": "max units for 1st year psych?",
            "should_contain": [
                "don't have the official maximum number of units",
                "Bachelor of Science in Psychology",
                "check with the department head",
                "DR. PV"
            ],
            "expect_source": False,
            "desc": "Max Units - Psychology"
        },
        {
            "cat": "Units-Max",
            "input": "maximum number of units for 2nd year polsci?",
            "should_contain": [
                "don't have the official maximum number of units",
                "Bachelor of Arts in Political Science",
                "check with the department head",
                "DR. PV"
            ],
            "expect_source": False,
            "desc": "Max Units - Political Science"
        },
        {
            "cat": "Units-Max",
            "input": "max units allowed for 3rd year communication?",
            "should_contain": [
                "don't have the official maximum number of units",
                "Bachelor of Arts in Communication",
                "check with the department head",
                "DR. JV"
            ],
            "expect_source": False,
            "desc": "Max Units - Communication"
        },
        {
            "cat": "Units-Max",
            "input": "maximum units I can overload in 2nd year biology?",
            "should_contain": [
                "don't have the official maximum number of units",
                "Bachelor of Science in Biology",
                "check with the department head",
                "PROF. RP"
            ],
            "expect_source": False,
            "desc": "Max Units - Biology"
        },
        {
            "cat": "Units-Max",
            "input": "english language overload",
            "should_contain": [
                "BA in English Language",
                "Language and Literature",
                "DR. JV",
                "haven't been given the curriculum data"
            ],
            "should_not_contain": [
                "usual total units",
                "split per trimester",
                "I'm not sure which program"
            ],
            "expect_source": False,
            "desc": "Max Units - Unsupported BAEL (Static Response)"
        },

        # ==============================================================================
        # SECTION 10: WHEN TAKEN / YEAR LEVEL QUERIES
        # ==============================================================================
        {
            "cat": "WhenTaken",
            "input": "What year do I take Microbiology?",
            "should_contain": ["In **Bachelor of Science in Biology**", "Microbiology", "normally taken in **Second Year**"],
            "expect_source": True,
            "desc": "When taken - Unique course (Bio)"
        },
        {
            "cat": "WhenTaken",
            "input": "When do we take CC 111?",
            "should_contain": ["Bachelor of Science in Computer Science", "First year", "First Trimester"],
            "expect_source": True,
            "desc": "When taken - Course Code (CS)"
        },
        {
            "cat": "WhenTaken",
            "input": "Is Experimental Psychology a 2nd year subject?",
            "should_contain": ["Bachelor of Science in Psychology", "Second year", "First Trimester"],
            "expect_source": True,
            "desc": "When taken - Confirmation question"
        },
        {
            "cat": "WhenTaken",
            "input": "what year level is ethics?",
            "should_contain": ["appears in multiple programs", "Could you tell me which program"],
            "expect_source": None,
            "desc": "When taken - Ambiguous course (Ethics)"
        },
        {
            "cat": "WhenTaken",
            "input": "When do I take Ethics in Political Science?",
            "should_contain": ["Bachelor of Arts in Political Science", "Second year"],
            "expect_source": True,
            "desc": "When taken - Ambiguous resolved by entity"
        },
        {
            "cat": "WhenTaken",
            "input": "what year is microbiology in computer science?",
            "should_contain": ["don't see", "Microbiology", "Computer Science"],
            "expect_source": True,
            "desc": "When taken - Course not in specified program"
        },
        # ==============================================================================
        # SECTION 11: EXPANDED WHEN-TAKEN PATTERNS & ALIASES
        # ==============================================================================
        {
            "cat": "WhenTaken-Pattern",
            "input": "When should I take Data Structures?",
            "should_contain": ["In **Bachelor of Science in Computer Science**", "Data Structures and Algorithm", "normally taken in **First Year**"],
            "expect_source": True,
            "desc": "Pattern: 'When should I take' + Alias 'Data Structures'"
        },
        {
            "cat": "WhenTaken-Pattern",
            "input": "What Year is Advertising Principles?",
            "should_contain": ["In **Bachelor of Arts in Communication**", "Advertising Principles and Practice", "normally taken in **Second Year**"],
            "expect_source": True,
            "desc": "Pattern: 'What Year is' + Alias 'Advertising Principles'"
        },
        {
            "cat": "WhenTaken-Pattern",
            "input": "When do we take introduction to computing?",
            "should_contain": ["Bachelor of Science in Computer Science", "Introduction to Computing", "First Year"],
            "expect_source": True,
            "desc": "Pattern: 'When do we take' + Full Title (lowercase)"
        },
        {
            "cat": "WhenTaken-Pattern",
            "input": "In what Year is Fundamentals of Political Science usually taken?",
            "should_contain": ["Bachelor of Arts in Political Science", "First Year"],
            "expect_source": True,
            "desc": "Pattern: 'In what Year is... usually taken'"
        },
        {
            "cat": "WhenTaken-Capitalization",
            "input": "When do I take Microbiology?",
            "should_contain": ["Second Year"],
            "expect_source": True,
            "desc": "Strict Capitalization Check (Second Year)"
        },
        {
            "cat": "WhenTaken-Capitalization",
            "input": "What Year do I take Gen Zoology?",
            "should_contain": ["First Year"],
            "expect_source": True,
            "desc": "Strict Capitalization Check (First Year) + fuzzy title"
        },
        # ==============================================================================
        # SECTION 12: NEW TESTS FOR ROBUSTNESS
        # ==============================================================================
        {
            "cat": "NewCoverage",
            "input": "When is intro to computing taken?",
            "should_contain": ["First Year", "Computer Science"],
            "expect_source": True,
            "desc": "Alias 'intro to computing' check"
        },
        {
            "cat": "NewCoverage",
            "input": "prereq of general zoology",
            "should_contain": ["General Zoology", "no listed prerequisites"],
            "expect_source": True,
            "desc": "Explicit full title 'general zoology'"
        },
        {
            "cat": "NewCoverage",
            "input": "prereq of gen zoo",
            "should_contain": ["General Zoology", "no listed prerequisites"],
            "expect_source": True,
            "desc": "Short alias 'gen zoo' check (matches gen zoology alias)"
        },
        {
            "cat": "NewCoverage",
            "input": "units for botany",
            "should_contain": ["General Botany", "units"],
            "expect_source": True,
            "desc": "Single word alias 'botany'"
        },

        # ==============================================================================
        # SECTION 13: LAB SUBJECTS
        # ==============================================================================
        {
            "cat": "Labs",
            "input": "1st year cs lab subjects",
            "should_contain": ["Bachelor of Science in Computer Science", "Introduction to Computing", "CC 111", "Fundamentals of Programming", "CC 112"],
            "should_not_contain": ["CC 111 L/L", "CC 112 L/L"],
            "expect_source": True,
            "desc": "CS Year 1 Labs (L/L Code logic + Strip formatting)"
        },
        {
            "cat": "Labs",
            "input": "lab classes for biology",
            "should_contain": ["Bachelor of Science in Biology", "First Year", "General Zoology", "ZOO 101", "Second Year", "Microbiology"],
            "should_not_contain": ["ZOO 101 L/L"],
            "expect_source": True,
            "desc": "Bio All Labs (Grouped by Year - No year specified)"
        },
        {
            "cat": "Labs",
            "input": "which subjects have labs in 2nd year polsci?",
            "should_contain": ["Bachelor of Arts in Political Science", "Multimedia", "IMM L"],
            "expect_source": True,
            "desc": "PolSci Year 2 Labs (Lab Hours Logic, IMM L has no L/L but has hours)"
        },
        {
            "cat": "Labs",
            "input": "psychology lab subjects 1st year 2nd sem",
            "should_contain": ["Bachelor of Science in Psychology", "Psychological Statistics"],
            "expect_source": True,
            "desc": "Psych Year 1 Sem 2 Labs (Specific Slice)"
        },
        {
            "cat": "Labs",
            "input": "lab subjects",
            "should_contain": ["need to know which program"],
            "expect_source": None,
            "desc": "Missing Program for Lab Query"
        },
        {
            "cat": "Labs",
            "input": "communication lab classes",
            "should_contain": ["Bachelor of Arts in Communication", "Multimedia", "IMM L"],
            "expect_source": True,
            "desc": "Comm Labs (Sparse lab program check)"
        },

        # ==============================================================================
        # SECTION 14: COMPREHENSIVE LAB SUBJECTS TESTS
        # ==============================================================================
        
        # --- 14.1 Computer Science ---
        {
            "cat": "Labs-CS",
            "input": "1st year computer science lab subjects",
            "should_contain": [
                "3 units (2 lec / 1 lab)", 
                "Total units for these lab subjects",
                "includes the lecture component"
            ],
            "expect_source": True,
            "desc": "CS Year 1 Labs (Specific Year - Breakdown & Total)"
        },
        {
            "cat": "Labs-CS",
            "input": "computer science lab subjects",
            "should_contain": [
                "Total units for First Year lab subjects",
                "Total units for Second Year lab subjects",
                "Total units for Third Year lab subjects",
                "3 units (2 lec / 1 lab)"
            ],
            "should_not_contain": ["Tip: If you want a shorter list"],
            "expect_source": True,
            "desc": "CS All Labs (Grouped View - Totals per year)"
        },

        # --- 14.2 Biology ---
        {
            "cat": "Labs-Bio",
            "input": "lab subjects for biology",
            "should_contain": [
                "Total units for First Year lab subjects",
                "Total units for Second Year lab subjects",
                "Total units for Third Year lab subjects",
                "5 units (3 lec / 2 lab)" # BIO 103 check
            ],
            "expect_source": True,
            "desc": "Bio All Labs (Grouped View - Unit Logic)"
        },

        # --- 14.3 Psychology ---
        {
            "cat": "Labs-Psych",
            "input": "psychology lab subjects 2nd year",
            "should_contain": [
                "Bachelor of Science in Psychology",
                "Total units for these lab subjects",
                "Experimental Psychology",
                "5 units (3 lec / 2 lab)"
            ],
            "expect_source": True,
            "desc": "Psych Year 2 Labs (Specific Year)"
        },

        # --- 14.4 Political Science ---
        {
            "cat": "Labs-PolSci",
            "input": "lab subjects for political science",
            "should_contain": [
                "Multimedia (IMM L)",
                "Total units for Second Year lab subjects: 1"
            ],
            "expect_source": True,
            "desc": "PolSci All Labs (Sparse - Correct Total)"
        },
        {
            "cat": "Labs-PolSci",
            "input": "3rd year pol sci lab subjects",
            "should_contain": ["Bachelor of Arts in Political Science", "don't see any lab subjects listed"],
            "should_not_contain": ["Computer Science", "CS"],
            "expect_source": True,
            "desc": "PolSci Year 3 Labs (Empty Year Check)"
        },

        # --- 14.5 Communication ---
        {
            "cat": "Labs-Comm",
            "input": "lab subjects for communication",
            "should_contain": [
                "Multimedia (IMM L)",
                "1 unit"
            ],
            "expect_source": True,
            "desc": "Comm All Labs (Single unit formatting)"
        },

        # --- 14.6 Error Handling ---
        {
            "cat": "Labs-Error",
            "input": "4th year cs lab subjects",
            "should_contain": [
                "3-year trimester courses", 
                "don't have any subjects listed for a 4th year"
            ],
            "expect_source": None,
            "desc": "4th Year Lab Fallback (Natural phrasing)"
        },
        {
            "cat": "Labs-Error",
            "input": "5th year biology lab subjects",
            "should_contain": [
                "3-year trimester courses", 
                "don't have any subjects listed for a 5th year"
            ],
            "expect_source": None,
            "desc": "5th Year Lab Fallback (Natural phrasing)"
        },
        {
            "cat": "Labs-Error",
            "input": "lab subjects",
            "should_contain": ["need to know which program"],
            "expect_source": None,
            "desc": "Missing Program Prompt"
        },

        # ==============================================================================
        # SECTION 15: MAJOR / MINOR / NON-MAJOR QUERIES
        # ==============================================================================
        {
            "cat": "MajorMinor",
            "input": "What are the major subjects for 1st year Computer Science?",
            "should_contain": [
                "doesn't tag each subject as major or minor",
                "check with PROF. RC",
                "I can show you the usual subjects"
            ],
            "should_not_contain": ["Here are the major subjects"],
            "expect_source": None,
            "desc": "Major Subjects - Supported Program (CS)"
        },
        {
            "cat": "MajorMinor",
            "input": "minor subjects for BA English Language",
            "should_contain": [
                "don't have the official BA in English Language",
                "check with the Language and Literature department head, DR. JV"
            ],
            "expect_source": None,
            "desc": "Minor Subjects - Unsupported Program (BAEL)"
        },
        {
            "cat": "MajorMinor",
            "input": "non-major subjects for 4th year psychology",
            "should_contain": [
                "data only goes up to 3rd year",
                "trimester setup",
                "DR. PV"
            ],
            "expect_source": None,
            "desc": "Non-Major Subjects - 4th Year Boundary Check"
        },
        {
            "cat": "MajorMinor",
            "input": "what are the non-minor subjects?",
            "should_contain": [
                "I can help more once I know your program"
            ],
            "expect_source": None,
            "desc": "Major/Minor - Missing Program"
        },

        # ==============================================================================
        # SECTION 16: SPECIFIC BUG FIXES & ROBUSTNESS
        # ==============================================================================
        {
            "cat": "BugFix",
            "input": "prereq of medical microbiology",
            "should_contain": ["Medical Microbiology", "MED 102"],
            "should_not_contain": ["I found a few courses", "no listed prerequisites"],
            "expect_source": True,
            "desc": "Prioritize exact title 'Medical Microbiology' over 'Microbiology'"
        },
        {
            "cat": "BugFix",
            "input": "is there a prereq for fundamentals of discrete structures?",
            "should_contain": ["Fundamentals of Discrete Structures", "no listed prerequisites", "CS 121"],
            "should_not_contain": ["I found a few courses", "Advanced Discrete Structures"],
            "expect_source": True,
            "desc": "Disambiguate 'Fundamentals of Discrete...' vs 'Advanced Discrete...'"
        },
        {
            "cat": "Edge",
            "input": "is discrete structure in the curriculum?",
            "should_contain": ["Fundamentals of Discrete Structures", "Advanced Discrete Structures"],
            "should_not_contain": ["not quite sure which program"],
            "expect_source": True,
            "desc": "List multiple matches for generic existence query"
        },
        {
            "cat": "Edge-Expanded",
            "input": "BS Computer Science",
            "should_contain": ["I'm a bit lost", "tell me exactly what you need"],
            "should_not_contain": ["Calculus for Computer Science", "I found"],
            "expect_source": None,
            "desc": "Treat bare program query as vague (BS CS)"
        },
        {
            "cat": "Edge-Expanded",
            "input": "Bachelor of Science in Psychology",
            "should_contain": ["I'm a bit lost", "tell me exactly what you need"],
            "should_not_contain": ["Introduction to Psychology", "I found"],
            "expect_source": None,
            "desc": "Treat bare program query as vague (Psych)"
        },
        {
            "cat": "Edge-Expanded",
            "input": "bs psych",
            "should_contain": ["I'm a bit lost"],
            "expect_source": None,
            "desc": "Treat bare program query as vague (Abbrev)"
        }


        ]


    passed_count = 0
    total_count = len(test_cases)
    for i, t in enumerate(test_cases, 1):
        print(f"Test {i}: [{t['cat']}] {t['desc']}")
        print(f"Query: '{t['input']}'")
        try:
            st.session_state.awaiting_dept_scope = False
            st.session_state.awaiting_college_scope = False
            st.session_state.pending_intent = None
            result = route(t['input'])
            if isinstance(result, tuple):
                response_text, response_source = result
            else:
                response_text = result
                response_source = None
        except Exception as e:
            print(f"❌ ERROR: {e}")
            continue

        failures = []
        for phrase in t.get('should_contain', []):
            if phrase.lower() not in response_text.lower():
                failures.append(f"Missing text: '{phrase}'")

        for phrase in t.get('should_not_contain', []):
            if phrase.lower() in response_text.lower():
                failures.append(f"Forbidden text: '{phrase}'")
        expects_source = t.get('expect_source', False)
        if expects_source:
            if response_source != OFFICIAL_SOURCE:
                failures.append(f"Missing Official Source. Got: {response_source}")
        elif expects_source is False:
            if response_source is not None:
                failures.append(f"Unexpected Source attached. Expected None, got: {response_source}")

        if not failures:
            print("✅ PASS")
            passed_count += 1
        else:
            print("❌ FAIL")
            for f in failures:
                print(f"   - {f}")
            print(f"   Actual Text: {response_text[:150]}...")
            print(f"   Actual Source: {response_source}")
        print("-" * 60)

    print(f"\nResult: {passed_count}/{total_count} tests passed.")


if __name__ == "__main__":
    run_tests()
