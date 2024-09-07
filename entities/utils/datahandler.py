import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from datetime import datetime
from sklearn.cluster import KMeans

from entities.utils.files import mGetDBDImgsDir


class DBDDataHandler:
    def __init__(self):
        # Set paths
        self.__generation_path = os.path.join(mGetDBDImgsDir(), 'generated')
        # Set data
        self.__df = None

    @staticmethod
    def mConvertSQLToDF(aQueryResults: tuple) -> pd.DataFrame:
        return pd.DataFrame(aQueryResults)

    @staticmethod
    def mPreprocessData(aDf: pd.DataFrame) -> pd.DataFrame:
        # Handle missing values (example: drop rows with any missing values)
        _df = aDf.dropna()
        return _df

    def mLoadAndCleanData(self, aQueryResults: tuple) -> None:
        # Convert query results to a dataframe
        self.__df = self.mConvertSQLToDF(aQueryResults)
        # Preprocess and clean the data
        self.__df = self.mPreprocessData(self.__df)

    def mGetDataFrame(self) -> pd.DataFrame:
        return self.__df

    def mCreateBarPlot(self, aX: str, aY: str, aSavePath: str, aTitle: str = 'Generated Plot'):
        # Set the plot
        plt.style.use('dark_background')
        fig, ax = plt.subplots()
        # Get data
        _df = self.mGetDataFrame()
        _x = _df[aX]
        _y = _df[aY]
        # Plot data
        _df.plot(kind='barh', x=_x, y=_y, ax=ax, color='#00ff7f')
        ax.set_title(aTitle, fontsize=16, color='white')
        ax.set_xlabel(aX, fontsize=12, color='white')
        ax.set_ylabel(aY, fontsize=12, color='white')
        ax.tick_params(axis='x', colors='white')
        ax.tick_params(axis='y', colors='white')
        plt.gca().invert_yaxis()
        plt.tight_layout()
        # Save image
        plt.savefig(aSavePath)
