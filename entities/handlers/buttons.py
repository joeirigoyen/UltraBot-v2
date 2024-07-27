# Specific imports
from discord import ButtonStyle, Interaction
from discord.ui import View, Button, button

# Custom imports
from entities.handlers.dbd import DbdHandler
from log.logger import mLogInfo
from entities.utils.datahandler import *

class ResultsButtons(View):
    def __init__(self, aHandler: DbdHandler, aOriginalInt: Interaction) -> None:
        super().__init__()
        self.__context = aOriginalInt
        self.__handler = aHandler
        self.__userId = aHandler.mGetUserId(self.__context)
        self.__pressed = False

    @button(label="Won", style=ButtonStyle.primary, custom_id="win")
    async def mRegisterWin(self, aInteraction: Interaction, aButton: Button):
        # Check if the user is the worker
        if aInteraction.user.id != self.__userId:
            await aInteraction.response.send_message("Don't interfere with builds that aren't yours.", ephemeral=True)
            return
        # Check if the user has already registered their results
        if not self.__pressed:
            self.__pressed = True
            self.__handler.mRegisterWin(aInteraction)
            mLogInfo(f"Win registered by {aInteraction.user.name}")
            await aInteraction.response.send_message("Win registered.", ephemeral=True)
        else:
            await aInteraction.response.send_message("Already registered your results.", ephemeral=True)

    @button(label="Lost", style=ButtonStyle.danger, custom_id="loss")
    async def mRegisterLoss(self, aInteraction: Interaction, aButton: Button):
        _worker = self.__handler.mCreateWorker(aInteraction)
        # Check if the user is the worker
        if aInteraction.user.id != _worker.userId:
            await aInteraction.response.send_message("Don't interfere with builds that aren't yours.", ephemeral=True)
            return
        # Check if the user has already registered their results
        if not self.__pressed:
            self.__pressed = True
            self.__handler.mRegisterLoss(aInteraction)
            mLogInfo(f"Win registered by {aInteraction.user.name}")
            await aInteraction.response.send_message("Loss registered.", ephemeral=True)
        else:
            await aInteraction.response.send_message("Already registered your results.", ephemeral=True)
