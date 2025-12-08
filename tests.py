import streamlit as st
import sys

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
    print("CASmate Logic Comprehensive Unit Tests")
    print("==========================================================\n")

    test_cases = [
        # --- 1. PROGRAM UNITS ---
        {
            "cat": "Program Units",
            "input": "How many units does 1st year Computer Science take?",
            "should_contain": ["Total units for", "First year", "Bachelor of Science in Computer Science"],
            "should_not_contain": ["I found multiple courses", "Calculus for Computer Science"],
            "desc": "Specific Program Year Units"
        },
        {
            "cat": "Program Units",
            "input": "1st year cs units?",
            "should_contain": ["Total units for", "First year"],
            "desc": "Short Program Units"
        },

        # --- 2. PROGRAM SUBJECTS ---
        {
            "cat": "Program Subjects",
            "input": "CS subjects?",
            "should_contain": ["tell me which year level"], 
            "desc": "Program Subjects (No Year) -> Expect Clarification"
        },
        {
            "cat": "Program Subjects",
            "input": "1st year cs subjects?",
            "should_contain": ["Courses for First year Bachelor of Science in Computer Science"],
            "desc": "Specific Program Year Subjects"
        },

        # --- 3. COURSE PREREQS ---
        {
            "cat": "Course Prereqs",
            "input": "Prereq of Data Structures",
            "should_contain": ["Prerequisite", "Intermediate Programming"],
            "desc": "Prerequisite of Data Structures (Alias)"
        },
        {
            "cat": "Course Prereqs",
            "input": "Prerequisite of Math in the Modern World?",
            "should_contain": ["Prerequisite", "Math Review"],
            "desc": "Prerequisite of MMW"
        },
        {
            "cat": "Course Prereqs",
            "input": "Multimedia prerequisite?",
            "should_contain": ["Prerequisite", "Living in the IT Era"],
            "desc": "Prerequisite of Multimedia (Alias check)"
        },

        # --- 4. COURSE UNITS ---
        {
            "cat": "Course Units",
            "input": "How many units for MMW?",
            "should_contain": ["MMW", "3 units"],
            "desc": "Units for Course Code"
        },
        {
            "cat": "Course Units",
            "input": "cs 111 units?",
            "should_contain": ["possible match", "CC 111", "units"],
            "should_not_contain": ["Total units for Bachelor of Science"],
            "desc": "Fuzzy Course Code vs Program Code (CS 111 -> CC 111)"
        },
        {
            "cat": "Course Units",
            "input": "CS 123 units?",
            "should_contain": ["possible match", "CC 123", "units"],
            "should_not_contain": ["Total units for Bachelor of Science"],
            "desc": "Fuzzy Course Code vs Program Code (CS 123 -> CC 123)"
        },


        # --- 5. CURRICULUM CHECK ---
        {
            "cat": "Curriculum",
            "input": "Is intermediate programming in the curriculum?",
            "should_contain": ["Yes", "in the curriculum", "Computer Science"],
            "desc": "Check if specific course is in curriculum"
        },

        # --- 6. AMBIGUITY & SEARCH ---
        {
            "cat": "Search",
            "input": "Psychology",
            "should_contain": ["Introduction to Psychology", "Social Psychology"],
            "desc": "Ambiguous Search"
        },
        {
            "cat": "Search",
            "input": "Communication?",
            "should_contain": ["Communication Theory", "Purposive Communication"],
            "desc": "Ambiguous Search"
        },
        
        # --- 7. AMBIGUOUS PROGRAM vs COURSE ---
        {
            "cat": "Fallback",
            "input": "CS units",
            "should_contain": ["Total units for", "Bachelor of Science in Computer Science"],
            "desc": "Program match 'CS units' -> Program total"
        },

        # --- 8. FALSE POSITIVE INTENT CHECK ---
        {
            "cat": "Ambiguity/Noise",
            "input": "Community",
            "should_contain": ["Community Health Psychology"],
            "should_not_contain": ["Total units for"],
            "desc": "Word 'Community' should NOT trigger Units intent"
        }
    ]

    passed_count = 0
    for i, t in enumerate(test_cases, 1):
        print(f"Test {i}: [{t['cat']}] {t['desc']}")
        print(f"Query: '{t['input']}'")
        
        try:
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
            print(f"   Actual: {response[:150]}...")
        
        print("-" * 60)

    print(f"\nResult: {passed_count}/{len(test_cases)} tests passed.")

if __name__ == "__main__":
    run_tests()
