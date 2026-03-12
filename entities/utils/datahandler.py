import os
import matplotlib.pyplot as plt
import matplotlib.animation as animation
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
    def mConvertSQLToDF(aQueryResults: tuple, aColumns: list[str]) -> pd.DataFrame:
        return pd.DataFrame(
            data=aQueryResults,
            columns=aColumns
        )

    @staticmethod
    def mPreprocessData(aDf: pd.DataFrame) -> pd.DataFrame:
        # Handle missing values (example: drop rows with any missing values)
        _df = aDf.dropna()
        return _df

    def mLoadAndCleanData(self, aQueryResults: tuple, aColumns: list[str]) -> None:
        # Convert query results to a dataframe
        self.__df = self.mConvertSQLToDF(aQueryResults, aColumns)
        # Preprocess and clean the data
        self.__df = self.mPreprocessData(self.__df)

    def mGetDataFrame(self) -> pd.DataFrame:
        return self.__df

    def mCreateBarPlot(self, aX: str, aY: str, aSavePath: str, aTitle: str = 'Generated Plot'):
        # Get data
        _df = self.__df
        _x = _df[aX]
        _y = _df[aY]
        y_positions = np.arange(len(_x))

        # Set initial plot
        plt.style.use('dark_background')
        fig, ax = plt.subplots()
        bars = ax.barh(y_positions, np.zeros(len(_y)), color='#34d8eb')

        # Customize plot
        ax.set_title(aTitle, fontsize=16, color='white')
        ax.set_xlabel(aY, fontsize=12, color='white')
        ax.set_ylabel(aX, fontsize=12, color='white')
        ax.set_yticks(y_positions)
        ax.set_yticklabels(_x, fontsize=12, color='white')
        ax.set_xlim([0, max(_y) * 1.1])
        ax.tick_params(axis='x', colors='white')
        ax.tick_params(axis='y', colors='white')
        plt.gca().invert_yaxis()
        plt.tight_layout()

        # Animation function
        def animate(frame):
            # Update the height of the bars gradually
            for i, bar in enumerate(bars):
                bar.set_width(_y[i] * (frame / 60))
            return bars

        # Animate
        ani = animation.FuncAnimation(fig, animate, frames=60, interval=20, blit=True)

        # Save image
        ani.save(aSavePath, writer='ffmpeg', fps=60)
