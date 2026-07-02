from fastapi.templating import Jinja2Templates

from app.config import settings
from app.messages import get_flash_message

templates = Jinja2Templates(directory=settings.templates_dir)
templates.env.globals["app_name"] = settings.app_name
templates.env.globals["bootstrap_css"] = settings.bootstrap_css
templates.env.globals["bootstrap_js"] = settings.bootstrap_js
templates.env.globals["get_flash_message"] = get_flash_message
