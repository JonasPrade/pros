from prosd import db
from prosd.models import Text, TextType, ProjectContent

projectcontent_id = 95394
type = 2
header = "Hochleistungskorridor mit Fußnote 1"
weblink = None
text_content = "In dem Dokument des BMDV zum Hochleistungskorridor Stand 14.09.2023 wird für dieses Projekt eine mögliche Verschiebung des Projekts vorgemerkt. Hierzu findet ein Austausch mit dem Land Niedersachsen statt. Dieser wird nach Informationen mit dem Projekt ABS/NBS Hamburg – Hannover im Zusammenhang stehen."
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

