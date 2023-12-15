from prosd import db
from prosd.models import Text, TextType, ProjectContent

projectcontent_id = 95447
type = 1
header = "Ergänzung des Projektumfangs im GBeschlG 2023"
weblink = "https://dserver.bundestag.de/btd/20/068/2006879.pdf"
text_content = "Ergänzung des fest disponierten Vorhabens ABS/NBS Dresden – Leipzig (VDE 9) um das Vorhaben einer zusätzlichen Weichenverbindung zwischen Dresden Hbf und Dresden Neustadt"
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

