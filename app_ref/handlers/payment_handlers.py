"""
Обработчики платежей
"""
from telegram import Update
from telegram.ext import CallbackContext
from telegram.constants import ParseMode

from ..services.user_service import UserService
from ..core.structured_logger import StructuredLogger
from ..core.logging_schema import EventType


class PaymentHandlers:
    """
    Обработчики для платежей
    
    Команды:
    - /donate - Поддержка разработчика
    - PreCheckoutQuery - Проверка перед оплатой
    - SuccessfulPayment - Обработка успешной оплаты
    """
    
    def __init__(
        self,
        user_service: UserService,
        logger: StructuredLogger
    ):
        self.user_service = user_service
        self.logger = logger
    
    async def donate_cmd(self, update: Update, context: CallbackContext) -> None:
        """Команда /donate - Поддержка разработчика"""
        user = update.effective_user
        
        if self.user_service.is_user_blocked(user.id):
            return
        
        donate_text = (
            "💰 <b>Поддержать проект</b>\n\n"
            "Если вам нравится бот и вы хотите поддержать его развитие,\n"
            "буду благодарен за любую поддержку!\n\n"
            "<b>Способы поддержки:</b>\n"
            "• ЮMoney (ЮKassa): <code>410011808872422</code>\n"
            "• Тинькофф: <code>5536 9138 1822 8888</code>\n"
            "• СБП (Сбербанк): <code>+79261234567</code>\n\n"
            "🪙 <b>Crypto:</b>\n"
            "• BTC: <code>bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh</code>\n"
            "• ETH: <code>0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb</code>\n\n"
            "💡 <b>Почему это важно:</b>\n"
            "• Оплата серверов и баз данных\n"
            "• Развитие новых функций\n"
            "• Поддержка свободного доступа к знаниям\n\n"
            "Спасибо за вашу поддержку! 🙏"
        )
        
        # TODO: Добавить кнопку для тестовой оплаты
        # from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        # keyboard = [[InlineKeyboardButton("💳 Тестовая оплата", callback_data="test_payment:100")]]
        # reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(donate_text, parse_mode=ParseMode.HTML)
        
        self.logger.log_user_action(
            EventType.DONATE_VIEW, user.id, user.username, {"action": "viewed donate"}
        )
    
    async def pre_checkout_handler(self, update: Update, context: CallbackContext) -> None:
        """Обработка pre-checkout query (как в старой архитектуре)"""
        query = update.pre_checkout_query
        await query.answer(ok=True)

    async def successful_payment_handler(self, update: Update, context: CallbackContext) -> None:
        """Обработка успешной оплаты (как в старой архитектуре)"""
        payment = update.message.successful_payment
        user = update.effective_user

        # Отправляем благодарность с GIF
        await update.message.reply_photo(
            photo='https://gifdb.com/images/high/robocop-thank-you-for-your-cooperation-gqen0zm4lhjdh14d.webp',
            caption=f"🎉 Спасибо за донат! Вы отправили {payment.total_amount} звёзд!\n"
                    f"Все средства пойдут на аренду VPS! ❤️"
        )

        # Логируем платеж
        self.logger.log_payment(
            user_id=user.id,
            username=user.username or user.first_name or "Unknown",
            payment_id=payment.telegram_payment_charge_id,
            amount=payment.total_amount,
            currency=payment.currency,
            chat_type="private",
            chat_id=user.id
        )
    
    async def create_invoice(self, update: Update, context: CallbackContext) -> None:
        """Создание инвойса (для тестирования)"""
        user = update.effective_user
        
        # TODO: Реализовать создание инвойса через Telegram Payments
        await update.message.reply_text(
            "💳 <b>Создание платежа</b>\n\n"
            "Функция в разработке...\n"
            "В будущем можно будет оплатить прямо в боте!",
            parse_mode=ParseMode.HTML
        )
        
        self.logger.log_user_action(
            EventType.DONATE_VIEW, user.id, user.username, {"action": "invoice_request"}
        )