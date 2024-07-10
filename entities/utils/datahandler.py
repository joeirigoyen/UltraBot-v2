import os
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

from pandas import DataFrame
from shutil import copyfile

from entities.utils.files import mEnsureFile, mGetFile, mMakeUserFile

def mLoadCsvData(aFilePath: str) -> DataFrame:
    # Load template file
    _templatePath = mGetFile('assets/dbd/data/templates/dbdperkusage_template.csv')
    # Ensure file exists
    mEnsureFile(aFilePath, aCopy=_templatePath)
    # Load CSV data
    return pd.read_csv(aFilePath)

def mSaveCsvData(aData: DataFrame, aFilePath: str) -> None:
    aData.to_csv(aFilePath, index=False)

def mIncrementColumn(aData: DataFrame, aModifiedColumn: str, aIdColumnName: str, aId: str) -> None:
    aData.loc[aData[aIdColumnName] == aId, aModifiedColumn] += 1
    return aData

def mCreateUsageGraph(aData: DataFrame, aTitle: str, aUser: str = None, aPerk: str = None) -> str:
    """
    Create a bar plot to visualize the usage data.
    
    Parameters:
        aData (pd.DataFrame): Data containing 'id', 'title', 'games', 'escapes', 'deaths'.
        aTitle (str): Title of the graph.
        aUser (str): Optional user name to be included in the title.
    
    Returns:
        str: File path of the saved plot image.
    """
    # Set the style and context for the plot
    sns.set_theme(style="whitegrid")
    sns.set_context("talk")

    # Filter the data if a perk is specified
    if aPerk:
        aData = aData[aData['title'] == aPerk]

    # Melt the data for better visualization
    _meltedData = aData.melt(id_vars=["id", "title"], 
                            value_vars=["games", "escapes", "deaths"], 
                            var_name="Category", 
                            value_name="Count")

    # Create the bar plot
    plt.figure(figsize=(56, 16))
    _barPlot = sns.barplot(x="title", y="Count", hue="Category", data=_meltedData)

    # Add title and labels
    if aUser:
        aTitle += f" for {aUser}"
    plt.title(aTitle)
    plt.xlabel("Title")
    plt.ylabel("Count")
    
    # Rotate x labels for better readability
    plt.xticks(rotation=90)

    # Adjust the layout
    plt.tight_layout()

    # Save the plot to a file
    _prefix = aUser if aUser else 'all'
    _plotsPath = mGetFile(f'assets/dbd/data/plots/dbdperkusage_{_prefix}.png')
    _filePath = mMakeUserFile(aUser, _plotsPath)
    plt.savefig(_filePath)
    plt.close()
    
    return _filePath