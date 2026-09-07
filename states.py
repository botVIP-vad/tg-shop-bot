from aiogram.fsm.state import State, StatesGroup


class AddOffer(StatesGroup):
    title = State()
    description = State()
    price = State()
    photo = State()


class MakeOrder(StatesGroup):
    contact = State()
    payment_method = State()
    hosting = State()
    comment = State()


class ContactAdmin(StatesGroup):
    message = State()


class EnterPromo(StatesGroup):
    code = State()
