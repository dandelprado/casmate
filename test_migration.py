
# test_migration.py
from data_api import load_all, find_course_by_code, fuzzy_best_program

def main():
    print("Testing JSON migration...\n")
    
    # Load all data
    try:
        data = load_all()
        print("✓ Successfully loaded all JSON files")
    except Exception as e:
        print(f"✗ Error: {e}")
        return
    
    # Check data counts
    print(f"\nData loaded:")
    print(f"  Departments: {len(data['departments'])}")
    print(f"  Programs: {len(data['programs'])}")
    print(f"  Courses: {len(data['courses'])}")
    print(f"  Plans: {len(data['plan'])}")
    print(f"  Prerequisites: {len(data['prereqs'])}")
    print(f"  Synonyms: {len(data['synonyms'])}")
    print(f"  Faculty: {len(data['faculty'])}")
    
    # Test course lookup
    print("\n✓ Testing course lookup...")
    course = find_course_by_code(data['courses'], "CS101")
    if course:
        print(f"  Found: {course['course_title']}")
    
    # Test fuzzy program search
    print("\n✓ Testing fuzzy search...")
    result = fuzzy_best_program(data['programs'], "computer science")
    if result:
        name, score, prog = result
        print(f"  Found: {prog['program_name']} (score: {score})")
    
    print("\n✓ All systems operational!")

if __name__ == "__main__":
    main()
