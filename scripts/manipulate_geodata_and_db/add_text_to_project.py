from prosd import db
from prosd.models import Text, TextType, ProjectContent

projectcontent_id = 95834
type = 2
header = "Hinweis zur Finanzierungsvereinbarung"
weblink = ""
text_content = "Die Finanzierungsvereinbarung bezieht sich ausschließlich auf dem vom Bund finanzierten Anteil."
logo_url = None

text = Text(
    type=type,
    header=header,
    weblink=weblink,
    text=text_content,
    logo_url = logo_url
)

db.session.add(text)
db.session.commit()
db.session.refresh(text)

pc = ProjectContent.query.get(projectcontent_id)
pc.texts.append(text)
db.session.add(pc)
db.session.commit()

