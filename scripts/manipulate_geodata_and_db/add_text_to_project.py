from prosd import db
from prosd.models import Text, TextType, ProjectContent

projectcontent_id = 95377
type = 2
header = "GVFG"
weblink = ""
text_content = "Gemäß Verkehrsinvestitionsbericht wird das Projekt über Gemeindeverkehrsfinanzierungsgesetz (GVFG) gefördert."
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

