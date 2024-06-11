import logging

from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram.utils.deep_linking import decode_payload
from aiogram.filters import CommandStart, CommandObject
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.widgets.kbd import Button, Select
from fluentogram import TranslatorRunner

from sqlalchemy import insert, delete, select, column
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio.engine import AsyncEngine

from states.states import WantSG, AccountSG, CatalogueSG, StartSG, NewUserSG
from database.tables import users, catalogue
from services.ton_services import wallet_deploy
from services.services import new_user

router = Router()

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(filename)s:%(lineno)d #%(levelname)-8s '
           '[%(asctime)s] - %(name)s - %(message)s')


'''Base Switchers'''


# Process START command
@router.message(CommandStart(deep_link_encoded=True))
async def command_start_process(
        message: Message,
        db_engine: AsyncEngine,
        dialog_manager: DialogManager,
        command: CommandObject
) -> None:
    logger.info(f'==== Message: {message.text} ====')
    logger.info(f'==== Command.args: {command.args} ====')

    # If user start bot by referral link
    if command.args:
        logger.warning(f'CommandObject is {command}')
        args = command.args
        payload = decode_payload(args)
    else:
        payload = None
    user = []
    logger.info(f'Process START command from default state by user {message.from_user.id}\nPayload: {payload}')

    # Read users data from database
    statement = (
        select("*")
        .select_from(users)
        .where(users.c.telegram_id == message.from_user.id)
    )
    async with db_engine.connect() as conn:
        user_data = await conn.execute(statement)
        logger.info(f'User data of {message.from_user.id} is executed')

    for row in user_data:
        user.append(row)
        logger.info(f'User data of {message.from_user.id} appended: {user[0]}')

    # If User is New...
    if len(user) == 0:

        logger.warning(f'{message.from_user.id} is new user')
        await new_user(db_engine,
                       message.from_user.id,
                       message.from_user.first_name,
                       message.from_user.last_name,
                       payload)
        await dialog_manager.start(state=StartSG.start,
                                   data={'user_id': message.from_user.id}
                                   )
    else:
        logger.info(f'{message.from_user.id} is old user')
        await dialog_manager.start(state=StartSG.start,
                                   data={'user_id': message.from_user.id}
                                   )


# Process START command from another states
async def go_start(
        callback: CallbackQuery,
        db_engine: AsyncEngine,
        dialog_manager: DialogManager
) -> None:
    logger.info(f'Process START command from non-default state by user {callback.from_user.id}')
    await dialog_manager.start(state=StartSG.start,
                               mode=StartMode.RESET_STACK,
                               data={'user_id': callback.from_user.id}
                               )


# Switch to Account dialogue
# Cheking if new user
async def switch_to_account(
        callback: CallbackQuery,
        db_engine: AsyncEngine,
        dialog_manager: DialogManager
):
    logger.info(f'Switch to Account dialog by user {callback.from_user.id}')
    await dialog_manager.start(state=AccountSG.account,
                               data={'user_id': callback.from_user.id}
                               )


# Switch to Catalogue dialog
async def switch_to_catalogue(
        callback: CallbackQuery,
        db_engine: AsyncEngine,
        dialog_manager: DialogManager
):
    logger.info(f'Switch to Catalogue dialog by user {callback.from_user.id}')
    await dialog_manager.start(state=CatalogueSG.catalogue)


# Switch to Want dialogue
async def switch_to_want(
        callback: CallbackQuery,
        dialog_manager: DialogManager
):
    logger.info(f'Switch to Want dialog by user {callback.from_user.id}')
    await dialog_manager.start(state=WantSG.want)


"""Catalogue Switchers"""


# NFT from catalogue selected
async def item_selection(
        callback: CallbackQuery,
        widget: Select,
        dialog_manager: DialogManager,
        item_id: str
):
    logger.info(f'User {callback.from_user.id} selected item {item_id} from catalogue')

    # Switcher to start dialog Window
    await dialog_manager.start(state=StartSG.show_item,
                               data={'item_id': item_id,
                                     'user_id': callback.from_user.id})


# Pressing on Previous Page button
async def previous_page(
        callback: CallbackQuery,
        db_engine: AsyncEngine,
        dialog_manager: DialogManager
):
    user_id = callback.from_user.id
    logger.info(f'User {user_id} pressed PREVIOUS PAGE')
    await dialog_manager.switch_to(state=StartSG.start_previous)


# Pressing on Next Page button
async def next_page(
        callback: CallbackQuery,
        db_engine: AsyncEngine,
        dialog_manager: DialogManager
):
    user_id = callback.from_user.id
    logger.info(f'User {user_id} pressed NEXT PAGE')
    await dialog_manager.switch_to(state=StartSG.start_next)