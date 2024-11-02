import pyomo.environ as pyo 


class BillSplit():
    def __init__(self):
        self.npeople = 0
        self.people = []
        self.people_dict_person_num = {}
        self.people_dict_num_person = {}

        self.expenses_dict = {}
        self.nexpenses = 0

        self.balances = {}

        self.history_expenses = []

    def add_person(self, name: str):
        if name in self.people:
            ValueError("This name was previously added.")
        self.people.append(name)
        self.people_dict_person_num[name] = self.npeople 
        self.people_dict_num_person[self.npeople] = name
        self.npeople += 1
        

    def add_expenses(self, payer: str, payed_list: list, amount: float, concept: str = ""):
        self.expenses_dict[self.nexpenses] = {
            "payer": payer,
            "payed": payed_list,
            "amount": amount,
            "concept": concept
        }
        self.nexpenses += 1

    def compute_balances(self):

        for name  in self.people:
            self.balances[name] = 0

        for n in range(self.nexpenses):
            self.balances[self.expenses_dict[n]["payer"]] += self.expenses_dict[n]["amount"] - self.expenses_dict[n]["amount"]/(len(self.expenses_dict[n]["payed"])+1)
            for payed_name in self.expenses_dict[n]["payed"]:
                self.balances[payed_name] -= self.expenses_dict[n]["amount"]/(len(self.expenses_dict[n]["payed"])+1)
        
        if sum(self.balances.values()) != 0:
            ValueError("Check the balances")


    def solve_problem(self):
        # Create the Pyomo model
        model = pyo.ConcreteModel()

        # Define binary variables for "who pays who" and continuous variables for payment amounts
        model.who_pays_who = pyo.Var(self.people, self.people, domain=pyo.Binary)
        model.how_much_who_pays_who = pyo.Var(self.people, self.people, domain=pyo.NonNegativeReals)

        # Objective: minimize the number of payments
        model.objective = pyo.Objective(
            expr=sum(model.who_pays_who[p1, p2] for p1 in self.people for p2 in self.people if p1 != p2),
            sense=pyo.minimize
        )

        # Rule for balance constraints
        def balance_rule(model, person):
            amount = self.balances[person]
            if amount < 0:
                return sum(model.how_much_who_pays_who[person, p2] for p2 in self.people if p2 != person) == abs(amount)
            elif amount > 0:
                return sum(model.how_much_who_pays_who[p1, person] for p1 in self.people if p1 != person) == amount
            else:
                return pyo.Constraint.Skip  # Skip constraint for zero balance

        model.balance_constraints = pyo.Constraint(self.people, rule=balance_rule)

        # Rule for linking constraints: require a binary indicator if payment occurs
        def linking_rule(model, p1, p2):
            if p1 != p2:
                return model.how_much_who_pays_who[p1, p2] <= model.who_pays_who[p1, p2] * 1000
            return pyo.Constraint.Skip
        model.link_constraints_upper = pyo.Constraint(self.people, self.people, rule=linking_rule)

        # Rule for ensuring minimum payment when binary indicator is set
        def min_payment_rule(model, p1, p2):
            if p1 != p2:
                return model.how_much_who_pays_who[p1, p2] >= model.who_pays_who[p1, p2] * 0.00001
            return pyo.Constraint.Skip
        
        model.link_constraints_lower = pyo.Constraint(self.people, self.people, rule=min_payment_rule)

        # Solve the model
        solver = pyo.SolverFactory('glpk')
        solution = solver.solve(model, tee=False)

        # Display results
        for p1 in self.people:
            for p2 in self.people:
                if p1 != p2 and model.who_pays_who[p1, p2].value == 1:
                    print(f"{p1} pays {p2} amount: {model.how_much_who_pays_who[p1, p2].value}")

    def reset_balances(self):
        self.history_expenses.append(self.expenses_dict)
        self.expenses_dict = {}
        self.nexpenses = 0

        self.balances = {}
