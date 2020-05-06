import sys
import copy
import time
from Queue import PriorityQueue

# Running script: given code can be run with the command:
# python file.py, ./path/to/init_state.txt ./output/output.txt

class Sudoku(object):
    def __init__(self, puzzle):
        self.puzzle = puzzle
		
		# all empty squares in input puzzle
        self.remaining_var_list, self.domains = self.get_variables_and_domains()         
        # neighbours of each unassigned variable
        self.neighbours = self.init_neighbours()
        self.binary_constraints = self.init_binary_constraints() # for ac3 inference heuristic
        
        self.ans = copy.deepcopy(puzzle)       
        
    def solve(self):         
        start_time = time.time()
        complete_assignment = self.backtracking_search()
        end_time = time.time()
        print(end_time - start_time)
        
        self.add_to_puzzle(complete_assignment, self.ans)
        
        return self.ans
        
    def get_variables_and_domains(self):
        var_list = list()
        domains = list()
        for i in range(0, 9):
            row = list()
            for j in range(0, 9):
                row.append(list())
            domains.append(row)
        for i in range(9):
            for j in range(9):
                if self.puzzle[i][j] == 0:
                    var_list.append((i,j))
                    domains[i][j] = list(k for k in range(1, 10))
        constraints = self.init_constraints()
        self.edit_domains(var_list, domains, constraints)
        return var_list, domains
    
    def init_constraints(self):
        constraints = list()
        for i in range(0, 27):
            new = list(k for k in range(1, 10))
            constraints.append(new)
        for row in range(9):
            for col in range(9):
                if self.puzzle[row][col] != 0:
                    constraints[row].remove(self.puzzle[row][col])
                    constraints[col+9].remove(self.puzzle[row][col])
                    if self.puzzle[row][col] in constraints[(row/3)*3+col/3+18]:
                        constraints[(row/3)*3+col/3+18].remove(self.puzzle[row][col])
        return constraints
    
    def edit_domains(self, var_list, domains, constraints):
        for var in var_list:
            x, y = var
            for val in reversed(domains[x][y]):
                if (val not in constraints[x]) or (val not in constraints[y+9]) or (val not in constraints[(x/3)*3+y/3+18]):     
                    domains[x][y].remove(val)    
        
    def init_neighbours(self):
        neighbours = dict()
        for var in self.remaining_var_list:
            x, y = var
            neighbours[var] = list()
            var_box = (x/3)*3+y/3
            for other_var in self.remaining_var_list:
                if other_var == var:
                    continue
                other_x, other_y = other_var
                other_var_box = (other_x/3)*3+other_y/3
                if other_x == x or other_y == y or var_box == other_var_box:
                    neighbours[var].append(other_var)
        return neighbours
    
    # binary constraints: tuple for each pair of neighbour
    def init_binary_constraints(self):
        lst = list()
        for var in self.remaining_var_list:
            for neighbour in self.neighbours[var]:
                lst.append((var, neighbour))
        return lst
    
    def add_to_puzzle(self, assignment, puzzle):
        for var, value in assignment.items():
            x, y = var
            puzzle[x][y] = value
        
    # Wrapper function for backtracking algorithm
    def backtracking_search(self):
        return self.recursive_backtrack({})
        
    def recursive_backtrack(self, assignment):
        if self.is_completed_assignment():
            return assignment
        var = self.select_unassigned_var() 
        #var = self.remaining_var_list[0] #use this to remove MRV
        domain = self.order_domain_val(var) 
        #domain = self.domains[var[0]][var[1]] #use this to remove LCV
        for val in domain: 
            #if self.is_consistent(val, var, assignment):
            assignment[var] = val
            self.remaining_var_list.remove(var)
            self.domains[var[0]][var[1]] = []
            is_valid, inferences = self.forward_checking(var, val) #can change to ac3 to try out
            if is_valid: 
                result = self.recursive_backtrack(assignment)
                if result != -1:
                    return result                       
            del assignment[var]                  
            self.remaining_var_list.append(var)
            self.revert_domains(inferences)   
        self.domains[var[0]][var[1]] = copy.copy(domain)
        return -1
    
    # variable ordering     
    def select_unassigned_var(self):
        most_constrained_variables = self.minimum_remaining_values()

        most_constraining_variable = most_constrained_variables[0]
        max_constraining_variables_num = self.degree(most_constraining_variable)
        for var in most_constrained_variables[1:]:
            constraining_variables_num = self.degree(var)
            if constraining_variables_num > max_constraining_variables_num:
                most_constraining_variable = var
                max_constraining_variables_num = constraining_variables_num
        return most_constraining_variable
    
    # heuristic for choosing variable: minimum remaining values (MRV)
    def minimum_remaining_values(self):
        min_size = 100
        variables = []
        for var in self.remaining_var_list:
            domain_size = len(self.domains[var[0]][var[1]])
            if domain_size != 0 and domain_size < min_size:
                min_size = domain_size
                variables = [var]
            elif domain_size != 0 and domain_size == min_size:
                variables.append(var)
        return variables

    def degree(self, var):
        count = 0
        for neighbour in self.neighbours[var]:
            if neighbour in self.remaining_var_list:
                count += 1
        return count
    
    # order domain values for a variable   
    def order_domain_val(self, var):
        return self.least_constraining_value(var)
    
    # heuristic for ordering domain values: least constraining value(LCV)
    def least_constraining_value(self, var):
        x, y = var
        if len(self.domains[x][y]) == 1:
            return self.domains[x][y] 
        return sorted(self.domains[x][y], key=(lambda value: self.count_conflicts(var, value)))
        
    def count_conflicts(self, var, value):
        total = 0
        for neighbour in self.neighbours[var]:
            if len(self.domains[neighbour[0]][neighbour[1]]) > 1 and value in self.domains[neighbour[0]][neighbour[1]]:
                total += 1
        return total
        
    def revert_domains(self, inferences):
        for entry in inferences:
            var, val = entry
            self.domains[var[0]][var[1]].append(val)
        inferences = []
    
    # To determine completed assignment, check if there are unassigned variables.
    def is_completed_assignment(self):
        if len(self.remaining_var_list) == 0:
            return True
        return False  
        
    # Checks if a value of a variable is consistent with assignment
    def is_consistent(self, value, variable, assignment):
        for var, val in assignment.items():
            if val == value and variable in self.neighbours[var]:
                return False
        return True 
    
    # heuristic for inference: arc consistency 3
    def ac3(self, variable, value):
        inferences = list()
        for neighbour in self.neighbours[variable]:
            if value in self.domains[neighbour[0]][neighbour[1]]:
                self.domains[neighbour[0]][neighbour[1]].remove(value)
                inferences.append(((neighbour[0],neighbour[1]),value))
                if self.domains[neighbour[0]][neighbour[1]] == []:
                    return False, inferences
        queue = self.binary_constraints
        
        while queue:
            var1, var2 = queue.pop(0)
            if var1 not in self.remaining_var_list or var2 not in self.remaining_var_list:
                continue
            if self.revise(var1, var2, inferences):
                if self.domains[var1[0]][var1[1]] == []:
                    return False, inferences
                for var in self.neighbours[var1]:
                    if var != var2 and var in self.remaining_var_list:
                        queue.append((var, var1))        
        return True, inferences     
        
    def revise(self, var1, var2, inferences): 
        revised = False
        for val in self.domains[var1[0]][var1[1]]:
            if not any(val != other_val for other_val in self.domains[var2[0]][var2[1]]):
                self.domains[var1[0]][var1[1]].remove(val)
                inferences.append(((var1[0],var1[1]),val))
                revised = True
        return revised
        
    # heuristic for inference: forward checking
    def forward_checking(self, variable, value):
        inferences = list()
        for neighbour in self.neighbours[variable]:
            x, y = neighbour
            if neighbour in self.remaining_var_list and value in self.domains[x][y]:
                self.domains[x][y].remove(value)  
                inferences.append(((x, y), value))
                if self.domains[x][y] == []:
                    return False, inferences
        return True, inferences                

if __name__ == "__main__":
    # STRICTLY do NOT modify the code in the main function here
    if len(sys.argv) != 3:
        print ("\nUsage: python CS3243_P2_Sudoku_XX.py input.txt output.txt\n")
        raise ValueError("Wrong number of arguments!")

    try:
        f = open(sys.argv[1], 'r')
    except IOError:
        print ("\nUsage: python CS3243_P2_Sudoku_XX.py input.txt output.txt\n")
        raise IOError("Input file not found!")

    puzzle = [[0 for i in range(9)] for j in range(9)]
    lines = f.readlines()

    i, j = 0, 0
    for line in lines:
        for number in line:
            if '0' <= number <= '9':
                puzzle[i][j] = int(number)
                j += 1
                if j == 9:
                    i += 1
                    j = 0

    sudoku = Sudoku(puzzle)
    ans = sudoku.solve()

    with open(sys.argv[2], 'a') as f:
        for i in range(9):
            for j in range(9):
                f.write(str(ans[i][j]) + " ")
            f.write("\n")
