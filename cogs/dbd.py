# Imports
import time

# Specific imports
import discord
from discord import app_commands, Interaction, Color, Embed, Message, File
from discord.ext import commands

# Custom imports
from entities.handlers import dbd
from entities.handlers.buttons import ResultsButtons
from entities.utils.rare import mCheckIntOrStr, mFindMostSimilarPartial, mListMostSimilarPartial, mBuildEnlistedMessage, mFindMostSimilarJelly
from log.logger import mLogInfo, mLogError

class Dbd(commands.Cog, name='dbd'):
    def __init__(self, aBot: commands.Bot) -> None:
        # Initialize cog
        super().__init__()
        self.__bot: commands.Bot = aBot
        self.__handler = dbd.DbdHandler()
        mLogInfo('Dbd cog initialized')

    def mEmbedMessage(self, aMessage: str, aTitle: str = None, aImagePath: str = None):
        _embed = Embed(title=aTitle, description=aMessage, colour=Color.blue())
        if aImagePath:
            _embed.set_image(url=f"attachment://{aImagePath}")
        return _embed

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
            aCtx (Interaction): The context of the command.
        """
        # Log command call
        mLogInfo(f'Command {aCtx.command} called by {aCtx.user}')
        await aCtx.response.defer(thinking=True)
        # Create a handler for current user
        _perks, _collage = self.__handler.mGetRandomBuild(aCtx)
        # Send message
        _formattedPerks = "  |  ".join(_perks)
        _embed = self.mEmbedMessage(_formattedPerks, aTitle=f"Random build for **{aCtx.user.name}**", aImagePath=_collage)
        _msg = await aCtx.followup.send(f'{_formattedPerks}', file=File(_collage), view=ResultsButtons(self.__handler, aCtx, _perks), wait=True)
        mLogInfo(f"Message is of type: {type(_msg)}")
        # Store message
        self.__handler.mSetLastBuildId(aCtx, _msg.id)

    @app_commands.command(name='dbdsuggest', description='Suggests a build of a given type (RUSH, SLUG, LOOP, etc.)')
    @app_commands.describe(perktype='The type of perk you want (LOOP, RUSH, INFO, SLUG, TUNNEL, SUPPORT)')
    async def mSuggestBuild(self, aCtx: Interaction, perktype: str):
        """
        This method returns a random Dead by Daylight survivor perk build based on a type of perk.

        Args:
            aCtx (Interaction): The context of the command.
            perktype (str): The type of perk.
        """
        # Log command call
        mLogInfo(f'Command {aCtx.command} called by {aCtx.user}')
        await aCtx.response.defer(thinking=True)
        # Create a handler for current user
        _perks, _collage = self.__handler.mGetSuggestion(aCtx, perktype)
        # Send message
        _formattedPerks = "  |  ".join(_perks)
        _msg = await aCtx.followup.send(f'{_formattedPerks}', file=File(_collage),
                                        view=ResultsButtons(self.__handler, aCtx, _perks), wait=True)
        # Store message
        self.__handler.mSetLastBuildId(aCtx, _msg.id)


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
        # Convert index to list of ints
        if isinstance(index, str):
            _indices = [int(i) - 1 for i in index.split(',')]
        else:
            _indices = [int(index) - 1]
        # Create a handler for current user
        try:
            _perks, _collage = self.__handler.mReplacePerks(aCtx, _indices)
            _msg = "  |  ".join(_perks)
            # Send message
            await aCtx.response.send_message(_msg, file=_collage, view=ResultsButtons(self.__handler, aCtx, _perks))
            _msg: Message = await aCtx.original_response()
            mLogInfo(f"Message is of type: {type(_msg)}")
            # Erase last build message
            try:
                _lastBuildId = self.__handler.mGetLastBuildId(aCtx)
                _lastBuildMsg = await aCtx.channel.fetch_message(_lastBuildId)
                await _lastBuildMsg.delete()
            except Exception as e:
                mLogError(f"Could not delete previous build message due to error: {str(e)}")
            # Store new build
            self.__handler.mSetLastBuildId(aCtx, _msg.id)
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
        # Convert index to list of ints
        if isinstance(index, str):
            _indices = [int(i) - 1 for i in index.split(',')]
        else:
            _indices = [int(index) - 1]
        # Add perk to blacklist
        for _index in _indices:
            _perkId = self.__handler.mGetPerkIdFromBuild(aCtx, _index)
            self.__handler.mAddPerkToBlacklist(aCtx, _perkId)
        # Replace perk in current build
        try:
            _perks, _collage = self.__handler.mReplacePerks(aCtx, _indices)
            _msg = "  |  ".join(_perks)
            # Send message
            await aCtx.response.send_message(_msg, file=_collage, view=ResultsButtons(self.__handler, aCtx, _perks))
            _response: Message = await aCtx.original_response()
            mLogInfo(f"Message is of type: {type(_response)}")
            # Erase last build message
            try:
                _lastBuildId = self.__handler.mGetLastBuildId(aCtx)
                _lastBuildMsg = await aCtx.channel.fetch_message(_lastBuildId)
                await _lastBuildMsg.delete()
            except Exception as e:
                mLogError(f"Could not delete previous build message due to error: {str(e)}")
            # Store new build
            self.__handler.mSetLastBuildId(aCtx, _response.id)
        except (ValueError, IndexError) as e:
            mLogError(e)
            await aCtx.response.send_message(f'No perks to blacklist at index {index}')
        finally:
            # Update blacklist to DB
            self.__handler.mUpdateBlacklistToDB(aCtx)

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
        _perkName = mCheckIntOrStr(index)
        if isinstance(_perkName, str):
            _perkName = mFindMostSimilarPartial(_perkName, self.__handler.mGetAllPerkNames(aCtx))
            mLogInfo(f'Most similar perk: {_perkName}')
        else:
            _perkName = self.__handler.mGetPerkIdFromBuild(aCtx, int(index) - 1)
        
        # Add perk to blacklist
        self.__handler.mAddPerkToBlacklist(aCtx, _perkName)
        await aCtx.response.send_message(f'Perk ***{_perkName}*** removed from future builds')

        # Update blacklist to DB
        self.__handler.mUpdateBlacklistToDB(aCtx)

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
        
        # Remove perk from blacklist using its id
        self.__handler.mRemovePerkFromBlacklist(aCtx, _perkName)
        await aCtx.response.send_message(f'Perk ***{_perkName}*** added back to future builds')

        # Update blacklist to DB
        self.__handler.mUpdateBlacklistToDB(aCtx)

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
    @app_commands.describe(index='The perk name or the index of the roulette where the perk is.',
                           user='Optional: check another user\'s build instead of your own.')
    async def mShowHelp(self, aCtx: Interaction, index: str, user: discord.Member = None):
        """
        This method helps in showing the info about the perks.

        Args:
            ctx (commands.Context): The context of the command.
            user (discord.Member): Optional user whose build to look up.
        """
        # Log command call
        mLogInfo(f'Command {aCtx.command} called by {aCtx.user}')

        # Determine which user's build to look up
        _targetUserId = user.id if user else None
        _targetUserName = user.display_name if user else aCtx.user.name

        # If a user was specified, check that they have an active build
        if user:
            _worker = self.__handler.mGetWorker(_targetUserId)
            if _worker is None:
                await aCtx.response.send_message(f'**{_targetUserName}** has no current build.')
                return

        # Send message
        try:
            _index = mCheckIntOrStr(index)
            mLogInfo(f'Index: {_index}')
            _perkId = ""
            if isinstance(_index, str):
                _index = mFindMostSimilarPartial(_index, self.__handler.mGetAllPerkNames(aCtx, aUserId=_targetUserId))
                mLogInfo(f'Most similar perk: {_index}')
                _perkId = _index
            else:
                _perkId = self.__handler.mGetPerkIdFromBuild(aCtx, int(_index) - 1, aUserId=_targetUserId)
                if _perkId is None:
                    await aCtx.response.send_message(f'**{_targetUserName}** has no current build.')
                    return
            _perkInfo = self.__handler.mGetHelp(aCtx, _perkId, aUserId=_targetUserId)
            _image = self.__handler.mGetPerkImage(aCtx, _perkId, aUserId=_targetUserId)
            
            if not _perkInfo:
                await aCtx.response.send_message(f"Could not find information for perk `{_perkId}`.")
                return

            _embed = Embed(title=f"--- {_perkInfo['title'].upper()} ---", color=Color.purple())
            _embed.add_field(name="Owner", value=_perkInfo['owner'], inline=True)
            _embed.add_field(name="Categories", value=_perkInfo['categories'], inline=True)
            _embed.add_field(name="Effect", value=_perkInfo['effect'], inline=False)
            if user:
                _embed.set_footer(text=f"From {_targetUserName}'s build")
            _embed.set_thumbnail(url=f"attachment://{_image.filename}")
            
            await aCtx.response.send_message(embed=_embed, file=_image)
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
        _image = self.__handler.mGetPerkImage(aCtx, _name)
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
            _perkIds.append(_perkName)

        # Set custom build
        _names, _collage = self.__handler.mSetCustomBuild(aCtx, _perkIds)
        _nameStr = "  |  ".join(_names)

        # Send message
        await aCtx.response.send_message(f'--- ***Custom build set*** ---\n{_nameStr}', file=_collage, view=ResultsButtons(self.__handler, aCtx, _perkIds))

    @app_commands.command(name='dbdmystats', description='Shows your perk usage and match statistics.')
    async def mShowUserUsageStats(self, aCtx: Interaction):
        """
        This method shows the user's perk/results statistics.

        Args:
            aCtx (Interaction): The context of the command.
        """
        # Log command call
        mLogInfo(f'Command {aCtx.command} called by {aCtx.user}')
        await aCtx.response.defer()
        # Get user stats
        _stats = self.__handler.mGetUsageStats(aCtx, aUser=aCtx.user.name)
        
        # Build embed
        _embed = Embed(title=f"--- {aCtx.user.name}'s Usage Stats ---", color=Color.blue())
        _embed.add_field(name="Total Matches", value=str(_stats["total_matches"]), inline=False)
        _embed.add_field(name="Wins", value=str(_stats["wins"]), inline=True)
        _embed.add_field(name="Losses", value=str(_stats["losses"]), inline=True)
        
        # Top 5 Perks
        _topValue = "\n".join([f"**{p['name']}**: {p['wins']} wins" for p in _stats["top_perks"]]) if _stats["top_perks"] else "No data"
        _embed.add_field(name="Top 5 Best Perks (by Wins)", value=_topValue, inline=False)
        
        # Worst 5 Perks
        _worstValue = "\n".join([f"**{p['name']}**: {p['losses']} losses" for p in _stats["worst_perks"]]) if _stats["worst_perks"] else "No data"
        _embed.add_field(name="Top 5 Worst Perks (by Losses)", value=_worstValue, inline=False)
        
        # Send message
        await aCtx.followup.send(embed=_embed)


    @app_commands.command(name='dbdstats', description='Shows the perk usage and match statistics of all players.')
    async def mShowUsageStats(self, aCtx: Interaction):
        """
        This method shows the global perk/results statistics.

        Args:
            aCtx (Interaction): The context of the command.
        """
        # Log command call
        mLogInfo(f'Command {aCtx.command} called by {aCtx.user}')
        await aCtx.response.defer()
        # Get overall stats
        _stats = self.__handler.mGetUsageStats(aCtx)
        
        # Build embed
        _embed = Embed(title="--- Global Usage Stats ---", color=Color.blue())
        _embed.add_field(name="Total Matches", value=str(_stats["total_matches"]), inline=False)
        _embed.add_field(name="Wins", value=str(_stats["wins"]), inline=True)
        _embed.add_field(name="Losses", value=str(_stats["losses"]), inline=True)
        
        # Top 5 Perks
        _topValue = "\n".join([f"**{p['name']}**: {p['wins']} wins" for p in _stats["top_perks"]]) if _stats["top_perks"] else "No data"
        _embed.add_field(name="Top 5 Best Perks (by Wins)", value=_topValue, inline=False)
        
        # Worst 5 Perks
        _worstValue = "\n".join([f"**{p['name']}**: {p['losses']} losses" for p in _stats["worst_perks"]]) if _stats["worst_perks"] else "No data"
        _embed.add_field(name="Top 5 Worst Perks (by Losses)", value=_worstValue, inline=False)
        
        # Send message
        await aCtx.followup.send(embed=_embed)

    @app_commands.command(name='dbdupdate', description='Manually triggers a perk database update from the wiki.')
    async def mManualUpdate(self, aCtx: Interaction):
        """
        This method manually triggers the DBD perk scraper and updates the
        healthcheck task timestamp to avoid overlapping with the scheduled run.

        Args:
            aCtx (Interaction): The context of the command.
        """
        # Restrict to admin
        if aCtx.user.id != 612432506813284373:
            await aCtx.response.send_message('You are not authorized to run this command.')
            return

        mLogInfo(f'Command {aCtx.command} called by {aCtx.user}')
        await aCtx.response.defer(thinking=True)

        try:
            # Run the scraper
            from entities.utils.dbdwebscraper import DBDScraper
            DBDScraper().run()

            # Update hctasks.json to reset the scheduled timer
            from datetime import datetime
            from entities.utils.files import mGetFile, mParseJsonFile, mWriteJsonFile

            _tasksFile = mGetFile('config/hctasks.json')
            _tasks = mParseJsonFile(_tasksFile)
            if 'update_dbd_perks' in _tasks:
                _tasks['update_dbd_perks']['last_run'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                mWriteJsonFile(_tasksFile, _tasks)

            await aCtx.followup.send('Perk database updated successfully!')
        except Exception as e:
            mLogError(f'Manual update failed: {e}')
            await aCtx.followup.send(f'Update failed: {e}')

    @app_commands.command(name='dbdkill', description='Turns off the bot.')
    async def mKill(self, aCtx: Interaction):
        """
        This method kills the bot.
        """
        if aCtx.user.id != 612432506813284373:
            await aCtx.response.send_message('You are not authorized to kill the bot.')
            return
        mLogInfo('Killing bot')
        self.__handler.mUpdateBlacklistToDB()
        time.sleep(10)
        await aCtx.response.send_message('Killing the bot :( Goodbye!')
        await self.__bot.close()
        exit(0)
