from data_api import load_all, fuzzy_best_program

data = load_all()
programs = data["programs"]

print(fuzzy_best_program(programs, "BSCS"))
print(fuzzy_best_program(programs, "BSCS units?"))
print(fuzzy_best_program(programs, "BS Computer Science"))
print(fuzzy_best_program(programs, "Computer Science"))
