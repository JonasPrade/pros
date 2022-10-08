from prosd.models import TimetableTrainGroup
from prosd.calculation_methods.bvwp import BvwpSgv, BvwpSpfv, BvwpSpnv

# train_group_code = "SA3_X 3001 E 3"
# train_group = TimetableTrainGroup.query.filter(TimetableTrainGroup.code == train_group_code).one()

train_group_id = "tg_SA3_X_x0020_3001_75905"
train_group = TimetableTrainGroup.query.get(train_group_id)

transport_mode = train_group.category.transport_mode
match transport_mode:
    case "sgv":
        tg_use = BvwpSgv(tg_id=train_group.id)
    case "spfv":
        tg_use = BvwpSpfv(tg_id=train_group.id)
    case "spnv":
        tg_use = BvwpSpnv(tg_id=train_group.id)

