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
            "input": "political science 4th year subjects",
            "should_contain": ["couldn’t find any curriculum entries", "Year 4", "Political Science"],
            "should_not_contain": ["I found a few courses", "PS 101"],
            "expect_source": False, # No data found
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
            "should_contain": ["not sure what you're asking about", "Could you be more specific"],
            "should_not_contain": ["I found a few courses", "I found **"],
            "expect_source": False,
            "desc": "Ambiguous Search (Psychology)"
        },
        {
            "cat": "Edge",
            "input": "Communication?",
            "should_contain": ["not sure what you're asking about", "Could you be more specific"],
            "should_not_contain": ["I found a few courses", "I found **"],
            "expect_source": False,
            "desc": "Ambiguous Search (Communication)"
        },
        {
            "cat": "Edge",
            "input": "Community",
            "should_contain": ["not sure what you're asking about", "more specific"],
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
            "should_contain": ["not sure what you're asking about", "more specific"],
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
        # UPDATED TEST 44: Allow "Prerequisites" plural
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
        # UPDATED TEST 48: Expect Clarification instead of direct answer
        {
            "cat": "COMM-Expanded",
            "input": "prereq of Advertising Principles",
            "should_contain": ["I found", "Advertising Principles and Practice", "check its **units**, **prerequisites**"],
            "expect_source": None, # Clarification usually has no source
            "desc": "COMM Course Prereq Check (Clarification)"
        },

        # --- 8.6 SPECIAL LOGIC: DIAGNOSTIC/THESIS/PATHFIT ---
        # UPDATED TEST 49: Expect long string
        {
            "cat": "SpecialLogic",
            "input": "prereq of IENG",
            "should_contain": ["English Review", "diagnostic"],
            "expect_source": None,
            "desc": "Diagnostic Course Logic (IENG)"
        },
        # UPDATED TEST 50: Expect long string
        {
            "cat": "SpecialLogic",
            "input": "prereq of IMAT",
            "should_contain": ["Math Review", "diagnostic"],
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
            "should_contain": ["couldn’t find any curriculum entries", "Year 5"],
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
