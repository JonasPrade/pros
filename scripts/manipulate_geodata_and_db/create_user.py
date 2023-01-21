from prosd import db
from prosd.models import User

password = "Deutschlandtakt"
username = "germanwatch"
email = "dummy4"

user = User(
    username=username,
    password=password,
    email=email
)

db.session.add(user)
db.session.commit()
