import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from datetime import datetime
from sklearn.cluster import KMeans

from entities.utils.files import mGetDBDImgsDir


class DBDDataHandler:
    def __init__(self, aCsvFile: str):
        # Set paths
        self.__template_path = os.path.join(mGetDBDImgsDir(), 'templates', 'dbdperkusage_template.csv')
        self.__generation_path = os.path.join(mGetDBDImgsDir(), 'generated')
        # Set data 
        self.__csv_file = aCsvFile
        self.__df = self.mLoadAndCleanData()

    def mLoadAndCleanData(self) -> pd.DataFrame:
        # If the CSV file does not exist, use the template file to create a new CSV file
        if not os.path.exists(self.__csv_file):
            _template_df = pd.read_csv(self.__template_path)
            _template_df.to_csv(self.__csv_file, index=False)

        # Load the CSV file into a DataFrame
        _df = pd.read_csv(self.__csv_file)

        # Preprocess and clean the data
        _df = self.mPreprocessData(_df)

        return _df

    def mPreprocessData(self, aDf: pd.DataFrame) -> pd.DataFrame:
        # Calculate escape_rate and death_rate
        if aDf['games'].sum() == 0:
            aDf['escape_rate'] = 0
            aDf['death_rate'] = 0
        else:
            aDf['escape_rate'] = aDf['escapes'] / aDf['games']
            aDf['death_rate'] = aDf['deaths'] / aDf['games']

        # Set usage rate to be the number of games played by the number of games played by all perks
        if aDf['games'].sum() == 0:
            aDf['usage_rate'] = 0
        else:
            aDf['usage_rate'] = aDf['games'] / aDf['games'].sum()

        # Handle missing values (example: drop rows with any missing values)
        _df = aDf.dropna()

        # Save the updated DataFrame to the CSV file
        _df.to_csv(self.__csv_file, index=False)
        return _df

    def mGetDataFrame(self) -> pd.DataFrame:
        return self.__df

    def mIncrementColumns(self, aPerks: list[str], aColumns: list[str], aValues: list[int|float]) -> pd.DataFrame:
        # Increment the values of the specified columns for the specified perks
        for _perk, _column, _value in zip(aPerks, aColumns, aValues):
            self.__df.loc[self.__df['title'] == _perk, _column] += _value

        # Process the DataFrame to update escape_rate, death_rate, and usage_rate
        self.__df = self.mPreprocessData(self.__df)
        return self.__df

    def mRandomizeResults(self, aMin: int, aMax: int) -> pd.DataFrame:
        # Randomize the values of the specified columns
        _columns = ['escapes', 'deaths']
        for _column in _columns:
            self.__df[_column] = self.__df[_column].apply(lambda x: np.random.randint(aMin, aMax))

        # Set the values of games to be the sum of escapes and deaths
        self.__df['games'] = self.__df['escapes'] + self.__df['deaths']

        # Update the rates
        self.__df = self.mPreprocessData(self.__df)
        return self.__df

    def mResetResults(self) -> pd.DataFrame:
        # Reset the values of escapes, deaths, and games to 0
        _columns = ['escapes', 'deaths', 'games']
        for _column in _columns:
            self.__df[_column] = self.__df[_column].apply(lambda x: x * 0)

        # Update the rates
        self.__df = self.mPreprocessData(self.__df)
        return self.__df

    def mGetPerkNames(self) -> list:
        return self.__df['title'].unique().tolist()

    def mPlotClusterHeatmap(self) -> str:
        # Perform clustering on perks based on escape_rate and usage_rate
        _X = self.__df[['escape_rate', 'usage_rate']]

        # Apply KMeans clustering
        _kmeans = KMeans(n_clusters=4, random_state=42)
        _df = self.__df.copy()
        _df['cluster'] = _kmeans.fit_predict(_X)
    
        # Pivot the DataFrame to create a matrix for the heatmap
        _heatmap_data = _df.pivot_table(index='cluster', values=['escape_rate', 'usage_rate'], aggfunc='mean')

        # Plot the heatmap
        plt.figure(figsize=(10, 6))
        sns.heatmap(_heatmap_data, annot=True, cmap='coolwarm', fmt=".2f", linewidths=.5)
        plt.title('Perk Clustering Heatmap')
        plt.ylabel('Cluster')
        
        # Return as image
        _filename = datetime.now().strftime('%Y%m%d%H%M%S') + '_perk_cluster_heatmap.png'
        _filepath = os.path.join(self.__generation_path, _filename)
        plt.savefig(_filepath)
        return _filepath
