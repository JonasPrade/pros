import pandas

from prosd import db
from prosd.models import Budget, FinVe

# imports a prepared excel

def add_budget(budget):
    # check if finve exists (if not: create one)
    finve_id = budget["fin_ve"]
    finve = FinVe.query.get(finve_id)
    if finve is None:
        finve = FinVe(
            id=finve_id,
            name=budget["name"],
            starting_year=budget["starting_year"],
            cost_estimate_original=budget["cost_estimate_original"],
        )
        db.session.add(finve)
        db.session.commit()
        db.session.refresh(finve)

    budget_content = budget.to_dict()
    budget_content.pop("name")

    budget_model = Budget(
        **budget_content
    )

    db.session.add(budget_model)
    db.session.commit()


filename = '../../example_data/import/haushaltsinvestitionsbericht/2024_bedarfsplan.xlsx'
df = pandas.read_excel(filename)

for index, budget in df.iterrows():
    add_budget(budget)

