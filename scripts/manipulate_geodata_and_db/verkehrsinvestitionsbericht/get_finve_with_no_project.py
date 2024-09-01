from sqlalchemy import not_

from prosd.models import FinVe

finve = FinVe.query.filter(not_(FinVe.project_contents.any()))

print(finve.all())