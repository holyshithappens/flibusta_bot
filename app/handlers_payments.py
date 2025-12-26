from telegram import Update
from telegram.ext import CallbackContext

from structured_logger import structured_logger


# ==== ОБРАБОТКА ПОЛУЧЕНИЯ ДОНАТОВ ====

async def pre_checkout(update: Update, context: CallbackContext):
    query = update.pre_checkout_query
    await query.answer(ok=True)


async def successful_payment(update: Update, context: CallbackContext):
    payment = update.message.successful_payment
    user = update.message.from_user
    # Отправляем благодарность
    await update.message.reply_photo(
        photo='https://gifdb.com/images/high/robocop-thank-you-for-your-cooperation-gqen0zm4lhjdh14d.webp',
        caption=f"🎉 Спасибо за донат! Вы отправили {payment.total_amount} звёзд!\n"
                f"Все средства пойдут на аренду VPS! ❤️"
    )
    # logger.log_payment(payment, user)
    structured_logger.log_payment(
        user_id=user.id,
        username=user.username or user.first_name or "Unknown",
        payment_id=payment.telegram_payment_charge_id,
        amount=payment.total_amount,
        currency=payment.currency,
        chat_type="private",
        chat_id=user.id
    )


