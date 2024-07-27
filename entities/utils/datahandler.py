import os
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

from matplotlib import patheffects
from matplotlib.patches import FancyBboxPatch
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

def mCreateUsageGraph(aData: DataFrame, aUserId: str | None = None) -> str:
    """
    Create a bar plot to visualize the usage data.
    
    Parameters:
        aData (pd.DataFrame): Data containing 'id', 'title', 'games', 'escapes', 'deaths'.
        aTitle (str): Title of the graph.
        aUser (str): Optional user name to be included in the title.
    
    Returns:
        str: File path of the saved plot image.
    """

    # Calculate the escape rate
    aData['escape_rate'] = aData['escapes'] / aData['games']
    aData = aData.replace([float('inf'), -float('inf')], 0)  # Replace infinite values with 0
    aData = aData.fillna(0)  # Replace NaN values with 0

    # Sorting by a column to display top N rows
    _sortedData = aData.sort_values(by='escape_rate', ascending=False)

    # Plotting
    plt.figure(figsize=(16, 18))
    _barplot = sns.barplot(x='escape_rate', y='title', data=_sortedData, palette='viridis')

    # Adding data labels
    for p in _barplot.patches:
        width = p.get_width()
        plt.text(width + 0.01, p.get_y() + p.get_height() / 2,
                '{:.2f}'.format(width),
                ha='left', va='center')

    # Customizing the plot
    _barplot.set_xlabel('Count')
    _barplot.set_ylabel('Title')
    _barplot.set_title('Perk Usage')
    _barplot.invert_yaxis()  # Highest values at the top
    plt.yticks(range(len(_sortedData['title'])), _sortedData['title'])
    plt.tight_layout()

    # Rounding the bars
    for patch in _barplot.patches:
        patch.set_path_effects([
            patheffects.Normal()
        ])

    # Save the plot
    _userId = aUserId if aUserId else 'all'
    _plotPath = mMakeUserFile(_userId, 'assets/dbd/data/plots/dbdperkusage.png')
    plt.savefig(_plotPath)
    return _plotPath