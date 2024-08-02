from fastapi import FastAPI

from tgbot.deps import tg_bot
from tgbot.entities.web import AddBalanceRequest
from tgbot.servicecs import wallet
from tgbot.web_startup import lifespan


app = FastAPI(lifespan=lifespan)


@app.post('/add-balance')
async def add_balance_handler(r: AddBalanceRequest):
    await wallet.add(r.user_id, r.microdollars)
    await tg_bot.get().send_message(
        r.user_id,
        r.message or 'Зачислено на счёт ${:.2f}'.format(r.dollars),
    )
