from prosd import db
from prosd.models import Text, TextType, ProjectContent

projectcontent_id = 95252
type = 2
header = "Info zu BVWP-Projekt"
weblink = None
text_content = "Es wird angenommen, dass der im BVWP extra erwähnte Überholbahnhof Wulfen in diesem Planfeststellungsabschnitt umgesetzt wird."
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

