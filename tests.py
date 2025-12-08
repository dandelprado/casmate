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
    from app import route, data
except ImportError:
    print("❌ Error: Could not import 'app.py'.")
    sys.exit(1)

def run_tests():
    print("==========================================================")
    print("CASmate Comprehensive Unit Tests")
    print("==========================================================\n")

    test_cases = [
        # --- 1. CRITICAL BUGS FIX VERIFICATION ---
        {
            "cat": "BugFix",
            "input": "prereq of microbiology?",
            "should_contain": ["Microbiology", "no listed prerequisites"],
            "should_not_contain": ["I found a few courses", "Medical Microbiology"],
            "desc": "Exact Match Priority (Microbiology) - Should NOT trigger Vague Query check"
        },
        {
            "cat": "BugFix",
            "input": "medical microbiology prerequisite?",
            # Expect successful prereq answer
            "should_contain": ["Prerequisite of Medical Microbiology", "MED 102"],
            # Do NOT forbid "Microbiology" because it IS the prerequisite!
            # Only forbid the ambiguity prompt "I found a few courses"
            "should_not_contain": ["I found a few courses"],
            "desc": "Exact Match Priority (Medical Microbiology)"
        },
        {
            "cat": "BugFix",
            "input": "political science 4th year subjects",
            "should_contain": ["couldn’t find any curriculum entries", "Year 4", "Political Science"],
            "should_not_contain": ["I found a few courses", "PS 101"],
            "desc": "4th Year Missing Data Handling"
        },
        {
            "cat": "BugFix",
            "input": "2nd year 1st sem polsci subjects",
            "should_contain": ["Courses for Second year Bachelor of Arts in Political Science", "Introduction to International Relations"],
            "should_not_contain": ["First year", "Fundamentals of Political Science"],
            "desc": "Correct Year Parsing (2nd year != 1st year)"
        },

        # --- 2. COMPREHENSIVE CURRICULUM CHECK (All Programs / All Years) ---
        # CS
        {"cat": "Curriculum", "input": "1st year cs subjects", "should_contain": ["CC 111"], "desc": "CS Year 1"},
        {"cat": "Curriculum", "input": "2nd year cs subjects", "should_contain": ["CS 211"], "desc": "CS Year 2"},
        {"cat": "Curriculum", "input": "3rd year cs subjects", "should_contain": ["Software Engineering"], "desc": "CS Year 3"},
        
        # BIO
        {"cat": "Curriculum", "input": "1st year bio subjects", "should_contain": ["General Zoology"], "desc": "BIO Year 1"},
        {"cat": "Curriculum", "input": "2nd year bio subjects", "should_contain": ["Microbiology"], "desc": "BIO Year 2"},
        {"cat": "Curriculum", "input": "3rd year bio subjects", "should_contain": ["Medical Microbiology"], "desc": "BIO Year 3"},

        # PSYCH
        {"cat": "Curriculum", "input": "1st year psych subjects", "should_contain": ["Introduction to Psychology"], "desc": "PSYCH Year 1"},
        {"cat": "Curriculum", "input": "2nd year psych subjects", "should_contain": ["Experimental Psychology"], "desc": "PSYCH Year 2"},
        {"cat": "Curriculum", "input": "3rd year psych subjects", "should_contain": ["Research in Psychology"], "desc": "PSYCH Year 3"},

        # POLSCI
        {"cat": "Curriculum", "input": "1st year polsci subjects", "should_contain": ["Fundamentals of Political Science"], "desc": "POLS Year 1"},
        {"cat": "Curriculum", "input": "2nd year polsci subjects", "should_contain": ["Introduction to Comparative Politics"], "desc": "POLS Year 2"},
        {"cat": "Curriculum", "input": "3rd year polsci subjects", "should_contain": ["Qualitative and Quantitative"], "desc": "POLS Year 3"},

        # COMM
        {"cat": "Curriculum", "input": "1st year comm subjects", "should_contain": ["Communication Theory"], "desc": "COMM Year 1"},
        {"cat": "Curriculum", "input": "2nd year comm subjects", "should_contain": ["Advertising Principles"], "desc": "COMM Year 2"},
        {"cat": "Curriculum", "input": "3rd year comm subjects", "should_contain": ["Communication Management"], "desc": "COMM Year 3"},


        # --- 3. PREREQUISITES ---
        {
            "cat": "Prereq",
            "input": "Prereq of Data Structures",
            "should_contain": ["Prerequisite", "Intermediate Programming"],
            "desc": "Alias Prereq (Data Structures)"
        },
        {
            "cat": "Prereq",
            "input": "Prerequisite of Math in the Modern World?",
            "should_contain": ["Prerequisite", "Math Review"],
            "desc": "Prerequisite of MMW (General Ed)"
        },
        {
            "cat": "Prereq",
            "input": "prereq of thesis 2?",
            "should_contain": ["Thesis/Special Project 1", "Thesis 1"], 
            "desc": "Thesis Sequence Prereq"
        },
        {
            "cat": "Prereq",
            "input": "pathfit 4 prereq",
            "should_contain": ["PATHFIT 2"],
            "desc": "PATHFIT Sequence"
        },

        # --- 4. UNITS ---
        {
            "cat": "Units",
            "input": "How many units for MMW?",
            "should_contain": ["MMW", "3 units"],
            "desc": "Course Units (Code)"
        },
        {
            "cat": "Units",
            "input": "cs 111 units?",
            "should_contain": ["CC 111", "units"],
            "desc": "Course Units (Fuzzy Code)"
        },
        {
            "cat": "Units",
            "input": "total units 1st year cs",
            "should_contain": ["Total units for", "First year", "Bachelor of Science in Computer Science"],
            "desc": "Program Year Total Units"
        },

        # --- 5. DEPARTMENT HEADS ---
        {
            "cat": "DeptHead",
            "input": "who is the head of computer science?",
            "should_contain": ["PROF. RC"],
            "desc": "Specific Dept Head"
        },
        {
            "cat": "DeptHead",
            "input": "list department heads",
            "should_contain": ["Do you mean CAS department heads"],
            "desc": "List All Heads (Interactive check)"
        },
        {
            "cat": "DeptHead",
            "input": "who is the dean?",
            "should_contain": ["The current CAS Dean is DR. YSL", "check with their respective offices"],
            "should_not_contain": ["Which college dean"],
            "desc": "Dean Query (Direct Answer + Disclaimer)"
        },

        # --- 6. EDGE CASES / AMBIGUITY ---
        {
            "cat": "Edge",
            "input": "Psychology",
            "should_contain": ["not sure what you're asking about", "Could you be more specific"],
            # The fallback message contains "BS Psychology" as an example, so we allow it now.
            # We just want to ensure it doesn't give a specific answer like "I found..."
            "should_not_contain": ["I found a few courses", "I found **"],
            "desc": "Ambiguous Search (Psychology) - Should request specifics"
        },
        {
            "cat": "Edge",
            "input": "Communication?",
            "should_contain": ["not sure what you're asking about", "Could you be more specific"],
            "should_not_contain": ["I found a few courses", "I found **"],
            "desc": "Ambiguous Search (Communication) - Should request specifics"
        },
        {
            "cat": "Edge",
            "input": "Community",
            "should_contain": ["not sure what you're asking about", "more specific"],
            # Remove "asking about" from should_not_contain because it IS in the response
            "should_not_contain": ["Communication"],
            "desc": "False Positive Program Match (Community != Communication)"
        }
    ]

    passed_count = 0
    total_count = len(test_cases)
    
    for i, t in enumerate(test_cases, 1):
        print(f"Test {i}: [{t['cat']}] {t['desc']}")
        print(f"Query: '{t['input']}'")
        
        try:
            # We clear session state flags for each test to simulate a fresh turn
            st.session_state.awaiting_dept_scope = False
            st.session_state.awaiting_college_scope = False
            st.session_state.pending_intent = None
            
            response = route(t['input'])
        except Exception as e:
            print(f"❌ ERROR: {e}")
            continue

        failures = []
        for phrase in t.get('should_contain', []):
            if phrase.lower() not in response.lower():
                failures.append(f"Missing: '{phrase}'")

        for phrase in t.get('should_not_contain', []):
            if phrase.lower() in response.lower():
                failures.append(f"Forbidden: '{phrase}'")

        if not failures:
            print("✅ PASS")
            passed_count += 1
        else:
            print("❌ FAIL")
            for f in failures:
                print(f"   - {f}")
            print(f"   Actual: {response[:200]}...") # Limit output length
        
        print("-" * 60)

    print(f"\nResult: {passed_count}/{total_count} tests passed.")

if __name__ == "__main__":
    run_tests()
print("All files updated successfully.")
