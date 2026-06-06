from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

# Import all model files when this package is loaded
from . import coconut_product
from . import coconut_batch
from . import coconut_inspection
