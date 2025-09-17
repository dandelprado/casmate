# CASmate - NWU Laoag CAS Chatbot
This is a simple chatbot app that will be built using Streamlit for students of Northwestern University under College of Arts and Sciences. It should be able to answer course questions and other frequently asked questions about the college.

# ID conventions
- Programs refer to departments; courses refer to programs and departments; curriculum plans refer to programs and courses.

## department_id
- Pattern: `D-<DEPTCODE>` (e.g., `D-CS`, `D-SS`, `D-LL`, `D-NS`, `D-MATH`)
- Examples:
  - `D-CS` → Computer Science
  - `D-SS` → Social Sciences
  - `D-LL` → Language and Literature
  - `D-NS` → Natural Sciences
  - `D-MATH` → Mathematics
- Used in: `departments.csv` (primary key), referenced by `programs.csv` and `courses.csv`

## program_id
- Pattern: `P-<PROGRAMCODE>` (e.g., `P-CS`, `P-PSY`, `P-POLS`, `P-ENG`, `P-COMM`, `P-BIO`)
- Examples:
  - `P-CS` → Computer Science
  - `P-PSY` → Psychology
  - `P-POLS` → Political Science
  - `P-ENG` → English Language
  - `P-COMM` → Communications
  - `P-BIO` → Biology
- Used in: `programs.csv` (primary key), referenced by `courses.csv` and `curriculum_plan.csv`

## course_id
- Pattern: `<SUBJECT>-<NNN>`, where `<SUBJECT>` ∈ {CS, PSY, POLS, ENG, COMM, BIO, MATH, STAT} and `<NNN>` is a zero-padded numeric sequence
- Examples:
  - `CS-001`, `CS-002`
  - `PSY-001`
  - `POLS-001`
  - `ENG-001`, `COMM-001`
  - `BIO-001`
  - `MATH-001`, `STAT-001`
- Used in: `courses.csv` (primary key), referenced by `prerequisites.csv`, `synonyms.csv`, and `curriculum_plan.csv`

## plan_id
- Pattern: `PL-<PROGRAMCODE>-<YEAR>-<TERM>-<SEQ>`
  - `<PROGRAMCODE>` is program ID suffix (without `P-`) e.g., CS, PSY, POLS
  - `<YEAR>` is academic year level (1 to 4)
  - `<TERM>` is term code: 1–3 for trimesters (years 1 and 2) and 1–2 for semesters (years 3 and 4)
  - `<SEQ>` is a zero-padded sequence number per term, e.g., 001
- Examples:
  - `PL-CS-1-1-001`, `PL-PSY-1-3-001`, `PL-POLS-3-2-001`
- Used in: `curriculum_plan.csv` (primary key)

## faculty_id
- Pattern: `F-<NNN>`, zero-padded numeric sequence
- Examples:
  - `F-001` → Dean
  - `F-101` → Social Sciences Department Head
  - `F-201` → Computer Science Department Head
  - `F-301` → Language and Literature Department Head
  - `F-401` → Natural Sciences Department Head
  - `F-501` → Mathematics Department Head
- Used in: `faculty.csv` (primary key)

## alias
- Pattern: Free-text, human-friendly nickname for a course linked to `course_id`
- Examples:
  - `"Intro to Psych"` → `PSY-001`
  - `"Data Structures"` → `CS-002`
  - `"Academic Writing"` → `ENG-001`
- Used in: `synonyms.csv` for search and chatbot matching

## Cross-file references
- `programs.department_id` references `departments.department_id`
- `courses.program_id` references `programs.program_id`
- `courses.department_id` references `departments.department_id`
- `prerequisites.course_id` and `prerequisites.prerequisite_course_id` reference `courses.course_id`
- `curriculum_plan.program_id` references `programs.program_id`
- `curriculum_plan.course_id` references `courses.course_id`
- `synonyms.course_id` references `courses.course_id`

