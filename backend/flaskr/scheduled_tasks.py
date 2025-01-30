import schedule
from app import parameters

def start_tasks():
    schedule.every(parameters.ssm_refresh_interval).minutes.do(parameters.update_from_ssm)