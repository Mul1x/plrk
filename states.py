from aiogram.fsm.state import State, StatesGroup

class DealStates(StatesGroup):
    waiting_deal_type = State()
    waiting_description = State()
    waiting_amount = State()
    waiting_currency = State()

class RequisitesStates(StatesGroup):
    waiting_value = State()

class WithdrawStates(StatesGroup):
    waiting_amount = State()

class AdminStates(StatesGroup):
    waiting_admin_id_add = State()
    waiting_admin_id_remove = State()
    waiting_broadcast_msg = State()

class PaymentStates(StatesGroup):
    waiting_payment_confirmation = State()

class SubscriptionStates(StatesGroup):
    selecting_plan = State()
