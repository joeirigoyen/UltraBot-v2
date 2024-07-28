# Specific imports
from discord import app_commands, Interaction, Color, Embed, Message, Reaction, User
from discord.ext import commands

# Custom imports
from entities.handlers import dbd
from entities.handlers.dbdbuttons import ResultsButtons
from entities.utils.rare import mCheckIntOrStr, mFindMostSimilarPartial, mListMostSimilarPartial, mBuildEnlistedMessage
from log.logger import mLogInfo, mLogError

class Dbd(commands.Cog, name='dbd'):
    def __init__(self, aBot: commands.Bot) -> None:
        # Initialize cog
        super().__init__()
        self.__bot: commands.Bot = aBot
        self.__handler = dbd.DbdHandler()
        mLogInfo('Dbd cog initialized')

    @commands.Cog.listener()
    async def on_ready(self):
        mLogInfo('Dbd cog is ready')

    @app_commands.command()
    async def ping(self, aCtx: Interaction):
        yo = round(self.__bot.latency * 1000)
        embed = Embed(title="Pong! :ping_pong:", color=Color.random())
        embed.add_field(name="Latency:", value=f"{yo}ms")
        await aCtx.response.send_message(embed=embed)

    @app_commands.command(name='dbdrandom', description='Returns a random Dead by Daylight survivor perk build.')
    async def mGetRandomBuild(self, aCtx: Interaction):
        """
        This method returns a random Dead by Daylight survivor perk build.

        Args:
            ctx (Interaction): The context of the command.
        """
        # Log command call
        mLogInfo(f'Command {aCtx.command} called by {aCtx.user}')
        # Create a handler for current user
        _perks, _collage = self.__handler.mGetRandomBuild(aCtx)
        # Check if there is any build message
        _lastBuildId = self.__handler.mGetLastBuildId(aCtx)
        if _lastBuildId:
            _channel = aCtx.channel
            _message = await _channel.fetch_message(_lastBuildId)
            await _message.delete()
        # Send message
        await aCtx.response.defer()
        _formattedPerks = "  |  ".join(_perks)
        _response = await aCtx.followup.send(f'{_formattedPerks}', file=_collage, view=ResultsButtons(self.__handler, aCtx))
        self.__handler.mSetLastBuildId(aCtx, _response.id)

    @app_commands.command(name='dbdretry', description='Reruns previous roulette only at a specified index.')
    @app_commands.describe(index='The index of the roulette where the perk to rerun is.')
    async def mRetryBuild(self, aCtx: Interaction, index: str):
        """
        This method reruns the previous roulette at the specified index.

        Args:
            ctx (Interaction): The context of the command.
            index (str): The index of the roulette to rerun.
        """
        # Log command call
        mLogInfo(f'Command {aCtx.command} called by {aCtx.user}')
        # Create a handler for current user
        try:
            _perks, _collage = self.__handler.mReplacePerk(aCtx, int(index) - 1)
            _msg = "  |  ".join(_perks)
            # Check if there is any build message
            _lastBuildId = self.__handler.mGetLastBuildId(aCtx)
            if _lastBuildId:
                _channel = aCtx.channel
                _message = await _channel.fetch_message(_lastBuildId)
                await _message.delete()
            # Send message
            _response = await aCtx.response.send_message(_msg, file=_collage, view=ResultsButtons(self.__handler, aCtx))
            _message = await _response.original_message()
            self.__handler.mSetLastBuildId(aCtx, _message.id)
        except (ValueError, IndexError) as e:
            mLogError(e)
            await aCtx.response.send_message(f'No perks to retry at index {index}')

    @mRetryBuild.autocomplete("index")
    async def mRetryBuildAutoComplete(self, aCtx: Interaction, aCurrInput: str) -> list[app_commands.Choice[int]]:
        # Show indices if no input
        if aCurrInput == "":
            return [app_commands.Choice(name=i, value=i) for i in ['1', '2', '3', '4']]
        return [app_commands.Choice(name=aCurrInput, value=aCurrInput)]

    @app_commands.command(name='dbdban', description='Reruns roulette and removes the perk from your current and future builds.')
    @app_commands.describe(index='The index of the roulette where the perk to remove is.')
    async def mRemovePerkAndRerun(self, aCtx: Interaction, index: str):
        """
        This method removes the perk from the user's future builds.

        Args:
            ctx (commands.Context): The context of the command.
            perk (str): The perk to remove.
        """
        # Log command call
        mLogInfo(f'Command {aCtx.command} called by {aCtx.user}')
        # Add perk to blacklist
        _perkId = self.__handler.mGetPerkIdFromBuild(aCtx, int(index) - 1)
        self.__handler.mAddPerkToBlacklist(aCtx, _perkId)
        # Replace perk in current build
        try:
            _perks, _collage = self.__handler.mReplacePerk(aCtx, int(index) - 1)
            _msg = "  |  ".join(_perks)
            # Check if there is any build message
            _lastBuildId = self.__handler.mGetLastBuildId(aCtx)
            if _lastBuildId:
                _channel = aCtx.channel
                _message = await _channel.fetch_message(_lastBuildId)
                await _message.delete()
            # Send message
            _response = await aCtx.response.send_message(_msg, file=_collage, view=ResultsButtons(self.__handler, aCtx))
            _message = await _response.original_message()
            self.__handler.mSetLastBuildId(aCtx, _message.id)
        except (ValueError, IndexError) as e:
            mLogError(e)
            await aCtx.response.send_message(f'No perks to blacklist at index {index}')

    @mRemovePerkAndRerun.autocomplete("index")
    async def mRemovePerkAndRerunAutoComplete(self, aCtx: Interaction, aCurrInput: str) -> list[app_commands.Choice[int]]:
        # Show indices if no input
        if aCurrInput == "":
            return [app_commands.Choice(name=i, value=i) for i in ['1', '2', '3', '4']]
        return [app_commands.Choice(name=aCurrInput, value=aCurrInput)]

    @app_commands.command(name='dbdbye', description='Removes the perk from your future builds.')
    @app_commands.describe(index='The perk name or the index of the roulette where the perk to remove is.')
    async def mRemovePerk(self, aCtx: Interaction, index: str):
        """
        This method removes the perk from the user's future builds.

        Args:
            ctx (commands.Context): The context of the command.
            perk (str): The perk to remove.
        """
        # Log command call
        mLogInfo(f'Command {aCtx.command} called by {aCtx.user}')
        
        # Check if perk name is given or index
        _perkId = ""
        _perkName = mCheckIntOrStr(index)
        if isinstance(_perkName, str):
            _perkName = mFindMostSimilarPartial(_perkName, self.__handler.mGetAllPerkNames(aCtx))
            mLogInfo(f'Most similar perk: {_perkName}')
            _perkId = self.__handler.mGetPerkIdByName(aCtx, _perkName)
        else:
            _perkId = self.__handler.mGetPerkIdFromBuild(aCtx, int(index) - 1)
            _perkName = self.__handler.mGetPerkName(aCtx, _perkId)
        
        # Add perk to blacklist
        self.__handler.mAddPerkToBlacklist(aCtx, _perkId)
        await aCtx.response.send_message(f'Perk ***{_perkName}*** removed from future builds')

    @mRemovePerk.autocomplete("index")
    async def mRemovePerkAutoComplete(self, aCtx: Interaction, aCurrInput: str) -> list[app_commands.Choice[int|str]]:
        # Show indices if no input
        if aCurrInput == "":
            return [app_commands.Choice(name=i, value=i) for i in ['1', '2', '3', '4']]
        # Show perks that contain the input
        _choiceList = mListMostSimilarPartial(aCurrInput, self.__handler.mGetWhitelistedPerkNames(aCtx))
        _choices = [app_commands.Choice(name=_choice, value=_choice) for _choice in _choiceList if aCurrInput.lower() in _choice.lower()]
        if len(_choices) == 0:
            return [app_commands.Choice(name=aCurrInput, value=aCurrInput)]
        return _choices

    @app_commands.command(name='dbdadd', description='Adds back a perk back to your future builds.')
    @app_commands.describe(perk='The name of the perk to add back to your future builds.')
    async def mRemoveFromBlackList(self, aCtx: Interaction, perk: str):
        """
        This method adds back the perk to the user's future builds.

        Args:
            ctx (commands.Context): The context of the command.
            perk (str): The perk to add.
        """
        # Log command call
        mLogInfo(f'Command {aCtx.command} called by {aCtx.user}')
        
        # Check if perk name is given or index
        _perkName = mFindMostSimilarPartial(perk, self.__handler.mGetAllPerkNames(aCtx))
        mLogInfo(f'Most similar perk: {_perkName}')
        _perkId = self.__handler.mGetPerkIdByName(aCtx, _perkName)
        
        # Remove perk from blacklist using its id
        self.__handler.mRemovePerkFromBlacklist(aCtx, _perkId)
        await aCtx.response.send_message(f'Perk ***{_perkName}*** added back to future builds')

    @mRemoveFromBlackList.autocomplete("perk")
    async def mAddPerkAutoComplete(self, aCtx: Interaction, aCurrInput: str) -> list[app_commands.Choice[int|str]]:
        # Show first 20 perks if no input
        if aCurrInput == "":
            _blacklistedPerks = self.__handler.mGetBlacklistedPerkNames(aCtx)
            if len(_blacklistedPerks) > 20:
                return [app_commands.Choice(name=_perk, value=_perk) for _perk in _blacklistedPerks[:20]]
            return [app_commands.Choice(name=_perk, value=_perk) for _perk in _blacklistedPerks]
        
        # Show perks that contain the input
        _choiceList = mListMostSimilarPartial(aCurrInput, self.__handler.mGetBlacklistedPerkNames(aCtx))
        _choices = [app_commands.Choice(name=_choice, value=_choice) for _choice in _choiceList if aCurrInput.lower() in _choice.lower()]
        if len(_choices) == 0:
            return [app_commands.Choice(name=aCurrInput, value=aCurrInput)]
        return _choices

    @app_commands.command(name='dbdbanlist', description='Shows your blacklisted Dead by Daylight perks.')
    async def mGetBlackList(self, aCtx: Interaction):
        """
        This method shows the user's blacklisted perks.

        Args:
            ctx (commands.Context): The context of the command.
        """
        # Log command call
        mLogInfo(f'Command {aCtx.command} called by {aCtx.user}')
        # Get blacklisted perks
        _perks = self.__handler.mGetBlacklistedPerkNames(aCtx)
        _blacklistMsg = mBuildEnlistedMessage(f'--- *** {aCtx.user.name}\'s Blacklisted Perks*** ---', _perks)
        # Send message
        await aCtx.response.send_message(_blacklistMsg)

    @app_commands.command(name='dbdhelp', description='Shows the available info for the Dead by Daylight perks.')
    @app_commands.describe(index='The perk name or the index of the roulette where the perk is.')
    async def mShowHelp(self, aCtx: Interaction, index: str):
        """
        This method helps in showing the info about the perks.

        Args:
            ctx (commands.Context): The context of the command.
        """
        # Log command call
        mLogInfo(f'Command {aCtx.command} called by {aCtx.user}')
        # Send message
        try:
            _index = mCheckIntOrStr(index)
            mLogInfo(f'Index: {_index}')
            _perkId = ""
            if isinstance(_index, str):
                _index = mFindMostSimilarPartial(_index, self.__handler.mGetAllPerkNames(aCtx))
                mLogInfo(f'Most similar perk: {_index}')
                _perkId = self.__handler.mGetPerkIdByName(aCtx, _index)
            else:
                _perkId = self.__handler.mGetPerkIdFromBuild(aCtx, int(_index) - 1)
            _msg = self.__handler.mGetHelp(aCtx, _perkId)
            _image = self.__handler.mGetPerkImage(aCtx, _perkId)
            await aCtx.response.send_message(_msg, file=_image)
        except Exception as e:
            mLogError(e)
            await aCtx.response.send_message('Error showing help. Please try again later.')

    @mShowHelp.autocomplete("index")
    async def mHelpAutoComplete(self, aCtx: Interaction, aCurrInput: str) -> list[app_commands.Choice[int|str]]:
        # Show indices if no input
        if aCurrInput == "":
            return [app_commands.Choice(name=i, value=i) for i in ['1', '2', '3', '4']]
        # Show perks that contain the input
        _choiceList = mListMostSimilarPartial(aCurrInput, self.__handler.mGetAllPerkNames(aCtx))
        _choices = [app_commands.Choice(name=_choice, value=_choice) for _choice in _choiceList if aCurrInput.lower() in _choice.lower()]
        if len(_choices) == 0:
            return [app_commands.Choice(name=aCurrInput, value=aCurrInput)]
        return _choices

    @app_commands.command(name='dbdimg', description='Shows the image of a given Dead by Daylight perk.')
    @app_commands.describe(name='The name of the perk you want to see.')
    async def mShowImage(self, aCtx: Interaction, name: str):
        """
        This method shows the image of a given perk.

        Args:
            ctx (commands.Context): The context of the command.
            perk (str): The perk to show the image of.
        """
        # Log command call
        mLogInfo(f'Command {aCtx.command} called by {aCtx.user}')

        # Get most similar perk or the same perk that was requested
        mLogInfo(f'Getting image for perk {name}')
        _allPerks = self.__handler.mGetAllPerkNames(aCtx)
        _name = name
        if _name not in set(_allPerks):
            mLogInfo(f'Perk {name} not found. Getting most similar perk')
            _name = mFindMostSimilarPartial(name, _allPerks)
            mLogInfo(f'Most similar perk: {_name}')
        
        # Send message
        _id = self.__handler.mGetPerkIdByName(aCtx, _name)
        _image = self.__handler.mGetPerkImage(aCtx, _id)
        await aCtx.response.send_message(f"--- *** {_name} *** ---", file=_image)

    @mShowImage.autocomplete("name")
    async def mShowImageAutoComplete(self, aCtx: Interaction, aCurrInput: str) -> list[app_commands.Choice[int|str]]:
        # Show first 20 perks if no input
        if aCurrInput == "":
            return [app_commands.Choice(name=_perk, value=_perk) for _perk in self.__handler.mGetAllPerkNames(aCtx)[:20]]
        # Show perks that contain the input
        _choiceList = mListMostSimilarPartial(aCurrInput, self.__handler.mGetAllPerkNames(aCtx))
        _choices = [app_commands.Choice(name=_choice, value=_choice) for _choice in _choiceList if aCurrInput.lower() in _choice.lower()]
        if len(_choices) == 0:
            return [app_commands.Choice(name=aCurrInput, value=aCurrInput)]
        return _choices

    @app_commands.command(name='dbdwin', description='Registers a won game with your current build.')
    async def mRegisterWin(self, aCtx: Interaction):
        """
        This method registers a win for the user.

        Args:
            ctx (commands.Context): The context of the command.
        """
        # Log command call
        mLogInfo(f'Command {aCtx.command} called by {aCtx.user}')
        # Register win
        self.__handler.mRegisterWin(aCtx)
        # Send message
        await aCtx.response.send_message('Win registered')

    @app_commands.command(name='dbdloss', description='Registers a lost game with your current build.')
    async def mRegisterLoss(self, aCtx: Interaction):
        """
        This method registers a loss for the user.

        Args:
            ctx (commands.Context): The context of the command.
        """
        # Log command call
        mLogInfo(f'Command {aCtx.command} called by {aCtx.user}')
        # Register win
        self.__handler.mRegisterLoss(aCtx)
        # Send message
        await aCtx.response.send_message('Loss registered')

    @app_commands.command(name='dbdset', description='Sets a custom build.')
    @app_commands.describe(perks='The names of the perks you want to see (split by commas).')
    async def mSetCustomBuild(self, aCtx: Interaction, *, perks: str):
        """
        This method sets a custom build for the user.

        Args:
            ctx (commands.Context): The context of the command.
            perks (str): The perks to set.
        """
        # Log command call
        mLogInfo(f'Command {aCtx.command} called by {aCtx.user}')

        # Get correct name for each perk
        _allPerks = self.__handler.mGetAllPerkNames(aCtx)
        _userPerks = perks.split(',')
        _perkIds = []
        
        if len(_userPerks) != 4:
            mLogError('Invalid number of perks')
            await aCtx.response.send_message('Invalid number of perks. Please provide 4 perks.')
        
        for _perkName in _userPerks:
            mLogInfo(f'Processing specified perk: {_perkName}')
            _perkName = mFindMostSimilarPartial(_perkName, _allPerks)
            # Get perk id
            _perkId = self.__handler.mGetPerkIdByName(aCtx, _perkName)
            _perkIds.append(_perkId)

        # Set custom build
        _names, _collage = self.__handler.mSetCustomBuild(aCtx, _perkIds)
        _nameStr = "  |  ".join(_names)

        # Send message
        await aCtx.response.send_message(f'--- ***Custom build set*** ---\n{_nameStr}', file=_collage, view=ResultsButtons(self.__handler))

    @app_commands.command(name='dbdmyusage', description='Resets your custom build.')
    async def mShowUserUsageGraph(self, aCtx: Interaction):
        """
        This method shows the user's perk/results graph.

        Args:
            ctx (commands.Context): The context of the command.
        """
        # Log command call
        mLogInfo(f'Command {aCtx.command} called by {aCtx.user}')
        # Get user graph
        _graph = self.__handler.mGetUsageGraph(aCtx, aUser=True)
        # Send message
        await aCtx.response.send_message(file=_graph)

    @app_commands.command(name='dbdusage', description='Shows the perk/results graph of all players.')
    async def mShowUsageGraph(self, aCtx: Interaction):
        """
        This method shows the user's perk/results graph.

        Args:
            ctx (commands.Context): The context of the command.
        """
        # Log command call
        mLogInfo(f'Command {aCtx.command} called by {aCtx.user}')
        # Get user graph
        _graph = self.__handler.mGetUsageGraph(aCtx)
        # Send message
        await aCtx.response.send_message(file=_graph)

    @app_commands.command(name='dbdrandomizedata', description='Randomizes CSV data.')
    async def mRandomizeData(self, aCtx: Interaction):
        """
        This method randomizes the CSV data.

        Args:
            ctx (commands.Context): The context of the command.
        """
        # Log command call
        mLogInfo(f'Command {aCtx.command} called by {aCtx.user}')
        # Randomize data
        self.__handler.mRandomizeCSVData(aCtx)
        # Send message
        await aCtx.response.send_message('Data randomized')

    @app_commands.command(name='dbdresetdata', description='Resets CSV data.')
    async def mResetData(self, aCtx: Interaction):
        """
        This method resets the CSV data.

        Args:
            ctx (commands.Context): The context of the command.
        """
        # Log command call
        mLogInfo(f'Command {aCtx.command} called by {aCtx.user}')
        # Reset data
        self.__handler.mResetCSVData(aCtx)
        # Send message
        await aCtx.response.send_message('Data reset to zeroes')