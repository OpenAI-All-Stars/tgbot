from fastapi import FastAPI

from tgbot.entities.web import AddBalanceRequest
from tgbot.servicecs import wallet
from tgbot.web_startup import lifespan


app = FastAPI(lifespan=lifespan)


@app.post('/add-balance')
async def add_balance_handler(r: AddBalanceRequest):
    await wallet.add(r.user_id, r.microdollars)
